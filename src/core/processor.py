"""
處理器系統 - 策略模式實現
每個處理器負責一種處理模式
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, Any, List
import asyncio
from datetime import datetime

from .models import ProcessingContext, ProcessingMode, EventType
from .logger import structured_logger, LogCategory
from .prompts import PromptTemplates
import json
import time


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

        start_time = time.time()
        with self.logger.measure("llm_call"):
            # 使用 return_token_info 參數獲取 token 資訊
            result = await self.llm_client.generate(prompt, return_token_info=True)

            # 處理返回值
            if isinstance(result, tuple):
                response, token_info = result
                tokens_in = token_info.get("prompt_tokens", 0)
                tokens_out = token_info.get("completion_tokens", 0)
                total_tokens = token_info.get("total_tokens", 0)
            else:
                # 向後兼容：如果返回的是字符串
                response = result
                tokens_in = len(prompt.split())  # 粗略估算
                tokens_out = len(response.split())  # 粗略估算
                total_tokens = tokens_in + tokens_out

            duration_ms = (time.time() - start_time) * 1000

            # 記錄 LLM 調用
            self.logger.log_llm_call(
                model="gpt-4o",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=duration_ms
            )

            # 更新上下文的 token 統計
            if hasattr(self, 'context') and self.context:
                self.context.total_tokens += total_tokens

            return response

    async def _log_tool_decision(self, tool_name: str, reason: str, confidence: float = 0.9):
        """記錄工具決策"""
        self.logger.log_tool_decision(tool_name, confidence, reason)
        self.logger.info(
            f"🔧 Tool Decision: {tool_name}",
            "processor",
            "tool_decision",
            tool=tool_name,
            confidence=confidence,
            reason=reason
        )


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

        # 記錄 RAG 決策
        await self._log_tool_decision(
            "rag_retrieval",
            "使用知識庫檢索相關文檔",
            0.9
        )

        # Step 1: 檢索相關知識
        self.logger.progress("embedding", "start")
        await asyncio.sleep(0.1)  # 模擬 embedding
        self.logger.progress("embedding", "end")

        # Step 2: 搜索
        self.logger.progress("search", "start")

        # 記錄 RAG 操作
        self.logger.info(
            f"📚 RAG Search: {context.request.query[:50]}...",
            "rag",
            "search",
            query=context.request.query,
            vector_db="chromadb",
            embedding_model="text-embedding-ada-002"
        )

        # 這裡應該調用實際的 RAG 系統
        relevant_docs = ["Doc1: 相關內容...", "Doc2: 更多內容..."]

        # 記錄檢索結果
        self.logger.info(
            f"📖 RAG Results: Found {len(relevant_docs)} relevant documents",
            "rag",
            "results",
            docs_count=len(relevant_docs),
            top_score=0.92
        )

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

        # 記錄工具決策
        await self._log_tool_decision(
            "web_search",
            "用戶查詢需要網路搜索來獲取最新資訊",
            0.95
        )

        # Step 1: 生成 SERP 查詢
        self.logger.progress("query-generation", "start")
        search_queries = await self._generate_serp_queries(context.request.query)
        self.logger.progress("query-generation", "end", {"queries": len(search_queries)})

        # Step 2: 執行多個搜索
        self.logger.progress("searching", "start")
        all_results = []
        for query_obj in search_queries:
            results = await self._perform_search(query_obj.get('query', ''))
            all_results.append({
                'query': query_obj.get('query'),
                'goal': query_obj.get('researchGoal'),
                'results': results
            })
        self.logger.progress("searching", "end", {"total_results": len(all_results)})

        # Step 3: 使用專業 prompt 處理結果
        combined_context = "\n\n".join([
            f"Query: {r['query']}\nGoal: {r['goal']}\nResults: {r['results']}"
            for r in all_results
        ])

        prompt = PromptTemplates.get_search_result_prompt(
            query=context.request.query,
            research_goal="提供全面、準確的答案",
            context=combined_context
        )

        # 加上引用規則
        citation_rules = PromptTemplates.get_citation_rules()
        full_prompt = f"{prompt}\n\n{citation_rules}"

        response = await self._call_llm(full_prompt)

        self.logger.message(response)
        context.mark_step_complete("web-search")
        self.logger.progress("web-search", "end")

        return response

    async def _generate_serp_queries(self, user_query: str) -> List[Dict[str, str]]:
        """生成優化的 SERP 查詢 - 使用專業 prompt"""
        import json

        # 先生成簡單的研究計劃
        plan = f"研究主題: {user_query}"

        # 定義 schema
        output_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "researchGoal": {"type": "string"}
                }
            }
        }

        # 使用專業的 SERP 查詢提示詞
        prompt = PromptTemplates.get_serp_queries_prompt(plan, output_schema)

        response = await self._call_llm(prompt)

        # 解析 JSON 回應
        try:
            # 從回應中提取 JSON
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                queries = json.loads(json_match.group(1))
            else:
                # 如果沒有 markdown 包裝，直接解析
                queries = json.loads(response)
            return queries[:3]  # 限制最多 3 個查詢
        except:
            # 如果解析失敗，返回預設查詢
            return [{"query": user_query, "researchGoal": "獲取相關資訊"}]

    async def _perform_search(self, query: str) -> str:
        """執行網路搜索 - 使用 get_query_result_prompt 處理結果"""
        # 記錄搜索查詢
        self.logger.info(
            f"🔍 Web Query: {query}",
            "search",
            "query",
            query=query,
            provider="tavily"  # 或其他搜索提供者
        )

        # 這裡應該調用實際的搜索 API
        await asyncio.sleep(0.2)  # 模擬搜索延遲

        # 如果有 LLM，使用 get_query_result_prompt 來優化搜索結果
        raw_results = f"搜索結果：關於 {query} 的相關資訊..."

        if self.llm_client:
            # 使用專業的查詢結果 prompt
            result_prompt = PromptTemplates.get_query_result_prompt(
                query=query,
                research_goal="提供準確、最新的資訊"
            )
            full_prompt = f"{result_prompt}\n\n搜索結果：{raw_results}"
            processed_results = await self._call_llm(full_prompt)
            return processed_results

        return raw_results


class ThinkingProcessor(BaseProcessor):
    """深度思考處理器"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("deep-thinking", "start")
        context.set_current_step("deep-thinking")

        # 記錄思考決策
        await self._log_tool_decision(
            "deep_thinking",
            "複雜問題需要深度分析和推理",
            0.95
        )

        # 記錄思考計劃
        self.logger.info(
            f"🧠 Deep Thinking: Analyzing '{context.request.query[:50]}...'",
            "thinking",
            "start",
            category=LogCategory.TOOL,
            approach="multi-perspective-reasoning"
        )

        # Step 1: Problem decomposition and understanding
        self.logger.progress("problem-analysis", "start")
        self.logger.reasoning("Decomposing and understanding core elements...", streaming=True)

        # 使用思考模式的專業提示詞
        thinking_prompt = PromptTemplates.get_thinking_mode_prompt(context.request.query)

        # 執行深度思考
        thinking_response = await self._call_llm(thinking_prompt)

        self.logger.progress("problem-analysis", "end", {"analyzed": True})

        # Step 2: Multi-perspective analysis
        self.logger.progress("multi-perspective", "start")
        self.logger.reasoning("Analyzing from multiple perspectives...", streaming=True)

        # 使用批判性思維提示詞
        critical_prompt = PromptTemplates.get_critical_thinking_prompt(
            question=context.request.query,
            context=thinking_response
        )

        critical_analysis = await self._call_llm(critical_prompt)

        self.logger.progress("multi-perspective", "end", {"perspectives": 5})

        # Step 3: Deep reasoning
        self.logger.progress("deep-reasoning", "start")
        self.logger.reasoning("Conducting deep reasoning and logical analysis...", streaming=True)

        # 使用推理鏈提示詞
        reasoning_prompt = PromptTemplates.get_chain_of_thought_prompt(context.request.query)

        chain_reasoning = await self._call_llm(reasoning_prompt)

        self.logger.progress("deep-reasoning", "end")

        # Step 4: Synthesis and reflection
        self.logger.progress("synthesis-reflection", "start")
        self.logger.reasoning("Synthesizing all analysis and reflecting...", streaming=True)

        # 使用反思提示詞
        reflection_prompt = PromptTemplates.get_reflection_prompt(
            original_response=f"{thinking_response}\n\n{critical_analysis}\n\n{chain_reasoning}",
            question=context.request.query
        )

        reflection = await self._call_llm(reflection_prompt)

        self.logger.progress("synthesis-reflection", "end")

        # Step 5: Final answer generation
        self.logger.progress("final-synthesis", "start")

        # Combine all thinking processes
        complete_thinking = f"""
Deep Thinking Process:

【Problem Understanding & Decomposition】
{thinking_response}

【Critical Analysis】
{critical_analysis}

【Chain of Reasoning】
{chain_reasoning}

【Reflection & Improvement】
{reflection}

【Final Comprehensive Answer】
Based on the above deep thinking process, here is the complete answer to "{context.request.query}":
"""

        # 使用輸出指南確保答案品質
        output_guidelines = PromptTemplates.get_output_guidelines()
        final_prompt = f"{complete_thinking}\n\n{output_guidelines}"

        final_response = await self._call_llm(final_prompt)

        self.logger.progress("final-synthesis", "end")

        # Send complete thinking process and final answer
        full_response = f"{complete_thinking}\n{final_response}"
        self.logger.message(full_response)

        context.mark_step_complete("deep-thinking")
        self.logger.progress("deep-thinking", "end")

        return full_response


