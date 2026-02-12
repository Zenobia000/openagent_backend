"""
處理器系統 - 策略模式實現
每個處理器負責一種處理模式
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, Any, List, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime
import json
import time

from .models import ProcessingContext, ProcessingMode, EventType
from .logger import structured_logger, LogCategory
from .prompts import PromptTemplates
from .error_handler import robust_processor, enhanced_error_handler


class BaseProcessor(ABC):
    """處理器基類"""

    def __init__(self, llm_client=None, services: Optional[Dict[str, Any]] = None):
        self.llm_client = llm_client
        self.services = services or {}
        self.logger = structured_logger
        self._cognitive_level: Optional[str] = None

    @abstractmethod
    async def process(self, context: ProcessingContext) -> str:
        """處理請求 - 子類必須實現"""
        pass

    async def _call_llm(self, prompt: str, context: ProcessingContext = None) -> str:
        """調用 LLM - 公共方法"""
        if not self.llm_client:
            raise RuntimeError("LLM client not configured — cannot process request")

        # # 記錄 prompt (截取前500字符用於日誌)
        # self.logger.info(
        #     f"📝 LLM Prompt: {prompt[:500]}...",
        #     "llm",
        #     "prompt",
        #     prompt_length=len(prompt),
        #     prompt_preview=prompt[:200]
        # )

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

            # 記錄 LLM 調用 (包含 token 和時間資訊)
            self.logger.log_llm_call(
                model=getattr(self.llm_client, 'model_name', getattr(self.llm_client, 'provider_name', 'unknown')),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=duration_ms
            )

            # 記錄 LLM Response (用於 debugging，顯示實際輸出)
            # 檢查是否需要分割長內容
            try:
                from core.enhanced_logger import get_enhanced_logger
                enhanced_logger = get_enhanced_logger()

                if len(response) > 10000:  # 超過 10KB
                    # 使用增強日誌器處理長內容
                    trace_id = context.trace_id if context and hasattr(context, 'trace_id') else "unknown"
                    enhanced_logger.log_long_content(
                        "INFO",
                        f"LLM Response (Long: {len(response)} chars, {total_tokens} tokens)",
                        response,
                        trace_id,
                        "llm_response"
                    )
                    # 主日誌只記錄摘要
                    self.logger.info(
                        f"💬 LLM Response [Long content: {len(response)} chars, see segments]",
                        "llm",
                        "response",
                        response_length=len(response),
                        total_tokens=total_tokens
                    )
                else:
                    # 正常記錄
                    self.logger.info(
                        f"💬 LLM Response: {response[:5000]}...",
                        "llm",
                        "response",
                        response_length=len(response),
                        response_preview=response[:200]
                    )
            except ImportError:
                # 如果增強日誌器不可用，使用原始方式
                self.logger.info(
                    f"💬 LLM Response: {response[:5000]}...",
                    "llm",
                    "response",
                    response_length=len(response),
                    response_preview=response[:200]
                )

            # 檢查響應是否為空
            if not response or response.strip() == "":
                self.logger.warning(
                    "LLM returned empty response",
                    "llm",
                    "empty_response",
                    model=getattr(self.llm_client, 'model_name', 'unknown')
                )
                response = "[LLM returned empty response - please check API configuration]"

            # 更新上下文的 token 統計
            if context:
                context.total_tokens += total_tokens

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
        system_prompt = PromptTemplates.get_system_instruction()
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


class KnowledgeProcessor(BaseProcessor):
    """知識檢索處理器 - System 1 with Cache Support"""

    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("knowledge-retrieval", "start")
        context.set_current_step("knowledge-retrieval")

        # Step 1: Cache Check (System 1 特性 - 符合狀態機)
        cache_key = f"knowledge:{context.request.query}"
        cache = getattr(self, 'cache', None)

        if cache:
            cached_response = cache.get(cache_key)
            if cached_response:
                self.logger.info("💾 Cache HIT for knowledge query", "knowledge", "cache_hit")
                self.logger.message(cached_response)
                context.mark_step_complete("knowledge-retrieval")
                self.logger.progress("knowledge-retrieval", "end")
                return cached_response

        # 記錄 RAG 決策
        await self._log_tool_decision(
            "rag_retrieval",
            "使用知識庫檢索相關文檔",
            0.9
        )

        # Step 2: Generate Embeddings (符合狀態機)
        self.logger.progress("embedding", "start")
        self.logger.info(
            f"🔢 Generating embeddings for query: {context.request.query[:100]}",
            "knowledge",
            "embedding"
        )
        self.logger.progress("embedding", "end")

        # Step 2: 搜索
        self.logger.progress("search", "start")

        knowledge_service = self.services.get("knowledge")
        relevant_docs = []

        if knowledge_service:
            try:
                self.logger.info(
                    f"📚 RAG Search: {context.request.query[:50]}...",
                    "rag", "search",
                    query=context.request.query,
                    vector_db="qdrant"
                )
                docs = await knowledge_service.retrieve(context.request.query, top_k=5)
                if docs:
                    relevant_docs = [
                        doc.get("content", str(doc)) for doc in docs
                    ]
            except Exception as e:
                self.logger.warning(f"Knowledge service error, using fallback: {e}", "knowledge", "fallback")

        # Fallback: no knowledge base → LLM direct answer
        if not relevant_docs:
            self.logger.warning(
                "Knowledge base unavailable — falling back to LLM direct answer",
                "knowledge", "no_rag"
            )
            system_prompt = PromptTemplates.get_system_instruction()
            fallback_prompt = (
                f"{system_prompt}\n\n"
                f"[NOTE: Knowledge base is currently unavailable. "
                f"Answer based on your training data and clearly state that "
                f"this answer is NOT grounded in the local knowledge base.]\n\n"
                f"User: {context.request.query}"
            )
            response = await self._call_llm(fallback_prompt, context)
            self.logger.message(response)
            context.mark_step_complete("knowledge-retrieval")
            self.logger.progress("knowledge-retrieval", "end")
            return response

        # 記錄檢索結果到日誌
        self.logger.info(
            f"📖 RAG Results: Found {len(relevant_docs)} relevant documents",
            "rag",
            "results",
            docs_count=len(relevant_docs)
        )

        self.logger.progress("search", "end", {"docs_found": len(relevant_docs)})

        # Step 3: 文檔重排序 (P1 優化)
        if len(relevant_docs) > 1:
            self.logger.progress("rerank", "start")
            self.logger.info(
                f"🎯 Reranking {len(relevant_docs)} documents for relevance...",
                "knowledge",
                "reranking"
            )
            relevant_docs = await self._rerank_documents(relevant_docs, context.request.query)
            self.logger.progress("rerank", "end", {"reranked": len(relevant_docs)})

        # Step 4: 生成答案
        self.logger.info(
            f"🔄 Synthesizing answer from {len(relevant_docs)} retrieved documents...",
            "knowledge",
            "synthesis"
        )

        # 使用知識檢索提示詞模板
        prompt = PromptTemplates.get_search_knowledge_result_prompt(
            query=context.request.query,
            research_goal="提供準確、詳細的回答",
            context=' '.join(relevant_docs)
        )

        # 加上引用規則
        citation_rules = PromptTemplates.get_citation_rules()
        full_prompt = f"{prompt}\n\n{citation_rules}"

        response = await self._call_llm(full_prompt, context)

        # Step 5: Cache Put (System 1 特性 - 符合狀態機)
        if cache:
            cache.put(cache_key, response, ttl=300)
            self.logger.info("💾 Cache PUT for knowledge response", "knowledge", "cache_put")

        # 只輸出最終答案
        self.logger.message(response)
        context.mark_step_complete("knowledge-retrieval")
        self.logger.progress("knowledge-retrieval", "end")

        return response

    async def _rerank_documents(self, docs: List[str], query: str) -> List[str]:
        """使用 LLM 對文檔進行相關性重排序"""
        import json

        # 如果文檔太多，只重排前 10 個
        docs_to_rerank = docs[:10]

        # 準備重排序 prompt
        rerank_prompt = f"""Rank these documents by relevance to the query. Score each from 1-10.

