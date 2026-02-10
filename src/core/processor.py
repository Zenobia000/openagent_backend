"""
處理器系統 - 策略模式實現
每個處理器負責一種處理模式
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, Any
import asyncio
from datetime import datetime

from .models import ProcessingContext, ProcessingMode, EventType
from .logger import structured_logger
from .prompts import PromptTemplates


class BaseProcessor(ABC):
    """處理器基類"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.logger = structured_logger

    @abstractmethod
    async def process(self, context: ProcessingContext) -> str:
        """處理請求 - 子類必須實現"""
        pass

    async def _call_llm(self, prompt: str, streaming: bool = False) -> str:
        """調用 LLM - 公共方法"""
        if not self.llm_client:
            return f"[Mock Response] {prompt[:50]}..."

        with self.logger.measure("llm_call"):
            response = await self.llm_client.generate(prompt)
            # 記錄 LLM 調用
            self.logger.log_llm_call(
                model="gpt-4o",
                tokens_in=len(prompt.split()),
                tokens_out=len(response.split()),
                duration_ms=100  # 實際應從 measure 獲取
            )
            return response


class ChatProcessor(BaseProcessor):
    """對話處理器"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("chat", "start")
        context.set_current_step("chat")

        # 使用系統指令提示詞
        system_prompt = PromptTemplates.get_system_instruction()
        output_guidelines = PromptTemplates.get_output_guidelines()

        # 組合完整提示
        full_prompt = f"{system_prompt}\n\n{output_guidelines}\n\nUser: {context.request.query}"
        response = await self._call_llm(full_prompt)

        # 發送消息
        self.logger.message(response)

        context.mark_step_complete("chat")
        self.logger.progress("chat", "end")

        return response


class KnowledgeProcessor(BaseProcessor):
    """知識檢索處理器"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("knowledge-retrieval", "start")
        context.set_current_step("knowledge-retrieval")

        # Step 1: 檢索相關知識
        self.logger.progress("embedding", "start")
        await asyncio.sleep(0.1)  # 模擬 embedding
        self.logger.progress("embedding", "end")

        # Step 2: 搜索
        self.logger.progress("search", "start")
        # 這裡應該調用實際的 RAG 系統
        relevant_docs = ["Doc1: 相關內容...", "Doc2: 更多內容..."]
        self.logger.progress("search", "end", {"docs_found": len(relevant_docs)})

        # Step 3: 生成答案
        # 使用知識檢索提示詞模板
        prompt = PromptTemplates.get_search_knowledge_result_prompt(
            query=context.request.query,
            research_goal="提供準確、詳細的回答",
            context=' '.join(relevant_docs)
        )

        # 加上引用規則
        citation_rules = PromptTemplates.get_citation_rules()
        full_prompt = f"{prompt}\n\n{citation_rules}"

        response = await self._call_llm(full_prompt)

        self.logger.message(response)
        context.mark_step_complete("knowledge-retrieval")
        self.logger.progress("knowledge-retrieval", "end")

        return response


