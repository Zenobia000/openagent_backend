"""
重構版引擎 - 簡化的核心處理引擎
統一處理流程，整合日誌系統
"""

import asyncio
from typing import Optional, Dict, Any

from .models import Request, Response, ProcessingContext, ProcessingMode, EventType
from .processor import ProcessorFactory
from .logger import structured_logger


class RefactoredEngine:
    """
    重構版引擎 - 極簡設計
    職責：
    1. 請求路由
    2. 處理器調度
    3. 統一日誌
    4. 錯誤處理
    """

    def __init__(self, llm_client=None, config: Dict[str, Any] = None):
        """
        初始化引擎

        Args:
            llm_client: LLM 客戶端（可選）
            config: 配置字典（可選）
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.processor_factory = ProcessorFactory(llm_client)
        self.logger = structured_logger
        self.initialized = False

    async def initialize(self):
        """初始化引擎"""
        if self.initialized:
            return

        self.logger.info("Initializing RefactoredEngine")

        # 初始化各個組件
        # 這裡可以加載服務、連接數據庫等

        self.initialized = True
        self.logger.info("RefactoredEngine initialized successfully")

    async def process(self, request: Request) -> Response:
        """
        處理請求 - 核心方法

        Args:
            request: 統一請求對象

        Returns:
            Response: 統一響應對象
        """
        # 確保已初始化
        if not self.initialized:
            await self.initialize()

        # 設置日誌上下文
        self.logger.set_trace(request.trace_id)
        self.logger.set_context(
            context_id=request.context_id,
            mode=request.mode.value
        )

        # 創建處理上下文
        response = Response(
            result="",
            mode=request.mode,
            trace_id=request.trace_id
        )
        context = ProcessingContext(request=request, response=response)

        try:
            # 記錄開始
            self.logger.info(
                f"Processing request: {request.query[:50]}...",
                request_mode=request.mode.value
            )

            # SSE: 連接建立
            from .models import SSEEvent
            self.logger.emit_sse(SSEEvent(
                signal=EventType.INFO.value,
                data={"name": "opencode", "version": "2.0"}
            ))

            # 自動選擇模式
            if request.mode == ProcessingMode.AUTO:
                request.mode = await self._select_mode(request.query)
                self.logger.log_tool_decision(
                    tool=request.mode.value,
                    confidence=0.85,
                    reason="Auto-selected based on query analysis"
                )

            # 獲取處理器
            processor = self.processor_factory.get_processor(request.mode)

            # 執行處理
            with self.logger.measure(f"process_{request.mode.value}"):
                result = await processor.process(context)

            # 更新響應
            response.result = result
            response.time_ms = context.get_elapsed_time()

            # 記錄完成
            self.logger.info(
                "Request processed successfully",
                time_ms=response.time_ms,
                tokens_used=response.tokens_used
            )

            # SSE: 最終結果
            response.add_event(EventType.RESULT, result)

            return response

        except Exception as e:
            # 錯誤處理
            self.logger.log_error(e, {
                "query": request.query,
                "mode": request.mode.value
            })

            # SSE: 錯誤事件
            from .models import SSEEvent
            self.logger.emit_sse(SSEEvent(
                signal=EventType.ERROR.value,
                data={"message": str(e)}
            ))

            # 返回錯誤響應
            response.result = f"處理失敗: {str(e)}"
            response.add_event(EventType.ERROR, str(e))
            return response

        finally:
            # 清理上下文
            self.logger.clear_context()

    async def _select_mode(self, query: str) -> ProcessingMode:
        """
        自動選擇處理模式

        Args:
            query: 用戶查詢

        Returns:
            ProcessingMode: 選擇的處理模式
        """
        query_lower = query.lower()

        # 簡單的規則匹配
        if any(word in query_lower for word in ['代碼', 'code', '程式', 'function']):
            return ProcessingMode.CODE
        elif any(word in query_lower for word in ['搜尋', 'search', '查詢', 'find']):
            return ProcessingMode.SEARCH
        elif any(word in query_lower for word in ['知識', 'knowledge', '解釋', 'explain']):
            return ProcessingMode.KNOWLEDGE
        elif any(word in query_lower for word in ['深度', 'deep', '分析', 'analyze', '思考']):
            return ProcessingMode.THINKING
        else:
            return ProcessingMode.CHAT

    async def process_stream(self, request: Request):
        """
        流式處理 - 支持 SSE

        Args:
            request: 請求對象

        Yields:
            SSE 事件
        """
        # 設置流式標記
        request.stream = True

        # 設置 SSE 回調
        events = []

        def sse_callback(signal, data):
            events.append({"event": signal, "data": data})

        self.logger.set_sse_callback(sse_callback)

        # 處理請求
        response = await self.process(request)

        # 返回所有事件
        for event in events:
            yield event

        # 最終響應
        yield {
            "event": "result",
            "data": {"response": response.result}
        }

    def register_processor(self, mode: ProcessingMode, processor_class):
        """
        註冊自定義處理器

        Args:
            mode: 處理模式
            processor_class: 處理器類
        """
        self.processor_factory.register_processor(mode, processor_class)
        self.logger.info(f"Registered processor for mode: {mode.value}")


# ========================================
# 便捷函數
# ========================================

def create_engine(llm_client=None, **config) -> RefactoredEngine:
    """
    創建引擎實例

    Args:
        llm_client: LLM 客戶端
        **config: 配置參數

    Returns:
        RefactoredEngine: 引擎實例
    """
    return RefactoredEngine(llm_client=llm_client, config=config)


async def quick_process(query: str, mode: str = "auto") -> str:
    """
    快速處理 - 用於簡單場景

    Args:
        query: 查詢字符串
        mode: 處理模式

    Returns:
        str: 處理結果
    """
    engine = create_engine()
    await engine.initialize()

    request = Request(
        query=query,
        mode=ProcessingMode(mode)
    )

    response = await engine.process(request)
    return response.result