Query: {query}

Documents:
{chr(10).join([f"{i+1}. {doc[:300]}..." for i, doc in enumerate(docs_to_rerank)])}

Output JSON format:
[{{"doc_id": 1, "score": 8}}, {{"doc_id": 2, "score": 6}}, ...]

Only include documents with score >= 5.
Output the ranking:"""

        try:
            response = await self._call_llm(rerank_prompt, None)

            # 解析排名
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                rankings = json.loads(json_match.group(0))

                # 根據分數排序
                rankings.sort(key=lambda x: x.get('score', 0), reverse=True)

                # 重新排序文檔
                reranked_docs = []
                for rank in rankings:
                    doc_id = rank.get('doc_id', 0) - 1  # 轉為 0-based index
                    if 0 <= doc_id < len(docs_to_rerank) and rank.get('score', 0) >= 5:
                        reranked_docs.append(docs_to_rerank[doc_id])

                # 如果重排失敗或結果太少，保留原始順序的前幾個
                if len(reranked_docs) < 2:
                    return docs[:5]

                self.logger.info(
                    f"✅ Reranked {len(reranked_docs)} documents (filtered by relevance)",
                    "knowledge",
                    "rerank_complete"
                )
                return reranked_docs

        except Exception as e:
            self.logger.warning(f"Reranking failed, using original order: {e}", "knowledge", "rerank_error")

        # 失敗時返回原始順序
        return docs[:5]


class SearchProcessor(BaseProcessor):
    """網路搜索處理器 - 支援迭代搜索與質量評估"""

    @enhanced_error_handler(max_retries=2, retryable_categories=["NETWORK", "LLM"])
    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("web-search", "start")
        context.set_current_step("web-search")

        # 記錄工具決策
        await self._log_tool_decision(
            "web_search",
            "用戶查詢需要網路搜索來獲取最新資訊",
            0.95
        )

        # 迭代搜索機制
        MAX_ITERATIONS = 2
        all_search_results = []
        iteration = 0

        while iteration < MAX_ITERATIONS:
            iteration += 1
            self.logger.info(f"🔄 Search Iteration {iteration}/{MAX_ITERATIONS}", "search", "iteration")

            # Step 1: 生成 SERP 查詢
            self.logger.progress("query-generation", "start")

            if iteration == 1:
                # 第一次：基於原始查詢生成
                search_queries = await self._generate_serp_queries(context.request.query)
            else:
                # 後續迭代：基於質量評估改進查詢
                search_queries = await self._refine_search_queries(
                    context.request.query,
                    all_search_results
                )

            if not search_queries:
                break

            self.logger.info(
                f"📝 Generated {len(search_queries)} search queries",
                "search",
                "queries_generated",
                queries=search_queries
            )
            self.logger.progress("query-generation", "end", {"queries": len(search_queries)})

            # Step 2: 執行搜索
            self.logger.progress("searching", "start")
            iteration_results = []
            for i, query_obj in enumerate(search_queries, 1):
                self.logger.info(
                    f"🌐 Searching {i}/{len(search_queries)}: {query_obj.get('query', '')[:100]}",
                    "search",
                    "performing_search"
                )
                results = await self._perform_search(query_obj.get('query', ''))
                iteration_results.append({
                    'query': query_obj.get('query'),
                    'goal': query_obj.get('researchGoal'),
                    'results': results,
                    'iteration': iteration
                })
            self.logger.progress("searching", "end", {"total_results": len(iteration_results)})

            all_search_results.extend(iteration_results)

            # Step 3: 評估搜索質量
            is_sufficient = await self._evaluate_search_quality(all_search_results, context.request.query)

            if is_sufficient:
                self.logger.info("✅ Search quality is sufficient", "search", "quality_ok")
                break

            self.logger.info("📊 Search needs refinement, continuing...", "search", "refine")

        # Step 4: 合成最終結果
        combined_context = "\n\n".join([
            f"Query: {r['query']}\nGoal: {r['goal']}\nResults: {r['results']}"
            for r in all_search_results
        ])

        self.logger.info(
            f"🔄 Synthesizing {len(all_search_results)} search results...",
            "search",
            "synthesis"
        )

        prompt = PromptTemplates.get_search_result_prompt(
            query=context.request.query,
            research_goal="提供全面、準確的答案",
            context=combined_context
        )

        citation_rules = PromptTemplates.get_citation_rules()
        full_prompt = f"{prompt}\n\n{citation_rules}"

        response = await self._call_llm(full_prompt, context)

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

        response = await self._call_llm(prompt, None)

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
        """執行網路搜索 - 使用真實搜索服務或 LLM fallback"""
        # 記錄搜索查詢
        search_service = self.services.get("search")
        provider = getattr(search_service, 'primary_provider', 'none') if search_service else 'none'
        self.logger.info(
            f"🔍 Web Query: {query}",
            "search",
            "query",
            query=query,
            provider=provider
        )

        # Use real search service if available
        raw_results = ""
        if search_service:
            try:
                results = await search_service.search(query, max_results=5)
                if results:
                    raw_results = "\n\n".join(
                        f"[{r.title}]\n{r.snippet}\nURL: {r.url}"
                        for r in results
                    )
                    self.logger.info(
                        f"🔍 Search returned {len(results)} results",
                        "search", "results"
                    )
            except Exception as e:
                self.logger.warning(f"Search service error, falling back to LLM: {e}", "search", "fallback")

        # Fallback: no search results → LLM answers with disclaimer
        if not raw_results:
            self.logger.warning("No search results available — LLM will answer from training data", "search", "no_results")
            raw_results = (
                f"[Web search unavailable — no real-time results for '{query}'. "
                f"The following answer is based on the AI model's training data only.]"
            )

        if self.llm_client:
            result_prompt = PromptTemplates.get_query_result_prompt(
                query=query,
                research_goal="提供準確、最新的資訊"
            )
            full_prompt = f"{result_prompt}\n\n搜索結果：{raw_results}"
            processed_results = await self._call_llm(full_prompt, None)
            return processed_results

        return raw_results

    async def _evaluate_search_quality(self, results: List[Dict], original_query: str) -> bool:
        """評估搜索結果質量是否充分"""
        if not results:
            return False

        # 簡單的質量檢查
        total_content = sum(len(r.get('results', '')) for r in results)
        unique_queries = len(set(r['query'] for r in results))

        # 基於內容量和查詢多樣性評估
        if total_content < 500 or unique_queries < 2:
            return False

        # 使用 LLM 評估相關性
        evaluation_prompt = f"""Evaluate if the search results are sufficient for answering the query.

Original Query: {original_query}

Search Results Summary:
- Total results: {len(results)}
- Total content: {total_content} characters
- Unique queries: {unique_queries}

First few results:
{results[0].get('results', '')[:500] if results else 'No results'}

Answer with YES if sufficient, NO if more search is needed.
Consider: coverage, relevance, quality.

