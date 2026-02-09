"""
核心介面定義 (Protocols)
所有模組實作必須遵循這些契約
"""

from typing import (
    Protocol, Dict, Any, List, Optional, 
    AsyncIterator, Callable, runtime_checkable
)
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import uuid


# ============== 基礎列舉 ==============

class EventType(Enum):
    """事件類型"""
    # 核心事件
    INTENT = "intent"
    PLAN = "plan"
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    
    # Agent 事件
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ANSWER = "answer"
    SOURCE = "source"
    DONE = "done"
    
    # 系統事件
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    HEALTH_CHECK = "health_check"


class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ServiceStatus(Enum):
    """服務狀態"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


# ============== 基礎資料類型 ==============

@dataclass
class Context:
    """用戶上下文"""
    session_id: str
    user_id: str
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    active_plugins: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "permissions": self.permissions,
            "metadata": self.metadata,
            "conversation_history": self.conversation_history,
            "active_plugins": self.active_plugins
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        return cls(**data)


@dataclass
class Intent:
    """用戶意圖"""
    id: str
    type: str
    content: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Optional[Context] = None
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def create(cls, content: str, intent_type: str = "chat", **kwargs) -> "Intent":
        return cls(
            id=str(uuid.uuid4()),
            type=intent_type,
            content=content,
            **kwargs
        )


@dataclass
class Task:
    """任務定義"""
    id: str
    type: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    
    @classmethod
    def create(cls, tool: str, task_type: str = "execute", **kwargs) -> "Task":
        return cls(
            id=str(uuid.uuid4()),
            type=task_type,
            tool=tool,
            **kwargs
        )


@dataclass
class Event:
    """系統事件"""
    type: EventType
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source: str = "system"
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id
        }
    
    def to_sse(self) -> str:
        """轉換為 Server-Sent Events 格式"""
        import json
        data = {
            "type": self.type.value,
            "content": self.payload.get("content", ""),
            "data": self.payload.get("data")
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@dataclass
class ToolContract:
    """工具合約"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)


# ============== 核心引擎介面 ==============

@runtime_checkable
class EngineProtocol(Protocol):
    """OpenCode 引擎介面"""
    
    async def initialize(self) -> None:
        """初始化引擎"""
        ...
    
    async def process_intent(self, intent: Intent) -> AsyncIterator[Event]:
        """處理用戶意圖"""
        ...
    
    async def shutdown(self) -> None:
        """關閉引擎"""
        ...


@runtime_checkable
class ContextManagerProtocol(Protocol):
    """Context 管理介面"""
    
    async def initialize(self) -> None:
        """初始化"""
        ...
    
    async def get_context(self, session_id: str) -> Optional[Context]:
        """取得 Context"""
        ...
    
    async def save_context(self, context: Context) -> None:
        """儲存 Context"""
        ...
    
    async def update_conversation(
        self, 
        session_id: str, 
        message: Dict[str, Any]
    ) -> None:
        """更新對話歷史"""
        ...
    
    async def delete_context(self, session_id: str) -> None:
        """刪除 Context"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """事件匯流排介面"""
    
    def register_handler(
        self, 
        event_type: str, 
        handler: Callable
    ) -> None:
        """註冊事件處理器"""
        ...
    
    def register(self, handler: Callable) -> None:
        """註冊萬用處理器"""
        ...
    
    async def emit(self, event: Event) -> AsyncIterator[Event]:
        """發送事件並產生回應"""
        ...
    
    async def publish(self, event: Event) -> None:
        """發送事件 (不等待回應)"""
        ...


@runtime_checkable
class PluginProtocol(Protocol):
    """插件介面"""
    
    @property
    def name(self) -> str:
        """插件名稱"""
        ...
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化插件"""
        ...
    
    async def handle_event(self, event: Event) -> Optional[Event]:
        """處理事件"""
        ...
    
    async def shutdown(self) -> None:
        """關閉插件"""
        ...


# ============== 編排器介面 ==============

@runtime_checkable
class PlannerProtocol(Protocol):
    """規劃器介面"""
    
    async def create_plan(self, intent: Intent) -> Dict[str, Any]:
        """建立執行計畫"""
        ...


@runtime_checkable
class RouterProtocol(Protocol):
    """路由器介面"""
    
    async def route_task(self, task: Task) -> str:
        """路由任務到服務，返回服務 ID"""
        ...


@runtime_checkable
class ExecutorProtocol(Protocol):
    """執行器介面"""
    
    async def execute(self, task: Task) -> Dict[str, Any]:
        """執行任務"""
        ...


