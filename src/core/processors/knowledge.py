"""
Knowledge Processor - System 1 with RAG and Cache Support

Retrieves information from knowledge base with document reranking.
Extracted from monolithic processor.py
"""

import json
import re
from typing import List

from .base import BaseProcessor
from ..models import ProcessingContext
from ..prompts import PromptTemplates


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
            system_prompt = PromptTemplates.get_system_instruction("knowledge")
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