Answer (YES/NO):"""

        response = await self._call_llm(evaluation_prompt, None)
        return "YES" in response.upper()[:10]

    async def _refine_search_queries(self, original_query: str, previous_results: List[Dict]) -> List[Dict[str, str]]:
        """基於前次結果改進搜索查詢"""
        import json

        # 準備已有結果摘要
        results_summary = "\n".join([
            f"Query: {r['query']}\nFound: {r['results'][:200]}..."
            for r in previous_results[:3]
        ])

        refine_prompt = f"""Based on the original query and previous search results, generate improved search queries to fill knowledge gaps.

Original Query: {original_query}

Previous Search Results:
{results_summary}

Identify what's missing and generate 1-2 new search queries that would provide additional valuable information.

Output JSON array format:
[{{"query": "specific search query", "researchGoal": "what to find"}}]

Generate queries:"""

        response = await self._call_llm(refine_prompt, None)

        try:
            # 嘗試解析 JSON
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                queries = json.loads(json_match.group(0))
                return queries[:2]  # 限制最多2個新查詢
        except:
            pass

        return []


class ThinkingProcessor(BaseProcessor):
    """深度思考處理器"""

    @enhanced_error_handler(max_retries=1, retryable_categories=["LLM"])
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

        # 記錄階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 1: Problem Understanding & Decomposition",
            "thinking",
            "stage1",
            query=context.request.query[:100]
        )

        # 使用思考模式的專業提示詞
        thinking_prompt = PromptTemplates.get_thinking_mode_prompt(context.request.query)

        # 執行深度思考
        thinking_response = await self._call_llm(thinking_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 1 Result: {thinking_response[:500]}...",
            "thinking",
            "stage1_result",
            full_length=len(thinking_response)
        )

        # 記錄階段完成
        self.logger.info(
            f"✅ Stage 1: Problem Analysis Complete",
            "thinking",
            "stage1_complete",
            response_length=len(thinking_response)
        )

        self.logger.progress("problem-analysis", "end", {"analyzed": True})

        # Step 2: Multi-perspective analysis
        self.logger.progress("multi-perspective", "start")
        self.logger.reasoning("Analyzing from multiple perspectives...", streaming=True)

        # 記錄第二階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 2: Critical Multi-Perspective Analysis",
            "thinking",
            "stage2"
        )

        # 使用批判性思維提示詞
        critical_prompt = PromptTemplates.get_critical_thinking_prompt(
            question=context.request.query,
            context=thinking_response
        )

        critical_analysis = await self._call_llm(critical_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 2 Result: {critical_analysis[:500]}...",
            "thinking",
            "stage2_result",
            full_length=len(critical_analysis)
        )

        self.logger.progress("multi-perspective", "end", {"perspectives": 5})

        # Step 3: Deep reasoning
        self.logger.progress("deep-reasoning", "start")
        self.logger.reasoning("Conducting deep reasoning and logical analysis...", streaming=True)

        # 記錄第三階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 3: Chain of Deep Reasoning",
            "thinking",
            "stage3"
        )

        # 使用推理鏈提示詞
        reasoning_prompt = PromptTemplates.get_chain_of_thought_prompt(context.request.query)

        chain_reasoning = await self._call_llm(reasoning_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 3 Result: {chain_reasoning[:500]}...",
            "thinking",
            "stage3_result",
            full_length=len(chain_reasoning)
        )

        self.logger.progress("deep-reasoning", "end")

        # Step 4: Synthesis and reflection
        self.logger.progress("synthesis-reflection", "start")
        self.logger.reasoning("Synthesizing all analysis and reflecting...", streaming=True)

        # 記錄第四階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 4: Synthesis & Reflection",
            "thinking",
            "stage4"
        )

        # 使用反思提示詞
        reflection_prompt = PromptTemplates.get_reflection_prompt(
            original_response=f"{thinking_response}\n\n{critical_analysis}\n\n{chain_reasoning}",
            question=context.request.query
        )

        reflection = await self._call_llm(reflection_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 4 Result: {reflection[:500]}...",
            "thinking",
            "stage4_result",
            full_length=len(reflection)
        )

        self.logger.progress("synthesis-reflection", "end")

        # Step 5: Final answer generation
        self.logger.progress("final-synthesis", "start")

        # 記錄最終階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🎯 Stage 5: Final Comprehensive Answer",
            "thinking",
            "stage5"
        )

        # 準備最終答案提示詞
        final_synthesis_prompt = f"""
Based on the following deep thinking process, provide a comprehensive final answer to the question: "{context.request.query}"

Thinking Process Summary:
1. Problem Understanding: {thinking_response[:200]}...
2. Critical Analysis: {critical_analysis[:200]}...
3. Chain of Reasoning: {chain_reasoning[:200]}...
4. Reflection: {reflection[:200]}...

