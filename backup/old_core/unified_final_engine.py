"""
OpenCode Platform - 最終統一引擎
融合 Deep Thinking 架構與 Service 架構
Final Unified Engine combining both architectures
"""

import asyncio
import os
import sys
import json  # Added for parsing LLM responses
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# 添加 utils 到路徑


# 添加 utils 到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging_config import get_logger, LogContext, LogLevel

# 導入 OpenAI LLM Client
from services.llm.openai_client import OpenAILLMClient

# 獲取專用 logger
logger = get_logger("FinalUnifiedEngine", LogLevel.INFO)


# ========================================
# 統一模式定義 - 融合兩種架構
# ========================================


class ProcessingMode(Enum):
    """統一處理模式 - 融合 Thinking 和 Service 模式"""

    # Service 模式（執行導向）
    CHAT = "chat"  # AI 對話功能
    KNOWLEDGE = "knowledge"  # 知識庫檢索
    SANDBOX = "sandbox"  # 代碼執行
    PLUGIN = "plugin"  # 插件執行

    QUICK = "quick"  # 快速響應 (1-2步)
    THINKING = "thinking"  # 深度思考 (5-10步)
    RESEARCH = "research"  # 研究模式 (10+步)

    # 混合模式
    HYBRID = "hybrid"  # 思考 + 執行
    AUTO = "auto"  # 自動選擇


class ThinkingDepth:
    """思考深度配置 - 來自 unified_python_architecture.md"""

    SHALLOW = 1  # 淺層：1-2步
    MEDIUM = 3  # 中層：3-5步
    DEEP = 5  # 深層：5-10步
    RESEARCH = 10  # 研究：10+步


# ========================================
# 數據模型
# ========================================


@dataclass
class UnifiedRequest:
    """統一請求格式 - 支援所有模式"""

    query: str
    mode: Optional[ProcessingMode] = None

    # Service 參數
    context_id: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4000

    # Thinking 參數
    thinking_depth: Optional[int] = None
    enable_reflection: bool = True

    # 共用參數
    metadata: Optional[Dict[str, Any]] = None
    plugins: Optional[List[str]] = None


@dataclass
class UnifiedResponse:
    """統一響應格式"""

    result: Any
    mode: ProcessingMode

    # Thinking 相關
    thinking_trace: Optional[List[str]] = None
    confidence: float = 1.0

    # Service 相關
    usage: Optional[Dict[str, int]] = None
    context_id: Optional[str] = None

    # 元數據
    metadata: Optional[Dict[str, Any]] = None


# ========================================
# 思考引擎組件 (Deep Thinking)
# ========================================


