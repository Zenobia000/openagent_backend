"""
認證 API 路由
"""

import logging
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends

from .models import (
    UserCreate, UserLogin, UserUpdate, UserResponse, Token, UserRole
)
from .jwt import (
    create_access_token, get_current_user, require_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES, TokenData
)
from .service import get_user_service, UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["認證"])


@router.post("/register", response_model=UserResponse)
async def register(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    註冊新用戶
    
    預設角色為 viewer，管理員可以之後修改
    """
    try:
        # 強制新用戶為 viewer（除非是第一個用戶）
        if len(user_service.list_users()) > 0:
            user_create.role = UserRole.VIEWER
        
        user = user_service.create_user(user_create)
        return user_service.to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    """
    用戶登入
    
    返回 JWT Token
    """
    user = user_service.authenticate(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶名或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 更新最後登入時間
    user_service.update_last_login(user.id)
    
    # 創建 token
    access_token, expire = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )
    
    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_service.to_response(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """獲取當前用戶資訊"""
    user = user_service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return user_service.to_response(user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update: UserUpdate,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """更新當前用戶資訊（不能修改角色）"""
    # 普通用戶不能修改自己的角色和限制
    update.role = None
    update.status = None
    update.daily_query_limit = None
    update.daily_upload_limit = None
    
    user = user_service.update_user(current_user.user_id, update)
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return user_service.to_response(user)


# ========== 管理員 API ==========

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: TokenData = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """列出所有用戶（僅管理員）"""
    users = user_service.list_users()
    return [user_service.to_response(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: TokenData = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """獲取用戶詳情（僅管理員）"""
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return user_service.to_response(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update: UserUpdate,
    current_user: TokenData = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """更新用戶（僅管理員）"""
    user = user_service.update_user(user_id, update)
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return user_service.to_response(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: TokenData = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """刪除用戶（僅管理員）"""
    # 不能刪除自己
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="無法刪除自己")
    
    try:
        success = user_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="用戶不存在")
        return {"message": "用戶已刪除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users", response_model=UserResponse)
async def create_user_admin(
    user_create: UserCreate,
    current_user: TokenData = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """創建用戶（僅管理員，可指定角色）"""
    try:
        user = user_service.create_user(user_create)
        return user_service.to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
