"""
OpenAI LLM Client - 簡化版本
"""

from openai import AsyncOpenAI
import os
from typing import Optional, Dict, Any


class OpenAILLMClient:
    """OpenAI LLM 客戶端"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = 0.7
        self.max_tokens = 4096

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")

        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(self, prompt: str, **kwargs) -> tuple[str, Dict[str, Any]]:
        """生成回應，返回 (content, token_info)"""
        try:
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.temperature),
            }

            # 根據模型選擇正確的參數
            if self.model in ["gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-5"]:
                params["max_completion_tokens"] = kwargs.get("max_tokens", self.max_tokens)
            else:
                params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)

            response = await self.client.chat.completions.create(**params)

            # 提取 token 使用資訊
            token_info = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            # 為了向後兼容，如果 kwargs 中有 return_token_info=True，返回元組
            if kwargs.get("return_token_info", False):
                return response.choices[0].message.content, token_info

            # 默認只返回內容（向後兼容）
            return response.choices[0].message.content

        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            if kwargs.get("return_token_info", False):
                return f"[Error] {str(e)}", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            return f"[Error] {str(e)}"

    async def stream(self, prompt: str, **kwargs):
        """串流生成"""
        params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": True,
        }

        # 根據模型選擇正確的參數
        if self.model in ["gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-5"]:
            params["max_completion_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        else:
            params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)

        async for chunk in await self.client.chat.completions.create(**params):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content