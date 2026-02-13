"""
Processor Factory - Creates and manages processor instances

Maintains a registry of processors and handles instantiation with
proper dependency injection (LLM client, services, MCP client).
Extracted from monolithic processor.py
"""

from typing import Dict, Type, Optional, Any

from ..models import ProcessingMode
from .base import BaseProcessor
from .chat import ChatProcessor
from .knowledge import KnowledgeProcessor
from .search import SearchProcessor
from .thinking import ThinkingProcessor
from .code import CodeProcessor
from .research import DeepResearchProcessor


class ProcessorFactory:
    """處理器工廠 - 創建和管理處理器"""

    _processors: Dict[ProcessingMode, Type[BaseProcessor]] = {
        ProcessingMode.CHAT: ChatProcessor,
        ProcessingMode.KNOWLEDGE: KnowledgeProcessor,
        ProcessingMode.SEARCH: SearchProcessor,
        ProcessingMode.THINKING: ThinkingProcessor,
        ProcessingMode.CODE: CodeProcessor,
        ProcessingMode.DEEP_RESEARCH: DeepResearchProcessor,
    }

    # Cognitive level mapping for each processing mode
    COGNITIVE_MAPPING: Dict[str, str] = {
        "chat": "system1",
        "knowledge": "system1",
        "search": "system2",
        "code": "system2",
        "thinking": "system2",
        "deep_research": "agent",
    }

    def __init__(self, llm_client=None, services: Optional[Dict[str, Any]] = None, mcp_client=None):
        self.llm_client = llm_client
        self.services = services or {}
        self.mcp_client = mcp_client
        self._instances: Dict[ProcessingMode, BaseProcessor] = {}

    def get_processor(self, mode: ProcessingMode) -> BaseProcessor:
        """獲取處理器實例"""
        if mode not in self._instances:
            processor_class = self._processors.get(mode, ChatProcessor)
            instance = processor_class(self.llm_client, services=self.services, mcp_client=self.mcp_client)
            instance._cognitive_level = self.COGNITIVE_MAPPING.get(mode.value)
            self._instances[mode] = instance

        return self._instances[mode]

    def register_processor(self, mode: ProcessingMode, processor_class: Type[BaseProcessor]):
        """註冊自定義處理器"""
        self._processors[mode] = processor_class
        # 清除已有實例，下次獲取時會創建新的
        if mode in self._instances:
            del self._instances[mode]