Please provide a complete, well-structured answer that synthesizes all insights from the above analysis.
"""

        # 使用輸出指南確保答案品質
        output_guidelines = PromptTemplates.get_output_guidelines()
        final_prompt = f"{final_synthesis_prompt}\n\n{output_guidelines}"

        final_response = await self._call_llm(final_prompt, context)

        # 只輸出最終答案作為回應
        self.logger.message(final_response)

        self.logger.progress("final-synthesis", "end")

        context.mark_step_complete("deep-thinking")
        self.logger.progress("deep-thinking", "end")

        # 只返回最終答案
        return final_response


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
            article = await self._call_llm(content_prompt, context)
        else:
            # 直接使用提供的內容
            article = context.request.query

        self.logger.progress("content-preparation", "end")

        # Step 2: 生成知識圖譜
        self.logger.progress("graph-generation", "start")

        # 使用專業的知識圖譜 prompt
        graph_prompt = PromptTemplates.get_knowledge_graph_prompt()
        full_prompt = f"{graph_prompt}\n\n文章內容：\n{article}"

        mermaid_graph = await self._call_llm(full_prompt, context)

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

    @enhanced_error_handler(max_retries=1, retryable_categories=["LLM", "SANDBOX"])
    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("code-execution", "start")
        context.set_current_step("code-execution")

        # Step 1: 解析代碼請求
        self.logger.progress("code-analysis", "start")
        code_request = context.request.query
        self.logger.progress("code-analysis", "end")

        # Step 2: 生成代碼（使用專門的 prompt）
        self.logger.progress("code-generation", "start")
        prompt = PromptTemplates.get_code_generation_prompt(code_request)
        generated_code = await self._call_llm(prompt, context)

        # 清理可能的空白行
        generated_code = generated_code.strip()

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
        """在沙箱中執行代碼 — 使用真實沙箱服務，無則告知使用者"""
        sandbox_service = self.services.get("sandbox")

        if sandbox_service:
            try:
                result = await sandbox_service.execute("execute_python", {
                    "code": code,
                    "timeout": 30
                })
                return {
                    "success": result.get("success", False),
                    "output": result.get("stdout", "") or result.get("error", "No output")
                }
            except Exception as e:
                self.logger.warning(f"Sandbox service error, using fallback: {e}", "code", "fallback")

        # Sandbox unavailable — return code only, do not fake execution
        self.logger.warning("Sandbox unavailable — code generated but not executed", "code", "no_sandbox")
        return {
            "success": False,
            "output": "[Sandbox unavailable] Code was generated but could not be executed. "
                      "Please set up the Docker sandbox to enable code execution."
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
        rewritten_content = await self._call_llm(full_prompt, context)
        self.logger.progress("markdown-conversion", "end")

        # 輸出結果
        self.logger.message(rewritten_content)
        context.mark_step_complete("rewriting")
        self.logger.progress("rewriting", "end")

        return rewritten_content


# ============================================================
# Enhanced Deep Research Components
# ============================================================

class SearchProviderType(Enum):
    """搜索引擎提供商類型"""
    TAVILY = "tavily"
    EXA = "exa"  # Neural search with semantic understanding
    SERPER = "serper"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    MODEL = "model"  # AI內建搜索


@dataclass
class SearchEngineConfig:
    """搜索引擎配置"""
    primary: SearchProviderType = SearchProviderType.TAVILY
    fallback_chain: List[SearchProviderType] = None
    max_results: int = 10
    timeout: float = 30.0
    parallel_searches: int = 3
    # 平行策略配置
    enable_race_mode: bool = False  # 競速模式：所有引擎同時搜索
    enable_batch_parallel: bool = True  # 批次平行：多個查詢同時執行
    batch_size: int = 3  # 批次大小
    parallel_strategy: str = "batch"  # batch | race | hybrid

    def __post_init__(self):
        if self.fallback_chain is None:
            self.fallback_chain = [
                SearchProviderType.EXA,
                SearchProviderType.SERPER,
                SearchProviderType.DUCKDUCKGO,
                SearchProviderType.MODEL
            ]

        # 根據策略設置對應的標誌
        if self.parallel_strategy == "race":
            self.enable_race_mode = True
            self.enable_batch_parallel = False
        elif self.parallel_strategy == "batch":
            self.enable_race_mode = False
            self.enable_batch_parallel = True
        elif self.parallel_strategy == "hybrid":
            # 混合模式：批次執行 + 每個查詢使用競速
            self.enable_race_mode = True
            self.enable_batch_parallel = True


@dataclass
class ResearchEvent:
    """研究事件"""
    type: str  # progress, message, reasoning, error, search_result
    step: str  # plan, search, synthesize
    data: Any
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_sse(self) -> str:
        """轉換為 SSE 格式"""
        event_data = {
            "type": self.type,
            "step": self.step,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"


class DeepResearchProcessor(BaseProcessor):
    """
    深度研究處理器 - Agent Level with Enhanced Features

    Features:
    - WorkflowState tracking and retry mechanism
    - SSE Streaming support
    - Multi-search engine configuration
    - Event-driven architecture
    - Closed-loop iteration (max 3 iterations)
    - Academic-style reference formatting
    """

    def __init__(self,
                 llm_client=None,
                 services: Optional[Dict[str, Any]] = None,
                 search_config: Optional[SearchEngineConfig] = None,
                 event_callback: Optional[Callable[[ResearchEvent], None]] = None):
        """
        初始化增強版處理器

        Args:
            llm_client: LLM客戶端
            services: 服務字典
            search_config: 搜索引擎配置
            event_callback: 事件回調函數
        """
        super().__init__(llm_client, services)
        self.search_config = search_config or SearchEngineConfig()
        self.event_callback = event_callback
        self.event_queue: asyncio.Queue = asyncio.Queue()

        # 初始化增強日誌系統
        try:
            from core.enhanced_logger import get_enhanced_logger
            self.enhanced_logger = get_enhanced_logger()
        except ImportError:
            self.enhanced_logger = None
        self._streaming_enabled = False

    async def process(self, context: ProcessingContext) -> str:
        """執行完整的深度研究流程 - 符合 AgentRuntime 規範"""

        # Step 1: Init Workflow (符合狀態機 InitWorkflow)
        workflow_state = {
            "status": "running",
            "steps": ["plan", "search", "synthesize"],
            "current_step": None,
            "iterations": 0,
            "errors": []
        }
        context.intermediate_results["workflow_state"] = workflow_state

        # 記錄深度研究決策
        await self._log_tool_decision(
            "deep_research",
            "執行全面的深度研究以回答複雜問題",
            0.95
        )

        try:
            # 執行研究流程 (包裹在 retry 邏輯中)
            return await self._execute_with_retry(context, workflow_state)
        except Exception as e:
            # WorkflowFailed: 記錄失敗狀態
            workflow_state["status"] = "failed"
            workflow_state["errors"].append({
                "error": str(e),
                "step": workflow_state["current_step"],
                "timestamp": datetime.now().isoformat()
            })
            self.logger.error(f"Research workflow failed: {e}", "deep_research", "workflow_failed")
            raise

    async def _execute_with_retry(self, context: ProcessingContext, workflow_state: dict) -> str:
        """執行研究流程，支援重試機制 (符合狀態機 RetryBoundary)"""
        from core.errors import ErrorClassifier

        MAX_RETRIES = 2
        retry_count = 0
        last_error = None

        while retry_count <= MAX_RETRIES:
            try:
                # 執行核心研究流程
                return await self._execute_research_workflow(context, workflow_state)

            except Exception as e:
                # Error Classification (符合狀態機 ErrorHandling)
                error_category = ErrorClassifier.classify(e)

                workflow_state["errors"].append({
                    "error": str(e),
                    "category": error_category,
                    "retry_count": retry_count,
                    "step": workflow_state["current_step"]
                })

                if error_category in ["NETWORK", "LLM"] and retry_count < MAX_RETRIES:
                    # Retryable error - 指數退避重試
                    retry_count += 1
                    delay = 2 ** retry_count  # Exponential backoff
                    self.logger.warning(
                        f"Retryable error ({error_category}), retrying {retry_count}/{MAX_RETRIES} after {delay}s",
                        "deep_research", "retry"
                    )
                    await asyncio.sleep(delay)
                    last_error = e
                else:
                    # Non-retryable or max retries exceeded
                    raise e

        # 如果所有重試都失敗
        if last_error:
            raise last_error

    async def _execute_research_workflow(self, context: ProcessingContext, workflow_state: dict) -> str:
        """執行核心研究工作流程"""

        # 0. 如果查詢複雜，先澄清研究方向
        workflow_state["current_step"] = "clarification"
        if await self._should_clarify(context):
            await self._ask_clarifying_questions(context)

        # 1. 報告計劃階段 (WriteReportPlan)
        workflow_state["current_step"] = "plan"
        report_plan = await self._write_report_plan(context)

        # 初始化研究迭代
        MAX_ITERATIONS = 3
        all_search_results = []
        iteration = 0

        while iteration < MAX_ITERATIONS:
            iteration += 1
            workflow_state["iterations"] = iteration
            self.logger.info(f"🔄 Research Iteration {iteration}/{MAX_ITERATIONS}", "deep_research", "iteration")

            # 2. SERP 查詢生成 (GenerateSearchQueries)
            workflow_state["current_step"] = "search"
            if iteration == 1:
                search_tasks = await self._generate_serp_queries(context, report_plan)
            else:
                # 後續迭代：基於已有結果生成補充查詢
                search_tasks = await self._generate_followup_queries(
                    context, report_plan, all_search_results
                )

            if not search_tasks:  # 沒有更多查詢需求
                break

            # 3. 執行搜索任務 (ExecuteSearchTasks)
            search_results = await self._execute_search_tasks(context, search_tasks)
            all_search_results.extend(search_results)

            # 4. 評估研究是否充分
            is_sufficient = await self._review_research_completeness(
                context, report_plan, all_search_results, iteration
            )

            if is_sufficient:
                self.logger.info("✅ Research is sufficient, proceeding to final report", "deep_research", "complete")
                break

            self.logger.info(f"📊 Research needs more depth, continuing...", "deep_research", "continue")

        # 5. 生成最終報告 (WriteFinalReport)
        workflow_state["current_step"] = "synthesize"
        final_report = await self._write_final_report(context, all_search_results, report_plan)

        # WorkflowComplete: 標記成功完成
        workflow_state["status"] = "completed"
        self.logger.info("✅ Research workflow completed successfully", "deep_research", "workflow_complete")

        return final_report

    async def _should_clarify(self, context: ProcessingContext) -> bool:
        """判斷是否需要澄清研究方向"""
        # 基於查詢複雜度判斷
        complexity_indicators = ['比較', '分析', '評估', '深度', '全面', '詳細', '對比']
        query_lower = context.request.query.lower()
        return any(indicator in query_lower for indicator in complexity_indicators)

    async def _ask_clarifying_questions(self, context: ProcessingContext):
        """詢問澄清問題以更好理解研究需求"""
        self.logger.progress("clarification", "start")

        question_prompt = PromptTemplates.get_system_question_prompt(context.request.query)
        questions = await self._call_llm(question_prompt, context)

        self.logger.info(
            f"❓ Clarifying Questions Generated:\n{questions}",
            "deep_research",
            "clarification"
        )

        # 這裡可以實際發送給用戶並獲取回應
        # 目前先記錄供參考
        context.intermediate_results["clarifying_questions"] = questions

        self.logger.progress("clarification", "end")

    async def _generate_followup_queries(self, context: ProcessingContext,
                                        report_plan: str,
                                        existing_results: List[Dict]) -> List[Dict]:
        """生成後續查詢以填補研究空缺"""
        self.logger.progress("followup-query", "start")

        # 準備已有學習成果
        learnings = self._prepare_report_context(existing_results)

        # 使用 review prompt 來生成補充查詢
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

        review_prompt = PromptTemplates.get_review_prompt(
            plan=report_plan,
            learnings=learnings,
            suggestion="Focus on filling knowledge gaps and getting more specific details",
            output_schema=output_schema
        )

        response = await self._call_llm(review_prompt, context)

        # 解析新查詢
        try:
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                queries = json.loads(json_match.group(1))
            else:
                queries = json.loads(response)
        except:
            queries = []

        self.logger.info(
            f"📋 Follow-up Queries: Generated {len(queries)} additional queries",
            "deep_research",
            "followup"
        )

        self.logger.progress("followup-query", "end")
        return queries

    async def _review_research_completeness(self, context: ProcessingContext,
                                           report_plan: str,
                                           search_results: List[Dict],
                                           iteration: int) -> bool:
        """評估研究是否充分完整"""
        self.logger.progress("review", "start")

        # 準備評估上下文
        learnings = self._prepare_report_context(search_results)

        # 簡單的完整性檢查
        review_prompt = f"""Based on the research plan and collected information, evaluate if the research is sufficient.

