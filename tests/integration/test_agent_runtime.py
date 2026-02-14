"""
Integration tests for AgentRuntime.
Tests workflow execution, state tracking, and DeepResearch delegation.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.runtime.agent_runtime import AgentRuntime
from core.processors.factory import ProcessorFactory
from core.models_v2 import (
    ProcessingContext, Modes, Request, Response,
)
from core.logger import structured_logger


@pytest.fixture
def mock_llm():
    client = AsyncMock()
    client.generate = AsyncMock(side_effect=[
        "Research plan",
        '```json\n[{"query": "test q", "researchGoal": "goal", "priority": 1}]\n```',
        "Search result",
        "Processed result",
        "Final research report",
    ])
    return client


@pytest.fixture
def agent_runtime(mock_llm):
    factory = ProcessorFactory(mock_llm)
    return AgentRuntime(mock_llm, factory)


def _make_context(query: str = "research topic") -> ProcessingContext:
    req = Request(query=query, mode=Modes.DEEP_RESEARCH)
    resp = Response(result="", mode=Modes.DEEP_RESEARCH, trace_id=req.trace_id)
    return ProcessingContext(request=req, response=resp)


class TestAgentRuntimeSupports:
    """Test mode support."""

    def test_supports_deep_research(self, agent_runtime):
        assert agent_runtime.supports(Modes.DEEP_RESEARCH) is True

    def test_does_not_support_chat(self, agent_runtime):
        assert agent_runtime.supports(Modes.CHAT) is False

    def test_does_not_support_thinking(self, agent_runtime):
        assert agent_runtime.supports(Modes.THINKING) is False


class TestAgentRuntimeExecution:
    """Test workflow execution."""

    @pytest.mark.asyncio
    async def test_deep_research_execution(self, agent_runtime):
        ctx = _make_context("explain quantum computing")
        with patch.object(structured_logger, 'info'), \
             patch.object(structured_logger, 'progress'), \
             patch.object(structured_logger, 'message'), \
             patch.object(structured_logger, 'reasoning'), \
             patch.object(structured_logger, 'log_tool_decision'), \
             patch.object(structured_logger, 'log_llm_call'):
            result = await agent_runtime.execute(ctx)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_workflow_state_stored(self, agent_runtime):
        ctx = _make_context("analyze AI trends")
        with patch.object(structured_logger, 'info'), \
             patch.object(structured_logger, 'progress'), \
             patch.object(structured_logger, 'message'), \
             patch.object(structured_logger, 'reasoning'), \
             patch.object(structured_logger, 'log_tool_decision'), \
             patch.object(structured_logger, 'log_llm_call'):
            await agent_runtime.execute(ctx)

        # Verify workflow metadata was stored
        assert "workflow_state" in ctx.intermediate_results
        ws = ctx.intermediate_results["workflow_state"]
        assert ws["status"] == "completed"
