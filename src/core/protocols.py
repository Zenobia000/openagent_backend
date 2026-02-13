"""
協議定義 - 服務介面規範
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, List, Optional


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


class LongTermMemoryProtocol(ABC):
    """長期記憶協議 - 儲存、檢索、刪除"""

    @abstractmethod
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """儲存內容，回傳 doc_id"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """檢索內容"""
        pass

    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """刪除內容"""
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


class RouterProtocol(ABC):
    """Router protocol - decides how to process a request."""

    @abstractmethod
    async def route(self, request: Any) -> Any:
        """Route a request to a processing decision.

        Args:
            request: The incoming request

        Returns:
            RoutingDecision with mode, cognitive_level, runtime_type
        """
        pass


class RuntimeProtocol(ABC):
    """Runtime protocol - executes processing for a given context."""

    @abstractmethod
    async def execute(self, context: Any) -> str:
        """Execute processing and return result string."""
        pass

    @abstractmethod
    def supports(self, mode: Any) -> bool:
        """Check if this runtime supports the given processing mode."""
        pass


class MCPClientProtocol(ABC):
    """MCP Client 協議 — 管理與外部 MCP Server 的連線和工具呼叫"""

    @abstractmethod
    async def initialize(self) -> None:
        """啟動所有設定的 MCP Server 連線"""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """聚合所有已連線 server 的 tools"""
        pass

    @abstractmethod
    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """呼叫指定 server 的指定 tool"""
        pass

    @abstractmethod
    async def list_resources(self) -> List[Dict[str, Any]]:
        """聚合所有已連線 server 的 resources"""
        pass

    @abstractmethod
    async def read_resource(self, server_name: str, uri: str) -> Any:
        """讀取指定 server 的 resource"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """關閉所有連線"""
        pass


class A2AClientProtocol(ABC):
    """A2A Client 協議 — 管理與外部 Agent 的任務委派和協作"""

    @abstractmethod
    async def initialize(self) -> None:
        """啟動並發現所有設定的 A2A Agents"""
        pass

    @abstractmethod
    async def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有已連線的 Agent 及其能力"""
        pass

    @abstractmethod
    async def send_task(
        self, agent_name: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """向外部 Agent 發送任務，等待完成"""
        pass

    @abstractmethod
    async def send_task_streaming(
        self, agent_name: str, message: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """串流接收任務結果"""
        pass

    @abstractmethod
    async def get_task_status(self, agent_name: str, task_id: str) -> Dict[str, Any]:
        """查詢任務狀態"""
        pass

    @abstractmethod
    async def cancel_task(self, agent_name: str, task_id: str) -> bool:
        """取消進行中的任務"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """關閉所有連線"""
        pass