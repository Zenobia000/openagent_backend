"""OpenAI LLM provider."""

import os
from typing import Any, AsyncGenerator, Dict, Optional

from openai import AsyncOpenAI

from .base import LLMProvider
from .gpt5_adapter import GPT5Adapter


class OpenAILLMClient(LLMProvider):
    """OpenAI LLM client (GPT-4o, GPT-4o-mini, etc.)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = 0.7
        self.max_tokens = 4096

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")

        self.client = AsyncOpenAI(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, **kwargs) -> str | tuple[str, Dict[str, Any]]:
        """Generate a response via OpenAI ChatCompletion."""
        try:
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.temperature)
            }

            # 只有當明確指定 max_tokens 時才添加此參數
            max_tokens = kwargs.get("max_tokens")
            if max_tokens is not None and max_tokens > 0:
                params["max_tokens"] = max_tokens

            # 使用 GPT5Adapter 適配參數
            params = GPT5Adapter.adapt_parameters(self.model, params)

            response = await self.client.chat.completions.create(**params)

            token_info = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            # 檢查響應內容是否為空
            content = response.choices[0].message.content
            if not content:
                content = "[Empty response from OpenAI API]"
                import logging
                logging.warning(f"OpenAI API returned empty content for model {self.model}")

            if kwargs.get("return_token_info", False):
                return content, token_info

            return content

        except Exception as e:
            error_msg = f"[OpenAI Error] {e}"
            if kwargs.get("return_token_info", False):
                return error_msg, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            return error_msg

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response tokens via OpenAI ChatCompletion."""
        params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": True,
        }

        # 只有當明確指定 max_tokens 時才添加此參數
        max_tokens = kwargs.get("max_tokens")
        if max_tokens is not None and max_tokens > 0:
            params["max_tokens"] = max_tokens

        # 使用 GPT5Adapter 適配參數
        params = GPT5Adapter.adapt_parameters(self.model, params)

        async for chunk in await self.client.chat.completions.create(**params):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
