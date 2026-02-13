"""Multi-provider LLM client with automatic fallback chain.

Wraps multiple LLM providers behind the same generate()/stream() interface.
On failure, transparently falls to the next provider in the chain.
Integrates with ErrorClassifier from core.errors for smart retry decisions.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List

from .errors import LLMError

logger = logging.getLogger(__name__)


class MultiProviderLLMClient:
    """Fallback chain: try providers in order, skip on failure.

    Exposes the exact same interface as individual providers so callers
    (processors, engine) don't know or care about the chain.
    """

    def __init__(self, providers: List[Any]):
        if not providers:
            raise ValueError("At least one LLM provider is required")
        self.providers = providers
        self._last_provider: str = providers[0].provider_name

    @property
    def provider_name(self) -> str:
        return f"multi({','.join(p.provider_name for p in self.providers)})"

    @property
    def is_available(self) -> bool:
        return any(p.is_available for p in self.providers)

    async def generate(self, prompt: str, **kwargs) -> str | tuple[str, Dict[str, Any]]:
        """Try each provider in order until one succeeds."""
        last_error = None

        for i, provider in enumerate(self.providers):
            try:
                result = await provider.generate(prompt, **kwargs)
                self._last_provider = provider.provider_name

                if i > 0:
                    logger.info(
                        "Fallback succeeded: %s (after %d failed)",
                        provider.provider_name, i,
                    )
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    "Provider %s failed: %s%s",
                    provider.provider_name, e,
                    f" -> trying {self.providers[i + 1].provider_name}"
                    if i + 1 < len(self.providers) else " -> no more providers",
                )

                # Check retryability: use error.retryable attribute if available,
                # otherwise fall back to ErrorClassifier
                should_fallback = self._is_retryable(e)
                if not should_fallback:
                    raise

        raise last_error  # type: ignore[misc]

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Try each provider's stream in order until one succeeds."""
        last_error = None

        for i, provider in enumerate(self.providers):
            try:
                async for chunk in provider.stream(prompt, **kwargs):
                    yield chunk
                self._last_provider = provider.provider_name
                if i > 0:
                    logger.info(
                        "Stream fallback succeeded: %s (after %d failed)",
                        provider.provider_name, i,
                    )
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    "Stream provider %s failed: %s", provider.provider_name, e,
                )
                should_fallback = self._is_retryable(e)
                if not should_fallback:
                    raise

        if last_error:
            raise last_error

    def _is_retryable(self, error: Exception) -> bool:
        """Determine if an error should trigger fallback to the next provider.

        Uses the error's retryable attribute if available (from our LLMError hierarchy),
        otherwise falls back to ErrorClassifier for compatibility.
        """
        # First check if error has explicit retryable attribute (our exception hierarchy)
        if hasattr(error, "retryable"):
            return error.retryable  # type: ignore[no-any-return]

        # Fallback to ErrorClassifier for other exceptions
        try:
            from core.errors import ErrorClassifier
            return ErrorClassifier.is_retryable(error)
        except ImportError:
            # If ErrorClassifier not available, assume retryable for LLMError,
            # non-retryable for business logic errors
            if isinstance(error, LLMError):
                return True
            if isinstance(error, (ValueError, KeyError, TypeError)):
                return False
            return True  # Default to retryable for unknown errors
