"""
統一架構設計 - 整合原有架構與深度思考模式
Unified Architecture - Merging Legacy and Deep Thinking Mode
"""

from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass
import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """統一處理模式"""
    QUICK = "quick"           # 快速處理（原 MCP 直接執行）
    THINKING = "thinking"     # 思考模式（深度推理）
    RESEARCH = "research"     # 研究模式（多源探索）
    HYBRID = "hybrid"         # 混合模式（思考+執行）


class UnifiedEngine:
    """
    統一引擎 - 整合兩套架構的核心

    整合策略：
    1. 保留原有 MCP 服務作為執行層
    2. 新增深度思考作為智能層
    3. 智能路由決定使用哪種處理方式
    """

    def __init__(self):
        # 原有架構組件
        self.mcp_router = None  # 原 RouterActor
        self.orchestrator = None  # 原 OrchestratorActor
        self.executor_pool = None  # 原 ExecutorActor Pool

        # 新架構組件
        self.thinking_engine = None  # DeepThinkingEngine
        self.intelligent_router = None  # IntelligentRouter
        self.thinking_chain = None  # ThinkingChain

        # 服務層（共用）
        self.llm_service = None
        self.knowledge_base = None
        self.sandbox_service = None

        # 統一狀態管理
        self.context_store = {}
        self.memory_store = {}

    async def initialize(self):
        """初始化統一引擎"""
        # 初始化原有架構組件
        await self._init_legacy_components()

        # 初始化新架構組件
        await self._init_thinking_components()

        # 初始化服務層
        await self._init_services()

        logger.info("Unified Engine initialized successfully")

    async def _init_legacy_components(self):
        """初始化原有架構組件"""
        from opencode.orchestrator.actors.router import RouterActor
        from opencode.orchestrator.actors.orchestrator import OrchestratorActor
        from opencode.orchestrator.actors.executor import ExecutorActor

        self.mcp_router = RouterActor(name="mcp_router")
        self.orchestrator = OrchestratorActor(name="orchestrator")
        self.executor_pool = [
            ExecutorActor(name=f"executor_{i}")
            for i in range(5)
        ]

    async def _init_thinking_components(self):
        """初始化思考架構組件"""
        from core.thinking.engine import DeepThinkingEngine
        from core.thinking.chain import ThinkingChain
        from core.router import IntelligentRouter

        self.thinking_engine = DeepThinkingEngine()
        self.thinking_chain = ThinkingChain()
        self.intelligent_router = IntelligentRouter()

    async def _init_services(self):
        """初始化服務層"""
        from opencode.services.knowledge_base.service import KnowledgeBaseService
        from opencode.services.sandbox.service import SandboxService

        self.knowledge_base = KnowledgeBaseService()
        self.sandbox_service = SandboxService()

    async def process(
        self,
        request: Dict[str, Any],
        mode: Optional[ProcessingMode] = None
    ) -> Dict[str, Any]:
        """
        統一處理入口

        處理流程：
        1. 分析請求複雜度
        2. 選擇處理模式
        3. 執行相應流程
        4. 返回統一格式結果
        """
        # 自動選擇模式
        if mode is None:
            mode = await self._select_mode(request)

        logger.info(f"Processing request with mode: {mode.value}")

        if mode == ProcessingMode.QUICK:
            # 使用原有 MCP 架構快速處理
            return await self._quick_process(request)

        elif mode == ProcessingMode.THINKING:
            # 使用深度思考處理
            return await self._thinking_process(request)

        elif mode == ProcessingMode.RESEARCH:
            # 研究模式：思考+多源探索
            return await self._research_process(request)

        else:  # HYBRID
            # 混合模式：先思考後執行
            return await self._hybrid_process(request)

    async def _select_mode(self, request: Dict[str, Any]) -> ProcessingMode:
        """智能選擇處理模式"""
        # 分析請求類型
        query = request.get("query", "")
        intent = request.get("intent", {})

        # 簡單任務判斷
        simple_patterns = [
            "execute", "run", "list", "show", "get"
        ]
        if any(p in query.lower() for p in simple_patterns):
            return ProcessingMode.QUICK

        # 複雜推理判斷
        thinking_patterns = [
            "why", "how", "explain", "analyze", "design"
        ]
        if any(p in query.lower() for p in thinking_patterns):
            return ProcessingMode.THINKING

        # 研究任務判斷
        research_patterns = [
            "research", "investigate", "compare", "evaluate"
        ]
        if any(p in query.lower() for p in research_patterns):
            return ProcessingMode.RESEARCH

        # 默認混合模式
        return ProcessingMode.HYBRID

    async def _quick_process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """快速處理模式 - 使用原有 MCP 架構"""
        # 路由到對應服務
        service = await self.mcp_router.route(request)

        # 執行
        executor = self.executor_pool[0]  # 簡單負載均衡
        result = await executor.execute(service, request)

        return {
            "mode": "quick",
            "result": result,
            "thinking_trace": None
        }

    async def _thinking_process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """深度思考處理模式"""
        # 執行深度思考
        thinking_result = await self.thinking_engine.think_deeply(
            query=request.get("query"),
            context=request.get("context", {}),
            depth=5  # 中等深度
        )

        return {
            "mode": "thinking",
            "result": thinking_result.answer,
            "thinking_trace": thinking_result.thinking_trace,
            "confidence": thinking_result.confidence
        }

    async def _research_process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """研究模式處理"""
        # Step 1: 思考和規劃
        plan = await self.thinking_chain.generate_chain(
            problem=request.get("query"),
            context=request.get("context", {})
        )

        # Step 2: 並發探索
        exploration_tasks = []
        for step in plan:
            if step.type == "exploration":
                task = self._explore_source(step.details)
                exploration_tasks.append(task)

        results = await asyncio.gather(*exploration_tasks)

        # Step 3: 綜合分析
        synthesis = await self.thinking_engine.synthesize(
            plan=plan,
            explorations=results
        )

        return {
            "mode": "research",
            "result": synthesis.conclusion,
            "thinking_trace": plan,
            "explorations": results,
            "confidence": synthesis.confidence
        }

    async def _hybrid_process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """混合模式 - 思考+執行"""
        # Step 1: 思考和規劃
        thinking_result = await self.thinking_engine.think_deeply(
            query=request.get("query"),
            context=request.get("context", {}),
            depth=3  # 淺層思考
        )

        # Step 2: 基於思考結果執行
        execution_plan = thinking_result.execution_plan
        execution_results = []

        for action in execution_plan:
            # 路由到對應服務
            service = await self.mcp_router.route(action)
            executor = self.executor_pool[0]
            result = await executor.execute(service, action)
            execution_results.append(result)

        # Step 3: 整合結果
        final_result = await self._merge_results(
            thinking=thinking_result,
            executions=execution_results
        )

        return {
            "mode": "hybrid",
            "result": final_result,
            "thinking_trace": thinking_result.thinking_trace,
            "execution_trace": execution_results,
            "confidence": thinking_result.confidence
        }

    async def _explore_source(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """探索單個來源"""
        source_type = details.get("source_type")

        if source_type == "knowledge_base":
            return await self.knowledge_base.search(details.get("query"))
        elif source_type == "web":
            # 可以接入 web search service
            return {"source": "web", "results": []}
        else:
            return {"source": "unknown", "results": []}

    async def _merge_results(
        self,
        thinking: Any,
        executions: List[Any]
    ) -> Dict[str, Any]:
        """整合思考和執行結果"""
        return {
            "thought": thinking.answer,
            "actions": executions,
            "summary": f"Based on analysis: {thinking.answer}, executed {len(executions)} actions successfully."
        }


class UnifiedAPI:
    """統一 API 接口"""

    def __init__(self):
        self.engine = UnifiedEngine()

    async def initialize(self):
        """初始化 API"""
        await self.engine.initialize()

    async def process_request(
        self,
        query: str,
        mode: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """處理 API 請求"""
        request = {
            "query": query,
            "context": context or {},
            "metadata": {
                "timestamp": asyncio.get_event_loop().time(),
                "request_id": self._generate_request_id()
            }
        }

        # 轉換模式
        processing_mode = None
        if mode:
            processing_mode = ProcessingMode(mode)

        # 執行處理
        result = await self.engine.process(request, processing_mode)

        # 格式化響應
        return self._format_response(result)

    def _generate_request_id(self) -> str:
        """生成請求 ID"""
        import uuid
        return str(uuid.uuid4())

    def _format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化統一響應"""
        return {
            "status": "success",
            "mode": result.get("mode"),
            "data": {
                "answer": result.get("result"),
                "thinking_trace": result.get("thinking_trace"),
                "confidence": result.get("confidence", 1.0),
                "metadata": result.get("metadata", {})
            }
        }


# 使用範例
async def main():
    """使用範例"""
    # 創建統一 API
    api = UnifiedAPI()
    await api.initialize()

    # 範例 1: 快速執行
    result1 = await api.process_request(
        query="list all files in current directory",
        mode="quick"
    )
    print(f"Quick result: {result1}")

    # 範例 2: 深度思考
    result2 = await api.process_request(
        query="How to design a high-performance distributed system?",
        mode="thinking"
    )
    print(f"Thinking result: {result2}")

    # 範例 3: 自動選擇
    result3 = await api.process_request(
        query="Analyze the code structure and suggest improvements"
    )
    print(f"Auto mode result: {result3}")


if __name__ == "__main__":
    asyncio.run(main())