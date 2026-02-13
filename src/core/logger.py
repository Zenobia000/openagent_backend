"""
結構化日誌系統 - 優化版
簡潔、清晰、易於追蹤的日誌格式
"""

import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from contextlib import contextmanager
import time
from pathlib import Path
from enum import Enum

from .models import EventType, SSEEvent


# ANSI 顏色碼
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    RED = '\033[31m'
    GRAY = '\033[90m'
    WHITE = '\033[37m'


class LogLevel(Enum):
    """日誌等級"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日誌分類"""
    SYSTEM = "system"          # 系統啟動、初始化
    REQUEST = "request"        # 請求處理
    LLM = "llm"                # LLM 調用
    TOOL = "tool"              # 工具決策
    SEARCH = "search"          # 搜索操作
    MEMORY = "memory"          # 記憶體操作
    PERFORMANCE = "perf"       # 性能監控
    ERROR = "error"            # 錯誤
    SSE = "sse"                # SSE 事件（僅寫入檔案）


class StructuredLogger:
    """結構化日誌管理器 - 優化版"""

    def __init__(self, service_name: str = "opencode", log_level: str = "INFO"):
        self.service = service_name
        self.logger = logging.getLogger(service_name)

        # 設置日誌等級
        self.log_level = LogLevel[log_level]
        self.min_level_value = self._get_level_value(self.log_level)

        # SSE 回調函數
        self._sse_callback: Optional[Callable] = None

        # 當前上下文
        self.trace_id: Optional[str] = None
        self.context: Dict[str, Any] = {}

        # 初始化日誌目錄
        self.log_dir = Path(__file__).parent.parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

    def _get_level_value(self, level: LogLevel) -> int:
        """獲取日誌等級數值"""
        level_values = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50
        }
        return level_values.get(level, 20)

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

    def _should_log_to_console(self, level: LogLevel, category: LogCategory) -> bool:
        """判斷是否應該輸出到控制台"""
        # SSE 事件不輸出到控制台（太多噪音）
        if category == LogCategory.SSE:
            return False

        # 根據日誌等級判斷
        level_value = self._get_level_value(level)
        return level_value >= self.min_level_value

    def _format_console_message(self, level: LogLevel, category: LogCategory, message: str, **kwargs) -> str:
        """格式化控制台訊息"""
        # 時間戳
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 等級顏色
        level_colors = {
            LogLevel.DEBUG: Colors.GRAY,
            LogLevel.INFO: Colors.GREEN,
            LogLevel.WARNING: Colors.YELLOW,
            LogLevel.ERROR: Colors.RED,
            LogLevel.CRITICAL: Colors.MAGENTA
        }

        # 分類圖示
        category_icons = {
            LogCategory.SYSTEM: "🚀",
            LogCategory.REQUEST: "📥",
            LogCategory.LLM: "🤖",
            LogCategory.TOOL: "🔧",
            LogCategory.SEARCH: "🔍",
            LogCategory.MEMORY: "💾",
            LogCategory.PERFORMANCE: "⚡",
            LogCategory.ERROR: "❌"
        }

        level_color = level_colors.get(level, Colors.WHITE)
        icon = category_icons.get(category, "")

        # 構建訊息
        level_text = f"{level_color}{level.value:8}{Colors.RESET}"

        # 添加關鍵資訊
        extra_info = []
        if self.trace_id:
            extra_info.append(f"[{Colors.CYAN}{self.trace_id[:8]}{Colors.RESET}]")

        # 性能資訊
        if "duration_ms" in kwargs:
            duration = kwargs["duration_ms"]
            if duration > 1000:
                extra_info.append(f"{Colors.YELLOW}{duration:.0f}ms{Colors.RESET}")
            else:
                extra_info.append(f"{duration:.0f}ms")

        # LLM 資訊
        if "llm" in kwargs:
            llm_info = kwargs["llm"]
            tokens = llm_info.get("total_tokens", 0)
            extra_info.append(f"tokens={tokens}")

        extra_str = " ".join(extra_info)
        if extra_str:
            extra_str = " " + extra_str

        return f"{timestamp} {level_text} {icon} {message}{extra_str}"

    def _log(self, level: LogLevel, message: str, category: LogCategory = LogCategory.SYSTEM,
             module: str = None, function: str = None, **kwargs):
        """內部日誌方法 - 優化版"""
        # Sanitize surrogate characters from WSL2 / non-UTF-8 terminal input
        message = message.encode('utf-8', errors='replace').decode('utf-8')

        # 控制台輸出
        if self._should_log_to_console(level, category):
            console_msg = self._format_console_message(level, category, message, **kwargs)
            print(console_msg)

        # 檔案輸出（純文本格式）- 更易讀
        log_file = self.log_dir / f"opencode_{datetime.now().strftime('%Y%m%d')}.log"

        # 格式化檔案日誌
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # 建構日誌行
        log_parts = [
            timestamp,
            f"[{level.value:8}]",
            f"[{category.value:10}]"
        ]

        # 添加 trace_id (如果有)
        if self.trace_id:
            log_parts.append(f"[{self.trace_id[:8]}]")
        else:
            log_parts.append("[--------]")

        # 添加模組和函數
        module_name = module or self.service
        function_name = function or "process"
        log_parts.append(f"{module_name}.{function_name}")

        # 添加訊息
        log_parts.append(f"| {message}")

        # 添加重要的額外資訊
        extra_info = []

        # 添加 LLM 資訊
        if "llm" in kwargs:
            llm_info = kwargs["llm"]
            extra_info.append(f"model={llm_info.get('model', 'unknown')}")
            extra_info.append(f"tokens={llm_info.get('total_tokens', 0)}")
            if "duration_ms" in llm_info:
                extra_info.append(f"time={llm_info['duration_ms']:.0f}ms")

        # 添加性能資訊
        elif "duration_ms" in kwargs and "llm" not in kwargs:
            extra_info.append(f"time={kwargs['duration_ms']:.0f}ms")

        # 添加工具決策
        if "tool_decision" in kwargs:
            tool = kwargs["tool_decision"]
            extra_info.append(f"tool={tool.get('selected', 'unknown')}")
            extra_info.append(f"conf={tool.get('confidence', 0):.2f}")

        # 添加搜索資訊
        if "search" in kwargs:
            search = kwargs["search"]
            if "results" in search:
                extra_info.append(f"results={search['results']}")
            if "provider" in search:
                extra_info.append(f"provider={search['provider']}")

        # 添加錯誤資訊
        if "error" in kwargs:
            error = kwargs["error"]
            extra_info.append(f"error_type={error.get('type', 'unknown')}")

        # 如果有額外資訊，添加到日誌行
        if extra_info:
            log_parts.append(f"[{', '.join(extra_info)}]")

        # 組合最終日誌行
        log_line = " ".join(log_parts)

        # 寫入檔案 (replace surrogates from WSL2 terminal input)
        with open(log_file, 'a', encoding='utf-8', errors='replace') as f:
            f.write(log_line + '\n')

    # 標準日誌方法
    def debug(self, message: str, module: str = None, function: str = None, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        self._log(LogLevel.DEBUG, message, category, module, function, **kwargs)

    def info(self, message: str, module: str = None, function: str = None, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        self._log(LogLevel.INFO, message, category, module, function, **kwargs)

    def warning(self, message: str, module: str = None, function: str = None, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        self._log(LogLevel.WARNING, message, category, module, function, **kwargs)

    def error(self, message: str, module: str = None, function: str = None, category: LogCategory = LogCategory.ERROR, **kwargs):
        self._log(LogLevel.ERROR, message, category, module, function, **kwargs)

    # SSE 事件方法 - 只寫入檔案，不輸出到控制台
    def emit_sse(self, event: SSEEvent):
        """發送 SSE 事件"""
        if self._sse_callback:
            self._sse_callback(event.signal, event.to_dict())

        # 只記錄到檔案，不輸出控制台
        self._log(LogLevel.DEBUG, f"SSE Event: {event.signal}", LogCategory.SSE,
                  sse_event=event.to_dict())

    def progress(self, step: str, status: str, data: Any = None):
        """發送進度事件"""
        event = SSEEvent(
            signal="progress",
            step=step,
            status=status,
            data=data
        )
        self.emit_sse(event)

        # 重要進度也輸出到控制台（INFO 等級）
        if status == "start":
            # 為不同步驟添加專屬圖示
            step_icons = {
                "chat": "💬",
                "knowledge-retrieval": "📚",
                "web-search": "🌐",
                "deep-thinking": "🧠",
                "knowledge-graph": "🔗",
                "code-execution": "💻",
                "code-analysis": "🔍",
                "code-generation": "⚙️",
                "rewriting": "✏️",
                "embedding": "🔢",
                "search": "🔎",
                "query-generation": "📝",
                "searching": "🔍",
                "problem-analysis": "🎯",
                "multi-perspective": "🔄",
                "deep-reasoning": "💭",
                "synthesis-reflection": "🔮",
                "final-synthesis": "🎯",
                "content-preparation": "📄",
                "graph-generation": "🕸️",
                "markdown-conversion": "📋",
                "report-plan": "📊",
                "serp-query": "🔍",
                "task-list": "📝",
                "search-task": "🔎",
                "final-report": "📑"
            }
            icon = step_icons.get(step, "▶️")  # 默認圖示
            self.info(f"{icon} Starting: {step}", category=LogCategory.REQUEST)
        elif status == "end":
            self.info(f"✅ Completed: {step}", category=LogCategory.REQUEST)

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
    def measure(self, operation: str, category: LogCategory = LogCategory.PERFORMANCE):
        """測量操作性能"""
        start_time = time.time()

        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # 只有超過 100ms 的操作才記錄
            if duration_ms > 100:
                self.info(
                    f"{operation}",
                    category=category,
                    duration_ms=round(duration_ms, 2)
                )

    # 專門的日誌方法
    def log_llm_call(self, model: str, tokens_in: int, tokens_out: int, duration_ms: float):
        """記錄 LLM 調用"""
        self.info(
            f"🤖 LLM Call: {model}",
            category=LogCategory.LLM,
            llm={
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total_tokens": tokens_in + tokens_out,
                "duration_ms": round(duration_ms, 2)
            },
            duration_ms=round(duration_ms, 2)
        )

    def log_tool_decision(self, tool: str, confidence: float, reason: str = None):
        """記錄工具決策"""
        self.info(
            f"Tool Decision: {tool} (confidence: {confidence:.2f})",
            category=LogCategory.TOOL,
            tool_decision={
                "selected": tool,
                "confidence": confidence,
                "reason": reason
            }
        )

    def log_search(self, query: str, results_count: int = 0, provider: str = None):
        """記錄搜索操作"""
        self.info(
            f"Search: {query[:50]}...",
            category=LogCategory.SEARCH,
            search={
                "query": query,
                "results": results_count,
                "provider": provider
            }
        )

    def log_memory_operation(self, operation: str, key: str = None, size: int = None):
        """記錄記憶體操作"""
        self.info(
            f"Memory {operation}: {key or 'batch'}",
            category=LogCategory.MEMORY,
            memory={
                "operation": operation,
                "key": key,
                "size": size
            }
        )

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """記錄錯誤"""
        import traceback
        self.error(
            f"{type(error).__name__}: {str(error)}",
            category=LogCategory.ERROR,
            error={
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            },
            error_context=context or {}
        )

    def log_request(self, method: str, path: str = None, query: str = None, mode: str = None):
        """記錄請求"""
        msg_parts = [method]
        if path:
            msg_parts.append(path)
        if query:
            msg_parts.append(f"'{query[:30]}...'")

        self.info(
            " ".join(msg_parts),
            category=LogCategory.REQUEST,
            request={
                "method": method,
                "path": path,
                "query": query,
                "mode": mode
            }
        )


# 全局實例 - 從環境變數讀取日誌等級
import os
log_level = os.environ.get("LOG_LEVEL", "INFO")
structured_logger = StructuredLogger(log_level=log_level)


# 便捷函數
def with_logging(func):
    """日誌裝飾器"""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        with structured_logger.measure(func_name):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                structured_logger.log_error(e, {"function": func_name})
                raise
    return wrapper