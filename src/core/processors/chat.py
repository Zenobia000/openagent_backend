"""
Chat Processor - System 1 with Cache Support

Simple conversational responses with caching for repeated queries.
Extracted from monolithic processor.py
"""

from .base import BaseProcessor
from ..models import ProcessingContext
from ..prompts import PromptTemplates


class ChatProcessor(BaseProcessor):
    """對話處理器 - System 1 with Cache Support"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("chat", "start")
        context.set_current_step("chat")

        # Step 1: Cache Check (System 1 特性)
        cache_key = f"chat:{context.request.query}"
        cache = getattr(self, 'cache', None)  # 從處理器獲取快取實例

        if cache:
            cached_response = cache.get(cache_key)
            if cached_response:
                self.logger.info("💾 Cache HIT for chat query", "chat", "cache_hit")
                self.logger.message(cached_response)
                context.mark_step_complete("chat")
                self.logger.progress("chat", "end")
                return cached_response

        # Step 2: Build Prompt (符合狀態機 BuildPrompt)
        system_prompt = PromptTemplates.get_system_instruction("chat")
        output_guidelines = PromptTemplates.get_output_guidelines()
        full_prompt = f"{system_prompt}\n\n{output_guidelines}\n\nUser: {context.request.query}"

        # Step 3: Call LLM (符合狀態機 CallLLM)
        response = await self._call_llm(full_prompt, context)

        # Step 4: Cache Put (System 1 特性)
        if cache:
            cache.put(cache_key, response, ttl=300)
            self.logger.info("💾 Cache PUT for chat response", "chat", "cache_put")

        # 發送消息
        self.logger.message(response)

        context.mark_step_complete("chat")
        self.logger.progress("chat", "end")

        return response
