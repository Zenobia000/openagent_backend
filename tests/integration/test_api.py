"""Integration tests for API endpoints using httpx.AsyncClient."""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from httpx import AsyncClient, ASGITransport
from core.engine import RefactoredEngine
from core.logger import structured_logger
from auth.jwt import encode_token, UserRole


@pytest.fixture
def mock_llm():
    client = AsyncMock()
    client.generate = AsyncMock(return_value="Test response from LLM")
    return client


@pytest.fixture
def app(mock_llm):
    """Create a FastAPI app wired to a mock engine."""
    engine = RefactoredEngine(llm_client=mock_llm)
    engine.initialized = True

    from api.routes import create_app
    return create_app(engine=engine)


@pytest.fixture
def auth_header():
    """Valid JWT bearer header."""
    token = encode_token(user_id="test-user", username="tester", role=UserRole.USER)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def quiet_logger():
    with patch.object(structured_logger, 'info'), \
         patch.object(structured_logger, 'debug'), \
         patch.object(structured_logger, 'progress'), \
         patch.object(structured_logger, 'message'), \
         patch.object(structured_logger, 'reasoning'), \
         patch.object(structured_logger, 'log_llm_call'), \
         patch.object(structured_logger, 'log_tool_decision'), \
         patch.object(structured_logger, 'log_error'), \
         patch.object(structured_logger, 'set_trace'), \
         patch.object(structured_logger, 'set_context'), \
         patch.object(structured_logger, 'clear_context'), \
         patch.object(structured_logger, 'emit_sse'), \
         patch.object(structured_logger, 'set_sse_callback'), \
         patch.object(structured_logger, 'measure') as mock_measure:
        mock_measure.return_value.__enter__ = lambda s: s
        mock_measure.return_value.__exit__ = lambda s, *a: None
        yield


# ── Public Endpoints ──

class TestPublicEndpoints:
    @pytest.mark.asyncio
    async def test_root(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

    @pytest.mark.asyncio
    async def test_health(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_api_status(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/status")
        assert r.status_code == 200
        assert r.json()["engine_ready"] is True


# ── Auth ──

class TestAuthEndpoint:
    @pytest.mark.asyncio
    async def test_create_token(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/auth/token", json={"username": "alice", "password": "pass"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat", json={"query": "hello"})
        assert r.status_code in (401, 403)


# ── Chat ──

class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_success(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat", json={"query": "hello"}, headers=auth_header)
        assert r.status_code == 200
        body = r.json()
        assert "result" in body
        assert len(body["result"]) > 0
        assert "trace_id" in body

    @pytest.mark.asyncio
    async def test_chat_with_mode(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/chat",
                json={"query": "explain code", "mode": "thinking"},
                headers=auth_header,
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_invalid_mode(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/chat",
                json={"query": "hello", "mode": "invalid_mode"},
                headers=auth_header,
            )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_empty_query(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat", json={"query": ""}, headers=auth_header)
        assert r.status_code == 422


# ── Documents ──

class TestDocumentEndpoints:
    @pytest.mark.asyncio
    async def test_upload_document(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", b"hello world", "text/plain")},
                headers=auth_header,
            )
        assert r.status_code == 200
        body = r.json()
        assert "task_id" in body
        assert body["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_document_status(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            upload = await c.post(
                "/api/v1/documents/upload",
                files={"file": ("doc.pdf", b"pdf content", "application/pdf")},
                headers=auth_header,
            )
            task_id = upload.json()["task_id"]
            r = await c.get(f"/api/v1/documents/status/{task_id}", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["status"] in ("processing", "completed")

    @pytest.mark.asyncio
    async def test_document_status_not_found(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/documents/status/nonexistent-id", headers=auth_header)
        assert r.status_code == 404


# ── Search ──

class TestSearchEndpoint:
    @pytest.mark.asyncio
    async def test_search_success(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "quantum computing"},
                headers=auth_header,
            )
        assert r.status_code == 200
        body = r.json()
        assert "results" in body
        assert "trace_id" in body


# ── Error Format ──

class TestErrorFormat:
    @pytest.mark.asyncio
    async def test_404_returns_structured_error(self, app, auth_header):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/documents/status/bad-id", headers=auth_header)
        body = r.json()
        assert "error_code" in body
        assert "message" in body
