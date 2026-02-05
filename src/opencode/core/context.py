"""
Context Manager - 用戶上下文管理
支援 Redis 持久化、本地快取、TTL 管理
"""

from typing import Dict, Any, Optional
import asyncio
import json
import time
import logging

from opencode.core.protocols import Context, ContextManagerProtocol

logger = logging.getLogger(__name__)


class ContextManager(ContextManagerProtocol):
    """
    Context 管理器實作
    
    支援:
    - Redis 持久化儲存
    - 本地記憶體快取
    - TTL 自動過期
    - 對話歷史管理
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        cache_ttl: int = 3600,  # 1 小時
        max_history: int = 100,
        use_local_cache: bool = True
    ):
        self.redis_url = redis_url
        self.cache_ttl = cache_ttl
        self.max_history = max_history
        self.use_local_cache = use_local_cache
        
        self.redis_client = None
        self.local_cache: Dict[str, Context] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化 Context Manager"""
        try:
            import redis.asyncio as redis
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 測試連接
            await self.redis_client.ping()
            self._initialized = True
            logger.info("✅ ContextManager initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using local cache only")
            self.redis_client = None
            self._initialized = True
            logger.info("✅ ContextManager initialized with local cache")
    
    async def get_context(self, session_id: str) -> Optional[Context]:
        """
        取得用戶 Context
        
        Args:
            session_id: Session ID
            
        Returns:
            Context 或 None
        """
        # 優先從本地快取取得
        if self.use_local_cache and session_id in self.local_cache:
            logger.debug(f"Context cache hit: {session_id}")
            return self.local_cache[session_id]
        
        # 從 Redis 取得
        if self.redis_client:
            try:
                data = await self.redis_client.get(f"context:{session_id}")
                if data:
                    context_dict = json.loads(data)
                    context = Context.from_dict(context_dict)
                    
                    # 更新本地快取
                    if self.use_local_cache:
                        self.local_cache[session_id] = context
                    
                    logger.debug(f"Context loaded from Redis: {session_id}")
                    return context
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        logger.debug(f"Context not found: {session_id}")
        return None
    
    async def save_context(self, context: Context) -> None:
        """
        儲存用戶 Context
        
        Args:
            context: Context 實例
        """
        session_id = context.session_id
        
        # 更新本地快取
        if self.use_local_cache:
            self.local_cache[session_id] = context
        
        # 儲存到 Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"context:{session_id}",
                    self.cache_ttl,
                    json.dumps(context.to_dict(), ensure_ascii=False)
                )
                logger.debug(f"Context saved to Redis: {session_id}")
            except Exception as e:
                logger.error(f"Redis set error: {e}")
    
    async def update_conversation(
        self, 
        session_id: str, 
        message: Dict[str, Any]
    ) -> None:
        """
        更新對話歷史
        
        Args:
            session_id: Session ID
            message: 訊息 (包含 role, content 等)
        """
        context = await self.get_context(session_id)
        
        if context is None:
            # 建立新 Context
            context = Context(
                session_id=session_id,
                user_id="default",
                conversation_history=[]
            )
        
        # 加入時間戳
        message_with_time = {
            **message,
            "timestamp": time.time()
        }
        
        context.conversation_history.append(message_with_time)
        
        # 限制歷史大小
        if len(context.conversation_history) > self.max_history:
            context.conversation_history = context.conversation_history[-self.max_history:]
        
        await self.save_context(context)
    
    async def delete_context(self, session_id: str) -> None:
        """
        刪除 Context
        
        Args:
            session_id: Session ID
        """
        # 從本地快取刪除
        if session_id in self.local_cache:
            del self.local_cache[session_id]
        
        # 從 Redis 刪除
        if self.redis_client:
            try:
                await self.redis_client.delete(f"context:{session_id}")
                logger.debug(f"Context deleted: {session_id}")
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
    
    async def extend_ttl(self, session_id: str, ttl: Optional[int] = None) -> None:
        """
        延長 Context TTL
        
        Args:
            session_id: Session ID
            ttl: 新的 TTL (秒)，預設使用 cache_ttl
        """
        ttl = ttl or self.cache_ttl
        
        if self.redis_client:
            try:
                await self.redis_client.expire(f"context:{session_id}", ttl)
            except Exception as e:
                logger.error(f"Redis expire error: {e}")
    
    async def get_or_create(
        self, 
        session_id: str, 
        user_id: str = "default"
    ) -> Context:
        """
        取得或建立 Context
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            Context 實例
        """
        context = await self.get_context(session_id)
        
        if context is None:
            context = Context(
                session_id=session_id,
                user_id=user_id,
                permissions=[],
                metadata={},
                conversation_history=[],
                active_plugins=[]
            )
            await self.save_context(context)
            logger.info(f"Created new context: {session_id}")
        
        return context
    
    async def list_sessions(self, pattern: str = "*") -> list[str]:
        """
        列出所有 Session ID
        
        Args:
            pattern: Redis key 模式
            
        Returns:
            Session ID 列表
        """
        sessions = []
        
        # 從 Redis 取得
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(f"context:{pattern}")
                sessions = [k.replace("context:", "") for k in keys]
            except Exception as e:
                logger.error(f"Redis keys error: {e}")
        
        # 加入本地快取的 sessions
        for session_id in self.local_cache.keys():
            if session_id not in sessions:
                sessions.append(session_id)
        
        return sessions
    
    def clear_local_cache(self) -> None:
        """清除本地快取"""
        self.local_cache.clear()
        logger.info("Local cache cleared")
    
    async def close(self) -> None:
        """關閉連接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


# ============== 簡易本地實作 (無 Redis 依賴) ==============

class LocalContextManager(ContextManagerProtocol):
    """
    純本地 Context Manager (不需要 Redis)
    適合開發和測試
    """
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.contexts: Dict[str, Context] = {}
    
    async def initialize(self) -> None:
        logger.info("✅ LocalContextManager initialized")
    
    async def get_context(self, session_id: str) -> Optional[Context]:
        return self.contexts.get(session_id)
    
    async def save_context(self, context: Context) -> None:
        self.contexts[context.session_id] = context
    
    async def update_conversation(
        self, 
        session_id: str, 
        message: Dict[str, Any]
    ) -> None:
        context = self.contexts.get(session_id)
        
        if context is None:
            context = Context(
                session_id=session_id,
                user_id="default"
            )
            self.contexts[session_id] = context
        
        message["timestamp"] = time.time()
        context.conversation_history.append(message)
        
        if len(context.conversation_history) > self.max_history:
            context.conversation_history = context.conversation_history[-self.max_history:]
    
    async def delete_context(self, session_id: str) -> None:
        if session_id in self.contexts:
            del self.contexts[session_id]