class ThinkingEngine:
    """深度思考引擎 - 基於 unified_python_architecture.md"""

    def __init__(self, llm_client = None):
        self.thinking_chain = None
        self.reflection_module = None
        self.critique_module = None
        # Use provided llm_client, even if it's None (for mock mode)
        self.llm_client = llm_client

    async def think_deeply(
        self, query: str, depth: int = ThinkingDepth.MEDIUM, enable_reflection: bool = True
    ) -> Dict[str, Any]:
        """執行深度思考過程"""
        logger.info(
            f"🧠 Starting deep thinking: query='{query[:50]}...', depth={depth}, reflection={enable_reflection}"
        )

        thinking_trace = []

        # Phase 1: 問題理解與分解
        with LogContext(logger, "Problem Understanding", query=query[:100]):
            thinking_trace.append(f"📋 分析問題: {query}")
            understanding = await self._understand_problem(query)
            logger.debug(f"Understanding result: {understanding}")
            thinking_trace.append(understanding)

        # Phase 2: 多步推理（思考鏈）
        for step in range(depth):
            logger.debug(f"Thinking step {step+1}/{depth}")
            thinking_trace.append(f"🔍 思考步驟 {step+1}/{depth}")

            # 生成思考
            thought = await self._generate_thought(query, step)
            logger.debug(f"Generated thought at step {step+1}: {thought[:100]}")

            # 自我反思（如果啟用）
            if enable_reflection and step % 2 == 0:
                logger.debug(f"Applying self-reflection at step {step+1}")
                thinking_trace.append("💭 自我反思...")
                thought = await self._reflect_on_thought(thought)

        # Phase 3: 綜合與總結
        with LogContext(logger, "Conclusion Synthesis", steps=len(thinking_trace)):
            thinking_trace.append("📝 綜合結論...")
            conclusion = await self._synthesize_conclusion(thinking_trace)
            confidence = 0.85 + (depth * 0.02)  # 深度越深，信心越高

            logger.info(
                f"✅ Thinking completed: confidence={confidence:.2f}, trace_length={len(thinking_trace)}"
            )

            return {
                "answer": conclusion,
                "thinking_trace": thinking_trace,
                "confidence": confidence,
            }

    async def _understand_problem(self, query: str) -> str:
        """理解問題 - 透過 LLM 進行"""
        if self.llm_client is None:
            # Mock implementation
            if "你好" in query or "hello" in query.lower():
                return "Greeting: User is saying hello"
            elif "?" in query or "什麼" in query or "what" in query.lower():
                return "Question: User asking a question"
            else:
                return "Query: User making a request"

        prompt = f"Analyze the following user query to understand its intent and categorize it:\n'{query}'\n\nProvide a concise understanding (e.g., 'Greeting: User is saying hello', 'Question: User asking for definition')."
        return await self.llm_client.generate(prompt)

    async def _generate_thought(self, query: str, step: int) -> str:
        """生成思考步驟 - 透過 LLM 進行"""
        if self.llm_client is None:
            # Mock implementation with varied thoughts
            thoughts = [
                f"步驟 {step + 1}: 分析查詢內容",
                f"步驟 {step + 1}: 理解用戶意圖",
                f"步驟 {step + 1}: 搜集相關資訊",
                f"步驟 {step + 1}: 整理思路",
                f"步驟 {step + 1}: 準備回應"
            ]
            return thoughts[min(step, len(thoughts) - 1)]

        prompt = f"Given the query: '{query}', and that this is thinking step {step + 1}, generate a concise thought or next step in the analysis process."
        return await self.llm_client.generate(prompt)

    async def _reflect_on_thought(self, thought: str) -> str:
        """反思思考 - 透過 LLM 進行"""
        if self.llm_client is None:
            # Mock implementation
            return f"反思: {thought} - 確認邏輯正確"

        prompt = f"Critically reflect on the following thought to improve its quality or identify potential flaws:\n'{thought}'"
        return await self.llm_client.generate(prompt)

    async def _synthesize_conclusion(self, thinking_trace: List[str]) -> str:
        """綜合結論 - 透過 LLM 進行"""
        # Extract original query from the thinking trace
        original_query = ""
        for item in thinking_trace:
            if "分析問題:" in item or "analyzing" in item.lower():
                parts = item.split(":")
                if len(parts) > 1:
                    original_query = ":".join(parts[1:]).strip()
                    break

        prompt = f"Given the thinking trace:\n{chr(10).join(thinking_trace)}\n\nAnd the original query: '{original_query}'\n\nSynthesize a comprehensive and accurate conclusion or final answer. If the original query was a greeting, respond with a friendly greeting. If it was a status inquiry, provide a status report. If it was about features, describe them. Otherwise, provide a detailed expert response or deep analysis if relevant."

        if self.llm_client is None:
            # Mock implementation based on query type
            if "你好" in original_query or "hello" in original_query.lower():
                return "你好! 歡迎使用 OpenCode Platform。系統正在模擬模式下運行。"
            elif "狀態" in original_query or "status" in original_query.lower():
                return "系統狀態: 運行中 (模擬模式)。所有核心組件已載入。"
            elif "功能" in original_query or "feature" in original_query.lower():
                return "系統功能: 思考引擎、服務管理器、智能路由器 (模擬模式)。"
            elif "深度分析" in original_query:
                return f"深度分析結果 (模擬): 關於 '{original_query}' 的分析已完成。這是一個複雜的主題需要多層次的理解。"
            else:
                return f"處理查詢 '{original_query}' (模擬模式): 系統已分析您的請求並準備了回應。"

        return await self.llm_client.generate(prompt)


