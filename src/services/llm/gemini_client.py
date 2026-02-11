"""Google Gemini LLM provider."""

import os
from typing import Any, AsyncGenerator, Dict, Optional


class GeminiLLMClient:
    """Google Gemini client.

    Lazily imports google.generativeai so the package is only required
    when this provider is actually instantiated.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model
        self.temperature = 0.7
        self.max_tokens = 4096

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, **kwargs) -> str | tuple[str, Dict[str, Any]]:
        """Generate a response via Gemini generateContent."""
        import google.generativeai as genai

        config = genai.GenerationConfig(
            temperature=kwargs.get("temperature", self.temperature),
            max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
        )

        response = await self.model.generate_content_async(prompt, generation_config=config)

        content = response.text or ""

        token_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            token_info = {
                "prompt_tokens": getattr(meta, "prompt_token_count", 0) or 0,
                "completion_tokens": getattr(meta, "candidates_token_count", 0) or 0,
                "total_tokens": getattr(meta, "total_token_count", 0) or 0,
            }

        if kwargs.get("return_token_info", False):
            return content, token_info
        return content

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response tokens via Gemini generateContent."""
        import google.generativeai as genai

        config = genai.GenerationConfig(
            temperature=kwargs.get("temperature", self.temperature),
            max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
        )

        response = await self.model.generate_content_async(
            prompt, generation_config=config, stream=True,
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text
