"""
OpenCode Platform Core Module
核心模組 - 最終統一架構
"""

from .unified_final_engine import (
    FinalUnifiedEngine,
    Engine,
    UnifiedRequest,
    UnifiedResponse,
    ProcessingMode,
    ThinkingDepth,
    IntelligentRouter,
    ThinkingEngine,
    ServiceManager
)
from ..services.llm.openai_client import OpenAILLMClient # Add this import

__all__ = [
    'Engine',
    'FinalUnifiedEngine',
    'UnifiedRequest',
    'UnifiedResponse',
    'ProcessingMode',
    'ThinkingDepth',
    'IntelligentRouter',
    'ThinkingEngine',
    'ServiceManager',
    'OpenAILLMClient' # Add OpenAILLMClient to __all__
]