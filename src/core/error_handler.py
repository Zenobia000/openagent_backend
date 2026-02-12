"""
Enhanced Error Handling for Processors
通用錯誤處理增強模組
"""

import functools
import asyncio
from typing import Any, Callable
from datetime import datetime
from .errors import ErrorClassifier


def enhanced_error_handler(
    max_retries: int = 2,
    base_delay: float = 1.0,
    retryable_categories: list = None
):
    """
    通用錯誤處理裝飾器，為處理器提供智能重試機制

    Args:
        max_retries: 最大重試次數
        base_delay: 基礎延遲時間（秒）
        retryable_categories: 可重試的錯誤類別
    """
    if retryable_categories is None:
        retryable_categories = ["NETWORK", "LLM", "RATE_LIMIT"]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, context, *args, **kwargs) -> Any:
            """包裝函數，提供錯誤處理和重試邏輯"""

            logger = getattr(self, 'logger', None)
            retry_count = 0
            last_error = None

            # 初始化錯誤追蹤
            if not hasattr(context, 'error_history'):
                context.error_history = []

            while retry_count <= max_retries:
                try:
                    # 記錄嘗試
                    if retry_count > 0 and logger:
                        logger.info(
                            f"🔄 Retry attempt {retry_count}/{max_retries}",
                            "error_handler",
                            "retry",
                            processor=self.__class__.__name__,
                            attempt=retry_count
                        )

                    # 執行實際函數
                    result = await func(self, context, *args, **kwargs)

                    # 成功執行，記錄並返回
                    if retry_count > 0 and logger:
                        logger.info(
                            f"✅ Succeeded after {retry_count} retries",
                            "error_handler",
                            "retry_success"
                        )

                    return result

                except Exception as e:
                    # 分類錯誤
                    error_category = ErrorClassifier.classify(e)

                    # 記錄錯誤
                    error_record = {
                        "timestamp": datetime.now().isoformat(),
                        "processor": self.__class__.__name__,
                        "error": str(e),
                        "category": error_category,
                        "retry_count": retry_count,
                        "stack_trace": str(e.__traceback__)
                    }
                    context.error_history.append(error_record)

                    if logger:
                        logger.warning(
                            f"❌ Error occurred: {e}",
                            "error_handler",
                            "error",
                            category=error_category,
                            processor=self.__class__.__name__,
                            retry_count=retry_count
                        )

                    # 判斷是否應該重試
                    if error_category in retryable_categories and retry_count < max_retries:
                        retry_count += 1
                        delay = base_delay * (2 ** (retry_count - 1))  # 指數退避

                        if logger:
                            logger.info(
                                f"⏳ Waiting {delay}s before retry...",
                                "error_handler",
                                "backoff",
                                delay=delay
                            )

                        await asyncio.sleep(delay)
                        last_error = e
                        continue

                    # 不可重試或已達最大重試次數
                    if logger:
                        logger.error(
                            f"💀 Fatal error, cannot retry: {e}",
                            "error_handler",
                            "fatal",
                            category=error_category,
                            total_retries=retry_count
                        )

                    # 添加錯誤上下文到異常
                    e.error_context = {
                        "category": error_category,
                        "retries_attempted": retry_count,
                        "processor": self.__class__.__name__,
                        "error_history": context.error_history
                    }

                    raise e

            # 所有重試都失敗
            if last_error:
                if logger:
                    logger.error(
                        f"💀 All retries exhausted",
                        "error_handler",
                        "all_retries_failed",
                        max_retries=max_retries
                    )
                raise last_error

        return wrapper
    return decorator


def track_performance(func: Callable) -> Callable:
    """
    性能追蹤裝飾器
    """
    @functools.wraps(func)
    async def wrapper(self, context, *args, **kwargs) -> Any:
        import time

        logger = getattr(self, 'logger', None)
        start_time = time.time()

        # 初始化性能指標
        if not hasattr(context, 'metrics'):
            context.metrics = {}

        processor_name = self.__class__.__name__

        try:
            # 執行函數
            result = await func(self, context, *args, **kwargs)

            # 記錄成功指標
            elapsed = time.time() - start_time
            context.metrics[processor_name] = {
                "status": "success",
                "duration": elapsed,
                "timestamp": datetime.now().isoformat()
            }

            if logger:
                logger.info(
                    f"⚡ Performance: {elapsed:.2f}s",
                    "performance",
                    "timing",
                    processor=processor_name,
                    duration=elapsed
                )

            return result

        except Exception as e:
            # 記錄失敗指標
            elapsed = time.time() - start_time
            context.metrics[processor_name] = {
                "status": "failed",
                "duration": elapsed,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

            if logger:
                logger.error(
                    f"⚡ Failed after {elapsed:.2f}s",
                    "performance",
                    "failure",
                    processor=processor_name,
                    duration=elapsed
                )

            raise

    return wrapper


def validate_input(required_fields: list = None):
    """
    輸入驗證裝飾器
    """
    if required_fields is None:
        required_fields = ['query']

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, context, *args, **kwargs) -> Any:
            logger = getattr(self, 'logger', None)

            # 驗證必要欄位
            for field in required_fields:
                if not hasattr(context.request, field) or not getattr(context.request, field):
                    error_msg = f"Required field '{field}' is missing or empty"
                    if logger:
                        logger.error(error_msg, "validation", "missing_field")
                    raise ValueError(error_msg)

            # 驗證查詢長度
            if hasattr(context.request, 'query'):
                query_len = len(context.request.query)
                if query_len > 10000:
                    error_msg = f"Query too long: {query_len} characters (max: 10000)"
                    if logger:
                        logger.error(error_msg, "validation", "query_too_long")
                    raise ValueError(error_msg)

            # 執行原函數
            return await func(self, context, *args, **kwargs)

        return wrapper
    return decorator


# 組合裝飾器：錯誤處理 + 性能追蹤 + 輸入驗證
def robust_processor(max_retries: int = 2):
    """
    組合多個增強功能的裝飾器
    """
    def decorator(func: Callable) -> Callable:
        # 應用多個裝飾器（順序很重要）
        func = validate_input()(func)
        func = track_performance(func)
        func = enhanced_error_handler(max_retries=max_retries)(func)
        return func

    return decorator


# 導出
__all__ = [
    'enhanced_error_handler',
    'track_performance',
    'validate_input',
    'robust_processor'
]