"""
用戶模型 - 定義用戶資料結構
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
import uuid


class UserRole(str, Enum):
    """用戶角色"""
    ADMIN = "admin"          # 管理員 - 完整權限
    EDITOR = "editor"        # 編輯者 - 可上傳/編輯文件
    VIEWER = "viewer"        # 檢視者 - 只能查看和對話
    GUEST = "guest"          # 訪客 - 有限功能


class UserStatus(str, Enum):
    """用戶狀態"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(BaseModel):
    """用戶資料模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: Optional[str] = None
    hashed_password: str
    role: UserRole = UserRole.VIEWER
    status: UserStatus = UserStatus.ACTIVE
    
    # 配額限制
    daily_query_limit: int = 100       # 每日查詢限制
    daily_upload_limit: int = 10       # 每日上傳限制
    queries_today: int = 0
    uploads_today: int = 0
    last_reset_date: Optional[str] = None
    
    # 時間戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # 偏好設定
    preferences: dict = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class UserCreate(BaseModel):
    """創建用戶請求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.VIEWER


class UserLogin(BaseModel):
    """登入請求"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """更新用戶請求"""
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    daily_query_limit: Optional[int] = None
    daily_upload_limit: Optional[int] = None
    preferences: Optional[dict] = None


class UserResponse(BaseModel):
    """用戶回應（不含密碼）"""
    id: str
    username: str
    email: Optional[str]
    role: UserRole
    status: UserStatus
    daily_query_limit: int
    daily_upload_limit: int
    queries_today: int
    uploads_today: int
    created_at: datetime
    last_login: Optional[datetime]


class Token(BaseModel):
    """JWT Token 回應"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    """Token 內容"""
    user_id: str
    username: str
    role: UserRole
    exp: datetime
