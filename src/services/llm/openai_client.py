"""OpenAI LLM provider."""

import os
from typing import Any, AsyncGenerator, Dict, Optional

from openai import AsyncOpenAI

from .base import LLMProvider


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
                "temperature": kwargs.get("temperature", self.temperature),
            }

            # GPT-4, GPT-5 系列模型使用 max_completion_tokens
            if self.model.startswith(("gpt-4", "gpt-5")):
                params["max_completion_tokens"] = kwargs.get("max_tokens", self.max_tokens)
            else:
                params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)

            response = await self.client.chat.completions.create(**params)

            token_info = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            if kwargs.get("return_token_info", False):
                return response.choices[0].message.content, token_info

            return response.choices[0].message.content

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

        # GPT-4, GPT-5 系列模型使用 max_completion_tokens
        if self.model.startswith(("gpt-4", "gpt-5")):
            params["max_completion_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        else:
            params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)

        async for chunk in await self.client.chat.completions.create(**params):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
