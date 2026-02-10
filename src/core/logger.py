"""
結構化日誌系統 - 簡化版
整合 SSE 事件和系統日誌
"""

import json
import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from contextlib import contextmanager
import time

from .models import EventType, SSEEvent


class StructuredLogger:
    """結構化日誌管理器 - 簡化版"""

    def __init__(self, service_name: str = "opencode"):
        self.service = service_name
        self.logger = logging.getLogger(service_name)

        # SSE 回調函數
        self._sse_callback: Optional[Callable] = None

        # 當前上下文
        self.trace_id: Optional[str] = None
        self.context: Dict[str, Any] = {}

    def set_trace(self, trace_id: str):
        """設置追蹤 ID"""
        self.trace_id = trace_id

    def set_context(self, **kwargs):
        """設置上下文"""
        self.context.update(kwargs)

    def clear_context(self):
        """清除上下文"""
        self.context = {}
        self.trace_id = None

    def set_sse_callback(self, callback: Callable):
        """設置 SSE 事件回調"""
        self._sse_callback = callback

    def _log(self, level: str, message: str, **kwargs):
        """內部日誌方法"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "service": self.service,
            "message": message,
            "trace_id": self.trace_id,
            **self.context,
            **kwargs
        }

        # 移除 None 值
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        # 輸出日誌
        getattr(self.logger, level.lower())(json.dumps(log_entry, ensure_ascii=False))

    # 標準日誌方法
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)

    # SSE 事件方法
    def emit_sse(self, event: SSEEvent):
        """發送 SSE 事件"""
        if self._sse_callback:
            self._sse_callback(event.signal, event.to_dict())

        # 同時記錄到日誌
        self.debug(f"SSE Event: {event.signal}", sse_event=event.to_dict())

    def progress(self, step: str, status: str, data: Any = None):
        """發送進度事件"""
        event = SSEEvent(
            signal="progress",
            step=step,
            status=status,
            data=data
        )
        self.emit_sse(event)

    def message(self, text: str, streaming: bool = False):
        """發送消息事件"""
        event = SSEEvent(
            signal="message",
            data={"type": "text", "text": text, "streaming": streaming}
        )
        self.emit_sse(event)

    def reasoning(self, text: str, streaming: bool = False):
        """發送推理事件"""
        event = SSEEvent(
            signal="reasoning",
            data={"type": "text", "text": text, "streaming": streaming}
        )
        self.emit_sse(event)

    # 性能監控
    @contextmanager
    def measure(self, operation: str):
        """測量操作性能"""
        start_time = time.time()
        self.debug(f"Starting: {operation}")

        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"Completed: {operation}",
                performance={
                    "operation": operation,
                    "duration_ms": round(duration_ms, 2)
                }
            )

    # 專門的日誌方法
    def log_llm_call(self, model: str, tokens_in: int, tokens_out: int, duration_ms: float):
        """記錄 LLM 調用"""
        self.info(
            f"LLM Call: {model}",
            llm={
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total_tokens": tokens_in + tokens_out,
                "duration_ms": duration_ms
            }
        )

    def log_tool_decision(self, tool: str, confidence: float, reason: str = None):
        """記錄工具決策"""
        self.info(
            f"Tool Decision: {tool}",
            tool_decision={
                "selected": tool,
                "confidence": confidence,
                "reason": reason
            }
        )

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """記錄錯誤"""
        import traceback
        self.error(
            f"Error: {type(error).__name__}",
            error={
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            },
            error_context=context or {}
        )


# 全局實例
structured_logger = StructuredLogger()


# 便捷函數
def with_logging(func):
    """日誌裝飾器"""
    def wrapper(*args, **kwargs):
        structured_logger.debug(f"Calling {func.__name__}")
        try:
            result = func(*args, **kwargs)
            structured_logger.debug(f"Completed {func.__name__}")
            return result
        except Exception as e:
            structured_logger.log_error(e, {"function": func.__name__})
            raise
    return wrapper