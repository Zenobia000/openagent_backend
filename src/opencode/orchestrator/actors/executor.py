"""
Executor Actor - 任務執行器
透過 MCP Gateway 執行任務
"""

from typing import Dict, Any, Optional
import asyncio
import logging
import time

from opencode.orchestrator.actors.base import Actor, ActorMessage

logger = logging.getLogger(__name__)


class ExecutorActor(Actor):
    """
    執行 Actor
    
    職責:
    - 執行任務
    - 超時控制
    - 重試機制
    - 結果收集
    """
    
    def __init__(self, name: str = "executor", config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, config=config)
        
        # 配置
        self.default_timeout = config.get("timeout", 30) if config else 30
        self.max_retries = config.get("max_retries", 2) if config else 2
        
        # MCP Gateway 引用 (延遲設置)
        self.mcp_gateway = None
        
        # 本地服務實例 (fallback)
        self._local_services: Dict[str, Any] = {}
    
    async def on_start(self) -> None:
        """初始化"""
        # 嘗試取得 MCP Gateway
        try:
            from opencode.gateway.mcp_gateway import get_gateway
            self.mcp_gateway = await get_gateway()
        except Exception as e:
            logger.warning(f"MCP Gateway not available: {e}")
        
        # 初始化本地服務作為 fallback
        await self._init_local_services()
    
    async def _init_local_services(self) -> None:
        """初始化本地服務"""
        try:
            from opencode.services.knowledge_base.service import KnowledgeBaseService
            kb_service = KnowledgeBaseService()
            await kb_service.initialize()
            self._local_services["knowledge_base"] = kb_service
            logger.info("Local KnowledgeBase service initialized")
        except Exception as e:
            logger.warning(f"Failed to init local KnowledgeBase: {e}")
        
        try:
            from opencode.services.sandbox.service import SandboxService
            sandbox_service = SandboxService()
            await sandbox_service.initialize()
            self._local_services["sandbox"] = sandbox_service
            logger.info("Local Sandbox service initialized")
        except Exception as e:
            logger.warning(f"Failed to init local Sandbox: {e}")
        
        try:
            from opencode.services.web_search.service import get_web_search_service
            web_search_service = get_web_search_service()
            await web_search_service.initialize()
            self._local_services["web_search"] = web_search_service
            logger.info("Local WebSearch service initialized")
        except Exception as e:
            logger.warning(f"Failed to init local WebSearch: {e}")
        
        try:
            from opencode.services.repo_ops.service import RepoOpsService
            repo_ops_service = RepoOpsService()
            await repo_ops_service.initialize()
            self._local_services["repo_ops"] = repo_ops_service
            logger.info("Local RepoOps service initialized")
        except Exception as e:
            logger.warning(f"Failed to init local RepoOps: {e}")
    
    async def handle_message(self, message: ActorMessage) -> Optional[Any]:
        """處理訊息"""
        content = message.content
        msg_type = content.get("type")
        
        if msg_type == "execute_task":
            task = content.get("task", {})
            context = content.get("context", {})
            
            result = await self.execute(task, context)
            
            # 回傳結果給 parent
            if self.parent:
                await self.tell(self.parent, {
                    "type": "task_result",
                    "task_id": task.get("id"),
                    "result": result
                }, message.correlation_id)
            
            return result
        
        return None
    
    async def execute(
        self, 
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        執行任務
        
        Args:
            task: 任務定義
            context: 執行上下文
            
        Returns:
            執行結果
        """
        tool = task.get("tool", "")
        service_id = task.get("service", self._get_service_for_tool(tool))
        parameters = task.get("parameters", {})
        timeout = task.get("timeout", self.default_timeout)
        
        logger.info(f"🔧 ====== 執行任務 ======")
        logger.info(f"🔧 任務 ID: {task.get('id')}")
        logger.info(f"🔧 工具: {tool}")
        logger.info(f"🔧 服務: {service_id}")
        logger.info(f"🔧 參數: {parameters}")
        
        # 重試邏輯
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔧 嘗試執行 (attempt {attempt + 1}/{self.max_retries + 1})...")
                result = await asyncio.wait_for(
                    self._execute_on_service(service_id, tool, parameters),
                    timeout=timeout
                )
                
                # 記錄結果摘要
                if isinstance(result, dict):
                    result_keys = list(result.keys())
                    results_count = len(result.get('results', []))
                    sources_count = len(result.get('sources', []))
                    logger.info(f"✅ 任務完成! keys={result_keys}, results={results_count}, sources={sources_count}")
                    if result.get('error'):
                        logger.warning(f"⚠️ 結果包含錯誤: {result.get('error')}")
                else:
                    logger.info(f"✅ 任務完成! result_type={type(result)}")
                
                return result
                
            except asyncio.TimeoutError:
                last_error = f"Task timeout after {timeout}s"
                logger.warning(f"⏱️ 任務超時 (attempt {attempt + 1})")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ 任務錯誤: {e} (attempt {attempt + 1})")
                import traceback
                logger.error(traceback.format_exc())
            
            # 重試前等待
            if attempt < self.max_retries:
                await asyncio.sleep(1 * (attempt + 1))
        
        # 所有重試都失敗
        logger.error(f"❌ 任務失敗: {last_error}")
        return {"error": last_error, "success": False}
    
    async def _execute_on_service(
        self,
        service_id: str,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """在服務上執行方法"""
        
        # 優先使用 MCP Gateway
        if self.mcp_gateway:
            try:
                return await self.mcp_gateway.call(service_id, method, params)
            except Exception as e:
                logger.warning(f"MCP call failed: {e}, falling back to local")
        
        # Fallback 到本地服務
        service = self._local_services.get(service_id)
        if service:
            return await service.execute(method, params)
        
        raise RuntimeError(f"Service {service_id} not available")
    
    def _get_service_for_tool(self, tool: str) -> str:
        """根據工具名稱取得服務 ID"""
        tool_service_map = {
            # Knowledge Base
            "rag_search": "knowledge_base",
            "rag_search_multiple": "knowledge_base",
            "rag_ask": "knowledge_base",
            
            # Sandbox（程式碼執行）
            "sandbox_execute_python": "sandbox",
            "sandbox_execute_bash": "sandbox",
            "execute_python": "sandbox",
            "execute_bash": "sandbox",
            
            # Web Search（網路搜尋）
            "web_search": "web_search",
            "web_search_summarize": "web_search",
            
            # Repo Ops（Git 操作）
            "git_clone": "repo_ops",
            "git_status": "repo_ops",
            "git_commit": "repo_ops",
            "git_push": "repo_ops",
            "git_pull": "repo_ops",
            "git_branch": "repo_ops",
            "git_log": "repo_ops",
            "git_diff": "repo_ops"
        }
        return tool_service_map.get(tool, "knowledge_base")
