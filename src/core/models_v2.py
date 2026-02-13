"""
數據模型 V2 - Linus 風格重構

核心原則:
1. 數據自包含 - 無字典映射特殊情況
2. 不可變性 - 使用 frozen dataclass
3. 類型安全 - 完整的 type hints
4. 簡潔性 - 消除冗余字段

Reference: docs/REFACTORING_WBS_V2_LINUS.md Phase 1.1
Code Review: ProcessingMode 字典映射問題
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid


# ============================================
# Phase 1.1: ProcessingMode 重構
# ============================================

class RuntimeType(Enum):
    """Runtime type for execution dispatch"""
    MODEL = "model"      # ModelRuntime: System 1 + System 2
    AGENT = "agent"      # AgentRuntime: Stateful workflows


@dataclass(frozen=True)
class ProcessingMode:
    """
    處理模式 - 數據自包含，無特殊情況
    
    ❌ OLD (Bad):
        class ProcessingMode(Enum):
            @property
            def cognitive_level(self):
                return _mapping.get(self.value)  # 字典映射
    
    ✓ NEW (Good):
        ProcessingMode("chat", "system1", ...)  # 數據自包含
    
    Linus: "Good programmers worry about data structures."
    """
    name: str                    # Unique identifier: "chat", "search", etc.
    cognitive_level: str         # "system1" | "system2" | "agent"
    runtime_type: RuntimeType    # Dispatch target
    description: str             # Human-readable description
    
    # Processing defaults
    default_temperature: float = 0.7
    default_max_tokens: int = 4000
    
    # Metadata for routing hints
    keywords: tuple = ()         # Query matching keywords
    priority: int = 0            # For conflict resolution (higher = preferred)
    
    def __str__(self) -> str:
        return self.name
    
    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.name == other
        if isinstance(other, ProcessingMode):
            return self.name == other.name
        return False
    
    def __hash__(self) -> int:
        return hash(self.name)


class Modes:
    """
    預定義的處理模式常量
    
    ✓ 優點:
    - 集中定義，一處修改
    - 類型安全
    - IDE 自動補全
    - 無字典映射
    """
    
    # System 1: Fast, Intuitive (< 3s)
    CHAT = ProcessingMode(
        name="chat",
        cognitive_level="system1",
        runtime_type=RuntimeType.MODEL,
        description="Quick conversational response",
        default_temperature=0.7,
        keywords=("聊天", "chat", "對話", "問", "tell me"),
        priority=1
    )
    
    KNOWLEDGE = ProcessingMode(
        name="knowledge",
        cognitive_level="system1",
        runtime_type=RuntimeType.MODEL,
        description="Knowledge base retrieval (RAG)",
        default_temperature=0.3,  # Lower for factual accuracy
        keywords=("知識", "knowledge", "解釋", "explain", "what is"),
        priority=2
    )
    
    # System 2: Deliberate, Analytical (< 15s)
    SEARCH = ProcessingMode(
        name="search",
        cognitive_level="system2",
        runtime_type=RuntimeType.MODEL,
        description="Web search and synthesis",
        default_temperature=0.5,
        keywords=("搜尋", "search", "查詢", "find", "最新", "recent"),
        priority=3
    )
    
    THINKING = ProcessingMode(
        name="thinking",
        cognitive_level="system2",
        runtime_type=RuntimeType.MODEL,
        description="Deep analytical thinking",
        default_temperature=0.8,  # Higher for creativity
        keywords=("思考", "think", "分析", "analyze", "評估", "evaluate"),
        priority=2
    )
    
    CODE = ProcessingMode(
        name="code",
        cognitive_level="system2",
        runtime_type=RuntimeType.MODEL,
        description="Code generation and execution",
        default_temperature=0.3,  # Lower for precision
        default_max_tokens=8000,  # More tokens for code
        keywords=("代碼", "code", "程式", "program", "function", "class"),
        priority=4
    )
    
    # Agent: Multi-step Workflow (< 60s)
    DEEP_RESEARCH = ProcessingMode(
        name="deep_research",
        cognitive_level="agent",
        runtime_type=RuntimeType.AGENT,
        description="Multi-phase research workflow",
        default_temperature=0.6,
        default_max_tokens=16000,  # Long reports
        keywords=("研究", "research", "深度", "deep", "報告", "report"),
        priority=5
    )
    
    # Auto mode (for backward compatibility)
    AUTO = ProcessingMode(
        name="auto",
        cognitive_level="system1",  # Default assumption
        runtime_type=RuntimeType.MODEL,
        description="Automatically select best mode",
        priority=0
    )
    
    # Mapping for backward compatibility with old ProcessingMode enum
    _BY_NAME: Dict[str, 'ProcessingMode'] = {}
    
    @classmethod
    def from_name(cls, name: str) -> 'ProcessingMode':
        """Get mode by name (backward compatibility)"""
        if not cls._BY_NAME:
            # Lazy init
            cls._BY_NAME = {
                "chat": cls.CHAT,
                "knowledge": cls.KNOWLEDGE,
                "search": cls.SEARCH,
                "thinking": cls.THINKING,
                "code": cls.CODE,
                "deep_research": cls.DEEP_RESEARCH,
                "auto": cls.AUTO,
            }
        return cls._BY_NAME.get(name.lower(), cls.CHAT)
    
    @classmethod
    def all(cls) -> List[ProcessingMode]:
        """Get all modes except AUTO"""
        return [
            cls.CHAT,
            cls.KNOWLEDGE,
            cls.SEARCH,
            cls.THINKING,
            cls.CODE,
            cls.DEEP_RESEARCH,
        ]


# ============================================
# Phase 1.2: 統一事件模型
# ============================================

class EventType(Enum):
    """事件類型 - 統一所有事件"""
    # Lifecycle
    START = "start"
    END = "end"
    
    # Information
    INFO = "info"
    MESSAGE = "message"
    PROGRESS = "progress"
    
    # Processing
    TOKEN = "token"
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    
    # Results
    SOURCE = "source"
    RESULT = "result"
    
    # Errors
    ERROR = "error"


@dataclass
class Event:
    """
    統一事件模型
    
    ❌ OLD (Bad): 三種不同的事件表示
        - EventType (Enum)
        - SSEEvent (dataclass)
        - Response.events: List[Dict]
    
    ✓ NEW (Good): 一個統一模型
        Event(type=EventType.INFO, data=...)
    
    用途:
    - SSE streaming (to_sse() method)
    - Event logging
    - Response event tracking
    """
    type: EventType
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None
    step: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於 JSON 序列化）"""
        result = {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.step:
            result["step"] = self.step
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    def to_sse(self) -> str:
        """轉換為 SSE 格式: data: {...}\n\n"""
        import json
        return f"data: {json.dumps(self.to_dict(), ensure_ascii=False)}\n\n"


# ============================================
# Phase 1.3: Request/Response 優化
# ============================================

@dataclass
class Request:
    """
    統一請求模型 - 簡化版
    
    改進:
    - 使用 Modes 常量而非 Enum
    - 添加驗證
    """
    query: str
    mode: ProcessingMode = field(default_factory=lambda: Modes.AUTO)
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Processing parameters (optional)
    temperature: Optional[float] = None  # None = use mode default
    max_tokens: Optional[int] = None     # None = use mode default
    stream: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """驗證和規範化"""
        # Validate query
        if not self.query or len(self.query.strip()) == 0:
            raise ValueError("Query cannot be empty")
        if len(self.query) > 50000:
            raise ValueError("Query too long (max 50000 characters)")
        self.query = self.query.strip()
        
        # Convert string mode to ProcessingMode (backward compatibility)
        if isinstance(self.mode, str):
            self.mode = Modes.from_name(self.mode)
        
        # Use mode defaults if not specified
        if self.temperature is None:
            self.temperature = self.mode.default_temperature
        if self.max_tokens is None:
            self.max_tokens = self.mode.default_max_tokens
        
        # Validate temperature
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"Temperature must be 0.0-2.0, got {self.temperature}")
    
    def get_effective_temperature(self) -> float:
        """獲取實際使用的溫度"""
        return self.temperature if self.temperature is not None else self.mode.default_temperature
    
    def get_effective_max_tokens(self) -> int:
        """獲取實際使用的 max tokens"""
        return self.max_tokens if self.max_tokens is not None else self.mode.default_max_tokens


