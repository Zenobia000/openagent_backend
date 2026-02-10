"""
審計日誌服務 - 記錄所有用戶操作
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict, field
import uuid

from core.utils import get_project_root

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """審計動作類型"""
    # 認證相關
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    
    # 文件操作
    UPLOAD_FILE = "upload_file"
    DELETE_FILE = "delete_file"
    VIEW_FILE = "view_file"
    
    # 對話操作
    CHAT_QUERY = "chat_query"
    SEARCH_QUERY = "search_query"
    
    # 工具使用
    TOOL_EXECUTE = "tool_execute"
    CODE_EXECUTE = "code_execute"
    WEB_SEARCH = "web_search"
    GIT_OPERATION = "git_operation"
    
    # 研究
    RESEARCH_START = "research_start"
    RESEARCH_COMPLETE = "research_complete"
    
    # 管理操作
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    SYSTEM_RESET = "system_reset"
    
    # 系統
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"


class AuditLevel(str, Enum):
    """審計級別"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditLog:
    """審計日誌條目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # 用戶資訊
    user_id: Optional[str] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    
    # 操作資訊
    action: str = ""
    level: str = AuditLevel.INFO.value
    resource: Optional[str] = None  # 操作的資源（如文件名）
    
    # 請求資訊
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    
    # 結果
    success: bool = True
    error_message: Optional[str] = None
    
    # 詳細資料
    details: Dict[str, Any] = field(default_factory=dict)
    
    # API 成本追蹤
    tokens_used: int = 0
    api_cost: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditService:
    """
    審計日誌服務
    
    功能:
    - 記錄所有用戶操作
    - 支援查詢和過濾
    - 自動清理舊日誌
    """
    
    def __init__(self):
        self.data_dir = get_project_root() / "data" / "audit"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = int(os.getenv("AUDIT_RETENTION_DAYS", "30"))
        
        # 記憶體快取（最近的日誌）
        self._recent_logs: List[AuditLog] = []
        self._max_memory_logs = 1000
        
        logger.info(f"✅ AuditService initialized (retention: {self.retention_days} days)")
    
    def _get_log_file(self, date: datetime = None) -> Path:
        """獲取指定日期的日誌文件"""
        if date is None:
            date = datetime.utcnow()
        filename = f"audit_{date.strftime('%Y-%m-%d')}.jsonl"
        return self.data_dir / filename
    
    def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        resource: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        level: AuditLevel = AuditLevel.INFO,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        details: Dict[str, Any] = None,
        tokens_used: int = 0,
        api_cost: float = 0.0
    ) -> AuditLog:
        """
        記錄審計日誌
        """
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            user_role=user_role,
            action=action.value if isinstance(action, AuditAction) else action,
            level=level.value if isinstance(level, AuditLevel) else level,
            resource=resource,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            details=details or {},
            tokens_used=tokens_used,
            api_cost=api_cost
        )
        
        # 寫入文件
        try:
            log_file = self._get_log_file()
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"❌ 寫入審計日誌失敗: {e}")
        
        # 加入記憶體快取
        self._recent_logs.append(log_entry)
        if len(self._recent_logs) > self._max_memory_logs:
            self._recent_logs = self._recent_logs[-self._max_memory_logs:]
        
        # 如果是錯誤，記錄到 logger
        if level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
            logger.error(f"AUDIT [{action}] user={username} resource={resource} error={error_message}")
        
        return log_entry
    
    def query(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        level: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查詢審計日誌
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            log_file = self._get_log_file(current_date)
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                log_entry = json.loads(line)
                                
                                # 過濾條件
                                if user_id and log_entry.get('user_id') != user_id:
                                    continue
                                if username and log_entry.get('username') != username:
                                    continue
                                if action and log_entry.get('action') != action:
                                    continue
                                if level and log_entry.get('level') != level:
                                    continue
                                if success is not None and log_entry.get('success') != success:
                                    continue
                                
                                results.append(log_entry)
                except Exception as e:
                    logger.error(f"❌ 讀取審計日誌失敗: {e}")
            
            current_date += timedelta(days=1)
        
        # 按時間倒序排列
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 分頁
        return results[offset:offset + limit]
    
    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """獲取最近的日誌"""
        return [log.to_dict() for log in reversed(self._recent_logs[-limit:])]
    
    def get_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """獲取統計資訊"""
        logs = self.query(start_date=start_date, end_date=end_date, limit=10000)
        
        stats = {
            "total_count": len(logs),
            "success_count": sum(1 for l in logs if l.get('success')),
            "error_count": sum(1 for l in logs if not l.get('success')),
            "total_tokens": sum(l.get('tokens_used', 0) for l in logs),
            "total_cost": sum(l.get('api_cost', 0) for l in logs),
            "by_action": {},
            "by_user": {},
            "by_level": {}
        }
        
        for log in logs:
            # 按動作統計
            action = log.get('action', 'unknown')
            stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
            
            # 按用戶統計
            username = log.get('username', 'anonymous')
            stats["by_user"][username] = stats["by_user"].get(username, 0) + 1
            
            # 按級別統計
            level = log.get('level', 'info')
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
        
        return stats
    
    def cleanup_old_logs(self) -> int:
        """清理過期日誌"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        deleted_count = 0
        
        for log_file in self.data_dir.glob("audit_*.jsonl"):
            try:
                # 從文件名提取日期
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"🗑️ 刪除過期日誌: {log_file.name}")
            except Exception as e:
                logger.error(f"❌ 清理日誌失敗: {e}")
        
        return deleted_count


# 全域實例
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """獲取審計服務實例"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
