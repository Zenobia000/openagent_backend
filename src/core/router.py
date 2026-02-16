"""
Router - Request routing and dispatch decisions.
Extracts routing logic from engine into a testable, independent component.
"""

from typing import Optional

from .models_v2 import (
    Request, Modes, RuntimeType,
    RoutingDecision, ComplexityScore,
)
from .feature_flags import FeatureFlags, feature_flags as default_flags
from .protocols import RouterProtocol
from .routing.tool_mask import ToolAvailabilityMask


class ComplexityAnalyzer:
    """Rule-based query complexity analysis.

    Produces a ComplexityScore based on surface-level heuristics.
    Gated behind feature flag `routing.complexity_analysis`.

    Design Decision:
    ----------------
    Uses keyword-based heuristics rather than ML models because:
    1. Simple, predictable, and debuggable
    2. No training data or model deployment overhead
    3. Good enough for initial routing decisions
    4. Can be enhanced with ML later without changing the interface

    Complexity Factors:
    -------------------
    - length: Longer queries tend to be more complex
    - multi_step: Keywords indicating multi-step reasoning (分析, compare, explain why)
    - tool_need: Keywords indicating tool usage (code, search, execute)
    - questions: Multiple questions increase complexity

    Scoring:
    --------
    Each factor contributes a weighted score (0.0-1.0):
    - length: 20% weight
    - multi_step: 30% weight
    - tool_need: 30% weight
    - questions: 20% weight

    Final score maps to cognitive levels:
    - >= 0.6: AGENT (requires tool usage and planning)
    - >= 0.3: SYSTEM2 (requires deeper reasoning)
    - < 0.3: SYSTEM1 (simple question-answering)
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
            recommended = "agent"
        elif score >= 0.3:
            recommended = "system2"
        else:
            recommended = "system1"

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
        self._tool_mask = ToolAvailabilityMask(self._flags)

    async def route(self, request: Request) -> RoutingDecision:
        """Route a request to a processing decision."""
        # Step 1: Resolve mode
        if request.mode == Modes.AUTO:
            mode = self._select_mode(request.query)
            reason = "auto-selected based on query analysis"
        else:
            mode = request.mode
            reason = "explicitly specified"

        # Step 2: Optional complexity analysis
        complexity = None
        if self._flags.is_enabled("routing.complexity_analysis"):
            complexity = self._complexity_analyzer.analyze(request.query)

        # cognitive_level and runtime_type are @property on RoutingDecision,
        # derived from mode — not constructor args.
        return RoutingDecision(
            mode=mode,
            complexity=complexity,
            confidence=0.85,
            reason=reason,
        )

    @property
    def tool_mask(self) -> ToolAvailabilityMask:
        """Expose tool mask for processors to query allowed tools."""
        return self._tool_mask

    @staticmethod
    def _select_mode(query: str):
        """Rule-based mode selection using keyword matching.

        Design Decision: Keyword-Based Routing
        ---------------------------------------
        This router uses simple keyword matching rather than ML classification because:

        1. **Predictability**: Users and developers can understand exactly why a query
           was routed to a specific mode by inspecting the keywords.

        2. **No Training Required**: No need for labeled data, model training, or
           deployment of ML models.

        3. **Low Latency**: Keyword matching is O(n*m) where n=query_length and
           m=keywords, typically < 1ms.

        4. **Easy to Tune**: Add/remove keywords based on user feedback without
           retraining models.

        5. **Good Enough**: For most queries, intent is clear from keywords. Edge
           cases can be handled by fallback to CHAT mode.

        Routing Priority:
        -----------------
        Keywords are checked in order of specificity:
        1. CODE: Programming-related keywords (highest priority for developers)
        2. SEARCH: Explicit search/lookup requests
        3. KNOWLEDGE: Knowledge base queries (explain, define, etc.)
        4. THINKING: Deep analysis requests
        5. CHAT: Default fallback for everything else

        Future Enhancement:
        -------------------
        If needed, can add ML-based routing as a feature-flagged option while
        keeping keyword-based routing as the default. The ProcessingMode abstraction
        makes this swap easy.

        Args:
            query: User query string (case-insensitive matching)

        Returns:
            ProcessingMode: The selected mode based on keyword matching
        """
        query_lower = query.lower()

        # Priority 1: Code-related queries
        if any(w in query_lower for w in ['代碼', 'code', '程式', 'function']):
            return Modes.CODE

        # Priority 2: Search/lookup queries
        elif any(w in query_lower for w in ['搜尋', 'search', '查詢', 'find']):
            return Modes.SEARCH

        # Priority 3: Knowledge base queries
        elif any(w in query_lower for w in ['知識', 'knowledge', '解釋', 'explain']):
            return Modes.KNOWLEDGE

        # Priority 4: Deep thinking queries
        elif any(w in query_lower for w in ['深度', 'deep', '分析', 'analyze', '思考']):
            return Modes.THINKING

        # Priority 5: Default fallback
        else:
            return Modes.CHAT