@dataclass
class Response:
    """
    統一響應模型 - 使用新 Event 模型
    
    改進:
    - events: List[Dict] → List[Event] (類型安全)
    """
    result: str
    mode: ProcessingMode
    trace_id: str
    
    # Usage statistics
    tokens_used: int = 0
    time_ms: float = 0
    cost_usd: float = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # ✓ NEW: 類型安全的事件列表
    events: List[Event] = field(default_factory=list)
    
    def add_event(self, event_type: EventType, data: Any, **kwargs):
        """添加事件到響應"""
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.utcnow(),
            trace_id=self.trace_id,
            **kwargs
        )
        self.events.append(event)
    
    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        """獲取特定類型的所有事件"""
        return [e for e in self.events if e.type == event_type]


@dataclass
class ProcessingContext:
    """
    處理上下文 - 簡化版
    
    改進:
    - 移除冗余字段
    - 更清晰的職責劃分
    """
    request: Request
    response: Response
    
    # Step tracking
    current_step: str = ""
    steps_completed: List[str] = field(default_factory=list)
    
    # Token統計（統一位置）
    total_tokens: int = 0
    
    # Performance
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    
    # 簡化：移除 intermediate_results（應該存在 response.metadata）
    # 簡化：移除 selected_tool（應該在 response.events 中）
    # 簡化：移除 tool_confidence（應該在決策日誌中）
    
    def mark_step_complete(self, step: str):
        """標記步驟完成"""
        if step not in self.steps_completed:
            self.steps_completed.append(step)
        self.current_step = ""
    
    def set_current_step(self, step: str):
        """設置當前步驟"""
        self.current_step = step
    
    def get_elapsed_time(self) -> float:
        """獲取已用時間（毫秒）"""
        return (datetime.utcnow().timestamp() - self.start_time) * 1000


