"""
重構版引擎 - 簡化的核心處理引擎
統一處理流程，整合日誌系統
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from .models_v2 import Request, Response, ProcessingContext, Modes, EventType, RuntimeType, Event
from .processors.factory import ProcessorFactory
from .logger import structured_logger
from .feature_flags import feature_flags
from .router import DefaultRouter
from .runtime import ModelRuntime, AgentRuntime
from .metrics import CognitiveMetrics
from .service_initializer import ServiceInitializer
from .context import ContextManager, TodoRecitation, ErrorPreservation, TemplateRandomizer, FileBasedMemory


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
        self._mcp_client = None
        self._a2a_client = None
        self._package_manager = None
        self.initialized = False

        # Context Engineering (Manus-aligned, feature-flag controlled)
        self._ce_enabled = self.feature_flags.is_enabled("context_engineering.enabled")
        if self._ce_enabled and self.feature_flags.is_enabled("context_engineering.append_only_context"):
            self.context_manager = ContextManager(self.feature_flags)
        else:
            self.context_manager = None

        if self._ce_enabled and self.feature_flags.is_enabled("context_engineering.todo_recitation"):
            self._todo_recitation = TodoRecitation(self.feature_flags)
        else:
            self._todo_recitation = None

        self._error_preservation = (
            self._ce_enabled
            and self.feature_flags.is_enabled("context_engineering.error_preservation")
        )

        if self._ce_enabled and self.feature_flags.is_enabled("context_engineering.template_randomizer"):
            self._template_randomizer = TemplateRandomizer(self.feature_flags)
        else:
            self._template_randomizer = None

        if self._ce_enabled and self.feature_flags.is_enabled("context_engineering.file_based_memory"):
            workspace = self.feature_flags.get_value(
                "context_engineering.file_memory_workspace", ".agent_workspace"
            )
            self._file_memory = FileBasedMemory(workspace_dir=workspace, feature_flags=self.feature_flags)
        else:
            self._file_memory = None

    async def initialize(self):
        """初始化引擎 — 建立外部服務（graceful degradation）

        This method uses ServiceInitializer to handle all external service setup.
        The initialization is designed with graceful degradation - each service
        failure is logged but doesn't prevent other services from starting.

        Initialization Steps:
        ---------------------
        1. Initialize core services (search, knowledge, sandbox)
        2. Initialize MCP client (external tool servers)
        3. Initialize A2A client (agent-to-agent collaboration)
        4. Initialize PackageManager (dynamic package loading)
        5. Rebuild processor factory and runtimes with available services
        """
        if self.initialized:
            return

        self.logger.info("Initializing RefactoredEngine")

        # Use ServiceInitializer for all external service setup
        initializer = ServiceInitializer(self.logger)

        # Initialize core services (search, knowledge, sandbox)
        services = await initializer.initialize_all()

        # Initialize MCP client (external tool servers)
        self._mcp_client = await initializer.initialize_mcp_client()

        # Initialize A2A client (external agent collaboration)
        self._a2a_client = await initializer.initialize_a2a_client()

        # Initialize PackageManager (dynamic package registration)
        packages_dir = Path(__file__).parent.parent.parent / "packages"
        self._package_manager = await initializer.initialize_package_manager(
            packages_dir, self._mcp_client, self._a2a_client
        )

        # Rebuild processor factory and runtimes with services
        self.processor_factory = ProcessorFactory(
            self.llm_client, services=services, mcp_client=self._mcp_client
        )
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
            mode=str(request.mode)
        )

        # 創建處理上下文
        response = Response(
            result="",
            mode=request.mode,
            trace_id=request.trace_id
        )
        context = ProcessingContext(request=request, response=response)

        # Context Engineering: reset and append user query
        if self.context_manager:
            self.context_manager.reset()
            self.context_manager.append_user(request.query)
        if self._todo_recitation:
            self._todo_recitation.reset()
            self._todo_recitation.create_initial_plan(request.query, str(request.mode))

        try:
            # 記錄開始
            self.logger.info(
                f"Processing request: {request.query[:50]}...",
                request_mode=str(request.mode)
            )

            # SSE: 連接建立
            self.logger.emit_sse(Event(
                type=EventType.INFO,
                data={"name": "opencode", "version": "2.0"},
                trace_id=request.trace_id
            ))

            # Route the request
            decision = await self.router.route(request)
            request.mode = decision.mode
            response.mode = decision.mode

            self.logger.log_tool_decision(
                tool=str(decision.mode),
                confidence=decision.confidence,
                reason=decision.reason,
            )

            # Execute via runtime dispatch or legacy path
            with self.logger.measure(f"process_{request.mode}"):
                result = await self._execute(decision, context)

            # Context Engineering: append assistant result
            if self.context_manager:
                self.context_manager.append_assistant(result)
            if self._todo_recitation:
                self._todo_recitation.update_from_output(result)

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
                "mode": str(request.mode)
            })

            # SSE: 錯誤事件
            self.logger.emit_sse(Event(
                type=EventType.ERROR,
                data={"message": str(e)},
                trace_id=request.trace_id
            ))

            # 返回錯誤響應
            response.result = f"處理失敗: {str(e)}"
            response.add_event(EventType.ERROR, str(e))
            return response

        finally:
            # 清理上下文
            self.logger.clear_context()

    async def _execute(self, decision, context: ProcessingContext) -> str:
        """Dispatch to the appropriate runtime, A2A agent, or legacy path.

        Priority:
        1. A2A delegation (if decision.delegate_to_agent is set)
        2. Runtime dispatch (if smart_routing feature flag is on)
        3. Legacy path (direct ProcessorFactory)
        """
        # A2A delegation path
        if decision.delegate_to_agent and self._a2a_client:
            try:
                self.logger.info(
                    f"Delegating to A2A agent: {decision.delegate_to_agent}",
                    agent=decision.delegate_to_agent,
                )
                result = await self._a2a_client.send_task(
                    decision.delegate_to_agent, context.request.query
                )
                if result.get("text"):
                    return result["text"]
                return str(result.get("artifacts", "No response from agent"))
            except Exception as e:
                self.logger.warning(
                    f"A2A delegation failed, falling back to local processing: {e}",
                    agent=decision.delegate_to_agent,
                )
                # Fall through to local processing

        use_runtime = self.feature_flags.is_enabled("routing.smart_routing")

        if not use_runtime:
            # Legacy path - direct ProcessorFactory (backward compatible)
            processor = self.processor_factory.get_processor(context.request.mode)
            result = await processor.process(context)
        elif decision.runtime_type == RuntimeType.AGENT:
            result = await self._agent_runtime.execute(context)
        else:
            result = await self._model_runtime.execute(context)

        # Context Engineering: error preservation with retry
        if (
            self._error_preservation
            and ErrorPreservation.should_retry(result, current_retry=0)
        ):
            # Append the failed result (never hide it)
            if self.context_manager:
                self.context_manager.append_error(result, context.request.query)

            retry_prompt = ErrorPreservation.build_retry_prompt(
                original_query=context.request.query,
                failed_result=result,
            )
            retry_request = Request(query=retry_prompt, mode=context.request.mode)
            retry_context = ProcessingContext(request=retry_request, response=context.response)

            if not use_runtime:
                result = await processor.process(retry_context)
            elif decision.runtime_type == RuntimeType.AGENT:
                result = await self._agent_runtime.execute(retry_context)
            else:
                result = await self._model_runtime.execute(retry_context)

        return result

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

    def register_processor(self, mode, processor_class):
        """
        註冊自定義處理器

        Args:
            mode: 處理模式 (ProcessingMode instance)
            processor_class: 處理器類
        """
        self.processor_factory.register_processor(mode, processor_class)
        self.logger.info(f"Registered processor for mode: {mode}")


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
        mode: 處理模式 (e.g., "auto", "chat", "search")

    Returns:
        str: 處理結果
    """
    engine = create_engine()
    await engine.initialize()

    request = Request(
        query=query,
        mode=Modes.from_name(mode)
    )

    response = await engine.process(request)
    return response.result