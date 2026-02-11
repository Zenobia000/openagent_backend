"""
Integration tests for ModelRuntime.
Ensures ModelRuntime produces identical results to direct ProcessorFactory calls.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.runtime.model_runtime import ModelRuntime
from core.processor import ProcessorFactory
from core.models import (
    ProcessingContext, ProcessingMode, Request, Response,
)
from core.logger import structured_logger


@pytest.fixture
def mock_llm():
    client = AsyncMock()
    client.generate = AsyncMock(return_value="Mock LLM Response")
    return client


@pytest.fixture
def model_runtime(mock_llm):
    factory = ProcessorFactory(mock_llm)
    return ModelRuntime(mock_llm, factory)


def _make_context(mode: ProcessingMode, query: str = "test") -> ProcessingContext:
    req = Request(query=query, mode=mode)
    resp = Response(result="", mode=mode, trace_id=req.trace_id)
    return ProcessingContext(request=req, response=resp)


class TestModelRuntimeSupports:
    """Test mode support checking."""

    def test_supports_chat(self, model_runtime):
        assert model_runtime.supports(ProcessingMode.CHAT) is True

    def test_supports_knowledge(self, model_runtime):
        assert model_runtime.supports(ProcessingMode.KNOWLEDGE) is True

    def test_supports_search(self, model_runtime):
        assert model_runtime.supports(ProcessingMode.SEARCH) is True

    def test_supports_code(self, model_runtime):
        assert model_runtime.supports(ProcessingMode.CODE) is True

    def test_supports_thinking(self, model_runtime):
        assert model_runtime.supports(ProcessingMode.THINKING) is True

    def test_does_not_support_deep_research(self, model_runtime):
        assert model_runtime.supports(ProcessingMode.DEEP_RESEARCH) is False


class TestModelRuntimeExecution:
    """Test that ModelRuntime execution matches ProcessorFactory."""

    @pytest.mark.asyncio
    async def test_chat_execution(self, model_runtime, mock_llm):
        ctx = _make_context(ProcessingMode.CHAT, "hello")
        with patch.object(structured_logger, 'info'), \
             patch.object(structured_logger, 'progress'), \
             patch.object(structured_logger, 'message'), \
             patch.object(structured_logger, 'log_llm_call'):
            result = await model_runtime.execute(ctx)
        assert result == "Mock LLM Response"

    @pytest.mark.asyncio
    async def test_knowledge_execution(self, model_runtime, mock_llm):
        ctx = _make_context(ProcessingMode.KNOWLEDGE, "what is AI")
        with patch.object(structured_logger, 'info'), \
             patch.object(structured_logger, 'progress'), \
             patch.object(structured_logger, 'message'), \
             patch.object(structured_logger, 'log_tool_decision'), \
             patch.object(structured_logger, 'log_llm_call'):
            result = await model_runtime.execute(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_matches_direct_factory_call(self, mock_llm):
        """ModelRuntime result must match direct ProcessorFactory call."""
        factory = ProcessorFactory(mock_llm)
        runtime = ModelRuntime(mock_llm, factory)

        ctx_direct = _make_context(ProcessingMode.CHAT, "hello")
        ctx_runtime = _make_context(ProcessingMode.CHAT, "hello")

        with patch.object(structured_logger, 'info'), \
             patch.object(structured_logger, 'progress'), \
             patch.object(structured_logger, 'message'), \
             patch.object(structured_logger, 'log_llm_call'):
            direct_result = await factory.get_processor(ProcessingMode.CHAT).process(ctx_direct)
            runtime_result = await runtime.execute(ctx_runtime)

        assert direct_result == runtime_result
