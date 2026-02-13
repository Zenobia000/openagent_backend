"""
重構版引擎 - 簡化的核心處理引擎
統一處理流程，整合日誌系統
"""

import asyncio
from typing import Optional, Dict, Any

from .models import Request, Response, ProcessingContext, ProcessingMode, EventType, RuntimeType
from .processor import ProcessorFactory
from .logger import structured_logger
from .feature_flags import feature_flags
from .router import DefaultRouter
from .runtime import ModelRuntime, AgentRuntime
from .metrics import CognitiveMetrics


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
        self.feature_flags = feature_flags
        self.router = DefaultRouter(feature_flags)
        self._model_runtime = ModelRuntime(llm_client, self.processor_factory)
        self._agent_runtime = AgentRuntime(llm_client, self.processor_factory)
        self._metrics = CognitiveMetrics()
        self.initialized = False

    async def initialize(self):
        """初始化引擎 — 建立外部服務（graceful degradation）"""
        if self.initialized:
            return

        self.logger.info("Initializing RefactoredEngine")

        # Initialize external services (each in own try/except for graceful degradation)
        services = {}

        try:
            from services.search.service import get_web_search_service
            services["search"] = get_web_search_service()
            self.logger.info("Search service initialized")
        except Exception as e:
            self.logger.warning(f"Search service unavailable: {e}")

        try:
            from services.knowledge.service import KnowledgeBaseService
            kb = KnowledgeBaseService()
            await kb.initialize()
            services["knowledge"] = kb
            self.logger.info("Knowledge service initialized")
        except Exception as e:
            self.logger.warning(f"Knowledge service unavailable: {e}")

        try:
            from services.sandbox.service import SandboxService
            sandbox = SandboxService()
            await sandbox.initialize()
            services["sandbox"] = sandbox
            self.logger.info("Sandbox service initialized")
        except Exception as e:
            self.logger.warning(f"Sandbox service unavailable: {e}")

        # Rebuild processor factory and runtimes with services
        self.processor_factory = ProcessorFactory(self.llm_client, services=services)
        self._model_runtime = ModelRuntime(self.llm_client, self.processor_factory)
        self._agent_runtime = AgentRuntime(self.llm_client, self.processor_factory)

        self.initialized = True
        self.logger.info(f"AI Engine initialized (services: {list(services.keys()) or 'none'})")

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

            # Route the request
            decision = await self.router.route(request)
            request.mode = decision.mode
            response.mode = decision.mode

            self.logger.log_tool_decision(
                tool=decision.mode.value,
                confidence=decision.confidence,
                reason=decision.reason,
            )

            # Execute via runtime dispatch or legacy path
            with self.logger.measure(f"process_{request.mode.value}"):
                result = await self._execute(decision, context)

            # 更新響應
            response.result = result
            response.time_ms = context.get_elapsed_time()
            response.tokens_used = context.total_tokens  # 從上下文獲取 token 統計

            # 記錄完成
            self.logger.info(
                "Request processed successfully",
                time_ms=response.time_ms,
                tokens_used=response.tokens_used
            )

            # SSE: 最終結果
            response.add_event(EventType.RESULT, result)

            # Record cognitive metrics (when enabled)
            if self.feature_flags.is_enabled("metrics.cognitive_metrics"):
                self._metrics.record_request(
                    cognitive_level=request.mode.cognitive_level,
                    latency_ms=response.time_ms,
                    tokens=response.tokens_used,
                    success=True,
                )

            return response

        except Exception as e:
            # Record failure metric
            if self.feature_flags.is_enabled("metrics.cognitive_metrics"):
                self._metrics.record_request(
                    cognitive_level=request.mode.cognitive_level,
                    latency_ms=context.get_elapsed_time(),
                    success=False,
                )

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

    async def _execute(self, decision, context: ProcessingContext) -> str:
        """Dispatch to the appropriate runtime or legacy path.

        When feature flag is off: uses ProcessorFactory directly (legacy).
        When feature flag is on: dispatches to ModelRuntime or AgentRuntime.
        """
        use_runtime = self.feature_flags.is_enabled("routing.smart_routing")

        if not use_runtime:
            # Legacy path - direct ProcessorFactory (backward compatible)
            processor = self.processor_factory.get_processor(context.request.mode)
            return await processor.process(context)

        # Runtime dispatch path
        if decision.runtime_type == RuntimeType.AGENT_RUNTIME:
            return await self._agent_runtime.execute(context)
        return await self._model_runtime.execute(context)

    async def process_stream(self, request: Request):
        """Async generator that yields SSE events during processing.

        Uses an asyncio.Queue to bridge the callback-based logger SSE
        system into a true async generator.
        """
        import json
        request.stream = True

        event_queue: asyncio.Queue = asyncio.Queue()
        done = asyncio.Event()

        def sse_callback(signal, data):
            event_queue.put_nowait({"event": signal, "data": data})

        self.logger.set_sse_callback(sse_callback)

        async def _run():
            try:
                resp = await self.process(request)
                event_queue.put_nowait({
                    "event": EventType.RESULT.value,
                    "data": {"response": resp.result, "trace_id": resp.trace_id},
                })
            except Exception as e:
                event_queue.put_nowait({
                    "event": EventType.ERROR.value,
                    "data": {"message": str(e)},
                })
            finally:
                done.set()

        task = asyncio.create_task(_run())

        try:
            while not done.is_set() or not event_queue.empty():
                try:
                    evt = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield evt
                except asyncio.TimeoutError:
                    continue
        finally:
            if not task.done():
                task.cancel()

    @property
    def metrics(self):
        """Return cognitive metrics summary."""
        return self._metrics.get_summary()

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