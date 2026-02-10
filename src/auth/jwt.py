"""
JWT 認證模組
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.utils import load_env
from .models import TokenData, UserRole

load_env()

logger = logging.getLogger(__name__)

# JWT 設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "opencode-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 預設 7 天 (7*24*60)

# Bearer Token 驗證
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """
    加密密碼（使用 SHA-256 + salt）
    兼容 Python 3.13
    """
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${password_hash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    try:
        if "$" not in hashed_password:
            # 舊格式（bcrypt），嘗試使用 passlib
            try:
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                return pwd_context.verify(plain_password, hashed_password)
            except Exception:
                return False
        
        # 新格式（SHA-256 + salt）
        salt, stored_hash = hashed_password.split("$", 1)
        password_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        return password_hash == stored_hash
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(
    user_id: str,
    username: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, datetime]:
    """
    創建 JWT Token
    
    Returns:
        (token, expire_time)
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def decode_token(token: str) -> Optional[TokenData]:
    """解碼 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))
        
        if user_id is None or username is None:
            return None
            
        return TokenData(
            user_id=user_id,
            username=username,
            role=UserRole(role),
            exp=exp
        )
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """
    獲取當前用戶（可選，未登入返回 None）
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    token_data = decode_token(token)
    return token_data


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    """
    獲取當前用戶（必須登入）
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無效的認證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        raise credentials_exception
    
    token = credentials.credentials
    token_data = decode_token(token)
    
    if token_data is None:
        raise credentials_exception
    
    # 檢查是否過期
    if token_data.exp < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已過期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


def require_role(allowed_roles: list[UserRole]):
    """
    角色權限裝飾器
    
    使用方式：
    @app.get("/admin")
    async def admin_route(user: TokenData = Depends(require_role([UserRole.ADMIN]))):
        ...
    """
    async def role_checker(
        user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"權限不足，需要角色: {[r.value for r in allowed_roles]}"
            )
        return user
    
    return role_checker


# 預定義的權限檢查
require_admin = require_role([UserRole.ADMIN])
require_editor = require_role([UserRole.ADMIN, UserRole.EDITOR])
require_viewer = require_role([UserRole.ADMIN, UserRole.EDITOR, UserRole.VIEWER])