# ========================================
# 服務管理器 (Service Layer)
# ========================================


class ServiceManager:
    """服務管理器 - 管理所有服務"""

    def __init__(self):
        self.services = {}
        self.llm_providers = {}
        self.plugins = {}

    async def initialize(self):
        """初始化所有服務"""
        logger.info("🔧 Initializing Service Manager...")

        # 初始化服務
        await self._init_knowledge_service()
        await self._init_sandbox_service()
        await self._init_search_service()
        await self._init_llm_providers()

    async def _init_knowledge_service(self):
        """初始化知識庫服務"""
        try:
            logger.debug("Attempting to initialize knowledge service...")
            from services.knowledge.service import KnowledgeBaseService

            self.services["knowledge"] = KnowledgeBaseService()
            logger.info("✓ Knowledge service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Knowledge service not available: {e}")

    async def _init_sandbox_service(self):
        """初始化沙箱服務"""
        try:
            from services.sandbox.service import SandboxService

            self.services["sandbox"] = SandboxService()
            logger.info("✓ Sandbox service initialized")
        except Exception as e:
            logger.warning(f"Sandbox service not available: {e}")

    async def _init_search_service(self):
        """初始化搜索服務"""
        try:
            from services.search.service import WebSearchService

            self.services["search"] = WebSearchService()
            logger.info("✓ Search service initialized")
        except Exception as e:
            logger.warning(f"Search service not available: {e}")

    async def _init_llm_providers(self):
        """初始化 LLM 提供者"""
        # 簡化的 LLM 提供者
        self.llm_providers["default"] = {
            "model": "gpt-4o",
            "api_key": os.getenv("OPENAI_API_KEY", ""),
        }

    async def execute_service(self, service_name: str, params: Dict[str, Any]) -> Any:
        """執行服務"""
        logger.debug(f"🚀 Executing service: {service_name}")

        if service_name in self.services:
            with LogContext(
                logger, f"Service Execution: {service_name}", params_keys=list(params.keys())
            ):
                service = self.services[service_name]
                # 調用服務的執行方法
                result = await service.execute(params)
                logger.debug(f"Service {service_name} completed successfully")
                return result
        else:
            logger.warning(f"⚠️ Service not found: {service_name}")
            return None


# ========================================
# 智能路由器
# ========================================


