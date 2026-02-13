"""
DEPRECATED: This module has been refactored into src/core/processors/

Backward compatibility shim - Re-exports all classes from the new modular structure.

Old import (deprecated):
    from core.processor import ChatProcessor, ProcessorFactory

New import (recommended):
    from core.processors import ChatProcessor, ProcessorFactory

This file will be removed in a future version. Please update your imports.
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "Importing from 'core.processor' is deprecated. "
    "Use 'from core.processors import ...' instead. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all classes from new modular structure
from .processors import (
    BaseProcessor,
    ProcessorFactory,
    ChatProcessor,
    KnowledgeProcessor,
    SearchProcessor,
    ThinkingProcessor,
    CodeProcessor,
    DeepResearchProcessor,
    SearchEngineConfig,
    SearchProviderType,
    ResearchEvent,
)

# For backward compatibility with direct imports
__all__ = [
    'BaseProcessor',
    'ProcessorFactory',
    'ChatProcessor',
    'KnowledgeProcessor',
    'SearchProcessor',
    'ThinkingProcessor',
    'CodeProcessor',
    'DeepResearchProcessor',
    'SearchEngineConfig',
    'SearchProviderType',
    'ResearchEvent',
]