Research Plan:
{report_plan[:500]}

Collected Information Summary:
- Number of sources: {sum(len(r['result'].get('sources', [])) for r in search_results)}
- Topics covered: {len(search_results)}
- Current iteration: {iteration}

Learnings:
{learnings[:1000]}

Answer with YES if research is sufficient, NO if more research is needed.
Consider: coverage of all plan sections, depth of information, quality of sources.

Answer (YES/NO):"""

        response = await self._call_llm(review_prompt, context)

        is_sufficient = "YES" in response.upper()[:10]

        self.logger.info(
            f"📊 Research Completeness: {'Sufficient' if is_sufficient else 'Needs more'}",
            "deep_research",
            "review",
            iteration=iteration,
            is_sufficient=is_sufficient
        )

        self.logger.progress("review", "end", {"is_sufficient": is_sufficient})

        return is_sufficient

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

        # 推理過程
        self.logger.reasoning("開始分析研究需求...", streaming=True)
        plan = await self._call_llm(plan_prompt, context)

        # 記錄計劃到日誌
        self.logger.info(
            f"📋 Research plan created: {plan[:300]}...",
            "deep_research",
            "plan_result",
            plan_length=len(plan)
        )

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
        response = await self._call_llm(serp_prompt, context)

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
        """Phase 3: 執行搜索任務 - 支援批次平行搜索"""
        self.logger.progress("task-list", "start")

        # 記錄任務列表
        self.logger.info(
            f"📋 Task List: Executing {len(search_tasks)} search tasks (parallel batch size: {self.search_config.parallel_searches})",
            "deep_research",
            "tasks",
            phase="task-list",
            total_tasks=len(search_tasks),
            parallel_batch_size=self.search_config.parallel_searches
        )

        results = []

        # 將任務分批執行
        batch_size = self.search_config.parallel_searches

        for batch_start in range(0, len(search_tasks), batch_size):
            batch_end = min(batch_start + batch_size, len(search_tasks))
            batch_tasks = search_tasks[batch_start:batch_end]

            self.logger.info(
                f"🚀 Executing batch {batch_start//batch_size + 1}: Tasks {batch_start+1}-{batch_end}",
                "deep_research",
                "batch_execution",
                batch_index=batch_start//batch_size + 1,
                batch_size=len(batch_tasks)
            )

            # 準備批次搜索任務
            async_tasks = []
            for i, task in enumerate(batch_tasks, batch_start + 1):
                query = task.get('query', '')
                goal = task.get('researchGoal', '')
                priority = task.get('priority', 1)

                # 記錄搜索任務
                self.logger.info(
                    f"🔎 Search Task {i}/{len(search_tasks)}: {query}",
                    "deep_research",
                    "search_task",
                    task_index=i,
                    query=query,
                    goal=goal,
                    priority=priority,
                    provider=self.search_config.primary.value
                )

                # 添加到異步任務列表
                async_tasks.append(
                    self._execute_single_search_task(i, task, query, goal, priority)
                )

            # 平行執行批次搜索
            batch_results = await asyncio.gather(*async_tasks, return_exceptions=True)

            # 處理批次結果
            for task, result in zip(batch_tasks, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"❌ Search task failed: {str(result)}",
                        "deep_research",
                        "search_error",
                        error=str(result)
                    )
                    # 創建錯誤結果
                    result = {
                        'query': task.get('query', ''),
                        'goal': task.get('researchGoal', ''),
                        'priority': task.get('priority', 1),
                        'result': {
                            'error': str(result),
                            'sources': [],
                            'summary': f"Search failed: {str(result)}"
                        }
                    }

                results.append(result)

        self.logger.progress("task-list", "end")

        # 記錄總結
        total_sources = sum(len(r.get('result', {}).get('sources', [])) for r in results)
        self.logger.info(
            f"📊 Search Summary: {total_sources} total sources from {len(search_tasks)} tasks",
            "deep_research",
            "summary",
            phase="search-complete",
            total_sources=total_sources,
            total_tasks=len(search_tasks)
        )

        return results

    async def _execute_single_search_task(self, index: int, task: Dict, query: str, goal: str, priority: int) -> Dict:
        """執行單個搜索任務"""
        try:
            # 開始單個搜索任務
            self.logger.progress("search-task", "start", {"name": query})

            # 推理過程
            self.logger.reasoning(f"正在搜索：{query}...", streaming=True)

            # 執行搜索（支援多引擎平行搜索）
            search_result = await self._perform_parallel_deep_search(query, goal)

            # 記錄搜索結果
            self.logger.info(
                f"✅ Search Result {index}: Found {len(search_result.get('sources', []))} sources",
                "deep_research",
                "search_result",
                task_index=index,
                sources_count=len(search_result.get('sources', [])),
                relevance_score=search_result.get('relevance', 0)
            )

            # 消息輸出
            self.logger.message(f"搜索 {index}: {query}\n結果: {search_result.get('summary', '')[:200]}...")

            # 結束單個搜索任務
            self.logger.progress("search-task", "end", {
                "name": query,
                "data": search_result
            })

            return {
                'query': query,
                'goal': goal,
                'priority': priority,
                'result': search_result
            }
        except Exception as e:
            self.logger.error(
                f"Error in search task: {str(e)}",
                "deep_research",
                "task_error"
            )
            raise

    async def _perform_parallel_deep_search(self, query: str, goal: str) -> Dict:
        """執行平行深度搜索 - 同時使用多個搜索引擎"""

        # 如果啟用了 race 模式，同時啟動所有搜索引擎
        if hasattr(self.search_config, 'enable_race_mode') and self.search_config.enable_race_mode:
            return await self._perform_race_search(query, goal)

        # 否則使用增強版搜索（帶降級）
        return await self._perform_deep_search_enhanced(query, goal)

    async def _perform_race_search(self, query: str, goal: str) -> Dict:
        """競速模式：同時執行多個搜索引擎，返回第一個成功的結果"""

        # 準備所有搜索提供商
        providers = [self.search_config.primary] + (self.search_config.fallback_chain or [])

        self.logger.info(
            f"🏁 Race mode: Starting {len(providers)} search engines in parallel",
            "deep_research",
            "race_mode",
            providers=[p.value for p in providers]
        )

        # 創建所有搜索任務
        search_tasks = [
            self._try_search_provider_with_timeout(provider, query, goal)
            for provider in providers
        ]

        # 使用 asyncio.as_completed 獲取第一個成功的結果
        for future in asyncio.as_completed(search_tasks):
            try:
                result = await future
                if result and result.get('sources'):
                    provider_name = result.get('provider', 'unknown')
                    self.logger.info(
                        f"🏆 Race winner: {provider_name} returned first with {len(result.get('sources', []))} sources",
                        "deep_research",
                        "race_winner",
                        provider=provider_name
                    )
                    return result
            except Exception as e:
                # 忽略單個引擎的錯誤，繼續等待其他引擎
                continue

        # 如果所有引擎都失敗，返回空結果
        return {
            'summary': 'No search results available',
            'sources': [],
            'relevance': 0
        }

    async def _try_search_provider_with_timeout(self, provider: SearchProviderType, query: str, goal: str) -> Optional[Dict]:
        """帶超時的搜索提供商嘗試"""
        try:
            # 使用配置的超時時間
            timeout = getattr(self.search_config, 'timeout', 30.0)

            result = await asyncio.wait_for(
                self._try_search_provider(provider, query, goal),
                timeout=timeout
            )

            if result:
                result['provider'] = provider.value

            return result

        except asyncio.TimeoutError:
            self.logger.warning(
                f"⏱️ Search timeout for {provider.value} after {timeout}s",
                "deep_research",
                "timeout"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Search error with {provider.value}: {str(e)}",
                "deep_research",
                "provider_error"
            )
            return None

    async def _perform_deep_search(self, query: str, goal: str) -> Dict:
        """執行深度搜索 — 使用真實搜索服務，無則返回空結果"""

        search_service = self.services.get("search")

        # 記錄 Web Query
        self.logger.info(
            f"🌐 Web Query: {query}",
            "web",
            "query",
            query=query,
            goal=goal,
            search_engine="web" if search_service else "none",
            max_results=10
        )

        # Use real search service if available
        search_result = None
        if search_service:
            try:
                results = await search_service.search(query, max_results=10)
                if results:
                    sources = [
                        {'url': r.url, 'title': r.title, 'relevance': 0.9}
                        for r in results
                    ]
                    summary = "\n".join(
                        f"- {r.title}: {r.snippet}" for r in results[:5]
                    )
                    search_result = {
                        'summary': summary,
                        'sources': sources,
                        'relevance': 0.92,
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                self.logger.warning(f"Search service error in deep research: {e}", "web", "fallback")

        # Fallback: search unavailable — return empty result with disclaimer
        if not search_result:
            self.logger.warning(
                f"Web search unavailable for deep research query: {query}",
                "web", "no_results"
            )
            search_result = {
                'summary': f"[Web search unavailable] Unable to retrieve real-time results for '{query}'. "
                           f"The final report will be based on the AI model's training data only.",
                'sources': [],
                'relevance': 0.0,
                'timestamp': datetime.now().isoformat()
            }

        # 記錄搜索結果詳情
        self.logger.info(
            f"🔗 Web Results: Retrieved {len(search_result['sources'])} sources",
            "web",
            "results",
            sources=search_result['sources'][:5],
            avg_relevance=search_result['relevance']
        )

        # 如果有 LLM，處理搜索結果
        if self.llm_client:
            result_prompt = PromptTemplates.get_search_result_prompt(
                query=query,
                research_goal=goal,
                context=json.dumps(search_result, ensure_ascii=False)
            )
            processed = await self._call_llm(result_prompt, None)
            search_result['processed'] = processed

        return search_result

    async def _write_final_report(self, context: ProcessingContext,
                                  search_results: List[Dict],
                                  report_plan: str) -> str:
        """Phase 4: 生成最終報告 - 學術論文格式（區分引用/未引用）"""
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

        # 準備上下文和參考文獻
        combined_context = self._prepare_report_context(search_results)
        references_list = self._extract_references(search_results)

        # 記錄記憶體操作
        self.logger.info(
            f"💾 Memory: Storing research context",
            "memory",
            "store",
            context_size=len(combined_context),
            chunks=len(search_results),
            type="research_report"
        )

        # 構建增強的 prompt，包含參考文獻指引
        enhanced_prompt = self._build_academic_report_prompt(
            report_plan,
            combined_context,
            references_list,
            context.request.query
        )

        # 推理最終報告
        self.logger.reasoning("綜合所有研究結果，生成最終報告...", streaming=True)

        # 生成報告主體
        report_body = await self._call_llm(enhanced_prompt, context)

        # 分析哪些參考文獻被實際引用
        cited_refs, uncited_refs = self._analyze_citations(report_body, references_list)

        # 組合完整報告：主體 + 區分的參考文獻
        final_report = self._format_report_with_categorized_references(
            report_body, cited_refs, uncited_refs, context
        )

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

    def _extract_references(self, search_results: List[Dict]) -> List[Dict]:
        """從搜索結果中提取參考文獻"""
        references = []
        ref_id = 1

        for result in search_results:
            sources = result.get('result', {}).get('sources', [])
            for source in sources:
                if source.get('url'):
                    references.append({
                        'id': ref_id,
                        'title': source.get('title', 'Untitled'),
                        'url': source.get('url'),
                        'query': result.get('query', ''),
                        'relevance': source.get('relevance', 0)
                    })
                    ref_id += 1

        # 按相關性排序
        references.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return references

    def _build_academic_report_prompt(self, plan: str, context: str,
                                     references: List[Dict], requirement: str) -> str:
        """構建學術格式的報告 prompt"""
        # 準備參考文獻摘要
        ref_summary = "\n".join([
            f"[{ref['id']}] {ref['title']}"
            for ref in references[:20]  # 最多使用前20個參考
        ])

        prompt = f"""Generate a comprehensive research report based on the following information.