class IntelligentRouter:
    """智能路由器 - 分析複雜度並選擇處理模式"""

    def __init__(self, llm_client = None):
        # Use provided llm_client, even if it's None (for mock mode)
        self.llm_client = llm_client

    async def analyze_complexity(self, query: str) -> Dict[str, float]:
        """分析查詢複雜度 - 透過 LLM 進行"""
        # If no LLM client, use heuristic-based complexity analysis
        if self.llm_client is None:
            query_lower = query.lower()
            # Simple heuristic complexity analysis
            complexity = {
                "reasoning_required": 0.3,
                "multi_step": 0.2,
                "domain_knowledge": 0.2,
                "creativity": 0.1,
                "research_needed": 0.1,
            }

            # Increase complexity for certain keywords
            if any(word in query_lower for word in ['深度分析', 'deep', '詳細', 'detailed']):
                complexity["reasoning_required"] = 0.8
                complexity["multi_step"] = 0.7
            if any(word in query_lower for word in ['研究', 'research', '調查']):
                complexity["research_needed"] = 0.8

            return complexity

        prompt = f"""Analyze the complexity of the following query across several dimensions:
Query: '{query}'

Provide your analysis as a JSON object with the following keys and float values between 0.0 and 1.0 (where 1.0 is highest complexity):
{{
    "reasoning_required": float,  // How much logical inference is needed?
    "multi_step": float,          // Does it require multiple distinct steps or sub-tasks?
    "domain_knowledge": float,    // How much specialized knowledge is required?
    "creativity": float,          // Does it require novel or creative solutions?
    "research_needed": float      // Does it require external information retrieval?
}}
Example: {{"reasoning_required": 0.8, "multi_step": 0.7, "domain_knowledge": 0.5, "creativity": 0.3, "research_needed": 0.9}}
"""
        # For now, the mock client will return a dummy string, parse it later
        llm_response = await self.llm_client.generate(prompt)
        # In a real scenario, you'd parse the JSON from the LLM response
        try:
            # Attempt to parse as JSON. If it fails, return a default complexity.
            # The MockLLMClient currently returns a string, so this will likely fail
            # unless the MockLLMClient is updated to return valid JSON strings for this prompt.
            complexity = json.loads(llm_response)
            if not isinstance(complexity, dict) or not all(
                isinstance(v, (int, float)) for v in complexity.values()
            ):
                raise ValueError("LLM did not return a valid complexity dictionary.")
            return complexity
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                f"LLM did not return parsable JSON for complexity analysis. Returning default scores. Response: {llm_response[:100]}..."
            )
            return {
                "reasoning_required": 0.5,
                "multi_step": 0.5,
                "domain_knowledge": 0.5,
                "creativity": 0.5,
                "research_needed": 0.5,
            }

    async def select_mode(
        self, query: str, hint: Optional[ProcessingMode] = None
    ) -> ProcessingMode:
        """選擇最佳處理模式 - 透過 LLM 進行"""
        logger.debug(f"🤔 Selecting processing mode for query: '{query[:50]}...'")

        # 如果有明確指定，使用指定模式
        if hint and hint != ProcessingMode.AUTO:
            logger.info(f"🎯 Using specified mode: {hint.value}")
            return hint

        # Use LLM to select the mode
        mode_options = ", ".join([f"'{mode.value}'" for mode in ProcessingMode])
        # If no LLM client available, use simple heuristics
        if self.llm_client is None:
            logger.debug("🎭 Using mock mode selection (no LLM client)")
            # Simple heuristic-based mode selection
            query_lower = query.lower()
            if any(word in query_lower for word in ['深度分析', 'deep analysis', '詳細', 'detailed']):
                return ProcessingMode.THINKING
            elif any(word in query_lower for word in ['研究', 'research', '調查']):
                return ProcessingMode.RESEARCH
            elif any(word in query_lower for word in ['知識', 'knowledge', '查詢', 'search']):
                return ProcessingMode.KNOWLEDGE
            else:
                return ProcessingMode.QUICK

        prompt = f"""Given the user query: '{query}', recommend the most appropriate ProcessingMode from the following options: {mode_options}.
Consider the inherent complexity of the query.

Provide only the recommended ProcessingMode value (e.g., 'thinking', 'chat', 'research')."""

        llm_recommendation = await self.llm_client.generate(prompt)
        llm_recommendation = llm_recommendation.strip().lower()  # Clean up the response

        # Try to match LLM's recommendation to a valid ProcessingMode
        for mode in ProcessingMode:
            if mode.value == llm_recommendation:
                logger.info(f"🤖 LLM-selected mode: {mode.value}")
                return mode

        # Fallback to a default mode if LLM's recommendation is invalid or unexpected
        logger.warning(
            f"LLM returned an invalid mode: '{llm_recommendation}'. Falling back to CHAT mode."
        )
        return ProcessingMode.CHAT

    def get_thinking_depth(self, mode: ProcessingMode) -> int:
        """根據模式獲取思考深度"""
        depth_mapping = {
            ProcessingMode.QUICK: ThinkingDepth.SHALLOW,
            ProcessingMode.CHAT: ThinkingDepth.SHALLOW,
            ProcessingMode.THINKING: ThinkingDepth.DEEP,
            ProcessingMode.RESEARCH: ThinkingDepth.RESEARCH,
            ProcessingMode.HYBRID: ThinkingDepth.MEDIUM,
        }
        return depth_mapping.get(mode, ThinkingDepth.SHALLOW)


# ========================================
# 最終統一引擎
# ========================================


