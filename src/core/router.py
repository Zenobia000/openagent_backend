"""
Router - Request routing and dispatch decisions.
Extracts routing logic from engine into a testable, independent component.
"""

from typing import Optional

from .models import (
    Request, ProcessingMode, CognitiveLevel, RuntimeType,
    RoutingDecision, ComplexityScore,
)
from .feature_flags import FeatureFlags, feature_flags as default_flags
from .protocols import RouterProtocol


class ComplexityAnalyzer:
    """Rule-based query complexity analysis.

    Produces a ComplexityScore based on surface-level heuristics.
    Gated behind feature flag `routing.complexity_analysis`.
    """

    # Keyword groups that indicate higher complexity
    _MULTI_STEP_KEYWORDS = [
        '分析', 'analyze', 'compare', '比較', 'evaluate', '評估',
        'explain why', '為什麼', 'step by step', '逐步',
    ]
    _TOOL_KEYWORDS = [
        'code', '代碼', '程式', 'search', '搜尋', 'execute', '執行',
        'research', '研究',
    ]

    def analyze(self, query: str) -> ComplexityScore:
        """Analyze query complexity and return a score."""
        factors = {}
        query_lower = query.lower()

        # Factor 1: query length (longer = more complex)
        length = len(query)
        factors["length"] = min(length / 500.0, 1.0)

        # Factor 2: multi-step indicators
        multi_step_count = sum(
            1 for kw in self._MULTI_STEP_KEYWORDS if kw in query_lower
        )
        factors["multi_step"] = min(multi_step_count / 3.0, 1.0)

        # Factor 3: tool requirement indicators
        tool_count = sum(
            1 for kw in self._TOOL_KEYWORDS if kw in query_lower
        )
        factors["tool_need"] = min(tool_count / 3.0, 1.0)

        # Factor 4: question marks (multiple questions = more complex)
        q_marks = query.count('?') + query.count('？')
        factors["questions"] = min(q_marks / 3.0, 1.0)

        # Weighted score
        score = (
            factors["length"] * 0.2
            + factors["multi_step"] * 0.3
            + factors["tool_need"] * 0.3
            + factors["questions"] * 0.2
        )

        # Recommend cognitive level based on score
        if score >= 0.6:
            recommended = CognitiveLevel.AGENT
        elif score >= 0.3:
            recommended = CognitiveLevel.SYSTEM2
        else:
            recommended = CognitiveLevel.SYSTEM1

        return ComplexityScore(
            score=round(score, 3),
            factors=factors,
            recommended_level=recommended,
        )


class DefaultRouter(RouterProtocol):
    """Default router - migrated from engine._select_mode().

    Responsibilities:
    1. Mode selection (AUTO -> concrete mode)
    2. Cognitive level classification
    3. Runtime type dispatch
    4. Optional complexity analysis (feature-flagged)
    """

    def __init__(self, feature_flags: Optional[FeatureFlags] = None):
        self._flags = feature_flags or default_flags
        self._complexity_analyzer = ComplexityAnalyzer()

    async def route(self, request: Request) -> RoutingDecision:
        """Route a request to a processing decision."""
        # Step 1: Resolve mode
        if request.mode == ProcessingMode.AUTO:
            mode = self._select_mode(request.query)
            reason = "auto-selected based on query analysis"
        else:
            mode = request.mode
            reason = "explicitly specified"

        # Step 2: Cognitive level from the mode
        cognitive_level = mode.cognitive_level

        # Step 3: Runtime dispatch
        runtime_type = self._select_runtime(cognitive_level)

        # Step 4: Optional complexity analysis
        complexity = None
        if self._flags.is_enabled("routing.complexity_analysis"):
            complexity = self._complexity_analyzer.analyze(request.query)

        return RoutingDecision(
            mode=mode,
            cognitive_level=cognitive_level,
            runtime_type=runtime_type,
            complexity=complexity,
            confidence=0.85,
            reason=reason,
        )

    @staticmethod
    def _select_mode(query: str) -> ProcessingMode:
        """Rule-based mode selection. Identical to the original engine logic."""
        query_lower = query.lower()

        if any(w in query_lower for w in ['代碼', 'code', '程式', 'function']):
            return ProcessingMode.CODE
        elif any(w in query_lower for w in ['搜尋', 'search', '查詢', 'find']):
            return ProcessingMode.SEARCH
        elif any(w in query_lower for w in ['知識', 'knowledge', '解釋', 'explain']):
            return ProcessingMode.KNOWLEDGE
        elif any(w in query_lower for w in ['深度', 'deep', '分析', 'analyze', '思考']):
            return ProcessingMode.THINKING
        else:
            return ProcessingMode.CHAT

    @staticmethod
    def _select_runtime(cognitive_level: str) -> RuntimeType:
        """Map cognitive level to runtime type."""
        if cognitive_level == CognitiveLevel.AGENT:
            return RuntimeType.AGENT_RUNTIME
        return RuntimeType.MODEL_RUNTIME
