"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional


class LLMProvider(ABC):
    """Unified interface for all LLM providers.

    Every provider must implement generate() and stream() with identical
    signatures so they are interchangeable in the fallback chain.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier, e.g. 'openai', 'anthropic', 'gemini'."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True when the provider has a valid API key configured."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str | tuple[str, Dict[str, Any]]:
        """Generate a response.

        Returns:
            str when called without return_token_info.
            (str, token_info_dict) when return_token_info=True in kwargs.
        """

    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Yield response tokens as an async generator."""
