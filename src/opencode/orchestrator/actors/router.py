"""
Router Actor - 任務路由器
將任務路由到適當的 MCP 服務
"""

from typing import Dict, Any, Optional
import logging

from opencode.orchestrator.actors.base import Actor, ActorMessage

logger = logging.getLogger(__name__)


class RouterActor(Actor):
    """
    路由 Actor
    
    職責:
    - 根據任務類型選擇服務
    - 負載平衡
    - 服務健康檢查
    """
    
    def __init__(self, name: str = "router", config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, config=config)
        
        # 工具到服務的映射
        self.tool_service_map = {
            # Knowledge Base 服務
            "rag_search": "knowledge_base",
            "rag_search_multiple": "knowledge_base",
            "rag_ask": "knowledge_base",
            "document_upload": "knowledge_base",
            "document_list": "knowledge_base",
            "document_delete": "knowledge_base",
            
            # Sandbox 服務（程式碼執行）
            "sandbox_execute_python": "sandbox",
            "sandbox_execute_bash": "sandbox",
            "execute_python": "sandbox",
            "execute_bash": "sandbox",
            "file_read": "sandbox",
            "file_write": "sandbox",
            
            # Repo Ops 服務
            "git_clone": "repo_ops",
            "git_status": "repo_ops",
            "git_commit": "repo_ops",
            "git_push": "repo_ops",
            "git_pull": "repo_ops",
            
            # Data Services
            "db_query": "data_services",
            "api_call": "data_services"
        }
        
        # 服務健康狀態
        self.service_health: Dict[str, bool] = {}
    
    async def handle_message(self, message: ActorMessage) -> Optional[Any]:
        """處理訊息"""
        content = message.content
        msg_type = content.get("type")
        
        if msg_type == "route_task":
            task = content.get("task", {})
            service_id = await self.route(task)
            
            return {"service_id": service_id}
        
        elif msg_type == "update_health":
            service_id = content.get("service_id")
            healthy = content.get("healthy", True)
            self.service_health[service_id] = healthy
        
        return None
    
    async def route(self, task: Dict[str, Any]) -> str:
        """
        路由任務到服務
        
        Args:
            task: 任務定義
            
        Returns:
            服務 ID
        """
        tool = task.get("tool", "")
        
        # 先檢查任務是否已指定服務
        if "service" in task:
            return task["service"]
        
        # 根據工具查找服務
        service_id = self.tool_service_map.get(tool)
        
        if service_id is None:
            logger.warning(f"Unknown tool: {tool}, using default service")
            service_id = "knowledge_base"  # 預設服務
        
        # 檢查服務健康狀態
        if not self.service_health.get(service_id, True):
            logger.warning(f"Service {service_id} is unhealthy")
            # 可以在這裡實作 fallback 邏輯
        
        return service_id
    
    def register_tool(self, tool_name: str, service_id: str) -> None:
        """註冊工具映射"""
        self.tool_service_map[tool_name] = service_id
        logger.info(f"Registered tool {tool_name} -> {service_id}")
    
    def update_service_health(self, service_id: str, healthy: bool) -> None:
        """更新服務健康狀態"""
        self.service_health[service_id] = healthy