# ============================================
# Routing Models
# ============================================

@dataclass
class ComplexityScore:
    """Query complexity assessment"""
    score: float  # 0.0 (trivial) to 1.0 (very complex)
    factors: Dict[str, float] = field(default_factory=dict)
    recommended_level: str = "system1"


@dataclass
class RoutingDecision:
    """Result of routing analysis"""
    mode: ProcessingMode
    confidence: float = 0.85
    reason: str = ""
    complexity: Optional[ComplexityScore] = None
    delegate_to_agent: Optional[str] = None  # A2A delegation
    
    @property
    def cognitive_level(self) -> str:
        """便捷訪問認知層級"""
        return self.mode.cognitive_level
    
    @property
    def runtime_type(self) -> RuntimeType:
        """便捷訪問運行時類型"""
        return self.mode.runtime_type


# ============================================
# Runtime Models
# ============================================

@dataclass
class ExecutionResult:
    """Unified execution result from any runtime"""
    result: str
    tokens: int = 0
    duration_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Stateful workflow tracking for AgentRuntime"""
    steps: List[str] = field(default_factory=list)
    current_step: str = ""
    completed_steps: List[str] = field(default_factory=list)
    checkpoints: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    
    def advance(self, step: str):
        """Mark current step complete and move to next"""
        if self.current_step and self.current_step not in self.completed_steps:
            self.completed_steps.append(self.current_step)
        self.current_step = step
        self.status = "running"
    
    def complete(self):
        """Mark workflow as completed"""
        if self.current_step and self.current_step not in self.completed_steps:
            self.completed_steps.append(self.current_step)
        self.current_step = ""
        self.status = "completed"
    
    def checkpoint(self, key: str, data: Any):
        """Save checkpoint for potential resume"""
        self.checkpoints[key] = data


# ============================================
# Backward Compatibility Layer
# ============================================

class ProcessingModeEnum(Enum):
    """
    向後兼容層 - 模擬舊的 ProcessingMode Enum
    
    用法:
        # Old code (still works)
        from core.models import ProcessingMode
        mode = ProcessingMode.CHAT
        
        # New code (preferred)
        from core.models_v2 import Modes
        mode = Modes.CHAT
    """
    AUTO = "auto"
    CHAT = "chat"
    KNOWLEDGE = "knowledge"
    SEARCH = "search"
    CODE = "code"
    THINKING = "thinking"
    DEEP_RESEARCH = "deep_research"
    
    def to_v2(self) -> ProcessingMode:
        """Convert to V2 ProcessingMode"""
        return Modes.from_name(self.value)
    
    @property
    def cognitive_level(self) -> str:
        """Backward compatibility for cognitive_level property"""
        return self.to_v2().cognitive_level


# Export for backward compatibility
ProcessingMode_LEGACY = ProcessingModeEnum


# ============================================
# Validation & Utilities
# ============================================

def validate_request(request: Request) -> None:
    """Validate request before processing (can raise ValueError)"""
    # Validation happens in Request.__post_init__
    # This function is for additional runtime validation if needed
    pass


def create_response(request: Request) -> Response:
    """Factory function to create Response from Request"""
    return Response(
        result="",
        mode=request.mode,
        trace_id=request.trace_id,
    )


def create_context(request: Request) -> ProcessingContext:
    """Factory function to create ProcessingContext"""
    response = create_response(request)
    return ProcessingContext(request=request, response=response)
