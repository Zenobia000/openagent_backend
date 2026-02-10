"""
增強版引擎 - 整合統一日誌系統
展示如何在現有系統中使用新的日誌架構
"""

import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 導入統一日誌系統
from utils.unified_logger import (
    unified_logger,
    sse_logger,
    EventType,
    LogLevel,
    measure_async_performance,
    log_function_call
)

# 導入原有系統組件
from core.unified_final_engine import (
    ProcessingMode,
    UnifiedRequest,
    UnifiedResponse
)


class EnhancedEngine:
    """
    增強版引擎 - 展示統一日誌系統的使用
    """

    def __init__(self):
        self.logger = unified_logger
        self.sse_logger = sse_logger
        self.llm_client = None

    async def process_request(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        處理請求 - 完整的日誌記錄示例
        """
        # 1. 開始新的追蹤
        trace_id = self.logger.with_trace().trace_id
        self.logger.with_context(
            context_id=request.context_id,
            request_mode=request.mode.value if request.mode else "auto"
        )

        try:
            # 2. 記錄請求開始
            self.logger.info(
                f"Processing request: {request.query[:50]}...",
                event_type=EventType.PIPELINE_START,
                metadata={
                    "mode": request.mode.value if request.mode else None,
                    "query_length": len(request.query)
                }
            )

            # 3. SSE 事件: 開始處理
            self.sse_logger.log_progress("request-processing", "start")

            # 4. 工具決策
            selected_tool = await self._decide_tool(request)

            # 5. 執行處理
            with self.logger.measure_performance("main_processing"):
                if selected_tool == "llm":
                    result = await self._process_with_llm(request)
                elif selected_tool == "rag":
                    result = await self._process_with_rag(request)
                elif selected_tool == "web_search":
                    result = await self._process_with_web_search(request)
                else:
                    result = await self._process_default(request)

            # 6. SSE 事件: 處理完成
            self.sse_logger.log_progress("request-processing", "end", {
                "tool_used": selected_tool,
                "response_length": len(result.result)
            })

            # 7. 記錄成功
            self.logger.info(
                "Request processed successfully",
                event_type=EventType.PIPELINE_END,
                metadata={
                    "trace_id": trace_id,
                    "tool_used": selected_tool
                },
                performance={
                    "total_tokens": result.usage.get("tokens", 0)
                }
            )

            return result

        except Exception as e:
            # 8. 錯誤處理
            self.logger.log_exception(e, {
                "trace_id": trace_id,
                "query": request.query,
                "mode": request.mode.value if request.mode else None
            })

            # SSE 錯誤事件
            self.sse_logger.log_progress("request-processing", "error", {
                "error": str(e)
            })

            raise
        finally:
            # 9. 清理
            self.logger.clear_context()

    async def _decide_tool(self, request: UnifiedRequest) -> str:
        """
        工具決策 - 記錄決策過程
        """
        with self.logger.measure_performance("tool_decision"):
            # 模擬工具決策邏輯
            query_lower = request.query.lower()

            if "搜尋" in query_lower or "search" in query_lower:
                selected = "web_search"
                alternatives = ["rag", "llm"]
                confidence = 0.9
            elif "知識" in query_lower or "knowledge" in query_lower:
                selected = "rag"
                alternatives = ["web_search", "llm"]
                confidence = 0.85
            else:
                selected = "llm"
                alternatives = ["rag", "web_search"]
                confidence = 0.7

            # 記錄工具決策
            self.logger.log_tool_decision(
                selected_tool=selected,
                alternatives=alternatives,
                confidence=confidence,
                reason=f"Based on query analysis: '{request.query[:30]}...'"
            )

            return selected

    @measure_async_performance("llm_processing")
    async def _process_with_llm(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        LLM 處理 - 記錄 LLM 調用
        """
        # SSE: 開始 LLM 處理
        self.sse_logger.log_progress("llm-generation", "start")

        # 模擬 LLM 調用
        start_time = asyncio.get_event_loop().time()

        # 記錄 prompt 準備
        self.logger.debug(
            "Preparing LLM prompt",
            metadata={"prompt_template": "default", "max_tokens": 2000}
        )

        # 模擬流式響應
        response_chunks = [
            "這是", "一個", "模擬的", "LLM", "響應",
            "，展示", "如何", "記錄", "流式", "輸出"
        ]

        full_response = ""
        for i, chunk in enumerate(response_chunks):
            await asyncio.sleep(0.1)  # 模擬延遲

            # 記錄流式輸出
            self.sse_logger.log_message(chunk, is_streaming=True)
            full_response += chunk

            # 每 5 個 chunk 記錄一次進度
            if i % 5 == 0:
                self.logger.trace(f"LLM streaming progress: {i}/{len(response_chunks)}")

        # 計算性能指標
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        prompt_tokens = len(request.query.split())
        completion_tokens = len(full_response.split())

        # 記錄 LLM 調用統計
        self.logger.log_llm_call(
            provider="openai",
            model="gpt-4o",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=0.002 * (prompt_tokens + completion_tokens) / 1000
        )

        # SSE: 完成 LLM 處理
        self.sse_logger.log_progress("llm-generation", "end", {
            "response_length": len(full_response)
        })

        return UnifiedResponse(
            result=full_response,
            mode=ProcessingMode.CHAT,
            usage={"tokens": prompt_tokens + completion_tokens}
        )

    @measure_async_performance("rag_processing")
    async def _process_with_rag(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        RAG 處理 - 記錄檢索過程
        """
        # SSE: 開始 RAG 處理
        self.sse_logger.log_progress("rag-retrieval", "start")

        # 1. Embedding 階段
        with self.logger.measure_performance("embedding_generation"):
            await asyncio.sleep(0.05)  # 模擬 embedding
            embedding_dim = 1536
            self.logger.debug(
                "Generated query embedding",
                metadata={"dimension": embedding_dim}
            )

        # 2. 檢索階段
        retrieval_start = asyncio.get_event_loop().time()
        await asyncio.sleep(0.1)  # 模擬檢索

        # 記錄 RAG 操作
        self.logger.log_rag_operation(
            operation="retrieval",
            collection="knowledge_base",
            query_time_ms=(asyncio.get_event_loop().time() - retrieval_start) * 1000,
            results_count=5,
            top_score=0.92
        )

        # 3. 生成響應
        self.sse_logger.log_message("基於知識庫生成響應...")

        response = f"根據知識庫檢索，關於 '{request.query}' 的答案是..."

        # SSE: 完成 RAG 處理
        self.sse_logger.log_progress("rag-retrieval", "end", {
            "documents_used": 5
        })

        return UnifiedResponse(
            result=response,
            mode=ProcessingMode.KNOWLEDGE,
            usage={"tokens": 500}
        )

    @measure_async_performance("web_search_processing")
    async def _process_with_web_search(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        Web 搜尋處理 - 記錄搜尋過程
        """
        # SSE: 開始搜尋
        self.sse_logger.log_progress("web-search", "start")

        # 記錄搜尋查詢
        self.logger.info(
            f"Performing web search",
            event_type=EventType.WEB_SEARCH,
            metadata={
                "query": request.query,
                "provider": "duckduckgo",
                "max_results": 10
            }
        )

        # 模擬搜尋
        await asyncio.sleep(0.2)

        # 記錄搜尋結果
        self.logger.debug(
            "Web search completed",
            metadata={
                "results_count": 10,
                "top_domain": "wikipedia.org",
                "relevance_score": 0.88
            }
        )

        response = f"搜尋 '{request.query}' 的結果..."

        # SSE: 完成搜尋
        self.sse_logger.log_progress("web-search", "end", {
            "results_found": 10
        })

        return UnifiedResponse(
            result=response,
            mode=ProcessingMode.KNOWLEDGE,
            usage={"tokens": 300}
        )

    async def _process_default(self, request: UnifiedRequest) -> UnifiedResponse:
        """默認處理"""
        self.logger.warn(
            "Using default processor",
            metadata={"reason": "No specific tool matched"}
        )

        return UnifiedResponse(
            result=f"處理查詢: {request.query}",
            mode=ProcessingMode.CHAT,
            usage={"tokens": 100}
        )


# ========================================
# 使用示例
# ========================================
async def demo():
    """演示統一日誌系統的使用"""

    # 配置日誌
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(message)s'
    )

    # 創建引擎
    engine = EnhancedEngine()

    # 測試不同類型的請求
    test_queries = [
        "什麼是量子計算？",
        "搜尋最新的 AI 新聞",
        "從知識庫查詢 Python 教程"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"處理查詢: {query}")
        print('='*60)

        request = UnifiedRequest(
            query=query,
            mode=None,  # 自動決定
            context_id="demo_context"
        )

        try:
            response = await engine.process_request(request)
            print(f"\n響應: {response.result}")
        except Exception as e:
            print(f"\n錯誤: {e}")


if __name__ == "__main__":
    asyncio.run(demo())