class FinalUnifiedEngine:
    """
    最終統一引擎 - 融合 Deep Thinking 與 Service Architecture

    核心理念：
    1. 智能路由決定處理模式
    2. 思考引擎提供深度推理
    3. 服務層執行具體功能
    4. 統一接口對外提供服務
    """

    def __init__(self):
        self.initialized = False

        # 核心組件 - Try to create LLM client, use mock if no API key
        try:
            self.llm_client = OpenAILLMClient()
            logger.info("✅ OpenAI LLM Client initialized successfully")
        except ValueError as e:
            logger.warning(f"⚠️ 無法初始化 OpenAI client: {e}. 使用 Mock LLM Client")
            self.llm_client = None  # Will use mock responses

        self.router = IntelligentRouter(llm_client=self.llm_client)
        self.thinking_engine = ThinkingEngine(
            llm_client=self.llm_client
        )  # Pass it to ThinkingEngine
        self.service_manager = ServiceManager()

        # 狀態管理
        self.contexts = {}
        self.memory = {}

    async def initialize(self):
        """初始化引擎"""
        logger.info("=" * 50)
        logger.info("🚀 Initializing Final Unified Engine")
        logger.info("=" * 50)

        try:
            # 初始化服務管理器
            await self.service_manager.initialize()

            # 初始化思考引擎
            # self.thinking_engine 已在 __init__ 中創建

            self.initialized = True
            logger.info("✅ Final Unified Engine initialized successfully")
            logger.debug(f"Services loaded: {list(self.service_manager.services.keys())}")
            logger.debug(f"LLM providers: {list(self.service_manager.llm_providers.keys())}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize engine: {e}", exc_info=True)
            raise

    async def process(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        統一處理入口 - 智能路由到不同處理器
        """
        logger.info(f"📥 Received request: mode={request.mode}, query='{request.query[:50]}...'")

        if not self.initialized:
            logger.debug("Engine not initialized, initializing now...")
            await self.initialize()

        # 智能選擇處理模式
        if request.mode is None or request.mode == ProcessingMode.AUTO:
            request.mode = await self.router.select_mode(request.query)

        logger.info(f"🌐 Processing with mode: {request.mode.value}")

        # 根據模式類型路由
        if request.mode in [ProcessingMode.QUICK, ProcessingMode.THINKING, ProcessingMode.RESEARCH]:
            # 思考導向模式
            return await self._process_thinking_mode(request)

        elif request.mode in [
            ProcessingMode.CHAT,
            ProcessingMode.KNOWLEDGE,
            ProcessingMode.SANDBOX,
            ProcessingMode.PLUGIN,
        ]:
            # 服務導向模式
            return await self._process_service_mode(request)

        elif request.mode == ProcessingMode.HYBRID:
            # 混合模式
            return await self._process_hybrid_mode(request)

        else:
            # 默認 CHAT 模式
            request.mode = ProcessingMode.CHAT
            return await self._process_service_mode(request)

    async def _process_thinking_mode(self, request: UnifiedRequest) -> UnifiedResponse:
        """處理思考導向模式"""
        with LogContext(logger, "Thinking Mode Processing", mode=request.mode.value):
            # 獲取思考深度
            depth = request.thinking_depth or self.router.get_thinking_depth(request.mode)
            logger.debug(f"Using thinking depth: {depth}")

        # 執行深度思考
        result = await self.thinking_engine.think_deeply(
            query=request.query, depth=depth, enable_reflection=request.enable_reflection
        )

        response = UnifiedResponse(
            result=result["answer"],
            mode=request.mode,
            thinking_trace=result.get("thinking_trace"),
            confidence=result.get("confidence", 0.8),
            metadata={"depth": depth},
        )

        logger.info(f"✅ Thinking mode completed: confidence={response.confidence:.2f}")
        return response

    async def _process_service_mode(self, request: UnifiedRequest) -> UnifiedResponse:
        """處理服務導向模式"""
        with LogContext(logger, "Service Mode Processing", mode=request.mode.value):
            service_mapping = {
                ProcessingMode.KNOWLEDGE: "knowledge",
                ProcessingMode.SANDBOX: "sandbox",
                ProcessingMode.PLUGIN: "plugin",
                ProcessingMode.CHAT: "chat",
            }

        service_name = service_mapping.get(request.mode, "chat")

        # 準備服務參數
        params = {
            "query": request.query,
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        # 執行服務
        if service_name in self.service_manager.services:
            result = await self.service_manager.execute_service(service_name, params)
        else:
            # 當服務不可用時，使用 LLM client 處理所有模式
            if self.llm_client is not None:
                logger.info(f"📡 Service '{service_name}' not available, using LLM fallback")

                # 根據不同模式構建適當的提示詞
                if service_name == "knowledge":
                    prompt = f"請詳細解釋這個問題，提供準確和有用的知識：{request.query}"
                elif service_name == "sandbox":
                    prompt = f"請分析並回答這個技術問題：{request.query}"
                elif service_name == "plugin":
                    prompt = f"請處理這個請求：{request.query}"
                else:  # chat 或其他
                    prompt = request.query

                result = await self.llm_client.generate(prompt)
            else:
                # 完全沒有 LLM 時的回退
                result = f"Service '{service_name}' is not available and no LLM configured."

        response = UnifiedResponse(
            result=result,
            mode=request.mode,
            context_id=request.context_id,
            usage={"tokens": 0},
            metadata={"service": service_name},
        )

        logger.info(f"✅ Service mode completed: service={service_name}")
        return response

    async def _process_hybrid_mode(self, request: UnifiedRequest) -> UnifiedResponse:
        """處理混合模式 - 先思考後執行"""

        # Step 1: 思考階段
        thinking_result = await self.thinking_engine.think_deeply(
            query=request.query, depth=ThinkingDepth.MEDIUM, enable_reflection=True
        )

        # Step 2: 基於思考結果選擇服務
        # 這裡簡化處理，實際應該根據思考結果動態選擇
        service_params = {"query": request.query, "thinking_context": thinking_result}

        # Step 3: 執行服務
        service_result = await self.service_manager.execute_service("chat", service_params)

        # Step 4: 整合結果
        return UnifiedResponse(
            result={
                "thought": thinking_result["answer"],
                "action": service_result,
                "summary": "Completed hybrid processing",
            },
            mode=ProcessingMode.HYBRID,
            thinking_trace=thinking_result.get("thinking_trace"),
            confidence=thinking_result.get("confidence", 0.8),
            metadata={"hybrid": True},
        )

    async def get_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        return {
            "initialized": self.initialized,
            "services": list(self.service_manager.services.keys()),
            "thinking_engine": "active" if self.thinking_engine else "inactive",
            "router": "active" if self.router else "inactive",
            "contexts": len(self.contexts),
            "supported_modes": [mode.value for mode in ProcessingMode],
        }


# ========================================
# 簡化的 Engine 接口（保持兼容）
# ========================================


class Engine:
    """簡化的 Engine 類，保持向後兼容"""

    def __init__(self):
        self.unified_engine = FinalUnifiedEngine()

    async def initialize(self):
        """初始化引擎"""
        await self.unified_engine.initialize()

    async def process(self, query: str) -> str:
        """處理查詢 - 簡化接口"""
        request = UnifiedRequest(query=query, mode=ProcessingMode.AUTO)
        response = await self.unified_engine.process(request)

        # 返回字符串結果
        if isinstance(response.result, str):
            return response.result
        elif isinstance(response.result, dict):
            # Prioritize 'answer', then 'summary', then a generic string representation of the dict
            return str(
                response.result.get("answer", response.result.get("summary", response.result))
            )
        return str(response.result)


# ========================================
# 導出
# ========================================

__all__ = [
    "FinalUnifiedEngine",
    "Engine",
    "UnifiedRequest",
    "UnifiedResponse",
    "ProcessingMode",
    "ThinkingDepth",
    "IntelligentRouter",
    "ThinkingEngine",
    "ServiceManager",
]
