"""
Event Bus - 異步事件匯流排
支援事件發布/訂閱、中介層、歷史記錄
"""

from typing import Dict, Any, List, Callable, AsyncIterator, Optional
import asyncio
from collections import defaultdict
import logging
import time

from opencode.core.protocols import Event, EventType, EventBusProtocol

logger = logging.getLogger(__name__)


class EventBus(EventBusProtocol):
    """異步事件匯流排實作"""
    
    def __init__(self, max_history: int = 1000):
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.wildcard_handlers: List[Callable] = []
        self.middleware: List[Callable] = []
        self.event_history: List[Event] = []
        self.max_history = max_history
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化 Event Bus"""
        self._initialized = True
        logger.info("✅ EventBus initialized")
    
    def register_handler(
        self, 
        event_type: str, 
        handler: Callable
    ) -> None:
        """
        註冊特定事件類型的處理器
        
        Args:
            event_type: 事件類型 (字串或 EventType.value)
            handler: 處理函數 (async 或 sync)
        """
        self.handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")
    
    def register(self, handler: Callable) -> None:
        """
        註冊萬用處理器 (接收所有事件)
        
        Args:
            handler: 處理函數
        """
        self.wildcard_handlers.append(handler)
        logger.debug(f"Registered wildcard handler: {handler}")
    
    def unregister_handler(
        self, 
        event_type: str, 
        handler: Callable
    ) -> bool:
        """取消註冊處理器"""
        if event_type in self.handlers:
            try:
                self.handlers[event_type].remove(handler)
                return True
            except ValueError:
                return False
        return False
    
    def add_middleware(self, middleware: Callable) -> None:
        """
        添加中介層
        中介層可以修改或過濾事件
        
        Args:
            middleware: async function(event) -> event
        """
        self.middleware.append(middleware)
        logger.debug(f"Added middleware: {middleware}")
    
    async def emit(
        self, 
        event: Event
    ) -> AsyncIterator[Event]:
        """
        發送事件並產生回應
        
        Args:
            event: 要發送的事件
            
        Yields:
            處理器產生的回應事件
        """
        # 記錄歷史
        self._record_event(event)
        
        # 應用中介層
        processed_event = event
        for mw in self.middleware:
            try:
                if asyncio.iscoroutinefunction(mw):
                    processed_event = await mw(processed_event)
                else:
                    processed_event = mw(processed_event)
                
                if processed_event is None:
                    # 中介層過濾掉了事件
                    logger.debug(f"Event filtered by middleware: {event.type}")
                    return
            except Exception as e:
                logger.error(f"Middleware error: {e}")
        
        # 取得處理器
        event_type_str = (
            event.type.value 
            if isinstance(event.type, EventType) 
            else event.type
        )
        handlers = list(self.handlers.get(event_type_str, []))
        handlers.extend(self.wildcard_handlers)
        
        if not handlers:
            logger.debug(f"No handlers for event type: {event_type_str}")
            return
        
        # 執行處理器
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(processed_event)
                else:
                    result = handler(processed_event)
                
                if result is not None:
                    # 處理器返回了結果
                    if hasattr(result, '__aiter__'):
                        # 異步迭代器
                        async for r in result:
                            if r is not None:
                                yield r
                    elif hasattr(result, '__iter__') and not isinstance(result, (str, dict)):
                        # 同步迭代器
                        for r in result:
                            if r is not None:
                                yield r
                    else:
                        # 單一結果
                        yield result
                        
            except Exception as e:
                logger.error(f"Handler error for {event_type_str}: {e}", exc_info=True)
                yield Event(
                    type=EventType.ERROR,
                    payload={
                        "message": str(e),
                        "handler": str(handler),
                        "original_event": event.to_dict()
                    },
                    timestamp=time.time(),
                    source="event_bus",
                    correlation_id=event.correlation_id
                )
    
    async def publish(self, event: Event) -> None:
        """
        發送事件 (不等待回應)
        
        Args:
            event: 要發送的事件
        """
        async for _ in self.emit(event):
            pass  # 消費所有回應但不處理
    
    async def emit_and_collect(self, event: Event) -> List[Event]:
        """
        發送事件並收集所有回應
        
        Args:
            event: 要發送的事件
            
        Returns:
            所有回應事件的列表
        """
        results = []
        async for response in self.emit(event):
            results.append(response)
        return results
    
    def _record_event(self, event: Event) -> None:
        """記錄事件到歷史"""
        self.event_history.append(event)
        
        # 限制歷史大小
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
    
    def get_history(
        self, 
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        取得事件歷史
        
        Args:
            event_type: 過濾特定類型 (可選)
            limit: 返回數量限制
            
        Returns:
            事件列表
        """
        history = self.event_history
        
        if event_type:
            history = [
                e for e in history 
                if (e.type.value if isinstance(e.type, EventType) else e.type) == event_type
            ]
        
        return history[-limit:]
    
    def clear_history(self) -> None:
        """清除事件歷史"""
        self.event_history.clear()
    
    @property
    def handler_count(self) -> int:
        """取得總處理器數量"""
        count = len(self.wildcard_handlers)
        for handlers in self.handlers.values():
            count += len(handlers)
        return count


# ============== 內建中介層 ==============

async def logging_middleware(event: Event) -> Event:
    """日誌記錄中介層"""
    logger.info(f"Event: {event.type} from {event.source}")
    return event


async def timing_middleware(event: Event) -> Event:
    """計時中介層 - 在 payload 中加入處理時間"""
    event.payload["_emit_time"] = time.time()
    return event


def create_filter_middleware(
    allowed_types: List[EventType]
) -> Callable:
    """
    建立事件過濾中介層
    
    Args:
        allowed_types: 允許的事件類型列表
        
    Returns:
        中介層函數
    """
    async def filter_middleware(event: Event) -> Optional[Event]:
        if event.type in allowed_types:
            return event
        return None
    
    return filter_middleware


# ============== 便利函數 ==============

def create_event(
    event_type: EventType,
    content: str = "",
    data: Optional[Dict[str, Any]] = None,
    source: str = "system",
    correlation_id: Optional[str] = None
) -> Event:
    """
    便利函數：建立事件
    
    Args:
        event_type: 事件類型
        content: 主要內容
        data: 附加資料
        source: 來源
        correlation_id: 關聯 ID
        
    Returns:
        Event 實例
    """
    payload = {"content": content}
    if data:
        payload["data"] = data
    
    return Event(
        type=event_type,
        payload=payload,
        timestamp=time.time(),
        source=source,
        correlation_id=correlation_id
    )
