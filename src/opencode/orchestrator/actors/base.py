"""
Actor Base - Actor 系統基類
實作 Actor Model 模式用於任務編排
"""

from typing import Any, Dict, Optional, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import asyncio
import uuid
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ActorMessage:
    """Actor 間傳遞的訊息"""
    sender: str
    content: Dict[str, Any]
    correlation_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        if self.correlation_id is None:
            self.correlation_id = self.id


class ActorState:
    """Actor 狀態"""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class Actor(ABC):
    """
    Actor 基類
    
    特性:
    - 封裝狀態
    - 異步訊息處理
    - 階層結構 (parent/children)
    - 錯誤隔離
    """
    
    def __init__(
        self, 
        name: str, 
        mailbox_size: int = 1000,
        config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.config = config or {}
        self.mailbox = asyncio.Queue(maxsize=mailbox_size)
        
        # 狀態
        self.state = ActorState.CREATED
        self.internal_state: Dict[str, Any] = {}
        
        # 階層
        self.parent: Optional['Actor'] = None
        self.children: Dict[str, 'Actor'] = {}
        
        # 控制
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._error_handlers: List[Callable] = []
    
    async def start(self) -> None:
        """啟動 Actor"""
        if self.running:
            logger.warning(f"Actor {self.name} is already running")
            return
        
        self.state = ActorState.STARTING
        
        try:
            # 執行初始化
            await self.on_start()
            
            # 啟動訊息處理迴圈
            self.running = True
            self._task = asyncio.create_task(self._process_loop())
            
            # 啟動子 Actor
            for child in self.children.values():
                await child.start()
            
            self.state = ActorState.RUNNING
            logger.info(f"✅ Actor {self.name} started")
            
        except Exception as e:
            self.state = ActorState.ERROR
            logger.error(f"Actor {self.name} start failed: {e}")
            raise
    
    async def stop(self) -> None:
        """停止 Actor"""
        if not self.running:
            return
        
        self.state = ActorState.STOPPING
        self.running = False
        
        # 停止子 Actor
        for child in self.children.values():
            await child.stop()
        
        # 取消處理任務
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # 執行清理
        await self.on_stop()
        
        self.state = ActorState.STOPPED
        logger.info(f"Actor {self.name} stopped")
    
    async def send(self, message: ActorMessage) -> None:
        """
        發送訊息到此 Actor
        
        Args:
            message: 訊息
        """
        if not self.running:
            logger.warning(f"Actor {self.name} is not running, message dropped")
            return
        
        try:
            await asyncio.wait_for(
                self.mailbox.put(message),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Actor {self.name} mailbox full, message dropped")
    
    async def tell(
        self, 
        target: 'Actor', 
        content: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> None:
        """
        發送訊息給其他 Actor
        
        Args:
            target: 目標 Actor
            content: 訊息內容
            correlation_id: 關聯 ID
        """
        message = ActorMessage(
            sender=self.name,
            content=content,
            correlation_id=correlation_id
        )
        await target.send(message)
    
    async def ask(
        self,
        target: 'Actor',
        content: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Any]:
        """
        發送訊息並等待回應 (Request-Response 模式)
        
        Args:
            target: 目標 Actor
            content: 訊息內容
            timeout: 超時時間
            
        Returns:
            回應內容
        """
        correlation_id = str(uuid.uuid4())
        response_future = asyncio.Future()
        
        # 暫存 future 以接收回應
        self._pending_asks = getattr(self, '_pending_asks', {})
        self._pending_asks[correlation_id] = response_future
        
        try:
            # 發送請求
            await self.tell(target, content, correlation_id)
            
            # 等待回應
            return await asyncio.wait_for(response_future, timeout=timeout)
            
        except asyncio.TimeoutError:
            logger.warning(f"Ask timeout from {self.name} to {target.name}")
            return None
        finally:
            self._pending_asks.pop(correlation_id, None)
    
    def spawn_child(
        self, 
        actor_class: type, 
        name: str, 
        **kwargs
    ) -> 'Actor':
        """
        建立子 Actor
        
        Args:
            actor_class: Actor 類
            name: Actor 名稱
            **kwargs: 其他參數
            
        Returns:
            子 Actor 實例
        """
        child = actor_class(name=name, **kwargs)
        child.parent = self
        self.children[name] = child
        return child
    
    def add_error_handler(self, handler: Callable) -> None:
        """添加錯誤處理器"""
        self._error_handlers.append(handler)
    
    @abstractmethod
    async def handle_message(self, message: ActorMessage) -> Optional[Any]:
        """
        處理訊息 (子類必須實作)
        
        Args:
            message: 收到的訊息
            
        Returns:
            回應 (可選)
        """
        pass
    
    async def on_start(self) -> None:
        """啟動時的 hook (可覆寫)"""
        pass
    
    async def on_stop(self) -> None:
        """停止時的 hook (可覆寫)"""
        pass
    
    async def on_error(self, error: Exception, message: ActorMessage) -> None:
        """錯誤處理 hook (可覆寫)"""
        logger.error(f"Actor {self.name} error: {error}")
    
    async def _process_loop(self) -> None:
        """訊息處理迴圈"""
        while self.running:
            try:
                # 等待訊息 (帶超時以便檢查 running 狀態)
                message = await asyncio.wait_for(
                    self.mailbox.get(),
                    timeout=1.0
                )
                
                # 處理訊息
                try:
                    result = await self.handle_message(message)
                    
                    # 如果有 pending ask，發送回應
                    if message.correlation_id and hasattr(self, '_pending_asks'):
                        future = self._pending_asks.get(message.correlation_id)
                        if future and not future.done():
                            future.set_result(result)
                    
                except Exception as e:
                    await self._handle_error(e, message)
                    
            except asyncio.TimeoutError:
                # 正常超時，繼續迴圈
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Actor {self.name} loop error: {e}")
    
    async def _handle_error(
        self, 
        error: Exception, 
        message: ActorMessage
    ) -> None:
        """處理錯誤"""
        # 呼叫自訂錯誤處理器
        for handler in self._error_handlers:
            try:
                await handler(error, message)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")
        
        # 呼叫 hook
        await self.on_error(error, message)
        
        # 如果有 parent，通知 parent
        if self.parent:
            await self.tell(self.parent, {
                "type": "child_error",
                "child": self.name,
                "error": str(error),
                "message": message.content
            })


class SupervisorStrategy:
    """監督策略"""
    RESTART = "restart"      # 重啟失敗的 Actor
    STOP = "stop"           # 停止失敗的 Actor
    ESCALATE = "escalate"   # 上報給 parent
    RESUME = "resume"       # 繼續執行


class SupervisorActor(Actor):
    """
    監督 Actor
    管理子 Actor 的生命週期和錯誤恢復
    """
    
    def __init__(
        self, 
        name: str,
        strategy: str = SupervisorStrategy.RESTART,
        max_restarts: int = 3,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.strategy = strategy
        self.max_restarts = max_restarts
        self.restart_counts: Dict[str, int] = {}
    
    async def handle_message(self, message: ActorMessage) -> Optional[Any]:
        """處理監督訊息"""
        content = message.content
        msg_type = content.get("type")
        
        if msg_type == "child_error":
            await self._handle_child_error(content)
        else:
            # 轉發給子 Actor
            child_name = content.get("target")
            if child_name and child_name in self.children:
                await self.children[child_name].send(message)
        
        return None
    
    async def _handle_child_error(self, content: Dict[str, Any]) -> None:
        """處理子 Actor 錯誤"""
        child_name = content.get("child")
        error = content.get("error")
        
        logger.warning(f"Child {child_name} error: {error}")
        
        if self.strategy == SupervisorStrategy.RESTART:
            await self._restart_child(child_name)
        elif self.strategy == SupervisorStrategy.STOP:
            await self._stop_child(child_name)
        elif self.strategy == SupervisorStrategy.ESCALATE and self.parent:
            await self.tell(self.parent, content)
    
    async def _restart_child(self, child_name: str) -> None:
        """重啟子 Actor"""
        if child_name not in self.children:
            return
        
        # 檢查重啟次數
        self.restart_counts[child_name] = self.restart_counts.get(child_name, 0) + 1
        
        if self.restart_counts[child_name] > self.max_restarts:
            logger.error(f"Child {child_name} exceeded max restarts")
            await self._stop_child(child_name)
            return
        
        child = self.children[child_name]
        await child.stop()
        await child.start()
        
        logger.info(f"Child {child_name} restarted ({self.restart_counts[child_name]}/{self.max_restarts})")
    
    async def _stop_child(self, child_name: str) -> None:
        """停止子 Actor"""
        if child_name in self.children:
            await self.children[child_name].stop()
            del self.children[child_name]
