"""
成本追蹤 API 路由
"""

import logging
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query

from opencode.auth import get_current_user, require_admin, TokenData
from .service import get_cost_service, CostTrackingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost", tags=["成本追蹤"])


@router.get("/dashboard")
async def get_dashboard(
    current_user: TokenData = Depends(require_admin),
    cost_service: CostTrackingService = Depends(get_cost_service)
):
    """獲取成本儀表板數據（僅管理員）"""
    return cost_service.get_dashboard_data()


@router.get("/daily")
async def get_daily_usage(
    date_str: Optional[str] = Query(None, description="日期 (YYYY-MM-DD)，預設今天"),
    current_user: TokenData = Depends(require_admin),
    cost_service: CostTrackingService = Depends(get_cost_service)
):
    """獲取每日使用量（僅管理員）"""
    if date_str:
        date_obj = date.fromisoformat(date_str)
    else:
        date_obj = date.today()
    
    usage = cost_service.get_daily_usage(date_obj)
    # 不返回詳細記錄，減少回應大小
    usage.pop("records", None)
    return usage


@router.get("/monthly")
async def get_monthly_usage(
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, ge=1, le=12, description="月份"),
    current_user: TokenData = Depends(require_admin),
    cost_service: CostTrackingService = Depends(get_cost_service)
):
    """獲取每月使用量（僅管理員）"""
    return cost_service.get_monthly_usage(year, month)


@router.get("/user/{user_id}")
async def get_user_usage(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="查詢天數"),
    current_user: TokenData = Depends(require_admin),
    cost_service: CostTrackingService = Depends(get_cost_service)
):
    """獲取用戶使用量（僅管理員）"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return cost_service.get_user_usage(user_id, start_date, end_date)


@router.get("/my-usage")
async def get_my_usage(
    days: int = Query(30, ge=1, le=365, description="查詢天數"),
    current_user: TokenData = Depends(get_current_user),
    cost_service: CostTrackingService = Depends(get_cost_service)
):
    """獲取當前用戶的使用量"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return cost_service.get_user_usage(current_user.user_id, start_date, end_date)
