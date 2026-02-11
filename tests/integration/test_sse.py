"""Integration tests for SSE streaming."""

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
    client.generate = AsyncMock(return_value="Streamed response")
    return client


@pytest.fixture
def app(mock_llm):
    engine = RefactoredEngine(llm_client=mock_llm)
    engine.initialized = True
    from api.routes import create_app
    return create_app(engine=engine)


@pytest.fixture
def auth_header():
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


class TestSSEStreaming:
    @pytest.mark.asyncio
    async def test_stream_returns_sse_response(self, app, auth_header):
        """Stream endpoint should return text/event-stream content type."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/chat/stream",
                json={"query": "hello", "stream": True},
                headers=auth_header,
            )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_stream_contains_events(self, app, auth_header):
        """Stream should contain event data in the body."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/chat/stream",
                json={"query": "hello", "stream": True},
                headers=auth_header,
            )
        body = r.text
        # SSE format uses "event:" and "data:" lines
        assert "event:" in body or "data:" in body

    @pytest.mark.asyncio
    async def test_stream_without_auth_rejected(self, app):
        """Stream endpoint requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/chat/stream", json={"query": "hello"})
        assert r.status_code in (401, 403)