class KnowledgeGraphProcessor(BaseProcessor):
    """知識圖譜處理器 - 生成 Mermaid 圖表"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("knowledge-graph", "start")
        context.set_current_step("knowledge-graph")

        # Step 1: 獲取或生成文章內容
        self.logger.progress("content-preparation", "start")

        # 如果是問題，先生成相關內容
        if "?" in context.request.query or len(context.request.query) < 100:
            # 先生成詳細內容
            system_prompt = PromptTemplates.get_system_instruction()
            content_prompt = f"{system_prompt}\n\n請針對以下主題生成詳細的說明文章：{context.request.query}"
            article = await self._call_llm(content_prompt)
        else:
            # 直接使用提供的內容
            article = context.request.query

        self.logger.progress("content-preparation", "end")

        # Step 2: 生成知識圖譜
        self.logger.progress("graph-generation", "start")

        # 使用專業的知識圖譜 prompt
        graph_prompt = PromptTemplates.get_knowledge_graph_prompt()
        full_prompt = f"{graph_prompt}\n\n文章內容：\n{article}"

        mermaid_graph = await self._call_llm(full_prompt)

        self.logger.progress("graph-generation", "end")

        # Step 3: 組合最終輸出
        response = f"""## 知識圖譜分析

### 原始內容摘要
{article[:500]}...

