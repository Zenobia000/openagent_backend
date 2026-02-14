"""
Processor Factory - Creates and manages processor instances

Maintains a registry of processors and handles instantiation with
proper dependency injection (LLM client, services, MCP client).
Extracted from monolithic processor.py
"""

from typing import Dict, Type, Optional, Any

from ..models_v2 import Modes, ProcessingMode
from .base import BaseProcessor
from .chat import ChatProcessor
from .knowledge import KnowledgeProcessor
from .search import SearchProcessor
from .thinking import ThinkingProcessor
from .code import CodeProcessor
from .research import DeepResearchProcessor


class ProcessorFactory:
    """處理器工廠 - 創建和管理處理器"""

    _processors: Dict = {
        Modes.CHAT: ChatProcessor,
        Modes.KNOWLEDGE: KnowledgeProcessor,
        Modes.SEARCH: SearchProcessor,
        Modes.THINKING: ThinkingProcessor,
        Modes.CODE: CodeProcessor,
        Modes.DEEP_RESEARCH: DeepResearchProcessor,
    }

    def __init__(self, llm_client=None, services: Optional[Dict[str, Any]] = None, mcp_client=None):
        self.llm_client = llm_client
        self.services = services or {}
        self.mcp_client = mcp_client
        self._instances: Dict = {}

    def get_processor(self, mode) -> BaseProcessor:
        """獲取處理器實例

        ✓ NEW: Cognitive level from mode.cognitive_level (data self-contained)
        ❌ OLD: Used COGNITIVE_MAPPING dict (special case) - DELETED
        """
        if mode not in self._instances:
            processor_class = self._processors.get(mode, ChatProcessor)
            instance = processor_class(self.llm_client, services=self.services, mcp_client=self.mcp_client)

            # Get cognitive level from mode (backward compatible)
            if hasattr(mode, 'cognitive_level'):
                instance._cognitive_level = mode.cognitive_level
            elif hasattr(mode, 'value'):
                # Fallback for old ProcessingMode enum
                level_map = {
                    "chat": "system1", "knowledge": "system1",
                    "search": "system2", "code": "system2", "thinking": "system2",
                    "deep_research": "agent", "auto": "system1"
                }
                instance._cognitive_level = level_map.get(mode.value, "system1")

            self._instances[mode] = instance

        return self._instances[mode]

    def register_processor(self, mode, processor_class: Type[BaseProcessor]):
        """註冊自定義處理器"""
        self._processors[mode] = processor_class
        # 清除已有實例，下次獲取時會創建新的
        if mode in self._instances:
            del self._instances[mode]
