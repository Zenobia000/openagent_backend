"""
Unit tests for Router, ComplexityAnalyzer, and ToolAvailabilityMask.

Migrated from core.models (old Enum-based) to core.models_v2 (frozen dataclass).
"""

import pytest
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.router import DefaultRouter, ComplexityAnalyzer
from core.models_v2 import (
    Request, Modes, RuntimeType,
    RoutingDecision, ComplexityScore,
)
from core.feature_flags import FeatureFlags
from core.routing.tool_mask import ToolAvailabilityMask


# ========== Fixtures ==========

@pytest.fixture
def router():
    """Router with all feature flags off."""
    flags = FeatureFlags(config_path=Path("/nonexistent/path.yaml"))
    return DefaultRouter(feature_flags=flags)


@pytest.fixture
def router_with_complexity():
    """Router with complexity_analysis enabled."""
    yaml_content = """
cognitive_features:
  enabled: true
  routing:
    complexity_analysis: true
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        flags = FeatureFlags(config_path=Path(f.name))
    return DefaultRouter(feature_flags=flags)


@pytest.fixture
def analyzer():
    return ComplexityAnalyzer()


# ========== DefaultRouter: Mode Selection ==========

class TestRouterModeSelection:
    """Test that auto mode resolves to correct concrete modes."""

    @pytest.mark.asyncio
    async def test_auto_resolves_to_chat(self, router):
        req = Request(query="你好，今天天氣如何？", mode=Modes.AUTO)
        decision = await router.route(req)
        assert decision.mode == Modes.CHAT

    @pytest.mark.asyncio
    async def test_auto_resolves_to_code(self, router):
        req = Request(query="幫我寫一段 code", mode=Modes.AUTO)
        decision = await router.route(req)
        assert decision.mode == Modes.CODE

    @pytest.mark.asyncio
    async def test_auto_resolves_to_search(self, router):
        req = Request(query="搜尋最新 AI 新聞", mode=Modes.AUTO)
        decision = await router.route(req)
        assert decision.mode == Modes.SEARCH

    @pytest.mark.asyncio
    async def test_auto_resolves_to_knowledge(self, router):
        req = Request(query="解釋量子計算", mode=Modes.AUTO)
        decision = await router.route(req)
        assert decision.mode == Modes.KNOWLEDGE

    @pytest.mark.asyncio
    async def test_auto_resolves_to_thinking(self, router):
        req = Request(query="深度分析氣候變化", mode=Modes.AUTO)
        decision = await router.route(req)
        assert decision.mode == Modes.THINKING

    @pytest.mark.asyncio
    async def test_explicit_mode_preserved(self, router):
        """Explicit mode should not be overridden."""
        req = Request(query="hello", mode=Modes.THINKING)
        decision = await router.route(req)
        assert decision.mode == Modes.THINKING
        assert decision.reason == "explicitly specified"

    @pytest.mark.asyncio
    async def test_auto_mode_sets_reason(self, router):
        req = Request(query="hello", mode=Modes.AUTO)
        decision = await router.route(req)
        assert "auto-selected" in decision.reason


# ========== DefaultRouter: Cognitive Level ==========

class TestRouterCognitiveLevel:
    """Test cognitive level classification in routing decisions."""

    @pytest.mark.asyncio
    async def test_chat_is_system1(self, router):
        req = Request(query="hi", mode=Modes.CHAT)
        decision = await router.route(req)
        assert decision.cognitive_level == "system1"

    @pytest.mark.asyncio
    async def test_thinking_is_system2(self, router):
        req = Request(query="think", mode=Modes.THINKING)
        decision = await router.route(req)
        assert decision.cognitive_level == "system2"

    @pytest.mark.asyncio
    async def test_deep_research_is_agent(self, router):
        req = Request(query="research", mode=Modes.DEEP_RESEARCH)
        decision = await router.route(req)
        assert decision.cognitive_level == "agent"


# ========== DefaultRouter: Runtime Dispatch ==========

class TestRouterRuntimeDispatch:
    """Test runtime type assignment."""

    @pytest.mark.asyncio
    async def test_system1_gets_model_runtime(self, router):
        req = Request(query="hi", mode=Modes.CHAT)
        decision = await router.route(req)
        assert decision.runtime_type == RuntimeType.MODEL

    @pytest.mark.asyncio
    async def test_system2_gets_model_runtime(self, router):
        req = Request(query="think", mode=Modes.THINKING)
        decision = await router.route(req)
        assert decision.runtime_type == RuntimeType.MODEL

    @pytest.mark.asyncio
    async def test_agent_gets_agent_runtime(self, router):
        req = Request(query="research", mode=Modes.DEEP_RESEARCH)
        decision = await router.route(req)
        assert decision.runtime_type == RuntimeType.AGENT


# ========== DefaultRouter: Complexity Integration ==========

class TestRouterComplexityIntegration:
    """Test complexity analysis feature flag integration."""

    @pytest.mark.asyncio
    async def test_no_complexity_when_flag_off(self, router):
        req = Request(query="analyze this deeply", mode=Modes.AUTO)
        decision = await router.route(req)
        assert decision.complexity is None

    @pytest.mark.asyncio
    async def test_complexity_present_when_flag_on(self, router_with_complexity):
        req = Request(query="analyze this deeply", mode=Modes.AUTO)
        decision = await router_with_complexity.route(req)
        assert decision.complexity is not None
        assert isinstance(decision.complexity, ComplexityScore)
        assert 0.0 <= decision.complexity.score <= 1.0


# ========== ComplexityAnalyzer ==========

class TestComplexityAnalyzer:
    """Test rule-based complexity scoring."""

    def test_simple_query_low_score(self, analyzer):
        score = analyzer.analyze("hi")
        assert score.score < 0.3
        assert score.recommended_level == "system1"

    def test_complex_query_higher_score(self, analyzer):
        query = "請逐步分析並比較 Python 和 Go 的並發模型，為什麼 Go 更適合微服務？"
        score = analyzer.analyze(query)
        assert score.score > 0.3

    def test_tool_heavy_query(self, analyzer):
        query = "search for the latest research papers and execute code analysis"
        score = analyzer.analyze(query)
        assert score.factors["tool_need"] > 0

    def test_multiple_questions(self, analyzer):
        query = "What is AI? How does it work? What are the risks?"
        score = analyzer.analyze(query)
        assert score.factors["questions"] > 0

    def test_score_bounded_0_to_1(self, analyzer):
        """Score must always be between 0 and 1."""
        for q in ["", "hi", "a" * 2000, "分析比較評估逐步" * 10]:
            score = analyzer.analyze(q)
            assert 0.0 <= score.score <= 1.0

    def test_factors_all_present(self, analyzer):
        score = analyzer.analyze("test query")
        for key in ["length", "multi_step", "tool_need", "questions"]:
            assert key in score.factors


# ========== RoutingDecision Model ==========

class TestRoutingDecisionModel:
    """Test the RoutingDecision dataclass."""

    def test_default_values(self):
        d = RoutingDecision(mode=Modes.CHAT)
        assert d.cognitive_level == "system1"  # @property from mode
        assert d.runtime_type == RuntimeType.MODEL  # @property from mode
        assert d.complexity is None
        assert d.confidence == 0.85
        assert d.reason == ""

    def test_full_construction(self):
        d = RoutingDecision(
            mode=Modes.DEEP_RESEARCH,
            complexity=ComplexityScore(score=0.8, recommended_level="agent"),
            confidence=0.95,
            reason="complex research task",
        )
        assert d.mode == Modes.DEEP_RESEARCH
        assert d.cognitive_level == "agent"  # @property
        assert d.runtime_type == RuntimeType.AGENT  # @property
        assert d.complexity.score == 0.8


# ========== ToolAvailabilityMask ==========

class TestToolMaskIntegration:
    """Test ToolAvailabilityMask integration with Router."""

    def test_router_exposes_tool_mask(self, router):
        """Router should expose tool_mask property."""
        assert isinstance(router.tool_mask, ToolAvailabilityMask)

    def test_tool_mask_all_modes_have_respond(self, router):
        """All modes should at least allow 'respond' tool."""
        for mode in Modes.all():
            allowed = router.tool_mask.get_allowed_tools(mode.name)
            assert "respond" in allowed, f"{mode.name} missing respond"