class SearchProcessor(BaseProcessor):
    """網路搜索處理器"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("web-search", "start")
        context.set_current_step("web-search")

        # Step 1: 生成搜索查詢
        self.logger.progress("query-generation", "start")
        search_query = await self._generate_search_query(context.request.query)
        self.logger.progress("query-generation", "end", {"query": search_query})

        # Step 2: 執行搜索
        self.logger.progress("searching", "start")
        search_results = await self._perform_search(search_query)
        self.logger.progress("searching", "end", {"results": len(search_results)})

        # Step 3: 綜合結果
        prompt = f"""
        基於搜索結果回答：
        搜索結果：{search_results}
        問題：{context.request.query}
        """
        response = await self._call_llm(prompt)

        self.logger.message(response)
        context.mark_step_complete("web-search")
        self.logger.progress("web-search", "end")

        return response

    async def _generate_search_query(self, user_query: str) -> str:
        """生成優化的搜索查詢"""
        prompt = f"將以下問題轉換為搜索引擎查詢：{user_query}"
        return await self._call_llm(prompt)

    async def _perform_search(self, query: str) -> str:
        """執行網路搜索"""
        # 這裡應該調用實際的搜索 API
        await asyncio.sleep(0.2)  # 模擬搜索延遲
        return f"搜索結果：關於 {query} 的相關資訊..."


class ThinkingProcessor(BaseProcessor):
    """深度思考處理器"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("deep-thinking", "start")
        context.set_current_step("deep-thinking")

        thinking_steps = []

        # 多步驟思考
        for i in range(3):
            step_name = f"thinking-step-{i+1}"
            self.logger.progress(step_name, "start")

            # 發送推理過程
            reasoning = f"步驟 {i+1}: 分析問題的第 {i+1} 個層面..."
            self.logger.reasoning(reasoning)
            thinking_steps.append(reasoning)

            await asyncio.sleep(0.1)  # 模擬思考時間
            self.logger.progress(step_name, "end")

        # 綜合結論
        self.logger.progress("synthesis", "start")
        prompt = f"""
        基於以下思考過程，提供最終答案：
        思考過程：{' '.join(thinking_steps)}
        原始問題：{context.request.query}
        """
        response = await self._call_llm(prompt)
        self.logger.progress("synthesis", "end")

        self.logger.message(response)
        context.mark_step_complete("deep-thinking")
        self.logger.progress("deep-thinking", "end")

        return response


class CodeProcessor(BaseProcessor):
    """代碼執行處理器"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("code-execution", "start")
        context.set_current_step("code-execution")

        # Step 1: 解析代碼請求
        self.logger.progress("code-analysis", "start")
        code_request = context.request.query
        self.logger.progress("code-analysis", "end")

        # Step 2: 生成代碼
        self.logger.progress("code-generation", "start")
        prompt = f"生成代碼來完成：{code_request}"
        generated_code = await self._call_llm(prompt)
        self.logger.message(f"```python\n{generated_code}\n```")
        self.logger.progress("code-generation", "end")

        # Step 3: 執行代碼（沙箱環境）
        self.logger.progress("code-execution", "start")
        result = await self._execute_code(generated_code)
        self.logger.progress("code-execution", "end", {"success": result.get("success")})

        response = f"代碼執行結果：\n{result.get('output', 'No output')}"
        self.logger.message(response)

        context.mark_step_complete("code-execution")
        self.logger.progress("code-execution", "end")

        return response

    async def _execute_code(self, code: str) -> Dict[str, Any]:
        """在沙箱中執行代碼"""
        # 這裡應該調用實際的沙箱服務
        await asyncio.sleep(0.1)
        return {
            "success": True,
            "output": "Hello World!"
        }


class ProcessorFactory:
    """處理器工廠 - 創建和管理處理器"""

    _processors: Dict[ProcessingMode, Type[BaseProcessor]] = {
        ProcessingMode.CHAT: ChatProcessor,
        ProcessingMode.KNOWLEDGE: KnowledgeProcessor,
        ProcessingMode.SEARCH: SearchProcessor,
        ProcessingMode.THINKING: ThinkingProcessor,
        ProcessingMode.CODE: CodeProcessor,
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._instances: Dict[ProcessingMode, BaseProcessor] = {}

    def get_processor(self, mode: ProcessingMode) -> BaseProcessor:
        """獲取處理器實例"""
        if mode not in self._instances:
            processor_class = self._processors.get(mode, ChatProcessor)
            self._instances[mode] = processor_class(self.llm_client)

        return self._instances[mode]

    def register_processor(self, mode: ProcessingMode, processor_class: Type[BaseProcessor]):
        """註冊自定義處理器"""
        self._processors[mode] = processor_class
        # 清除已有實例，下次獲取時會創建新的
        if mode in self._instances:
            del self._instances[mode]