# ============== 記憶系統介面 ==============

@runtime_checkable
class SessionMemoryProtocol(Protocol):
    """Session 記憶介面 (短期)"""
    
    async def store(self, session_id: str, data: Dict[str, Any]) -> None:
        """儲存 Session 資料"""
        ...
    
    async def retrieve(self, session_id: str) -> Optional[Dict[str, Any]]:
        """取得 Session 資料"""
        ...
    
    async def clear(self, session_id: str) -> None:
        """清除 Session"""
        ...
    
    async def extend_ttl(self, session_id: str, ttl: int) -> None:
        """延長 Session TTL"""
        ...


@runtime_checkable
class SkillMemoryProtocol(Protocol):
    """Skill 記憶介面 (中期)"""
    
    async def record_skill(
        self, 
        name: str,
        trigger_patterns: List[str],
        execution_template: Dict[str, Any]
    ) -> str:
        """記錄技能"""
        ...
    
    async def find_similar_skills(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """尋找相似技能"""
        ...
    
    async def update_skill_stats(
        self, 
        skill_id: str, 
        success: bool
    ) -> None:
        """更新技能統計"""
        ...


@runtime_checkable
class LongTermMemoryProtocol(Protocol):
    """長期記憶介面 (RAG)"""
    
    async def store(
        self, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """儲存內容"""
        ...
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """檢索內容"""
        ...
    
    async def delete(self, doc_id: str) -> bool:
        """刪除內容"""
        ...


# ============== MCP 服務介面 ==============

@runtime_checkable
class MCPServiceProtocol(Protocol):
    """MCP 服務介面"""
    
    @property
    def service_id(self) -> str:
        """服務 ID"""
        ...
    
    @property
    def capabilities(self) -> List[str]:
        """服務能力列表"""
        ...
    
    async def initialize(self) -> None:
        """初始化服務"""
        ...
    
    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """執行方法"""
        ...
    
    async def health_check(self) -> bool:
        """健康檢查"""
        ...
    
    async def shutdown(self) -> None:
        """關閉服務"""
        ...


@runtime_checkable
class MCPGatewayProtocol(Protocol):
    """MCP Gateway 介面"""
    
    async def register_service(self, service: MCPServiceProtocol) -> None:
        """註冊服務"""
        ...
    
    async def unregister_service(self, service_id: str) -> None:
        """取消註冊服務"""
        ...
    
    async def call(
        self, 
        service_id: str, 
        method: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """呼叫服務方法"""
        ...
    
    async def discover_services(self) -> List[Dict[str, Any]]:
        """發現可用服務"""
        ...


# ============== 控制平面介面 ==============

@runtime_checkable
class PolicyEngineProtocol(Protocol):
    """Policy 引擎介面"""
    
    async def check_permission(
        self, 
        actor: str, 
        resource: str, 
        action: str
    ) -> tuple[bool, Optional[str]]:
        """檢查權限，返回 (允許, 原因)"""
        ...
    
    async def is_tool_allowed(
        self, 
        tool_name: str, 
        context: Context
    ) -> tuple[bool, Optional[str]]:
        """檢查工具是否允許使用"""
        ...
    
    def get_risk_level(self, tool_name: str) -> str:
        """取得工具風險等級"""
        ...


@runtime_checkable
class TracerProtocol(Protocol):
    """追蹤器介面"""
    
    def start_trace(self, name: str) -> str:
        """開始追蹤，返回 trace_id"""
        ...
    
    def start_span(
        self, 
        name: str, 
        trace_id: Optional[str] = None
    ) -> str:
        """開始 Span，返回 span_id"""
        ...
    
    def end_span(
        self, 
        span_id: str, 
        result: Optional[Any] = None
    ) -> None:
        """結束 Span"""
        ...
    
    def end_trace(self, trace_id: str) -> None:
        """結束追蹤"""
        ...


@runtime_checkable
class AuditLogProtocol(Protocol):
    """稽核日誌介面"""
    
    async def log(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """記錄稽核日誌"""
        ...
    
    async def query(
        self, 
        filters: Dict[str, Any], 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查詢稽核日誌"""
        ...


@runtime_checkable 
class CostTrackerProtocol(Protocol):
    """成本追蹤介面"""
    
    def record(
        self, 
        input_tokens: int, 
        output_tokens: int, 
        model: str
    ) -> None:
        """記錄使用量"""
        ...
    
    def get_total_cost(self) -> float:
        """取得總成本"""
        ...
    
    def is_over_budget(self, budget: Optional[float] = None) -> bool:
        """是否超出預算"""
        ...
