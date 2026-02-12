"""Anthropic (Claude) LLM provider."""

import os
from typing import Any, AsyncGenerator, Dict, Optional


class AnthropicLLMClient:
    """Anthropic Claude client.

    Lazily imports the anthropic SDK so the package is only required
    when this provider is actually instantiated.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.temperature = 0.7
        self.max_tokens = 4096

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        import anthropic

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, **kwargs) -> str | tuple[str, Dict[str, Any]]:
        """Generate a response via Anthropic Messages API."""
        # 構建參數
        params = {
            "model": self.model,
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": [{"role": "user", "content": prompt}]
        }

        # Anthropic API 需要 max_tokens，但我們使用更大的預設值
        max_tokens = kwargs.get("max_tokens")
        if max_tokens is not None and max_tokens > 0:
            params["max_tokens"] = max_tokens
        else:
            # 使用較大的預設值讓模型自由發揮
            params["max_tokens"] = 8192

        response = await self.client.messages.create(**params)

        content = response.content[0].text if response.content else ""

        token_info = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        if kwargs.get("return_token_info", False):
            return content, token_info
        return content

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response tokens via Anthropic Messages API."""
        # 構建參數
        params = {
            "model": self.model,
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": [{"role": "user", "content": prompt}]
        }

        # Anthropic API 需要 max_tokens
        max_tokens = kwargs.get("max_tokens")
        if max_tokens is not None and max_tokens > 0:
            params["max_tokens"] = max_tokens
        else:
            params["max_tokens"] = 8192

        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text
