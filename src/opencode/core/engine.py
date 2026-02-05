"""
OpenCode Core Engine - 核心引擎
統一管理 Context、Event、Plugin、Orchestrator
"""

from typing import Dict, Any, Optional, AsyncIterator, List
import asyncio
import logging
import time
import uuid

from opencode.core.protocols import (
    EngineProtocol, Context, Intent, Event, EventType,
    PluginProtocol
)
from opencode.core.context import ContextManager, LocalContextManager
from opencode.core.events import EventBus, create_event

logger = logging.getLogger(__name__)


class EngineState:
    """引擎狀態"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class OpenCodeEngine(EngineProtocol):
    """
    OpenCode 核心引擎
    
    職責:
    - 初始化和管理所有核心元件
    - 處理用戶意圖
    - 協調 Orchestrator 執行
    - 管理插件生命週期
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.state = EngineState.INITIALIZING
        
        # 核心元件
        self.context_manager: Optional[ContextManager] = None
        self.event_bus: Optional[EventBus] = None
        self.orchestrator = None  # 延遲載入避免循環引用
        
        # 插件
        self.plugins: Dict[str, PluginProtocol] = {}
        
        # MCP Gateway
        self.mcp_gateway = None  # 延遲載入
        
        # 控制
        self._shutdown_event = asyncio.Event()
        self._processing_count = 0
    
    async def initialize(self) -> None:
        """初始化引擎"""
        try:
            logger.info("🚀 Initializing OpenCode Engine...")
            
            # 初始化 Context Manager
            redis_url = self.config.get("redis_url", "redis://localhost:6379")
            use_redis = self.config.get("use_redis", True)
            
            if use_redis:
                self.context_manager = ContextManager(redis_url=redis_url)
            else:
                self.context_manager = LocalContextManager()
            
            await self.context_manager.initialize()
            
            # 初始化 Event Bus
            self.event_bus = EventBus()
            await self.event_bus.initialize()
            
            # 初始化 Orchestrator
            await self._init_orchestrator()
            
            # 初始化 MCP Gateway
            await self._init_mcp_gateway()
            
            # 載入插件
            await self._load_plugins()
            
            # 註冊事件處理
            self._register_handlers()
            
            self.state = EngineState.READY
            logger.info("✅ OpenCode Engine ready")
            
            # 發送啟動事件
            await self.event_bus.publish(create_event(
                EventType.STARTUP,
                content="Engine started",
                source="engine"
            ))
            
        except Exception as e:
            self.state = EngineState.ERROR
            logger.error(f"❌ Engine initialization failed: {e}", exc_info=True)
            raise
    
    async def _init_orchestrator(self) -> None:
        """初始化 Orchestrator"""
        try:
            from opencode.orchestrator.actors.orchestrator import OrchestratorActor
            
            self.orchestrator = OrchestratorActor(
                config=self.config.get("orchestrator", {})
            )
            await self.orchestrator.start()
            logger.info("✅ Orchestrator initialized")
        except ImportError:
            logger.warning("Orchestrator not available, using direct execution")
            self.orchestrator = None
    
    async def _init_mcp_gateway(self) -> None:
        """初始化 MCP Gateway"""
        try:
            from opencode.gateway.mcp_gateway import MCPGateway
            
            self.mcp_gateway = MCPGateway(
                config=self.config.get("gateway", {})
            )
            await self.mcp_gateway.initialize()
            logger.info("✅ MCP Gateway initialized")
        except ImportError:
            logger.warning("MCP Gateway not available")
            self.mcp_gateway = None
    
    async def _load_plugins(self) -> None:
        """載入插件"""
        plugin_configs = self.config.get("plugins", [])
        
        for plugin_config in plugin_configs:
            try:
                plugin_id = plugin_config.get("id")
                module_path = plugin_config.get("module")
                
                if not plugin_id or not module_path:
                    continue
                
                # 動態載入插件
                plugin_class = self._import_plugin(module_path)
                plugin = plugin_class()
                
                await plugin.initialize(plugin_config.get("config", {}))
                self.plugins[plugin_id] = plugin
                
                # 註冊到 Event Bus
                self.event_bus.register(plugin.handle_event)
                
                logger.info(f"✅ Plugin loaded: {plugin_id}")
                
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_config}: {e}")
    
    def _import_plugin(self, module_path: str) -> type:
        """動態載入插件類"""
        module_name, class_name = module_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    
    def _register_handlers(self) -> None:
        """註冊事件處理器"""
        # 註冊內部處理器
        self.event_bus.register_handler(
            EventType.INTENT.value,
            self._handle_intent_event
        )
        
        self.event_bus.register_handler(
            EventType.ERROR.value,
            self._handle_error_event
        )
    
    async def _handle_intent_event(self, event: Event) -> AsyncIterator[Event]:
        """處理意圖事件"""
        intent_data = event.payload
        
        # 如果有 Orchestrator，透過它處理
        if self.orchestrator:
            async for response in self.orchestrator.process_intent(intent_data):
                yield response
        else:
            # 直接處理 (簡化路徑)
            yield create_event(
                EventType.ANSWER,
                content="Orchestrator not available",
                source="engine",
                correlation_id=event.correlation_id
            )
    
    async def _handle_error_event(self, event: Event) -> None:
        """處理錯誤事件"""
        error_msg = event.payload.get("message", "Unknown error")
        logger.error(f"Error event: {error_msg}")
    
    async def process_intent(
        self, 
        intent: Intent
    ) -> AsyncIterator[Event]:
        """
        處理用戶意圖
        
        Args:
            intent: 用戶意圖
            
        Yields:
            處理過程中產生的事件
        """
        self._processing_count += 1
        self.state = EngineState.PROCESSING
        correlation_id = intent.id
        
        try:
            # 確保有 Context
            if intent.context is None:
                context = await self.context_manager.get_or_create(
                    session_id="default",
                    user_id="default"
                )
                intent.context = context
            
            # 更新對話歷史
            await self.context_manager.update_conversation(
                intent.context.session_id,
                {"role": "user", "content": intent.content}
            )
            
            # 建立意圖事件
            intent_event = Event(
                type=EventType.INTENT,
                payload={
                    "id": intent.id,
                    "type": intent.type,
                    "content": intent.content,
                    "parameters": intent.parameters,
                    "context": intent.context.to_dict() if intent.context else {},
                    "timestamp": intent.timestamp
                },
                timestamp=time.time(),
                source="engine",
                correlation_id=correlation_id
            )
            
            # 發送到 Event Bus 並收集回應
            response_content = ""
            async for response in self.event_bus.emit(intent_event):
                yield response
                
                # 收集回答內容
                if response.type == EventType.ANSWER:
                    response_content = response.payload.get("content", "")
            
            # 更新對話歷史 (助手回應)
            if response_content:
                await self.context_manager.update_conversation(
                    intent.context.session_id,
                    {"role": "assistant", "content": response_content}
                )
            
        except Exception as e:
            logger.error(f"Intent processing error: {e}", exc_info=True)
            yield create_event(
                EventType.ERROR,
                content=str(e),
                source="engine",
                correlation_id=correlation_id
            )
        finally:
            self._processing_count -= 1
            if self._processing_count == 0:
                self.state = EngineState.READY
    
    async def execute_tool(
        self,
        service_id: str,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        直接執行工具 (透過 MCP Gateway)
        
        Args:
            service_id: 服務 ID
            method: 方法名稱
            params: 參數
            
        Returns:
            執行結果
        """
        if self.mcp_gateway is None:
            raise RuntimeError("MCP Gateway not initialized")
        
        return await self.mcp_gateway.call(service_id, method, params)
    
    async def get_available_services(self) -> List[Dict[str, Any]]:
        """取得可用服務列表"""
        if self.mcp_gateway:
            return await self.mcp_gateway.discover_services()
        return []
    
    async def shutdown(self) -> None:
        """關閉引擎"""
        logger.info("Shutting down OpenCode Engine...")
        self.state = EngineState.SHUTDOWN
        
        # 發送關閉事件
        if self.event_bus:
            await self.event_bus.publish(create_event(
                EventType.SHUTDOWN,
                content="Engine shutting down",
                source="engine"
            ))
        
        # 停止 Orchestrator
        if self.orchestrator:
            await self.orchestrator.stop()
        
        # 關閉 MCP Gateway
        if self.mcp_gateway:
            await self.mcp_gateway.shutdown()
        
        # 關閉插件
        for plugin_id, plugin in self.plugins.items():
            try:
                await plugin.shutdown()
                logger.info(f"Plugin shutdown: {plugin_id}")
            except Exception as e:
                logger.error(f"Plugin shutdown error: {e}")
        
        # 關閉 Context Manager
        if hasattr(self.context_manager, 'close'):
            await self.context_manager.close()
        
        self._shutdown_event.set()
        logger.info("✅ OpenCode Engine shutdown complete")
    
    async def wait_for_shutdown(self) -> None:
        """等待引擎關閉"""
        await self._shutdown_event.wait()
    
    @property
    def is_ready(self) -> bool:
        """引擎是否就緒"""
        return self.state == EngineState.READY
    
    @property
    def is_processing(self) -> bool:
        """是否正在處理"""
        return self._processing_count > 0


# ============== 便利函數 ==============

_default_engine: Optional[OpenCodeEngine] = None


async def get_engine() -> OpenCodeEngine:
    """取得預設引擎實例"""
    global _default_engine
    
    if _default_engine is None:
        _default_engine = OpenCodeEngine()
        await _default_engine.initialize()
    
    return _default_engine


async def shutdown_engine() -> None:
    """關閉預設引擎"""
    global _default_engine
    
    if _default_engine:
        await _default_engine.shutdown()
        _default_engine = None
