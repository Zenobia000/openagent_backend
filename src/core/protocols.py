"""
協議定義 - 服務介面規範
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class MCPServiceProtocol(ABC):
    """MCP 服務協議"""

    @property
    @abstractmethod
    def service_id(self) -> str:
        """服務 ID"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """服務能力列表"""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服務"""
        pass

    @abstractmethod
    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """執行方法"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康檢查"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """關閉服務"""
        pass


class LLMClientProtocol(ABC):
    """LLM 客戶端協議"""

    @abstractmethod
    async def generate(self, prompt: str, streaming: bool = False) -> str:
        """生成回應"""
        pass

    @abstractmethod
    async def complete(self, messages: List[Dict[str, str]]) -> str:
        """完成對話"""
        pass