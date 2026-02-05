"""
Browser Service - Manus 風格深度研究
"""

from .service import (
    BrowserService,
    SearchService,
    DeepResearchAgent,
    SearchResult,
    BrowseResult,
    ResearchStep,
    get_research_agent,
    PLAYWRIGHT_AVAILABLE
)

__all__ = [
    "BrowserService",
    "SearchService",
    "DeepResearchAgent",
    "SearchResult",
    "BrowseResult",
    "ResearchStep",
    "get_research_agent",
    "PLAYWRIGHT_AVAILABLE"
]
