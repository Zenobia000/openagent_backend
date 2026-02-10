"""
SRE-Compliant Logging System
專業的分層日誌架構，符合 SRE 最佳實踐
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
import threading
from queue import Queue
import gzip
import shutil


class LogCategory(Enum):
    """日誌分類 - 對應不同的關注點"""
    TRANSACTION = "transaction"  # 交易日誌 - API 請求/回應
    AUDIT = "audit"              # 審計日誌 - 用戶操作、權限變更
    PERFORMANCE = "performance"  # 性能日誌 - 延遲、吞吐量、資源使用
    SECURITY = "security"        # 安全日誌 - 認證、授權、異常訪問
    SYSTEM = "system"            # 系統日誌 - 啟動、關閉、配置變更
    APPLICATION = "application"  # 應用日誌 - 業務邏輯、處理流程
    ERROR = "error"              # 錯誤日誌 - 異常、錯誤堆疊
    DEBUG = "debug"              # 調試日誌 - 開發時使用
    ANALYTICS = "analytics"      # 分析日誌 - 用戶行為、業務指標
    INTEGRATION = "integration"  # 整合日誌 - 外部服務調用


class LogLevel(Enum):
    """日誌級別 - 符合 RFC 5424"""
    EMERGENCY = 0  # 系統不可用
    ALERT = 1      # 必須立即採取行動
    CRITICAL = 2   # 關鍵狀況
    ERROR = 3      # 錯誤狀況
    WARNING = 4    # 警告狀況
    NOTICE = 5     # 正常但重要的狀況
    INFO = 6       # 資訊性消息
    DEBUG = 7      # 調試級別消息


@dataclass
class LogEntry:
    """標準化日誌條目"""
    # 必要欄位
    timestamp: str
    level: str
    category: str
    service: str
    message: str

    # 追蹤欄位
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None

    # 上下文欄位
    module: Optional[str] = None
    function: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # 性能欄位
    duration_ms: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None

    # 元數據
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

    # 錯誤相關
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_json(self) -> str:
        """轉換為 JSON 格式"""
        data = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(data, ensure_ascii=False)


class LogRouter:
    """日誌路由器 - 將不同類型的日誌路由到不同的處理器"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.handlers: Dict[LogCategory, List[logging.Handler]] = {}
        self._setup_handlers()

    def _setup_handlers(self):
        """設置不同類別的日誌處理器"""
        # 確保日誌目錄存在
        log_dirs = {
            LogCategory.TRANSACTION: self.base_path / "transaction",
            LogCategory.AUDIT: self.base_path / "audit",
            LogCategory.PERFORMANCE: self.base_path / "performance",
            LogCategory.SECURITY: self.base_path / "security",
            LogCategory.ERROR: self.base_path / "error",
            LogCategory.APPLICATION: self.base_path / "application",
            LogCategory.ANALYTICS: self.base_path / "analytics",
        }

        for category, path in log_dirs.items():
            path.mkdir(parents=True, exist_ok=True)

            # 為每個類別創建檔案處理器
            file_handler = self._create_file_handler(path, category.value)
            self.handlers[category] = [file_handler]

    def _create_file_handler(self, path: Path, category: str) -> logging.Handler:
        """創建檔案處理器，支援日誌輪換"""
        from logging.handlers import TimedRotatingFileHandler

        log_file = path / f"{category}_{datetime.now().strftime('%Y%m%d')}.log"
        handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=30,  # 保留 30 天
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        return handler

    def route(self, entry: LogEntry):
        """路由日誌條目到適當的處理器"""
        category = LogCategory[entry.category.upper()]
        handlers = self.handlers.get(category, [])

        for handler in handlers:
            record = logging.LogRecord(
                name=entry.service,
                level=self._get_log_level(entry.level),
                pathname="",
                lineno=0,
                msg=entry.to_json(),
                args=(),
                exc_info=None
            )
            handler.emit(record)

    def _get_log_level(self, level: str) -> int:
        """轉換日誌級別到 logging 模組級別"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "NOTICE": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "ALERT": logging.CRITICAL,
            "EMERGENCY": logging.CRITICAL
        }
        return level_map.get(level.upper(), logging.INFO)


class AsyncLogBuffer:
    """異步日誌緩衝器 - 提高性能"""

    def __init__(self, router: LogRouter, buffer_size: int = 1000):
        self.router = router
        self.buffer_size = buffer_size
        self.queue = Queue(maxsize=buffer_size)
        self.running = True  # 必須在啟動執行緒之前設置
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        """背景工作執行緒"""
        while self.running:
            try:
                # 批量處理
                entries = []
                while not self.queue.empty() and len(entries) < 100:
                    entries.append(self.queue.get(timeout=0.1))

                for entry in entries:
                    self.router.route(entry)

            except:
                pass

    def write(self, entry: LogEntry):
        """寫入日誌到緩衝區"""
        try:
            self.queue.put_nowait(entry)
        except:
            # 緩衝區滿，直接寫入
            self.router.route(entry)

    def flush(self):
        """清空緩衝區"""
        while not self.queue.empty():
            entry = self.queue.get()
            self.router.route(entry)

    def shutdown(self):
        """關閉緩衝器"""
        self.running = False
        self.flush()
        self.worker_thread.join(timeout=5)


class SRELogger:
    """SRE 日誌管理器 - 主要介面"""

    def __init__(self, service_name: str = "opencode", base_path: Optional[Path] = None):
        self.service = service_name
        self.base_path = base_path or Path.cwd() / "logs"
        self.router = LogRouter(self.base_path)
        self.buffer = AsyncLogBuffer(self.router)

        # 上下文管理
        self.context = threading.local()

        # 性能指標收集
        self.metrics = {
            "log_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "avg_duration": 0
        }

    def set_context(self, trace_id: str = None, span_id: str = None,
                   user_id: str = None, session_id: str = None):
        """設置日誌上下文"""
        self.context.trace_id = trace_id
        self.context.span_id = span_id
        self.context.user_id = user_id
        self.context.session_id = session_id

    def clear_context(self):
        """清除上下文"""
        for attr in ['trace_id', 'span_id', 'user_id', 'session_id']:
            if hasattr(self.context, attr):
                delattr(self.context, attr)

    def _create_entry(self, level: str, category: str, message: str, **kwargs) -> LogEntry:
        """創建日誌條目"""
        return LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            category=category,
            service=self.service,
            message=message,
            trace_id=getattr(self.context, 'trace_id', None),
            span_id=getattr(self.context, 'span_id', None),
            user_id=getattr(self.context, 'user_id', None),
            session_id=getattr(self.context, 'session_id', None),
            **kwargs
        )

    # ========== 交易日誌 ==========
    def log_request(self, method: str, path: str, headers: Dict = None, body: Any = None):
        """記錄 API 請求"""
        entry = self._create_entry(
            level="INFO",
            category="transaction",
            message=f"API Request: {method} {path}",
            metadata={
                "method": method,
                "path": path,
                "headers": headers,
                "body_size": len(str(body)) if body else 0
            }
        )
        self.buffer.write(entry)

    def log_response(self, status: int, duration_ms: float, body_size: int = 0):
        """記錄 API 回應"""
        entry = self._create_entry(
            level="INFO",
            category="transaction",
            message=f"API Response: {status}",
            duration_ms=duration_ms,
            metadata={
                "status_code": status,
                "body_size": body_size,
                "success": 200 <= status < 300
            }
        )
        self.buffer.write(entry)

    # ========== 審計日誌 ==========
    def audit(self, action: str, resource: str, result: str, **details):
        """記錄審計事件"""
        entry = self._create_entry(
            level="NOTICE",
            category="audit",
            message=f"Audit: {action} on {resource} - {result}",
            metadata={
                "action": action,
                "resource": resource,
                "result": result,
                **details
            }
        )
        self.buffer.write(entry)

    # ========== 性能日誌 ==========
    def performance(self, operation: str, duration_ms: float,
                   cpu: float = None, memory: float = None):
        """記錄性能指標"""
        entry = self._create_entry(
            level="INFO",
            category="performance",
            message=f"Performance: {operation} took {duration_ms:.2f}ms",
            duration_ms=duration_ms,
            cpu_usage=cpu,
            memory_usage=memory,
            metadata={
                "operation": operation
            }
        )
        self.buffer.write(entry)

        # 更新指標
        self.metrics["avg_duration"] = (
            (self.metrics["avg_duration"] * self.metrics["log_count"] + duration_ms) /
            (self.metrics["log_count"] + 1)
        )

    # ========== 安全日誌 ==========
    def security(self, event_type: str, severity: str, details: Dict):
        """記錄安全事件"""
        level = "CRITICAL" if severity == "high" else "WARNING"
        entry = self._create_entry(
            level=level,
            category="security",
            message=f"Security Event: {event_type}",
            metadata={
                "event_type": event_type,
                "severity": severity,
                **details
            }
        )
        self.buffer.write(entry)

    # ========== 錯誤日誌 ==========
    def error(self, error: Exception, context: Dict = None):
        """記錄錯誤"""
        import traceback
        entry = self._create_entry(
            level="ERROR",
            category="error",
            message=f"Error: {type(error).__name__}",
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            metadata=context
        )
        self.buffer.write(entry)
        self.metrics["error_count"] += 1

    # ========== 應用日誌 ==========
    def info(self, message: str, module: str = None, function: str = None, **kwargs):
        """記錄一般資訊"""
        entry = self._create_entry(
            level="INFO",
            category="application",
            message=message,
            module=module,
            function=function,
            metadata=kwargs if kwargs else None
        )
        self.buffer.write(entry)
        self.metrics["log_count"] += 1

    def warning(self, message: str, module: str = None, function: str = None, **kwargs):
        """記錄警告"""
        entry = self._create_entry(
            level="WARNING",
            category="application",
            message=message,
            module=module,
            function=function,
            metadata=kwargs if kwargs else None
        )
        self.buffer.write(entry)
        self.metrics["warning_count"] += 1

    def debug(self, message: str, module: str = None, function: str = None, **kwargs):
        """記錄調試資訊"""
        entry = self._create_entry(
            level="DEBUG",
            category="debug",
            message=message,
            module=module,
            function=function,
            metadata=kwargs if kwargs else None
        )
        self.buffer.write(entry)

    # ========== 分析日誌 ==========
    def analytics(self, event: str, properties: Dict):
        """記錄分析事件"""
        entry = self._create_entry(
            level="INFO",
            category="analytics",
            message=f"Analytics: {event}",
            metadata={
                "event": event,
                "properties": properties
            }
        )
        self.buffer.write(entry)

    # ========== 工具方法 ==========
    def get_metrics(self) -> Dict[str, Any]:
        """獲取日誌指標"""
        return self.metrics.copy()

    def rotate_logs(self):
        """手動觸發日誌輪換"""
        for handlers in self.router.handlers.values():
            for handler in handlers:
                if hasattr(handler, 'doRollover'):
                    handler.doRollover()

    def compress_old_logs(self, days_old: int = 7):
        """壓縮舊日誌檔案"""
        import glob
        cutoff_date = datetime.now() - timedelta(days=days_old)

        for log_dir in self.base_path.iterdir():
            if log_dir.is_dir():
                for log_file in log_dir.glob("*.log"):
                    # 檢查檔案日期
                    file_date = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_date < cutoff_date and not log_file.suffix == '.gz':
                        # 壓縮檔案
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        log_file.unlink()  # 刪除原始檔案

    def shutdown(self):
        """關閉日誌系統"""
        self.buffer.shutdown()

        # 記錄關閉事件
        final_entry = self._create_entry(
            level="INFO",
            category="system",
            message=f"Logger shutdown - Total logs: {self.metrics['log_count']}, Errors: {self.metrics['error_count']}",
            metadata=self.metrics
        )
        self.router.route(final_entry)


# ========== 上下文管理器 ==========
from contextlib import contextmanager
from datetime import timedelta
import time

@contextmanager
def log_operation(logger: SRELogger, operation: str):
    """操作日誌上下文管理器"""
    start_time = time.time()
    logger.info(f"Starting: {operation}", function=operation)

    try:
        yield
    except Exception as e:
        logger.error(e, {"operation": operation})
        raise
    finally:
        duration = (time.time() - start_time) * 1000
        logger.performance(operation, duration)
        logger.info(f"Completed: {operation}", function=operation, duration_ms=duration)


# ========== 全局實例 ==========
sre_logger = SRELogger()


# ========== 整合現有系統 ==========
class StructuredLoggerAdapter:
    """適配器 - 將現有的 structured_logger 轉換為 SRE logger"""

    def __init__(self, sre_logger: SRELogger):
        self.sre = sre_logger

    def set_trace(self, trace_id: str):
        self.sre.set_context(trace_id=trace_id)

    def clear_context(self):
        self.sre.clear_context()

    def info(self, message: str, module: str = None, function: str = None, **kwargs):
        self.sre.info(message, module, function, **kwargs)

    def warning(self, message: str, module: str = None, function: str = None, **kwargs):
        self.sre.warning(message, module, function, **kwargs)

    def error(self, message: str, module: str = None, function: str = None, **kwargs):
        self.sre.warning(message, module, function, **kwargs)

    def debug(self, message: str, module: str = None, function: str = None, **kwargs):
        self.sre.debug(message, module, function, **kwargs)

    def log_llm_call(self, model: str, tokens_in: int, tokens_out: int, duration_ms: float):
        self.sre.analytics("llm_call", {
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "duration_ms": duration_ms
        })

    def log_tool_decision(self, tool: str, confidence: float, reason: str = None):
        self.sre.audit("tool_decision", tool, "selected", confidence=confidence, reason=reason)

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        self.sre.error(error, context)

    @contextmanager
    def measure(self, operation: str):
        with log_operation(self.sre, operation):
            yield