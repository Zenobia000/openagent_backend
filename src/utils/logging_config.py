"""
OpenCode Platform - Unified Logging Configuration
統一日誌配置系統
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
from enum import Enum


class LogLevel(Enum):
    """日誌級別定義"""
    DEBUG = logging.DEBUG       # 10 - 詳細調試信息
    INFO = logging.INFO         # 20 - 一般信息
    WARNING = logging.WARNING   # 30 - 警告信息
    ERROR = logging.ERROR       # 40 - 錯誤信息
    CRITICAL = logging.CRITICAL # 50 - 嚴重錯誤


class ColoredFormatter(logging.Formatter):
    """彩色日誌格式化器"""

    # ANSI 顏色碼
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 綠色
        'WARNING': '\033[33m',   # 黃色
        'ERROR': '\033[31m',     # 紅色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }

    def format(self, record):
        # 添加顏色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.msg = f"{self.COLORS[levelname]}{record.msg}{self.COLORS['RESET']}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """結構化 JSON 日誌格式化器"""

    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process': record.process,
            'thread': record.thread,
        }

        # 添加額外的上下文信息
        if hasattr(record, 'context'):
            log_obj['context'] = record.context

        # 添加異常信息
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


class LoggingManager:
    """統一日誌管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.loggers: Dict[str, logging.Logger] = {}
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
            self._initialized = True

    def setup_logging(
        self,
        name: str = "OpenCode",
        level: LogLevel = LogLevel.INFO,
        console: bool = True,
        file: bool = True,
        structured: bool = False
    ) -> logging.Logger:
        """設置日誌系統"""

        # 如果 logger 已存在，直接返回
        if name in self.loggers:
            return self.loggers[name]

        # 創建 logger
        logger = logging.getLogger(name)
        logger.setLevel(level.value)
        logger.handlers = []  # 清除既有 handlers

        # 控制台輸出
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level.value)

            if structured:
                console_formatter = StructuredFormatter()
            else:
                console_formatter = ColoredFormatter(
                    fmt='%(asctime)s | %(levelname)-8s | %(name)-15s | %(funcName)-20s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        # 文件輸出
        if file:
            # 主日誌文件（按日期輪轉）
            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=self.log_dir / f"{name.lower()}.log",
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            file_handler.setLevel(level.value)

            file_formatter = logging.Formatter(
                fmt='%(asctime)s | %(levelname)-8s | %(name)-15s | %(module)-20s | %(funcName)-20s | %(lineno)-4d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # 錯誤日誌文件（只記錄 ERROR 和 CRITICAL）
            error_handler = logging.handlers.RotatingFileHandler(
                filename=self.log_dir / f"{name.lower()}_error.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            logger.addHandler(error_handler)

        # 保存 logger
        self.loggers[name] = logger
        return logger

    def get_logger(self, name: str) -> logging.Logger:
        """獲取 logger"""
        if name not in self.loggers:
            return self.setup_logging(name)
        return self.loggers[name]

    def set_level(self, name: str, level: LogLevel):
        """動態設置日誌級別"""
        if name in self.loggers:
            self.loggers[name].setLevel(level.value)
            for handler in self.loggers[name].handlers:
                handler.setLevel(level.value)


class LogContext:
    """日誌上下文管理器"""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(
            f"🚀 Starting {self.operation}",
            extra={'context': self.context}
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(
                f"✅ Completed {self.operation} in {duration:.2f}s",
                extra={'context': {**self.context, 'duration': duration}}
            )
        else:
            self.logger.error(
                f"❌ Failed {self.operation} after {duration:.2f}s: {exc_val}",
                extra={'context': {**self.context, 'duration': duration, 'error': str(exc_val)}},
                exc_info=True
            )
        return False


# 創建全局日誌管理器實例
logging_manager = LoggingManager()

# 便捷函數
def get_logger(name: str, level: LogLevel = LogLevel.INFO) -> logging.Logger:
    """獲取配置好的 logger"""
    return logging_manager.setup_logging(name, level)


def log_function_call(logger: logging.Logger):
    """函數調用裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"📞 Calling {func_name} with args={args}, kwargs={kwargs}")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"✅ {func_name} returned: {result}")
                return result
            except Exception as e:
                logger.error(f"❌ {func_name} failed: {e}", exc_info=True)
                raise

        return wrapper
    return decorator


# 導出
__all__ = [
    'LogLevel',
    'LoggingManager',
    'LogContext',
    'get_logger',
    'log_function_call',
    'logging_manager'
]