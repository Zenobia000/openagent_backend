"""Decorator-based error handling for processors.

Provides:
- enhanced_error_handler: decorator with retry + category filtering
- robust_processor: alias kept for backwards compatibility
"""

import asyncio
import functools
import logging
from typing import List, Optional

from .errors import ErrorClassifier, ErrorCategory

logger = logging.getLogger(__name__)


def enhanced_error_handler(
    max_retries: int = 1,
    retryable_categories: Optional[List[str]] = None,
    base_delay: float = 1.0,
):
    """Decorator that adds retry with exponential backoff to async processor methods.

    Args:
        max_retries: Maximum number of retry attempts.
        retryable_categories: Error category names that should trigger a retry
            (e.g. ["NETWORK", "LLM"]). If None, uses ErrorClassifier.is_retryable.
        base_delay: Base delay in seconds for exponential backoff.
    """
    _retryable_set = None
    if retryable_categories:
        _retryable_set = set()
        for c in retryable_categories:
            try:
                _retryable_set.add(ErrorCategory(c.lower()))
            except ValueError:
                pass  # skip unknown categories like "SANDBOX"

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_error: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    category = ErrorClassifier.classify(e)

                    should_retry = (
                        category in _retryable_set
                        if _retryable_set is not None
                        else ErrorClassifier.is_retryable(e)
                    )

                    if attempt >= max_retries or not should_retry:
                        raise

                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Retry %d/%d after %.1fs (%s): %s",
                        attempt + 1, max_retries, delay, category.value, e,
                    )
                    await asyncio.sleep(delay)
            raise last_error  # unreachable
        return wrapper
    return decorator


# Alias kept for backwards compatibility
robust_processor = enhanced_error_handler
