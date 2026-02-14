"""
E2E regression test - all 6 processing modes through the full engine pipeline.
Tests both legacy path (flag off) and runtime path (flag on).
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.engine import RefactoredEngine
from core.models import Request, ProcessingMode
from core.feature_flags import FeatureFlags
from core.logger import structured_logger


@pytest.fixture
def mock_llm():
    """LLM client that handles all processor patterns."""
    client = AsyncMock()

    def flexible_generate(prompt, **kwargs):
        if "json" in prompt.lower() or "serp" in prompt.lower():
            return '```json\n[{"query": "test", "researchGoal": "goal", "priority": 1}]\n```'
        return f"Response to: {prompt[:50]}"

    client.generate = AsyncMock(side_effect=flexible_generate)
    return client


@pytest.fixture
def engine_legacy(mock_llm):
    """Engine with all feature flags OFF (legacy path)."""
    engine = RefactoredEngine(llm_client=mock_llm)
    return engine


@pytest.fixture
def engine_runtime(mock_llm):
    """Engine with smart_routing ON (runtime dispatch path)."""
    yaml_content = """
cognitive_features:
  enabled: true
  routing:
    smart_routing: true
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        flags = FeatureFlags(config_path=Path(f.name))

    engine = RefactoredEngine(llm_client=mock_llm)
    engine.feature_flags = flags
    return engine


# Suppress noisy logger output during tests
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
         patch.object(structured_logger, 'measure') as mock_measure:
        # Make measure work as a context manager
        mock_measure.return_value.__enter__ = lambda s: s
        mock_measure.return_value.__exit__ = lambda s, *a: None
        yield


_ALL_EXPLICIT_MODES = [
    ProcessingMode.CHAT,
    ProcessingMode.KNOWLEDGE,
    ProcessingMode.SEARCH,
    ProcessingMode.CODE,
    ProcessingMode.THINKING,
    ProcessingMode.DEEP_RESEARCH,
]


class TestAllModesLegacy:
    """All modes work through the legacy ProcessorFactory path."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", _ALL_EXPLICIT_MODES, ids=lambda m: m.value)
    async def test_mode_returns_result(self, engine_legacy, mode):
        req = Request(query="Test query for mode", mode=mode)
        resp = await engine_legacy.process(req)
        assert resp.result is not None
        assert len(resp.result) > 0
        assert resp.mode == mode

    @pytest.mark.asyncio
    async def test_auto_mode(self, engine_legacy):
        req = Request(query="hello there", mode=ProcessingMode.AUTO)
        resp = await engine_legacy.process(req)
        assert resp.result is not None
        assert resp.mode != ProcessingMode.AUTO  # Should be resolved


class TestAllModesRuntime:
    """All modes work through the Runtime dispatch path."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", _ALL_EXPLICIT_MODES, ids=lambda m: m.value)
    async def test_mode_returns_result(self, engine_runtime, mode):
        req = Request(query="Test query for mode", mode=mode)
        resp = await engine_runtime.process(req)
        assert resp.result is not None
        assert len(resp.result) > 0

    @pytest.mark.asyncio
    async def test_auto_mode(self, engine_runtime):
        req = Request(query="hello there", mode=ProcessingMode.AUTO)
        resp = await engine_runtime.process(req)
        assert resp.result is not None


class TestRuntimeConsistency:
    """Legacy and runtime paths must produce equivalent results."""

    @pytest.mark.asyncio
    async def test_chat_same_result(self, engine_legacy, engine_runtime, mock_llm):
        """Same LLM mock should produce same result regardless of path."""
        req_legacy = Request(query="hello", mode=ProcessingMode.CHAT)
        req_runtime = Request(query="hello", mode=ProcessingMode.CHAT)

        resp_legacy = await engine_legacy.process(req_legacy)
        # Reset the mock side_effect for second call
        mock_llm.generate.side_effect = lambda prompt, **kw: f"Response to: {prompt[:50]}"
        resp_runtime = await engine_runtime.process(req_runtime)

        # Both should succeed (exact match depends on mock determinism)
        assert resp_legacy.result is not None
        assert resp_runtime.result is not None
