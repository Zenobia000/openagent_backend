"""
Search Processor - Iterative web search with quality evaluation

Performs multi-iteration web searches with quality assessment and refinement.
Extracted from monolithic processor.py
"""

import json
import re
from typing import Dict, List

from .base import BaseProcessor
from ..models import ProcessingContext
from ..prompts import PromptTemplates
from ..error_handler import enhanced_error_handler


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
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                queries = json.loads(json_match.group(0))
                return queries[:2]  # 限制最多2個新查詢
        except:
            pass

        return []
