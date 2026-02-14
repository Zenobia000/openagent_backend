"""
單元測試 - 所有處理器模式
測試 chat, thinking, knowledge, search, code, research 六種模式
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.processor import (
    ChatProcessor,
    ThinkingProcessor,
    KnowledgeProcessor,
    SearchProcessor,
    CodeProcessor,
    DeepResearchProcessor,
    ProcessorFactory
)
from core.models import ProcessingContext, ProcessingMode, Request
from core.logger import structured_logger


# ========== Fixtures ==========
@pytest.fixture
def mock_llm_client():
    """模擬 LLM 客戶端"""
    client = AsyncMock()
    client.generate = AsyncMock(return_value="Test LLM Response")
    return client


@pytest.fixture
def processing_context():
    """創建測試用的處理上下文"""
    from core.models import Response

    request = Request(
        query="Test query",
        mode=ProcessingMode.CHAT
    )
    response = Response(
        result="",
        mode=ProcessingMode.CHAT,
        trace_id=request.trace_id
    )
    return ProcessingContext(request, response)


@pytest.fixture
def mock_logger():
    """模擬日誌器"""
    with patch.object(structured_logger, 'info') as mock_info, \
         patch.object(structured_logger, 'debug') as mock_debug, \
         patch.object(structured_logger, 'error') as mock_error, \
         patch.object(structured_logger, 'progress') as mock_progress, \
         patch.object(structured_logger, 'message') as mock_message, \
         patch.object(structured_logger, 'reasoning') as mock_reasoning, \
         patch.object(structured_logger, 'log_llm_call') as mock_llm_call, \
         patch.object(structured_logger, 'log_tool_decision') as mock_tool_decision:

        yield {
            'info': mock_info,
            'debug': mock_debug,
            'error': mock_error,
            'progress': mock_progress,
            'message': mock_message,
            'reasoning': mock_reasoning,
            'log_llm_call': mock_llm_call,
            'log_tool_decision': mock_tool_decision
        }


# ========== ChatProcessor Tests ==========
class TestChatProcessor:
    """測試對話處理器"""

    @pytest.mark.asyncio
    async def test_chat_process_basic(self, mock_llm_client, processing_context, mock_logger):
        """測試基本對話處理"""
        processor = ChatProcessor(mock_llm_client)

        result = await processor.process(processing_context)

        # 驗證結果
        assert result == "Test LLM Response"

        # 驗證 LLM 被調用
        mock_llm_client.generate.assert_called_once()

        # 驗證日誌
        mock_logger['progress'].assert_any_call("chat", "start")
        mock_logger['progress'].assert_any_call("chat", "end")
        mock_logger['message'].assert_called_once_with("Test LLM Response")

    @pytest.mark.asyncio
    async def test_chat_without_llm(self, processing_context, mock_logger):
        """測試沒有 LLM 時應拋出錯誤"""
        processor = ChatProcessor(None)

        with pytest.raises(RuntimeError, match="LLM client not configured"):
            await processor.process(processing_context)

    @pytest.mark.asyncio
    async def test_chat_context_tracking(self, mock_llm_client, processing_context, mock_logger):
        """測試上下文追蹤"""
        processor = ChatProcessor(mock_llm_client)

        await processor.process(processing_context)

        # 驗證步驟被正確標記
        assert processing_context.current_step == "chat"


# ========== ThinkingProcessor Tests ==========
class TestThinkingProcessor:
    """測試深度思考處理器"""
    pass


# ========== KnowledgeProcessor Tests ==========
class TestKnowledgeProcessor:
    """測試知識檢索處理器"""

    @pytest.mark.asyncio
    async def test_knowledge_rag_flow(self, mock_llm_client, processing_context, mock_logger):
        """測試 RAG 檢索流程 — 無知識服務時走 LLM 直答 fallback"""
        processor = KnowledgeProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.KNOWLEDGE

        result = await processor.process(processing_context)

        # 驗證 RAG 流程步驟
        mock_logger['progress'].assert_any_call("knowledge-retrieval", "start")
        mock_logger['progress'].assert_any_call("embedding", "start")
        mock_logger['progress'].assert_any_call("embedding", "end")

        # 無知識服務時，LLM 直接回答
        assert result == "Test LLM Response"
        mock_llm_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_knowledge_tool_decision(self, mock_llm_client, processing_context, mock_logger):
        """測試 RAG 工具決策"""
        processor = KnowledgeProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.KNOWLEDGE

        await processor.process(processing_context)

        # 驗證 RAG 工具決策
        mock_logger['log_tool_decision'].assert_called_once()
        call_args = mock_logger['log_tool_decision'].call_args[0]
        assert call_args[0] == "rag_retrieval"
        assert call_args[1] == 0.9  # confidence

    @pytest.mark.asyncio
    async def test_knowledge_with_real_service(self, mock_llm_client, processing_context, mock_logger):
        """測試有知識服務時走完整 RAG 流程（含引用）"""
        # Create mock knowledge service
        mock_kb = AsyncMock()
        mock_kb.retrieve = AsyncMock(return_value=[
            {"content": "Machine learning is a subset of AI that learns from data."},
            {"content": "Supervised learning uses labeled training data."}
        ])
        services = {"knowledge": mock_kb}

        processor = KnowledgeProcessor(mock_llm_client, services=services)
        processing_context.request.mode = ProcessingMode.KNOWLEDGE
        processing_context.request.query = "What is machine learning?"

        result = await processor.process(processing_context)

        # 驗證知識服務被呼叫
        mock_kb.retrieve.assert_called_once_with("What is machine learning?", top_k=5)

        # 驗證 LLM 調用包含引用規則
        llm_call = mock_llm_client.generate.call_args[0][0]
        assert "Citation" in llm_call or "引用" in llm_call


# ========== SearchProcessor Tests ==========
class TestSearchProcessor:
    """測試網路搜索處理器"""

    @pytest.mark.asyncio
    async def test_search_serp_generation(self, mock_llm_client, processing_context, mock_logger):
        """測試 SERP 查詢生成"""
        processor = SearchProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.SEARCH

        # 模擬 SERP 生成
        mock_llm_client.generate.side_effect = [
            '```json\n[{"query": "test search", "researchGoal": "find info"}]\n```',
            "Search result 1",
            "Final compiled result"
        ]

        result = await processor.process(processing_context)

        # 驗證 SERP 查詢生成
        mock_logger['progress'].assert_any_call("query-generation", "start")
        mock_logger['progress'].assert_any_call("searching", "start")

    @pytest.mark.asyncio
    async def test_search_web_query_logging(self, mock_llm_client, processing_context, mock_logger):
        """測試網路查詢日誌"""
        processor = SearchProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.SEARCH
        processing_context.request.query = "Latest AI news"

        await processor.process(processing_context)

        # 驗證網路查詢日誌
        info_calls = mock_logger['info'].call_args_list
        web_query_calls = [call for call in info_calls
                          if "Web Query" in str(call[0][0])]
        assert len(web_query_calls) > 0

    @pytest.mark.asyncio
    async def test_search_multiple_queries(self, mock_llm_client, processing_context, mock_logger):
        """測試多個搜索查詢"""
        processor = SearchProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.SEARCH

        # 模擬多個查詢
        queries_json = '''```json
        [
            {"query": "query 1", "researchGoal": "goal 1"},
            {"query": "query 2", "researchGoal": "goal 2"},
            {"query": "query 3", "researchGoal": "goal 3"}
        ]
        ```'''

        mock_llm_client.generate.side_effect = [
            queries_json,
            "Result 1", "Result 2", "Result 3",
            "Final compiled result"
        ]

        result = await processor.process(processing_context)

        # 驗證生成了3個查詢
        assert mock_llm_client.generate.call_count >= 4  # 3 searches + 1 final


# ========== CodeProcessor Tests ==========
class TestCodeProcessor:
    """測試代碼執行處理器"""

    @pytest.mark.asyncio
    async def test_code_generation_without_sandbox(self, mock_llm_client, processing_context, mock_logger):
        """測試無沙箱時 — 代碼生成但不執行"""
        processor = CodeProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.CODE
        processing_context.request.query = "Write hello world"

        mock_llm_client.generate.return_value = "print('Hello World')"

        result = await processor.process(processing_context)

        # 驗證代碼執行步驟
        mock_logger['progress'].assert_any_call("code-execution", "start")
        mock_logger['progress'].assert_any_call("code-analysis", "start")
        mock_logger['progress'].assert_any_call("code-generation", "start")

        # 無沙箱時應提示無法執行
        assert "Sandbox unavailable" in result

    @pytest.mark.asyncio
    async def test_code_generation_with_sandbox(self, mock_llm_client, processing_context, mock_logger):
        """測試有沙箱時 — 真實執行代碼"""
        mock_sandbox = AsyncMock()
        mock_sandbox.execute = AsyncMock(return_value={
            "success": True,
            "stdout": "Hello World\n",
            "stderr": ""
        })
        services = {"sandbox": mock_sandbox}

        processor = CodeProcessor(mock_llm_client, services=services)
        processing_context.request.mode = ProcessingMode.CODE
        processing_context.request.query = "Write hello world"

        mock_llm_client.generate.return_value = "print('Hello World')"

        result = await processor.process(processing_context)

        # 驗證沙箱被呼叫
        mock_sandbox.execute.assert_called_once()
        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_code_sandbox_execution_status(self, mock_llm_client, processing_context, mock_logger):
        """測試沙箱執行狀態記錄"""
        processor = CodeProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.CODE

        result = await processor.process(processing_context)

        # 驗證執行結果包含狀態
        assert "代碼執行結果" in result

        # 無沙箱時 success 為 False
        execution_end_calls = [call for call in mock_logger['progress'].call_args_list
                               if len(call[0]) > 2 and call[0][0] == "code-execution"
                               and call[0][1] == "end"]
        if execution_end_calls:
            assert execution_end_calls[0][0][2]["success"] == False


# ========== DeepResearchProcessor Tests ==========
class TestDeepResearchProcessor:
    """測試深度研究處理器"""

    @pytest.mark.asyncio
    async def test_research_complete_pipeline(self, mock_llm_client, processing_context, mock_logger):
        """測試完整的研究流程"""
        processor = DeepResearchProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.DEEP_RESEARCH
        processing_context.request.query = "Explain quantum computing"

        # 模擬各個階段的響應
        mock_llm_client.generate.side_effect = [
            "Research plan for quantum computing",  # report plan
            '''```json
            [
                {"query": "quantum computing basics", "researchGoal": "understand fundamentals", "priority": 1},
                {"query": "quantum applications", "researchGoal": "explore use cases", "priority": 2}
            ]
            ```''',  # SERP queries
            "Search result 1", "Processed result 1",  # search task 1
            "Search result 2", "Processed result 2",  # search task 2
            "Final comprehensive report on quantum computing"  # final report
        ]

        result = await processor.process(processing_context)

        # 驗證所有階段
        mock_logger['progress'].assert_any_call("report-plan", "start")
        mock_logger['progress'].assert_any_call("serp-query", "start")
        mock_logger['progress'].assert_any_call("task-list", "start")
        mock_logger['progress'].assert_any_call("search-task", "start", {"name": "quantum computing basics"})
        mock_logger['progress'].assert_any_call("final-report", "start")

        # 驗證最終報告
        assert isinstance(result, str) and len(result) > 0

    @pytest.mark.asyncio
    async def test_research_tool_decision(self, mock_llm_client, processing_context, mock_logger):
        """測試深度研究工具決策"""
        processor = DeepResearchProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.DEEP_RESEARCH

        # 簡化響應以快速測試
        mock_llm_client.generate.side_effect = [
            "Plan",
            '```json\n[{"query": "test", "researchGoal": "test", "priority": 1}]\n```',
            "Result", "Processed",
            "Final"
        ]

        await processor.process(processing_context)

        # 驗證工具決策
        mock_logger['log_tool_decision'].assert_called()
        call_args = mock_logger['log_tool_decision'].call_args[0]
        assert call_args[0] == "deep_research"
        assert call_args[1] == 0.95  # high confidence

    @pytest.mark.asyncio
    async def test_research_memory_operations(self, mock_llm_client, processing_context, mock_logger):
        """測試記憶體操作日誌"""
        processor = DeepResearchProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.DEEP_RESEARCH

        mock_llm_client.generate.side_effect = [
            "Plan",
            '```json\n[{"query": "test", "researchGoal": "test", "priority": 1}]\n```',
            "Result", "Processed",
            "Final"
        ]

        await processor.process(processing_context)

        # 驗證記憶體操作
        info_calls = mock_logger['info'].call_args_list

        # 檢查記憶體存儲
        memory_store_calls = [call for call in info_calls
                             if "Memory: Storing" in str(call[0][0])]
        assert len(memory_store_calls) > 0

        # 檢查記憶體檢索
        memory_retrieve_calls = [call for call in info_calls
                                if "Memory: Retrieved" in str(call[0][0])]
        assert len(memory_retrieve_calls) > 0

    @pytest.mark.asyncio
    async def test_research_error_handling(self, mock_llm_client, processing_context, mock_logger):
        """測試錯誤處理"""
        processor = DeepResearchProcessor(mock_llm_client)
        processing_context.request.mode = ProcessingMode.DEEP_RESEARCH

        # 模擬 SERP 解析錯誤
        mock_llm_client.generate.side_effect = [
            "Plan",
            "Invalid JSON",  # 這將導致解析失敗
            "Fallback result",
            "Final"
        ]

        result = await processor.process(processing_context)

        # 應該使用 fallback 並繼續
        assert result is not None
        assert len(result) > 0


# ========== ProcessorFactory Tests ==========
class TestProcessorFactory:
    """測試處理器工廠"""

    def test_factory_creates_all_processors(self, mock_llm_client):
        """測試工廠能創建所有處理器"""
        factory = ProcessorFactory(mock_llm_client)

        # 測試所有模式
        modes = [
            ProcessingMode.CHAT,
            ProcessingMode.THINKING,
            ProcessingMode.KNOWLEDGE,
            ProcessingMode.SEARCH,
            ProcessingMode.CODE,
            ProcessingMode.DEEP_RESEARCH
        ]

        for mode in modes:
            processor = factory.get_processor(mode)
            assert processor is not None
            assert processor.llm_client == mock_llm_client

    def test_factory_caches_instances(self, mock_llm_client):
        """測試工廠緩存處理器實例"""
        factory = ProcessorFactory(mock_llm_client)

        # 獲取兩次相同的處理器
        processor1 = factory.get_processor(ProcessingMode.CHAT)
        processor2 = factory.get_processor(ProcessingMode.CHAT)

        # 應該是同一個實例
        assert processor1 is processor2

    def test_factory_register_custom_processor(self, mock_llm_client):
        """測試註冊自定義處理器"""
        factory = ProcessorFactory(mock_llm_client)

        # 創建自定義處理器
        class CustomProcessor(ChatProcessor):
            pass

        # 註冊
        factory.register_processor(ProcessingMode.CHAT, CustomProcessor)

        # 獲取應該是新類型
        processor = factory.get_processor(ProcessingMode.CHAT)
        assert isinstance(processor, CustomProcessor)

    def test_cognitive_level_system1(self, mock_llm_client):
        """Test System 1 processors get correct cognitive level."""
        factory = ProcessorFactory(mock_llm_client)
        for mode in [ProcessingMode.CHAT, ProcessingMode.KNOWLEDGE]:
            processor = factory.get_processor(mode)
            assert processor._cognitive_level == "system1", f"{mode.value} should be system1"

    def test_cognitive_level_system2(self, mock_llm_client):
        """Test System 2 processors get correct cognitive level."""
        factory = ProcessorFactory(mock_llm_client)
        for mode in [ProcessingMode.SEARCH, ProcessingMode.CODE, ProcessingMode.THINKING]:
            processor = factory.get_processor(mode)
            assert processor._cognitive_level == "system2", f"{mode.value} should be system2"

    def test_cognitive_level_agent(self, mock_llm_client):
        """Test Agent-level processors get correct cognitive level."""
        factory = ProcessorFactory(mock_llm_client)
        processor = factory.get_processor(ProcessingMode.DEEP_RESEARCH)
        assert processor._cognitive_level == "agent"

    def test_cognitive_mapping_completeness(self, mock_llm_client):
        """Every processor must have a cognitive level assigned."""
        factory = ProcessorFactory(mock_llm_client)
        for mode in factory._processors:
            processor = factory.get_processor(mode)
            assert hasattr(processor, '_cognitive_level'), \
                f"Processor for {mode.value} missing _cognitive_level"
            assert processor._cognitive_level in ["system1", "system2", "agent"], \
                f"Invalid cognitive level for {mode.value}: {processor._cognitive_level}"


# ========== Integration Tests ==========
class TestProcessorIntegration:
    """整合測試 - 測試處理器之間的協作"""

    @pytest.mark.asyncio
    async def test_mode_switching(self, mock_llm_client, mock_logger):
        """測試模式切換"""
        factory = ProcessorFactory(mock_llm_client)

        # 測試不同模式的請求
        modes_and_queries = [
            (ProcessingMode.CHAT, "Hello"),
            (ProcessingMode.THINKING, "What is 2+2?"),
            (ProcessingMode.KNOWLEDGE, "What is AI?"),
            (ProcessingMode.SEARCH, "Latest news"),
            (ProcessingMode.CODE, "Print hello"),
            (ProcessingMode.DEEP_RESEARCH, "Climate change")
        ]

        for mode, query in modes_and_queries:
            from core.models import Response

            request = Request(query=query, mode=mode)
            response = Response(
                result="",
                mode=ProcessingMode.CHAT,
                trace_id=request.trace_id
            )
            context = ProcessingContext(request, response)
            processor = factory.get_processor(mode)

            # 簡化 LLM 響應
            if mode == ProcessingMode.DEEP_RESEARCH:
                mock_llm_client.generate.side_effect = [
                    "Plan",
                    '```json\n[{"query": "test", "researchGoal": "test", "priority": 1}]\n```',
                    "Result", "Processed",
                    "Final"
                ]
            else:
                mock_llm_client.generate.return_value = f"Response for {query}"

            result = await processor.process(context)

            assert result is not None
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_context_preservation(self, mock_llm_client):
        """測試上下文保持"""
        processor = ChatProcessor(mock_llm_client)

        # 創建多個請求使用相同的 trace_id
        trace_id = "test-trace-123"

        for i in range(3):
            from core.models import Response

            request = Request(
                query=f"Query {i}",
                mode=ProcessingMode.CHAT,
                trace_id=trace_id
            )
            response = Response(
                result="",
                mode=ProcessingMode.CHAT,
                trace_id=request.trace_id
            )
            context = ProcessingContext(request, response)

            result = await processor.process(context)

            # 驗證 trace_id 被保留
            assert context.request.trace_id == trace_id


# ========== Performance Tests ==========
class TestProcessorPerformance:
    """性能測試"""

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, mock_llm_client, mock_logger):
        """測試並發處理"""
        factory = ProcessorFactory(mock_llm_client)

        # 創建多個並發任務
        from core.models import Response

        tasks = []
        for i in range(10):
            mode = ProcessingMode.CHAT
            request = Request(query=f"Concurrent query {i}", mode=mode)
            response = Response(
                result="",
                mode=ProcessingMode.CHAT,
                trace_id=request.trace_id
            )
            context = ProcessingContext(request, response)
            processor = factory.get_processor(mode)
            tasks.append(processor.process(context))

        # 並發執行
        results = await asyncio.gather(*tasks)

        # 驗證所有任務完成
        assert len(results) == 10
        for result in results:
            assert result is not None

    pass


if __name__ == "__main__":
    # 運行所有測試
    pytest.main([__file__, "-v", "--tb=short"])