Research Plan:
{plan}

Research Context and Findings:
{context}

Available References:
{ref_summary}

Requirements:
1. Write in academic style with clear sections
2. Use inline citations like [1], [2], [3] when referencing information
3. Each claim should be supported by citations
4. DO NOT include a references section in your output (it will be added separately)
5. Focus on synthesis and analysis, not just summarization
6. Ensure logical flow between sections

User's Research Question:
{requirement}

IMPORTANT:
- Use citations [1] to [{len(references)}] naturally throughout the text
- Make the report comprehensive and detailed (aim for 1000+ words)
- Structure with clear headings using ## for main sections
- Write in professional, academic tone

Generate the report body (without references section):"""

        # 加上輸出指南
        output_guidelines = PromptTemplates.get_output_guidelines()
        return f"{prompt}\n\n{output_guidelines}"

    def _analyze_citations(self, report_body: str, references: List[Dict]) -> tuple:
        """分析報告中實際引用的參考文獻"""
        import re

        # 找出所有引用的編號
        citation_pattern = r'\[(\d+)\]'
        cited_numbers = set()

        for match in re.finditer(citation_pattern, report_body):
            try:
                ref_num = int(match.group(1))
                cited_numbers.add(ref_num)
            except ValueError:
                continue

        # 分類參考文獻
        cited_refs = []
        uncited_refs = []

        for ref in references:
            if ref['id'] in cited_numbers:
                cited_refs.append(ref)
            else:
                uncited_refs.append(ref)

        return cited_refs, uncited_refs

    def _format_report_with_categorized_references(self, report_body: str,
                                                   cited_refs: List[Dict],
                                                   uncited_refs: List[Dict],
                                                   context: ProcessingContext = None) -> str:
        """格式化報告，區分引用和未引用的參考文獻"""

        # 構建參考文獻部分
        references_section = "\n\n---\n\n"

        # 第一部分：引用的參考文獻
        if cited_refs:
            references_section += "## 📚 參考文獻 (Cited References)\n\n"
            references_section += "*以下為報告中實際引用的文獻：*\n\n"

            for ref in cited_refs[:30]:  # 限制最多30個
                ref_entry = f"[{ref['id']}] **{ref['title']}**\n"
                if ref.get('url'):
                    ref_entry += f"   📍 URL: {ref['url']}\n"
                if ref.get('query'):
                    ref_entry += f"   🔍 Search context: {ref['query'][:50]}...\n"
                references_section += f"{ref_entry}\n"

        # 第二部分：相關但未引用的參考文獻
        if uncited_refs:
            references_section += "\n## 📖 相關文獻 (Related Sources - Not Cited)\n\n"
            references_section += "*以下為研究過程中查閱但未直接引用的相關資料：*\n\n"

            for ref in uncited_refs[:20]:  # 限制最多20個
                ref_entry = f"• {ref['title']}\n"
                if ref.get('url'):
                    ref_entry += f"  URL: {ref['url']}\n"
                references_section += f"{ref_entry}\n"

        # 添加統計資訊
        references_section += f"\n---\n\n## 📊 引用統計 (Citation Statistics)\n\n"
        references_section += f"- **實際引用文獻**: {len(cited_refs)} 篇\n"
        references_section += f"- **相關未引用文獻**: {len(uncited_refs)} 篇\n"
        references_section += f"- **總查閱文獻**: {len(cited_refs) + len(uncited_refs)} 篇\n"
        references_section += f"- **引用率**: {len(cited_refs) / max(1, len(cited_refs) + len(uncited_refs)) * 100:.1f}%\n"
        references_section += f"\n---\n"
        references_section += f"*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        references_section += f"*Powered by OpenCode Deep Research Engine*"

        # 組合完整報告
        full_report = f"{report_body}{references_section}"

        # 保存報告到 Markdown（如果增強日誌器可用）
        if self.enhanced_logger and context:
            try:
                # 準備元數據
                metadata = {
                    "query": context.request.query if context.request else "N/A",
                    "mode": "deep_research",
                    "model": getattr(self.llm_client, 'model', 'unknown'),
                    "timestamp": datetime.now().isoformat(),
                    "duration_ms": context.intermediate_results.get("total_duration_ms", 0),
                    "tokens": context.intermediate_results.get("total_tokens", {}),
                    "citations": {
                        "cited_count": len(cited_refs),
                        "uncited_count": len(uncited_refs),
                        "total_count": len(cited_refs) + len(uncited_refs),
                        "citation_rate": len(cited_refs) / max(1, len(cited_refs) + len(uncited_refs)) * 100
                    },
                    "stages": context.intermediate_results.get("stages", [])
                }

                # 保存到 Markdown
                trace_id = context.trace_id if hasattr(context, 'trace_id') else str(hash(context.request.query))[:8]
                md_path = self.enhanced_logger.save_response_as_markdown(
                    full_report,
                    metadata,
                    trace_id
                )

                # 記錄長內容（如果超過限制）
                if len(full_report) > self.enhanced_logger.MAX_LOG_SIZE:
                    self.enhanced_logger.log_long_content(
                        "INFO",
                        "Deep Research Report Generated",
                        full_report,
                        trace_id,
                        "deep_research"
                    )

                self.logger.info(f"📄 Report saved to: {md_path}", "deep_research", "markdown_saved")

            except Exception as e:
                self.logger.warning(f"Failed to save markdown report: {e}", "deep_research", "save_error")

        return full_report

    # ============================================================
    # Enhanced Deep Research Methods (SSE Streaming & Events)
    # ============================================================

    async def process_with_streaming(self, context: ProcessingContext) -> AsyncGenerator[str, None]:
        """
        支援 SSE Streaming 的處理方法

        Yields:
            SSE 格式的事件字符串
        """
        self._streaming_enabled = True

        # 啟動事件處理協程
        event_task = asyncio.create_task(self._event_stream_handler())

        try:
            # 發送開始事件
            await self._emit_event(ResearchEvent(
                type="progress",
                step="init",
                data={"status": "start", "query": context.request.query}
            ))

            # 執行研究流程
            result = await self.process(context)

            # 發送完成事件
            await self._emit_event(ResearchEvent(
                type="progress",
                step="complete",
                data={"status": "complete", "result_length": len(result)}
            ))

            # 發送最終結果
            yield f"data: {json.dumps({'type': 'final_report', 'data': result}, ensure_ascii=False)}\n\n"

        finally:
            # 清理
            self._streaming_enabled = False
            await self.event_queue.put(None)  # 結束信號
            await event_task

    async def _event_stream_handler(self):
        """處理事件流"""
        while True:
            event = await self.event_queue.get()
            if event is None:
                break

            # 如果有回調函數，調用它
            if self.event_callback:
                try:
                    await self._call_event_callback(event)
                except Exception as e:
                    self.logger.warning(f"Event callback error: {e}", "deep_research", "callback_error")

    async def _call_event_callback(self, event: ResearchEvent):
        """安全調用事件回調"""
        if asyncio.iscoroutinefunction(self.event_callback):
            await self.event_callback(event)
        else:
            self.event_callback(event)

    async def _emit_event(self, event: ResearchEvent):
        """發送事件"""
        if hasattr(self, 'event_queue'):
            await self.event_queue.put(event)

        # 同時記錄到日誌
        self.logger.info(
            f"📡 Event: {event.type} - {event.step}",
            "deep_research",
            "event",
            event_type=event.type,
            event_step=event.step
        )

    # ============================================================
    # Multi-Search Engine Support
    # ============================================================

    async def _perform_deep_search_enhanced(self, query: str, goal: str) -> Dict:
        """
        增強版深度搜索 - 支援多搜索引擎和智能降級
        """
        # 發送搜索開始事件
        await self._emit_event(ResearchEvent(
            type="progress",
            step="search",
            data={
                "status": "start",
                "query": query,
                "goal": goal,
                "provider": self.search_config.primary.value
            }
        ))

        # 嘗試主要搜索引擎
        search_result = await self._try_search_provider(
            self.search_config.primary,
            query,
            goal
        )

        # 如果主要引擎失敗，嘗試備用鏈
        if not search_result or not search_result.get('sources'):
            for fallback_provider in self.search_config.fallback_chain:
                self.logger.info(
                    f"🔄 Switching to fallback: {fallback_provider.value}",
                    "deep_research",
                    "fallback"
                )

                await self._emit_event(ResearchEvent(
                    type="message",
                    step="search",
                    data={
                        "message": f"Switching to {fallback_provider.value}...",
                        "provider": fallback_provider.value
                    }
                ))

                search_result = await self._try_search_provider(
                    fallback_provider,
                    query,
                    goal
                )

                if search_result and search_result.get('sources'):
                    break

        # 發送搜索結果事件
        if search_result:
            await self._emit_event(ResearchEvent(
                type="search_result",
                step="search",
                data={
                    "query": query,
                    "sources_count": len(search_result.get('sources', [])),
                    "summary": search_result.get('summary', '')[:200]
                }
            ))

        return search_result or self._empty_search_result(query)

    async def _try_search_provider(self,
                                   provider: SearchProviderType,
                                   query: str,
                                   goal: str) -> Optional[Dict]:
        """嘗試使用特定搜索提供商"""
        try:
            if provider == SearchProviderType.MODEL:
                # 使用 AI 模型內建搜索
                return await self._model_based_search(query, goal)
            elif provider == SearchProviderType.EXA:
                # 使用 Exa neural search
                return await self._exa_search(query, goal)

            # 使用其他搜索服務
            search_service = self.services.get("search")
            if search_service:
                # 如果服務支援設置提供商
                if hasattr(search_service, 'set_provider'):
                    search_service.set_provider(provider.value.lower())

                results = await search_service.search(
                    query=query,
                    max_results=self.search_config.max_results
                )

                if results:
                    return self._format_search_results(results, provider.value)

        except Exception as e:
            self.logger.warning(
                f"Search error with {provider.value}: {e}",
                "deep_research",
                "search_error"
            )

        return None

    async def _exa_search(self, query: str, goal: str) -> Optional[Dict]:
        """使用 Exa API 進行神經搜索"""
        search_service = self.services.get("search")
        if not search_service:
            return None

        # 判斷搜索類型
        search_type = "general"
        if "code" in goal.lower() or "programming" in goal.lower():
            search_type = "code"
        elif "research" in goal.lower() or "paper" in goal.lower():
            search_type = "research"
        elif "news" in goal.lower() or "latest" in goal.lower():
            search_type = "news"

        try:
            # 使用整合的搜索服務（已包含 Exa）
            if hasattr(search_service, 'provider'):
                old_provider = search_service.provider
                search_service.provider = "exa"
                results = await search_service.search(
                    query=query,
                    max_results=self.search_config.max_results,
                    search_type=search_type
                )
                search_service.provider = old_provider

                if results:
                    return self._format_search_results(results, "exa")

        except Exception as e:
            self.logger.error(f"Exa search failed: {e}", "deep_research", "exa_error")

        return None

    async def _model_based_search(self, query: str, goal: str) -> Dict:
        """使用 AI 模型的內建搜索能力"""
        if not self.llm_client:
            return self._empty_search_result(query)

        search_prompt = f"""Please search and provide information about:
