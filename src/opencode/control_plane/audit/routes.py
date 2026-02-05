"""
審計日誌 API 路由
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query

from opencode.auth import get_current_user, require_admin, TokenData
from .service import get_audit_service, AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["審計日誌"])


@router.get("/logs")
async def get_audit_logs(
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    username: Optional[str] = Query(None, description="用戶名"),
    action: Optional[str] = Query(None, description="動作類型"),
    level: Optional[str] = Query(None, description="日誌級別"),
    success: Optional[bool] = Query(None, description="是否成功"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    查詢審計日誌（僅管理員）
    """
    # 解析日期
    start = None
    end = None
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    
    logs = audit_service.query(
        start_date=start,
        end_date=end,
        user_id=user_id,
        username=username,
        action=action,
        level=level,
        success=success,
        limit=limit,
        offset=offset
    )
    
    return {
        "logs": logs,
        "count": len(logs),
        "limit": limit,
        "offset": offset
    }


@router.get("/recent")
async def get_recent_logs(
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service)
):
    """獲取最近的日誌（僅管理員）"""
    logs = audit_service.get_recent(limit)
    return {
        "logs": logs,
        "count": len(logs)
    }


@router.get("/stats")
async def get_audit_stats(
    days: int = Query(7, ge=1, le=90, description="統計天數"),
    current_user: TokenData = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service)
):
    """獲取審計統計（僅管理員）"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    stats = audit_service.get_stats(start_date=start_date, end_date=end_date)
    stats["period_days"] = days
    stats["start_date"] = start_date.isoformat()
    stats["end_date"] = end_date.isoformat()
    
    return stats


@router.get("/my-logs")
async def get_my_logs(
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """獲取當前用戶的日誌"""
    logs = audit_service.query(
        user_id=current_user.user_id,
        limit=limit
    )
    return {
        "logs": logs,
        "count": len(logs)
    }


@router.post("/cleanup")
async def cleanup_old_logs(
    current_user: TokenData = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service)
):
    """清理過期日誌（僅管理員）"""
    deleted_count = audit_service.cleanup_old_logs()
    return {
        "message": f"已清理 {deleted_count} 個過期日誌文件",
        "deleted_count": deleted_count
    }
