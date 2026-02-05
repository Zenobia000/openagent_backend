"""
Audit Log - 稽核日誌
記錄所有重要操作以供審計
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
import time
import json
import uuid
import asyncio
from pathlib import Path

from opencode.core.protocols import AuditLogProtocol

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """稽核記錄項目"""
    id: str
    timestamp: float
    event_type: str
    actor: str
    action: str
    resource: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        return cls(**data)


class AuditLogger(AuditLogProtocol):
    """
    稽核日誌實作
    
    功能:
    - 記錄所有重要操作
    - 支援多種儲存後端
    - 查詢和過濾
    """
    
    def __init__(
        self, 
        storage_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.config = config or {}
        self.storage_path = storage_path or self.config.get("storage_path", "logs/audit")
        
        # 記錄緩衝區
        self.buffer: List[AuditEntry] = []
        self.buffer_size = self.config.get("buffer_size", 100)
        
        # 內存日誌 (最近的記錄)
        self.recent_logs: List[AuditEntry] = []
        self.max_recent = self.config.get("max_recent", 10000)
        
        # 確保目錄存在
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化"""
        self._initialized = True
        logger.info(f"✅ AuditLogger initialized (storage: {self.storage_path})")
    
    async def log(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        記錄稽核日誌
        
        Args:
            event_type: 事件類型 (e.g., "tool_call", "auth", "data_access")
            actor: 執行者 (用戶 ID)
            action: 動作 (e.g., "execute", "read", "write")
            resource: 資源 (e.g., 工具名稱, 文件名稱)
            success: 是否成功
            details: 詳細資訊
            **kwargs: 其他欄位 (session_id, trace_id, etc.)
        """
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            success=success,
            details=details or {},
            session_id=kwargs.get("session_id"),
            trace_id=kwargs.get("trace_id"),
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent")
        )
        
        # 加入緩衝區
        self.buffer.append(entry)
        
        # 加入近期記錄
        self.recent_logs.append(entry)
        if len(self.recent_logs) > self.max_recent:
            self.recent_logs = self.recent_logs[-self.max_recent:]
        
        # 緩衝區滿時寫入
        if len(self.buffer) >= self.buffer_size:
            await self._flush_buffer()
        
        # 記錄到標準日誌
        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"AUDIT: [{event_type}] {actor} {action} {resource} - {'SUCCESS' if success else 'FAILED'}"
        )
    
    async def query(
        self, 
        filters: Dict[str, Any], 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查詢稽核日誌
        
        Args:
            filters: 過濾條件
                - event_type: 事件類型
                - actor: 執行者
                - action: 動作
                - resource: 資源
                - success: 是否成功
                - start_time: 開始時間 (timestamp)
                - end_time: 結束時間 (timestamp)
            limit: 返回數量限制
            
        Returns:
            符合條件的日誌列表
        """
        results = []
        
        # 先從近期記錄查詢
        for entry in reversed(self.recent_logs):
            if self._match_filters(entry, filters):
                results.append(entry.to_dict())
                if len(results) >= limit:
                    break
        
        # 如果需要更多，從檔案讀取
        if len(results) < limit:
            file_results = await self._query_from_files(filters, limit - len(results))
            results.extend(file_results)
        
        return results[:limit]
    
    def _match_filters(self, entry: AuditEntry, filters: Dict[str, Any]) -> bool:
        """檢查記錄是否符合過濾條件"""
        for key, value in filters.items():
            if key == "start_time":
                if entry.timestamp < value:
                    return False
            elif key == "end_time":
                if entry.timestamp > value:
                    return False
            elif hasattr(entry, key):
                if getattr(entry, key) != value:
                    return False
        return True
    
    async def _flush_buffer(self) -> None:
        """寫入緩衝區到檔案"""
        if not self.buffer:
            return
        
        # 按日期分檔
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = Path(self.storage_path) / f"audit_{date_str}.jsonl"
        
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                for entry in self.buffer:
                    f.write(entry.to_json() + "\n")
            
            self.buffer.clear()
            logger.debug(f"Flushed audit buffer to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {e}")
    
    async def _query_from_files(
        self, 
        filters: Dict[str, Any], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """從檔案查詢"""
        results = []
        
        # 取得所有日誌檔案
        log_files = sorted(
            Path(self.storage_path).glob("audit_*.jsonl"),
            reverse=True
        )
        
        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            entry_dict = json.loads(line)
                            entry = AuditEntry.from_dict(entry_dict)
                            
                            if self._match_filters(entry, filters):
                                results.append(entry_dict)
                                if len(results) >= limit:
                                    return results
            except Exception as e:
                logger.error(f"Failed to read {log_file}: {e}")
        
        return results
    
    async def flush(self) -> None:
        """強制寫入緩衝區"""
        await self._flush_buffer()
    
    async def get_statistics(
        self, 
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        取得統計資訊
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            統計資訊
        """
        # 預設查詢最近 24 小時
        if start_time is None:
            start_time = time.time() - 86400
        if end_time is None:
            end_time = time.time()
        
        # 統計
        stats = {
            "total_events": 0,
            "success_count": 0,
            "failure_count": 0,
            "by_event_type": {},
            "by_actor": {},
            "by_action": {}
        }
        
        for entry in self.recent_logs:
            if start_time <= entry.timestamp <= end_time:
                stats["total_events"] += 1
                
                if entry.success:
                    stats["success_count"] += 1
                else:
                    stats["failure_count"] += 1
                
                # 按類型統計
                et = entry.event_type
                stats["by_event_type"][et] = stats["by_event_type"].get(et, 0) + 1
                
                # 按執行者統計
                actor = entry.actor
                stats["by_actor"][actor] = stats["by_actor"].get(actor, 0) + 1
                
                # 按動作統計
                action = entry.action
                stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
        
        return stats
    
    async def shutdown(self) -> None:
        """關閉並寫入剩餘緩衝"""
        await self._flush_buffer()
        logger.info("AuditLogger shutdown complete")
