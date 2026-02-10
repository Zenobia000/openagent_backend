"""
統一日誌系統 - OpenCode Platform
實現結構化日誌記錄、事件追蹤和性能監控
"""

import json
import time
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import IntEnum
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import threading
import psutil
import logging

# ========================================
# 日誌等級定義
# ========================================
class LogLevel(IntEnum):
    """統一日誌等級"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50


# ========================================
# 日誌事件類型
# ========================================
class EventType:
    """預定義事件類型"""
    # SSE 事件
    SSE_DISPATCH = "sse_dispatch"
    SSE_CONNECTION = "sse_connection"

    # Pipeline 事件
    PIPELINE_START = "pipeline_start"
    PIPELINE_STEP = "pipeline_step"
    PIPELINE_END = "pipeline_end"

    # AI/LLM 事件
    LLM_CALL = "llm_call"
    LLM_STREAM = "llm_stream"
    LLM_ERROR = "llm_error"

    # 工具決策
    TOOL_DECISION = "tool_decision"
    TOOL_EXECUTION = "tool_execution"

    # RAG 操作
    RAG_EMBEDDING = "rag_embedding"
    RAG_RETRIEVAL = "rag_retrieval"
    RAG_INDEXING = "rag_indexing"

    # Memory 操作
    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"
    MEMORY_CLEANUP = "memory_cleanup"

    # Web 查詢
    WEB_SEARCH = "web_search"
    WEB_SCRAPE = "web_scrape"

    # MCP 協議
    MCP_REQUEST = "mcp_request"
    MCP_RESPONSE = "mcp_response"

    # 性能監控
    PERFORMANCE = "performance"

    # 錯誤追蹤
    EXCEPTION = "exception"


# ========================================
# 日誌條目結構
# ========================================
@dataclass
class LogEntry:
    """統一日誌條目"""
    timestamp: str
    level: str
    trace_id: Optional[str]
    span_id: Optional[str]
    service: str
    module: str
    function: str
    message: str
    event_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


# ========================================
# 統一日誌管理器
# ========================================
class UnifiedLogger:
    """
    統一日誌管理器
    提供結構化日誌、追蹤和性能監控功能
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.trace_id = None
            self.span_stack = []
            self.context = {}
            self.service = "opencode"
            self.logger = logging.getLogger("UnifiedLogger")

            # 性能監控
            self.process = psutil.Process()

    def with_trace(self, trace_id: str = None) -> 'UnifiedLogger':
        """設置或生成追蹤 ID"""
        self.trace_id = trace_id or str(uuid.uuid4())
        return self

    def new_span(self) -> str:
        """創建新的 span ID"""
        span_id = str(uuid.uuid4())[:8]
        self.span_stack.append(span_id)
        return span_id

    def end_span(self):
        """結束當前 span"""
        if self.span_stack:
            self.span_stack.pop()

    def with_context(self, **kwargs) -> 'UnifiedLogger':
        """添加上下文信息"""
        self.context.update(kwargs)
        return self

    def clear_context(self):
        """清除上下文"""
        self.context = {}

    def log(
        self,
        level: LogLevel,
        message: str,
        event_type: str = None,
        **kwargs
    ):
        """記錄結構化日誌"""
        # 獲取調用者信息
        import inspect
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        module_name = caller_frame.f_globals.get('__name__', 'unknown')
        function_name = caller_frame.f_code.co_name

        # 構建日誌條目
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level.name,
            trace_id=self.trace_id,
            span_id=self.span_stack[-1] if self.span_stack else None,
            service=self.service,
            module=module_name,
            function=function_name,
            message=message,
            event_type=event_type,
            context=self.context.copy() if self.context else None,
            metadata=kwargs.get('metadata'),
            performance=kwargs.get('performance'),
            error=kwargs.get('error')
        )

        # 輸出日誌
        self._write(entry, level)

    def _write(self, entry: LogEntry, level: LogLevel):
        """寫入日誌"""
        # 轉換為 dict 並移除 None 值
        log_dict = {k: v for k, v in asdict(entry).items() if v is not None}

        # 根據日誌級別選擇輸出方法
        if level >= LogLevel.ERROR:
            self.logger.error(json.dumps(log_dict, ensure_ascii=False))
        elif level >= LogLevel.WARN:
            self.logger.warning(json.dumps(log_dict, ensure_ascii=False))
        elif level >= LogLevel.INFO:
            self.logger.info(json.dumps(log_dict, ensure_ascii=False))
        else:
            self.logger.debug(json.dumps(log_dict, ensure_ascii=False))

    # 便捷方法
    def trace(self, message: str, **kwargs):
        self.log(LogLevel.TRACE, message, **kwargs)

    def debug(self, message: str, **kwargs):
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self.log(LogLevel.INFO, message, **kwargs)

    def warn(self, message: str, **kwargs):
        self.log(LogLevel.WARN, message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self.log(LogLevel.CRITICAL, message, **kwargs)

    # 特定事件記錄方法
    def log_llm_call(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost_usd: float = None
    ):
        """記錄 LLM 調用"""
        self.info(
            f"LLM call to {provider}/{model}",
            event_type=EventType.LLM_CALL,
            metadata={
                "provider": provider,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost_usd": cost_usd
            },
            performance={
                "latency_ms": latency_ms
            }
        )

    def log_tool_decision(
        self,
        selected_tool: str,
        alternatives: List[str],
        confidence: float,
        reason: str = None
    ):
        """記錄工具決策"""
        self.info(
            f"Tool selected: {selected_tool}",
            event_type=EventType.TOOL_DECISION,
            metadata={
                "selected": selected_tool,
                "alternatives": alternatives,
                "confidence": confidence,
                "reason": reason
            }
        )

    def log_rag_operation(
        self,
        operation: str,
        collection: str,
        query_time_ms: float,
        results_count: int = None,
        top_score: float = None
    ):
        """記錄 RAG 操作"""
        self.debug(
            f"RAG {operation} on {collection}",
            event_type=EventType.RAG_RETRIEVAL,
            metadata={
                "operation": operation,
                "collection": collection,
                "results_count": results_count,
                "top_score": top_score
            },
            performance={
                "query_time_ms": query_time_ms
            }
        )

    def log_exception(self, exc: Exception, context: Dict[str, Any] = None):
        """記錄異常"""
        self.error(
            f"Exception: {type(exc).__name__}: {str(exc)}",
            event_type=EventType.EXCEPTION,
            error={
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc()
            },
            metadata=context
        )

    @contextmanager
    def measure_performance(self, operation: str):
        """性能測量上下文管理器"""
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        span_id = self.new_span()
        self.debug(f"Starting {operation}", event_type=EventType.PERFORMANCE)

        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            end_memory = self.process.memory_info().rss / 1024 / 1024
            memory_delta = end_memory - start_memory

            self.debug(
                f"Completed {operation}",
                event_type=EventType.PERFORMANCE,
                performance={
                    "operation": operation,
                    "duration_ms": round(duration_ms, 2),
                    "memory_start_mb": round(start_memory, 2),
                    "memory_end_mb": round(end_memory, 2),
                    "memory_delta_mb": round(memory_delta, 2)
                }
            )
            self.end_span()


# ========================================
# SSE 事件記錄器
# ========================================
class SSEEventLogger:
    """SSE 事件專用記錄器"""

    def __init__(self, logger: UnifiedLogger):
        self.logger = logger

    def log_progress(self, step: str, status: str, data: Any = None):
        """記錄 progress 事件"""
        self.logger.info(
            f"Progress: {step} - {status}",
            event_type=EventType.SSE_DISPATCH,
            metadata={
                "signal": "progress",
                "step": step,
                "status": status,
                "data": data
            }
        )

    def log_message(self, text: str, is_streaming: bool = False):
        """記錄 message 事件"""
        self.logger.debug(
            f"Message: {text[:50]}..." if len(text) > 50 else f"Message: {text}",
            event_type=EventType.SSE_DISPATCH,
            metadata={
                "signal": "message",
                "streaming": is_streaming,
                "text_length": len(text)
            }
        )

    def log_reasoning(self, text: str, is_streaming: bool = False):
        """記錄 reasoning 事件"""
        self.logger.debug(
            f"Reasoning: {text[:50]}..." if len(text) > 50 else f"Reasoning: {text}",
            event_type=EventType.SSE_DISPATCH,
            metadata={
                "signal": "reasoning",
                "streaming": is_streaming,
                "text_length": len(text)
            }
        )


# ========================================
# 全局實例
# ========================================
unified_logger = UnifiedLogger()
sse_logger = SSEEventLogger(unified_logger)


# ========================================
# 裝飾器工具
# ========================================
def log_function_call(level: LogLevel = LogLevel.DEBUG):
    """函數調用日誌裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            unified_logger.debug(f"Calling {func.__name__}",
                               metadata={"args_count": len(args), "kwargs": list(kwargs.keys())})
            try:
                result = func(*args, **kwargs)
                unified_logger.debug(f"Completed {func.__name__}")
                return result
            except Exception as e:
                unified_logger.log_exception(e, {"function": func.__name__})
                raise
        return wrapper
    return decorator


def measure_async_performance(operation: str = None):
    """異步性能測量裝飾器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            async with unified_logger.measure_performance(op_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator