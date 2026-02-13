"""
Research Submodule - Deep research processor and related components

Contains DeepResearchProcessor with multi-provider search, streaming,
and academic reference formatting.
"""

from .config import SearchProviderType, SearchEngineConfig
from .events import ResearchEvent
from .processor import DeepResearchProcessor

__all__ = [
    'SearchProviderType',
    'SearchEngineConfig',
    'ResearchEvent',
    'DeepResearchProcessor',
]
