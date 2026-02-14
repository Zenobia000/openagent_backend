"""
Modular Processor System - Linus Style Refactoring

每個處理器一個文件，最大 500 行。
消除 2611 行的 processor.py 怪獸。

Usage:
    from core.processors import ChatProcessor, ProcessorFactory
"""

from .base import BaseProcessor
from .factory import ProcessorFactory
from .chat import ChatProcessor
from .knowledge import KnowledgeProcessor
from .search import SearchProcessor
from .thinking import ThinkingProcessor
from .code import CodeProcessor
from .research import DeepResearchProcessor, SearchEngineConfig, SearchProviderType, ResearchEvent

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
