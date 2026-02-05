"""
Memory Actor - 記憶管理器
管理 Session、Skill、Long-term 記憶
"""

from typing import Dict, Any, Optional, List
import logging
import time

from opencode.orchestrator.actors.base import Actor, ActorMessage

logger = logging.getLogger(__name__)


class MemoryActor(Actor):
    """
    記憶 Actor
    
    職責:
    - 管理 Session 記憶 (短期)
    - 管理 Skill 記憶 (中期)
    - 協調 Long-term 記憶 (RAG)
    """
    
    def __init__(self, name: str = "memory", config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, config=config)
        
        # Session 記憶 (本地快取)
        self.session_memory: Dict[str, Dict] = {}
        
        # Skill 記憶 (成功的任務模式)
        self.skill_memory: List[Dict] = []
        
        # 配置
        self.max_session_history = config.get("max_session_history", 100) if config else 100
        self.max_skills = config.get("max_skills", 1000) if config else 1000
    
    async def handle_message(self, message: ActorMessage) -> Optional[Any]:
        """處理訊息"""
        content = message.content
        msg_type = content.get("type")
        
        if msg_type == "store_session":
            session_id = content.get("session_id")
            data = content.get("data")
            await self.store_session(session_id, data)
            
        elif msg_type == "get_session":
            session_id = content.get("session_id")
            return await self.get_session(session_id)
            
        elif msg_type == "record_skill":
            skill = content.get("skill")
            await self.record_skill(skill)
            
        elif msg_type == "find_similar_skills":
            query = content.get("query")
            limit = content.get("limit", 5)
            return await self.find_similar_skills(query, limit)
            
        elif msg_type == "update_skill_stats":
            skill_id = content.get("skill_id")
            success = content.get("success", True)
            await self.update_skill_stats(skill_id, success)
        
        return None
    
    async def store_session(
        self, 
        session_id: str, 
        data: Dict[str, Any]
    ) -> None:
        """
        儲存 Session 記憶
        
        Args:
            session_id: Session ID
            data: 要儲存的資料
        """
        if session_id not in self.session_memory:
            self.session_memory[session_id] = {
                "created_at": time.time(),
                "history": [],
                "metadata": {}
            }
        
        session = self.session_memory[session_id]
        session["history"].append({
            **data,
            "timestamp": time.time()
        })
        
        # 限制歷史大小
        if len(session["history"]) > self.max_session_history:
            session["history"] = session["history"][-self.max_session_history:]
        
        session["updated_at"] = time.time()
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """取得 Session 記憶"""
        return self.session_memory.get(session_id)
    
    async def clear_session(self, session_id: str) -> None:
        """清除 Session 記憶"""
        if session_id in self.session_memory:
            del self.session_memory[session_id]
    
    async def record_skill(self, skill: Dict[str, Any]) -> str:
        """
        記錄技能 (成功的任務模式)
        
        Args:
            skill: 技能定義
                - name: 技能名稱
                - trigger_patterns: 觸發模式
                - execution_template: 執行模板
                
        Returns:
            技能 ID
        """
        import uuid
        
        skill_id = str(uuid.uuid4())
        skill_record = {
            "id": skill_id,
            "name": skill.get("name", "unnamed"),
            "trigger_patterns": skill.get("trigger_patterns", []),
            "execution_template": skill.get("execution_template", {}),
            "created_at": time.time(),
            "success_count": 0,
            "failure_count": 0,
            "last_used": None
        }
        
        self.skill_memory.append(skill_record)
        
        # 限制技能數量
        if len(self.skill_memory) > self.max_skills:
            # 移除最少使用的技能
            self.skill_memory.sort(key=lambda s: s.get("success_count", 0))
            self.skill_memory = self.skill_memory[-self.max_skills:]
        
        logger.info(f"Recorded skill: {skill_record['name']}")
        return skill_id
    
    async def find_similar_skills(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        尋找相似技能
        
        Args:
            query: 查詢文字
            limit: 返回數量
            
        Returns:
            相似技能列表
        """
        # 簡單的關鍵字匹配 (未來可以改用向量搜尋)
        query_lower = query.lower()
        
        matches = []
        for skill in self.skill_memory:
            score = 0
            
            # 檢查名稱匹配
            if query_lower in skill.get("name", "").lower():
                score += 2
            
            # 檢查觸發模式匹配
            for pattern in skill.get("trigger_patterns", []):
                if query_lower in pattern.lower() or pattern.lower() in query_lower:
                    score += 1
            
            if score > 0:
                matches.append((score, skill))
        
        # 按分數排序
        matches.sort(key=lambda x: x[0], reverse=True)
        
        return [skill for _, skill in matches[:limit]]
    
    async def update_skill_stats(
        self, 
        skill_id: str, 
        success: bool
    ) -> None:
        """
        更新技能統計
        
        Args:
            skill_id: 技能 ID
            success: 是否成功
        """
        for skill in self.skill_memory:
            if skill["id"] == skill_id:
                if success:
                    skill["success_count"] = skill.get("success_count", 0) + 1
                else:
                    skill["failure_count"] = skill.get("failure_count", 0) + 1
                skill["last_used"] = time.time()
                break
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得記憶統計"""
        return {
            "session_count": len(self.session_memory),
            "skill_count": len(self.skill_memory),
            "total_session_messages": sum(
                len(s.get("history", [])) 
                for s in self.session_memory.values()
            )
        }
