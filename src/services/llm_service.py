"""
LLM 服務 - 簡化版
統一的 LLM 客戶端管理
"""

from openai import AsyncOpenAI
import os
from typing import Optional


class LLMService:
    """統一的 LLM 服務"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = None

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(self, prompt: str, **kwargs) -> str:
        """生成響應"""
        if not self.client:
            return f"[Mock] Response to: {prompt[:50]}..."

        try:
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7)
            }

            # 只有當明確指定 max_tokens 時才添加此參數
            max_tokens = kwargs.get("max_tokens")
            if max_tokens is not None and max_tokens > 0:
                # 根據模型選擇正確的參數名
                if "gpt-4" in self.model or "gpt-5" in self.model:
                    params["max_completion_tokens"] = max_tokens
                else:
                    params["max_tokens"] = max_tokens

            response = await self.client.chat.completions.create(**params)
            return response.choices[0].message.content

        except Exception as e:
            return f"Error: {str(e)}"

    async def stream(self, prompt: str, **kwargs):
        """流式生成"""
        if not self.client:
            yield "[Mock] Streaming response..."
            return

        try:
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "temperature": kwargs.get("temperature", 0.7)
            }

            # 只有當明確指定 max_tokens 時才添加此參數
            max_tokens = kwargs.get("max_tokens")
            if max_tokens is not None and max_tokens > 0:
                if "gpt-4" in self.model or "gpt-5" in self.model:
                    params["max_completion_tokens"] = max_tokens
                else:
                    params["max_tokens"] = max_tokens

            async for chunk in await self.client.chat.completions.create(**params):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error: {str(e)}"


# 全局實例
_llm_service = None


def get_llm_service() -> LLMService:
    """獲取 LLM 服務實例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service