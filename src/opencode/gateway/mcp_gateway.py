"""
MCP Gateway - 統一工具閘道
管理所有 MCP 服務的連接和呼叫
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging
import time

from opencode.core.protocols import MCPGatewayProtocol, MCPServiceProtocol

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """斷路器 - 防止故障擴散"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    def record_failure(self) -> None:
        """記錄失敗"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker opened")
    
    def record_success(self) -> None:
        """記錄成功"""
        self.failure_count = 0
        self.state = "closed"
    
    def can_execute(self) -> bool:
        """檢查是否可以執行"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # 檢查是否可以進入 half-open
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self.state = "half-open"
                    return True
            return False
        
        # half-open 狀態允許一次嘗試
        return True


class MCPGateway(MCPGatewayProtocol):
    """
    MCP Gateway 實作
    
    職責:
    - 服務註冊和發現
    - 呼叫路由
    - 斷路器保護
    - 健康檢查
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 服務註冊表
        self.services: Dict[str, MCPServiceProtocol] = {}
        
        # 斷路器
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # 健康狀態
        self.health_status: Dict[str, bool] = {}
        
        # 背景任務
        self._health_check_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化 Gateway"""
        # 啟動健康檢查
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        self._initialized = True
        logger.info("✅ MCP Gateway initialized")
    
    async def register_service(self, service: MCPServiceProtocol) -> None:
        """
        註冊服務
        
        Args:
            service: MCP 服務實例
        """
        service_id = service.service_id
        
        self.services[service_id] = service
        self.circuit_breakers[service_id] = CircuitBreaker()
        self.health_status[service_id] = True
        
        logger.info(f"Registered service: {service_id}")
    
    async def unregister_service(self, service_id: str) -> None:
        """取消註冊服務"""
        if service_id in self.services:
            service = self.services[service_id]
            await service.shutdown()
            
            del self.services[service_id]
            del self.circuit_breakers[service_id]
            del self.health_status[service_id]
            
            logger.info(f"Unregistered service: {service_id}")
    
    async def call(
        self, 
        service_id: str, 
        method: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        呼叫服務方法
        
        Args:
            service_id: 服務 ID
            method: 方法名稱
            params: 參數
            
        Returns:
            執行結果
        """
        # 檢查服務是否存在
        if service_id not in self.services:
            raise RuntimeError(f"Service not found: {service_id}")
        
        # 檢查斷路器
        circuit_breaker = self.circuit_breakers[service_id]
        if not circuit_breaker.can_execute():
            raise RuntimeError(f"Service {service_id} circuit breaker is open")
        
        # 執行呼叫
        service = self.services[service_id]
        
        try:
            result = await service.execute(method, params)
            circuit_breaker.record_success()
            return result
            
        except Exception as e:
            circuit_breaker.record_failure()
            logger.error(f"Service call failed: {service_id}.{method}: {e}")
            raise
    
    async def discover_services(self) -> List[Dict[str, Any]]:
        """發現可用服務"""
        services_info = []
        
        for service_id, service in self.services.items():
            services_info.append({
                "id": service_id,
                "capabilities": service.capabilities,
                "healthy": self.health_status.get(service_id, False)
            })
        
        return services_info
    
    async def _health_check_loop(self) -> None:
        """健康檢查迴圈"""
        while True:
            try:
                await asyncio.sleep(30)  # 每 30 秒檢查一次
                
                for service_id, service in self.services.items():
                    try:
                        healthy = await service.health_check()
                        self.health_status[service_id] = healthy
                        
                        if not healthy:
                            logger.warning(f"Service unhealthy: {service_id}")
                            
                    except Exception as e:
                        self.health_status[service_id] = False
                        logger.error(f"Health check failed for {service_id}: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def shutdown(self) -> None:
        """關閉 Gateway"""
        # 停止健康檢查
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # 關閉所有服務
        for service_id in list(self.services.keys()):
            await self.unregister_service(service_id)
        
        logger.info("MCP Gateway shutdown complete")


# ============== 單例模式 ==============

_default_gateway: Optional[MCPGateway] = None


async def get_gateway() -> MCPGateway:
    """取得預設 Gateway 實例"""
    global _default_gateway
    
    if _default_gateway is None:
        _default_gateway = MCPGateway()
        await _default_gateway.initialize()
    
    return _default_gateway


async def shutdown_gateway() -> None:
    """關閉預設 Gateway"""
    global _default_gateway
    
    if _default_gateway:
        await _default_gateway.shutdown()
        _default_gateway = None
