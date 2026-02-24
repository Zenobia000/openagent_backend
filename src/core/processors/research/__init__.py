"""
Research Submodule - Deep research processor and related components

Modular architecture:
- processor.py: Thin orchestrator (composes sub-modules)
- planner.py: Research planning and query generation
- search_executor.py: Multi-engine search execution
- analyzer.py: Synthesis and critical analysis
- computation.py: Chart planning and sandbox execution
- reporter.py: Report generation and persistence
- streaming.py: SSE event infrastructure
- config.py: Search engine configuration
- events.py: Research event types
"""

from .config import SearchProviderType, SearchEngineConfig
from .events import ResearchEvent
from .processor import DeepResearchProcessor
from .planner import ResearchPlanner
from .search_executor import SearchExecutor
from .analyzer import ResearchAnalyzer, summarize_search_results
from .computation import ComputationEngine
from .reporter import ReportGenerator, prepare_report_context
from .streaming import StreamingManager

__all__ = [
    # Primary export
    'DeepResearchProcessor',
    # Config & Events
    'SearchProviderType',
    'SearchEngineConfig',
    'ResearchEvent',
    # Sub-modules (for testing and advanced usage)
    'ResearchPlanner',
    'SearchExecutor',
    'ResearchAnalyzer',
    'ComputationEngine',
    'ReportGenerator',
    'StreamingManager',
    # Standalone functions
    'summarize_search_results',
    'prepare_report_context',
]