Query: {query}
Research Goal: {goal}

Provide a comprehensive answer based on your knowledge, formatted as:
1. Summary of findings
2. Key facts and details
3. Relevant context

Focus on accuracy and relevance."""

        try:
            response = await self._call_llm(search_prompt, None)

            return {
                'summary': response,
                'sources': [{
                    'title': 'AI Knowledge Base',
                    'url': 'model://knowledge',
                    'relevance': 0.8
                }],
                'relevance': 0.8,
                'timestamp': datetime.now().isoformat(),
                'provider': 'model'
            }
        except Exception as e:
            self.logger.error(f"Model search failed: {e}", "deep_research", "model_search_error")
            return self._empty_search_result(query)

    def _format_search_results(self, results: List, provider: str) -> Dict:
        """格式化搜索結果"""
        if not results:
            return None

        sources = []
        summary_parts = []

        for r in results[:self.search_config.max_results]:
            # 適配不同的結果格式
            if hasattr(r, 'url'):
                sources.append({
                    'url': r.url,
                    'title': getattr(r, 'title', 'Untitled'),
                    'relevance': getattr(r, 'score', 0.5)
                })
                summary_parts.append(f"- {r.title}: {getattr(r, 'snippet', '')[:100]}")
            elif isinstance(r, dict):
                sources.append({
                    'url': r.get('url', ''),
                    'title': r.get('title', 'Untitled'),
                    'relevance': r.get('score', 0.5)
                })
                summary_parts.append(f"- {r.get('title')}: {r.get('snippet', '')[:100]}")

        return {
            'summary': '\n'.join(summary_parts),
            'sources': sources,
            'relevance': sum(s['relevance'] for s in sources) / max(len(sources), 1),
            'timestamp': datetime.now().isoformat(),
            'provider': provider
        }

    def _empty_search_result(self, query: str) -> Dict:
        """返回空搜索結果"""
        return {
            'summary': f"[No search results available for: {query}]",
            'sources': [],
            'relevance': 0.0,
            'timestamp': datetime.now().isoformat(),
            'provider': 'none'
        }

    # Configuration methods
    def configure_search_engines(self, config: SearchEngineConfig):
        """動態配置搜索引擎"""
        self.search_config = config
        self.logger.info(
            f"Search engines configured: primary={config.primary.value}, "
            f"fallback={[p.value for p in config.fallback_chain]}",
            "deep_research",
            "config_update"
        )

    def enable_streaming(self, enabled: bool = True):
        """啟用/禁用 streaming"""
        self._streaming_enabled = enabled

    def set_event_callback(self, callback: Callable[[ResearchEvent], None]):
        """設置事件回調"""
        self.event_callback = callback


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

    # Cognitive level mapping for each processing mode
    COGNITIVE_MAPPING: Dict[str, str] = {
        "chat": "system1",
        "knowledge": "system1",
        "search": "system2",
        "code": "system2",
        "thinking": "system2",
        "deep_research": "agent",
    }

    def __init__(self, llm_client=None, services: Optional[Dict[str, Any]] = None):
        self.llm_client = llm_client
        self.services = services or {}
        self._instances: Dict[ProcessingMode, BaseProcessor] = {}

    def get_processor(self, mode: ProcessingMode) -> BaseProcessor:
        """獲取處理器實例"""
        if mode not in self._instances:
            processor_class = self._processors.get(mode, ChatProcessor)
            instance = processor_class(self.llm_client, services=self.services)
            instance._cognitive_level = self.COGNITIVE_MAPPING.get(mode.value)
            self._instances[mode] = instance

        return self._instances[mode]

    def register_processor(self, mode: ProcessingMode, processor_class: Type[BaseProcessor]):
        """註冊自定義處理器"""
        self._processors[mode] = processor_class
        # 清除已有實例，下次獲取時會創建新的
        if mode in self._instances:
            del self._instances[mode]