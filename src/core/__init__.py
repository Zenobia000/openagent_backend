"""
OpenCode Platform - 重構版核心模組
簡化架構，統一處理流程，整合日誌系統
"""

from .engine import RefactoredEngine
from .processors.factory import ProcessorFactory
from .models_v2 import Request, Response, ProcessingContext, Modes, EventType, Event, RuntimeType
from .logger import structured_logger

# Backward compatibility alias
ProcessingMode = Modes

__all__ = [
    'RefactoredEngine',
    'ProcessorFactory',
    'Request',
    'Response',
    'ProcessingContext',
    'ProcessingMode',
    'Modes',
    'EventType',
    'Event',
    'RuntimeType',
    'structured_logger'
]