### 知識圖譜視覺化
{mermaid_graph}

### 使用說明
將上述 Mermaid 代碼複製到支援 Mermaid 的 Markdown 編輯器中即可查看圖表。
"""

        self.logger.message(response)
        context.mark_step_complete("knowledge-graph")
        self.logger.progress("knowledge-graph", "end")

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


class RewritingProcessor(BaseProcessor):
    """文字重寫處理器 - 轉換為 Markdown 格式"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("rewriting", "start")
        context.set_current_step("rewriting")

        # 獲取要重寫的內容
        content_to_rewrite = context.request.query

        # 使用專業的重寫 prompt
        rewriting_prompt = PromptTemplates.get_rewriting_prompt()
        full_prompt = f"{rewriting_prompt}\n\nText to rewrite:\n{content_to_rewrite}"

        # 執行重寫
        self.logger.progress("markdown-conversion", "start")
        rewritten_content = await self._call_llm(full_prompt)
        self.logger.progress("markdown-conversion", "end")

        # 輸出結果
        self.logger.message(rewritten_content)
        context.mark_step_complete("rewriting")
        self.logger.progress("rewriting", "end")

        return rewritten_content


class DeepResearchProcessor(BaseProcessor):
    """深度研究處理器 - 完整 SSE 事件管道實現"""

    async def process(self, context: ProcessingContext) -> str:
        """執行完整的深度研究流程"""

        # 記錄深度研究決策
        await self._log_tool_decision(
            "deep_research",
            "執行全面的深度研究以回答複雜問題",
            0.95
        )

        # 1. 報告計劃階段
        report_plan = await self._write_report_plan(context)

        # 2. SERP 查詢生成
        search_tasks = await self._generate_serp_queries(context, report_plan)

        # 3. 執行搜索任務
        search_results = await self._execute_search_tasks(context, search_tasks)

        # 4. 生成最終報告
        final_report = await self._write_final_report(context, search_results, report_plan)

        return final_report

    async def _write_report_plan(self, context: ProcessingContext) -> str:
        """Phase 1: 生成研究報告計畫"""
        self.logger.progress("report-plan", "start")

        # 記錄計劃階段
        self.logger.info(
            f"📝 Planning: Creating research plan for '{context.request.query[:50]}...'",
            "deep_research",
            "planning",
            phase="report-plan",
            query_length=len(context.request.query)
        )

        # 使用報告計劃 prompt
        plan_prompt = PromptTemplates.get_report_plan_prompt(context.request.query)

        # 串流推理過程
        self.logger.reasoning("開始分析研究需求...", streaming=True)
        plan = await self._call_llm(plan_prompt, streaming=True)
        self.logger.reasoning(f"研究計劃制定完成：{plan[:100]}...", streaming=False)

        # 發送計劃消息
        self.logger.message(f"研究計劃：\n{plan}", streaming=False)

        self.logger.progress("report-plan", "end", {"plan": plan[:200]})

        return plan

    async def _generate_serp_queries(self, context: ProcessingContext, plan: str) -> List[Dict]:
        """Phase 2: 生成 SERP 查詢"""
        self.logger.progress("serp-query", "start")

        # 記錄查詢生成
        self.logger.info(
            f"🔍 SERP Generation: Extracting search queries from plan",
            "deep_research",
            "serp",
            phase="serp-query"
        )

        # 定義輸出 schema
        output_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "researchGoal": {"type": "string"},
                    "priority": {"type": "number"}
                }
            }
        }

        # 使用 SERP 查詢 prompt
        serp_prompt = PromptTemplates.get_serp_queries_prompt(plan, output_schema)
        response = await self._call_llm(serp_prompt)

        # 解析查詢
        try:
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                queries = json.loads(json_match.group(1))
            else:
                queries = json.loads(response)
        except:
            queries = [{"query": context.request.query, "researchGoal": "General research", "priority": 1}]

        # 記錄生成的查詢
        self.logger.info(
            f"📋 SERP Queries: Generated {len(queries)} search queries",
            "deep_research",
            "serp",
            queries_count=len(queries),
            queries=queries[:3]  # 只記錄前3個
        )

        self.logger.progress("serp-query", "end", {"queries": queries})

        return queries

    async def _execute_search_tasks(self, context: ProcessingContext, search_tasks: List[Dict]) -> List[Dict]:
        """Phase 3: 執行搜索任務"""
        self.logger.progress("task-list", "start")

        # 記錄任務列表
        self.logger.info(
            f"📋 Task List: Executing {len(search_tasks)} search tasks",
            "deep_research",
            "tasks",
            phase="task-list",
            total_tasks=len(search_tasks)
        )

        results = []

        for i, task in enumerate(search_tasks, 1):
            query = task.get('query', '')
            goal = task.get('researchGoal', '')
            priority = task.get('priority', 1)

            # 開始單個搜索任務
            self.logger.progress("search-task", "start", {"name": query})

            # 記錄搜索任務
            self.logger.info(
                f"🔎 Search Task {i}/{len(search_tasks)}: {query}",
                "deep_research",
                "search_task",
                task_index=i,
                query=query,
                goal=goal,
                priority=priority,
                provider="tavily"
            )

            # 推理過程
            self.logger.reasoning(f"正在搜索：{query}...", streaming=True)

            # 執行搜索
            search_result = await self._perform_deep_search(query, goal)

            # 記錄搜索結果
            self.logger.info(
                f"✅ Search Result {i}: Found {len(search_result.get('sources', []))} sources",
                "deep_research",
                "search_result",
                task_index=i,
                sources_count=len(search_result.get('sources', [])),
                relevance_score=search_result.get('relevance', 0)
            )

            # 消息輸出
            self.logger.message(f"搜索 {i}: {query}\n結果: {search_result.get('summary', '')[:200]}...")

            results.append({
                'query': query,
                'goal': goal,
                'priority': priority,
                'result': search_result
            })

            # 結束單個搜索任務
            self.logger.progress("search-task", "end", {
                "name": query,
                "data": search_result
            })

        self.logger.progress("task-list", "end")

        return results

    async def _perform_deep_search(self, query: str, goal: str) -> Dict:
        """執行深度搜索"""

        # 記錄 Web Query
        self.logger.info(
            f"🌐 Web Query: {query}",
            "web",
            "query",
            query=query,
            goal=goal,
            search_engine="google",
            max_results=10
        )

        # 模擬搜索延遲
        await asyncio.sleep(0.3)

        # 模擬搜索結果
        search_result = {
            'summary': f"關於 '{query}' 的綜合研究結果...",
            'sources': [
                {'url': 'https://example.com/1', 'title': 'Source 1', 'relevance': 0.95},
                {'url': 'https://example.com/2', 'title': 'Source 2', 'relevance': 0.88}
            ],
            'relevance': 0.92,
            'timestamp': datetime.now().isoformat()
        }

        # 記錄搜索結果詳情
        self.logger.info(
            f"🔗 Web Results: Retrieved {len(search_result['sources'])} sources",
            "web",
            "results",
            sources=search_result['sources'],
            avg_relevance=0.915
        )

        # 如果有 LLM，處理搜索結果
        if self.llm_client:
            result_prompt = PromptTemplates.get_search_result_prompt(
                query=query,
                research_goal=goal,
                context=json.dumps(search_result, ensure_ascii=False)
            )
            processed = await self._call_llm(result_prompt)
            search_result['processed'] = processed

        return search_result

    async def _write_final_report(self, context: ProcessingContext,
                                  search_results: List[Dict],
                                  report_plan: str) -> str:
        """Phase 4: 生成最終報告"""
        self.logger.progress("final-report", "start")

        # 記錄最終報告生成
        self.logger.info(
            f"📑 Final Report: Synthesizing {len(search_results)} search results",
            "deep_research",
            "final_report",
            phase="final-report",
            results_count=len(search_results),
            plan_length=len(report_plan)
        )

        # 準備上下文
        combined_context = self._prepare_report_context(search_results)

        # 記錄記憶體操作
        self.logger.info(
            f"💾 Memory: Storing research context",
            "memory",
            "store",
            context_size=len(combined_context),
            chunks=len(search_results),
            type="research_report"
        )

        # 使用最終報告 prompt
        # 準備來源和圖片（簡化版）
        sources = "\n".join([f"- {r['result'].get('summary', '')[:100]}..." for r in search_results[:5]])
        images = ""  # 暫時沒有圖片

        report_prompt = PromptTemplates.get_final_report_prompt(
            plan=report_plan,
            learnings=combined_context,
            sources=sources,
            images=images,
            requirement=context.request.query
        )

        # 加上引用規則和輸出指南
        citation_rules = PromptTemplates.get_citation_rules()
        output_guidelines = PromptTemplates.get_output_guidelines()
        full_prompt = f"{report_prompt}\n\n{citation_rules}\n\n{output_guidelines}"

        # 推理最終報告
        self.logger.reasoning("綜合所有研究結果，生成最終報告...", streaming=True)

        # 生成報告
        final_report = await self._call_llm(full_prompt, streaming=True)

        # 記錄記憶體回收
        self.logger.info(
            f"💾 Memory: Retrieved research synthesis",
            "memory",
            "retrieve",
            report_length=len(final_report),
            citations_included=True
        )

        # 發送最終報告
        self.logger.message(final_report, streaming=False)

        # 報告元數據
        report_metadata = {
            "title": f"Research Report: {context.request.query[:50]}",
            "sections": self._extract_report_sections(final_report),
            "sources_used": sum(len(r['result'].get('sources', [])) for r in search_results),
            "word_count": len(final_report.split()),
            "timestamp": datetime.now().isoformat()
        }

        # 記錄報告完成
        self.logger.info(
            f"✅ Report Completed: {report_metadata['word_count']} words, {report_metadata['sources_used']} sources",
            "deep_research",
            "complete",
            metadata=report_metadata
        )

        self.logger.progress("final-report", "end", {"data": report_metadata})

        return final_report

    def _prepare_report_context(self, search_results: List[Dict]) -> str:
        """準備報告上下文"""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"""
            搜索 {i}: {result['query']}
            目標: {result['goal']}
            優先級: {result.get('priority', 1)}
            結果摘要: {result['result'].get('summary', '')}
            處理結果: {result['result'].get('processed', '')}
            來源數量: {len(result['result'].get('sources', []))}
            """)
        return "\n\n".join(context_parts)

    def _extract_report_sections(self, report: str) -> List[str]:
        """提取報告章節"""
        import re
        # 匹配 Markdown 標題
        headers = re.findall(r'^#{1,3}\s+(.+)$', report, re.MULTILINE)
        return headers[:10]  # 返回前10個章節標題


class ProcessorFactory:
    """處理器工廠 - 創建和管理處理器"""

    _processors: Dict[ProcessingMode, Type[BaseProcessor]] = {
        ProcessingMode.CHAT: ChatProcessor,
        ProcessingMode.KNOWLEDGE: KnowledgeProcessor,
        ProcessingMode.SEARCH: SearchProcessor,
        ProcessingMode.THINKING: ThinkingProcessor,
        ProcessingMode.CODE: CodeProcessor,
        ProcessingMode.DEEP_RESEARCH: DeepResearchProcessor,
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