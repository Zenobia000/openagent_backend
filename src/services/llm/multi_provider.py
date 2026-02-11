"""Multi-provider LLM client with automatic fallback chain.

Wraps multiple LLM providers behind the same generate()/stream() interface.
On failure, transparently falls to the next provider in the chain.
Integrates with ErrorClassifier from core.errors for smart retry decisions.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List

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

                # Check for soft errors (OpenAI returns "[OpenAI Error] ..." instead of raising)
                if isinstance(result, str) and result.startswith("[") and "Error]" in result:
                    raise RuntimeError(result)
                if isinstance(result, tuple) and isinstance(result[0], str) and result[0].startswith("[") and "Error]" in result[0]:
                    raise RuntimeError(result[0])

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

                # Non-retryable errors (business logic, bad input) should not fallback
                try:
                    from core.errors import ErrorClassifier
                    if not ErrorClassifier.is_retryable(e):
                        raise
                except ImportError:
                    pass

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
                try:
                    from core.errors import ErrorClassifier
                    if not ErrorClassifier.is_retryable(e):
                        raise
                except ImportError:
                    pass

        if last_error:
            raise last_error
