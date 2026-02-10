"""
統一數據模型 - 簡化和標準化
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
import uuid


class ProcessingMode(Enum):
    """處理模式 - 簡化版"""
    AUTO = "auto"           # 自動選擇
    CHAT = "chat"           # 對話模式
    KNOWLEDGE = "knowledge" # 知識檢索
    SEARCH = "search"       # 網路搜索
    CODE = "code"           # 代碼執行
    THINKING = "thinking"   # 深度思考


class EventType(Enum):
    """事件類型 - SSE 兼容"""
    INFO = "info"
    MESSAGE = "message"
    REASONING = "reasoning"
    PROGRESS = "progress"
    ERROR = "error"
    RESULT = "result"


@dataclass
class Request:
    """統一請求模型"""
    query: str
    mode: ProcessingMode = ProcessingMode.AUTO
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 可選參數
    temperature: float = 0.7
    max_tokens: int = 4000
    stream: bool = False

    # 元數據
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """確保 mode 是 ProcessingMode 枚舉"""
        if isinstance(self.mode, str):
            self.mode = ProcessingMode(self.mode)


@dataclass
class Response:
    """統一響應模型"""
    result: str
    mode: ProcessingMode
    trace_id: str

    # 使用統計
    tokens_used: int = 0
    time_ms: float = 0
    cost_usd: float = 0

    # 附加數據
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def add_event(self, event_type: EventType, data: Any):
        """添加事件到響應"""
        self.events.append({
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })


@dataclass
class ProcessingContext:
    """處理上下文 - 跨組件共享狀態"""
    request: Request
    response: Response

    # 狀態追蹤
    current_step: str = ""
    steps_completed: List[str] = field(default_factory=list)

    # 工具決策
    selected_tool: Optional[str] = None
    tool_confidence: float = 0.0

    # 性能指標
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())

    # 中間結果
    intermediate_results: Dict[str, Any] = field(default_factory=dict)

    def mark_step_complete(self, step: str):
        """標記步驟完成"""
        self.steps_completed.append(step)
        self.current_step = ""

    def set_current_step(self, step: str):
        """設置當前步驟"""
        self.current_step = step

    def get_elapsed_time(self) -> float:
        """獲取已用時間（毫秒）"""
        return (datetime.utcnow().timestamp() - self.start_time) * 1000


@dataclass
class SSEEvent:
    """SSE 事件模型"""
    signal: str  # info, message, reasoning, progress, error
    data: Any
    step: Optional[str] = None
    status: Optional[str] = None  # start, end, error

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        result = {
            "signal": self.signal,
            "data": self.data
        }
        if self.step:
            result["step"] = self.step
        if self.status:
            result["status"] = self.status
        return result