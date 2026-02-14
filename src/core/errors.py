"""Error classification, retry, and fallback for the processing pipeline.

Provides:
- ErrorClassifier: categorize exceptions
- ExponentialBackoff: retry decorator with 2^n backoff
- Fallback utilities for LLM calls
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorCategory(str, Enum):
    NETWORK = "network"
    LLM = "llm"
    RESOURCE_LIMIT = "resource_limit"
    BUSINESS = "business"
    UNKNOWN = "unknown"


class ErrorClassifier:
    """Classify exceptions into actionable categories."""

    _NETWORK_KEYWORDS = ("timeout", "connection", "dns", "ssl", "socket", "unreachable")
    _LLM_KEYWORDS = ("rate_limit", "rate limit", "context_length", "content_filter", "model_not_found", "api_error")
    _RESOURCE_KEYWORDS = ("memory", "disk", "quota", "oom", "out of memory", "resource")

    @classmethod
    def classify(cls, error: Exception) -> ErrorCategory:
        # Check for our structured LLM exceptions first
        try:
            from services.llm.errors import LLMError, ProviderError, ValidationError
            if isinstance(error, ProviderError):
                return ErrorCategory.LLM
            if isinstance(error, ValidationError):
                return ErrorCategory.BUSINESS
            if isinstance(error, LLMError):
                return ErrorCategory.LLM
        except ImportError:
            pass

        msg = str(error).lower()
        etype = type(error).__name__.lower()

        if any(kw in msg or kw in etype for kw in cls._NETWORK_KEYWORDS):
            return ErrorCategory.NETWORK
        if any(kw in msg or kw in etype for kw in cls._LLM_KEYWORDS):
            return ErrorCategory.LLM
        if any(kw in msg or kw in etype for kw in cls._RESOURCE_KEYWORDS):
            return ErrorCategory.RESOURCE_LIMIT
        if isinstance(error, (ValueError, KeyError, TypeError)):
            return ErrorCategory.BUSINESS
        return ErrorCategory.UNKNOWN

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        # Use explicit retryable attribute if available (from our exception hierarchy)
        if hasattr(error, "retryable"):
            return error.retryable  # type: ignore[no-any-return]

        # Otherwise classify by category
        category = cls.classify(error)
        return category in (ErrorCategory.NETWORK, ErrorCategory.LLM)


async def retry_with_backoff(
    fn: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
) -> Any:
    """Call an async function with exponential backoff retry.

    Retries only for network/LLM errors (classified as retryable).
    """
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt >= max_retries or not ErrorClassifier.is_retryable(e):
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Retry %d/%d after %.1fs: %s",
                attempt + 1, max_retries, delay, e,
            )
            await asyncio.sleep(delay)
    raise last_error  # unreachable, but makes type checker happy


async def llm_fallback(
    primary_fn: Callable,
    fallback_fn: Callable,
    *args,
    **kwargs,
) -> Any:
    """Try primary LLM call, fall back to secondary on failure."""
    try:
        return await primary_fn(*args, **kwargs)
    except Exception as primary_error:
        category = ErrorClassifier.classify(primary_error)
        logger.warning(
            "Primary LLM failed (%s: %s), trying fallback",
            category.value, primary_error,
        )
        return await fallback_fn(*args, **kwargs)
