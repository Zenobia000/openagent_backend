"""
Tests for Phase 6: Management API endpoints, health check expansion, extension metrics.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.core.metrics import CognitiveMetrics


# ============================================================
# 6.3 Extension Metrics Tests
# ============================================================

class TestExtensionMetrics:
    def test_initial_extension_metrics(self):
        m = CognitiveMetrics()
        ext = m.get_extension_metrics()
        assert ext["mcp"]["tool_calls"] == 0
        assert ext["mcp"]["tool_errors"] == 0
        assert ext["mcp"]["avg_latency_ms"] == 0.0
        assert ext["a2a"]["tasks_sent"] == 0
        assert ext["a2a"]["tasks_completed"] == 0
        assert ext["a2a"]["tasks_failed"] == 0
        assert ext["a2a"]["avg_latency_ms"] == 0.0

    def test_record_mcp_call_success(self):
        m = CognitiveMetrics()
        m.record_mcp_call(latency_ms=50.0, success=True)
        m.record_mcp_call(latency_ms=100.0, success=True)
        ext = m.get_extension_metrics()
        assert ext["mcp"]["tool_calls"] == 2
        assert ext["mcp"]["tool_errors"] == 0
        assert ext["mcp"]["avg_latency_ms"] == 75.0

    def test_record_mcp_call_failure(self):
        m = CognitiveMetrics()
        m.record_mcp_call(latency_ms=200.0, success=False)
        ext = m.get_extension_metrics()
        assert ext["mcp"]["tool_calls"] == 1
        assert ext["mcp"]["tool_errors"] == 1

    def test_record_a2a_task_success(self):
        m = CognitiveMetrics()
        m.record_a2a_task(latency_ms=300.0, success=True)
        ext = m.get_extension_metrics()
        assert ext["a2a"]["tasks_sent"] == 1
        assert ext["a2a"]["tasks_completed"] == 1
        assert ext["a2a"]["tasks_failed"] == 0
        assert ext["a2a"]["avg_latency_ms"] == 300.0

    def test_record_a2a_task_failure(self):
        m = CognitiveMetrics()
        m.record_a2a_task(latency_ms=500.0, success=False)
        ext = m.get_extension_metrics()
        assert ext["a2a"]["tasks_sent"] == 1
        assert ext["a2a"]["tasks_completed"] == 0
        assert ext["a2a"]["tasks_failed"] == 1

    def test_reset_clears_extension_metrics(self):
        m = CognitiveMetrics()
        m.record_mcp_call(latency_ms=100.0)
        m.record_a2a_task(latency_ms=200.0)
        m.reset()
        ext = m.get_extension_metrics()
        assert ext["mcp"]["tool_calls"] == 0
        assert ext["a2a"]["tasks_sent"] == 0

    def test_extension_metrics_do_not_affect_cognitive(self):
        m = CognitiveMetrics()
        m.record_mcp_call(latency_ms=100.0)
        m.record_a2a_task(latency_ms=200.0)
        summary = m.get_summary()
        assert summary["total_requests"] == 0


# ============================================================
# 6.1 & 6.2 API Endpoint Tests (unit-level with mocked engine)
# ============================================================

@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.initialized = True
    engine._mcp_client = MagicMock()
    engine._mcp_client.connected_servers = ["weather", "translator"]
    engine._mcp_client.total_tools = 5
    engine._mcp_client.list_tools = AsyncMock(return_value=[
        {"server_name": "weather", "name": "get_weather", "description": "Get weather"},
    ])
    engine._a2a_client = MagicMock()
    engine._a2a_client.connected_agents = ["stock-analyst"]
    engine._a2a_client.total_skills = 3
    engine._a2a_client.list_agents = AsyncMock(return_value=[
        {"name": "stock-analyst", "url": "http://localhost:9001", "connected": True},
    ])
    engine._package_manager = MagicMock()
    engine._package_manager.list_packages = AsyncMock(return_value=[
        {"id": "weather", "name": "Weather", "version": "1.0.0", "type": "mcp-server", "status": "running", "error": None, "path": "/packages/weather"},
    ])
    engine._package_manager.start_package = AsyncMock()
    engine._package_manager.stop_package = AsyncMock()
    engine._metrics = CognitiveMetrics()
    engine.metrics = {"total_requests": 0}
    return engine


@pytest.fixture
def app(mock_engine):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from api.routes import create_app
    return create_app(engine=mock_engine)


@pytest.fixture
def auth_header():
    from auth.jwt import encode_token, UserRole
    token = encode_token(user_id="test-user", username="tester", role=UserRole.USER)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestHealthCheckExpanded:
    async def test_health_includes_mcp_a2a(self, app, mock_engine):
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["engine"] == "initialized"
            assert data["mcp"]["connected_servers"] == 2
            assert data["mcp"]["available_tools"] == 5
            assert data["a2a"]["connected_agents"] == 1
            assert data["a2a"]["available_skills"] == 3
            assert data["packages"]["total"] == 1
            assert data["packages"]["running"] == 1

    async def test_health_no_mcp_a2a(self, app, mock_engine):
        mock_engine._mcp_client = None
        mock_engine._a2a_client = None
        mock_engine._package_manager = None
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert "mcp" not in data
            assert "a2a" not in data
            assert "packages" not in data


@pytest.mark.asyncio
class TestMCPEndpoints:
    async def test_list_mcp_servers(self, app, auth_header):
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/mcp/servers", headers=auth_header)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["servers"]) == 2

    async def test_list_mcp_tools(self, app, auth_header):
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/mcp/tools", headers=auth_header)
            assert resp.status_code == 200
            assert len(resp.json()["tools"]) == 1

    async def test_mcp_servers_no_client(self, app, mock_engine, auth_header):
        mock_engine._mcp_client = None
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/mcp/servers", headers=auth_header)
            assert resp.json() == {"servers": []}


@pytest.mark.asyncio
class TestA2AEndpoints:
    async def test_list_a2a_agents(self, app, auth_header):
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/a2a/agents", headers=auth_header)
            assert resp.status_code == 200
            assert len(resp.json()["agents"]) == 1

    async def test_a2a_agents_no_client(self, app, mock_engine, auth_header):
        mock_engine._a2a_client = None
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/a2a/agents", headers=auth_header)
            assert resp.json() == {"agents": []}


@pytest.mark.asyncio
class TestPackageEndpoints:
    async def test_list_packages(self, app, auth_header):
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/packages", headers=auth_header)
            assert resp.status_code == 200
            assert len(resp.json()["packages"]) == 1

    async def test_start_package(self, app, auth_header):
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/packages/weather/start", headers=auth_header)
            assert resp.status_code == 200
            assert resp.json()["status"] == "started"

    async def test_stop_package(self, app, auth_header):
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/packages/weather/stop", headers=auth_header)
            assert resp.status_code == 200
            assert resp.json()["status"] == "stopped"

    async def test_start_nonexistent_package(self, app, mock_engine, auth_header):
        mock_engine._package_manager.start_package = AsyncMock(side_effect=KeyError("not found"))
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/packages/nope/start", headers=auth_header)
            assert resp.status_code == 404

    async def test_packages_no_manager(self, app, mock_engine, auth_header):
        mock_engine._package_manager = None
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/packages", headers=auth_header)
            assert resp.json() == {"packages": []}

    async def test_start_no_manager(self, app, mock_engine, auth_header):
        mock_engine._package_manager = None
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/packages/weather/start", headers=auth_header)
            assert resp.status_code == 503


@pytest.mark.asyncio
class TestMetricsEndpoint:
    async def test_metrics_includes_extensions(self, app, auth_header, mock_engine):
        mock_engine._metrics.record_mcp_call(latency_ms=50.0)
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/metrics", headers=auth_header)
            assert resp.status_code == 200
            data = resp.json()
            assert "extensions" in data
            assert data["extensions"]["mcp"]["tool_calls"] == 1
