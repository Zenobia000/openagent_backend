from openai import AsyncOpenAI
import os
from typing import Optional
from src.config import LLM_CONFIG
from src.utils.logging_config import get_logger, LogLevel

logger = get_logger("OpenAILLMClient", LogLevel.DEBUG)

class OpenAILLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key else LLM_CONFIG["api_key"]
        self.model = model if model else LLM_CONFIG["model"]
        self.temperature = LLM_CONFIG["temperature"]
        self.max_tokens = LLM_CONFIG["max_tokens"]

        if not self.api_key:
            logger.error("OPENAI_API_KEY is not set in LLM_CONFIG or environment variables.")
            raise ValueError("OPENAI_API_KEY is required for OpenAILLMClient.")

        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info(f"OpenAILLMClient initialized with model: {self.model}")

    async def generate(self, prompt: str) -> str:
        try:
            chat_completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {e}")
            return f"Error: Could not generate response. {e}"
