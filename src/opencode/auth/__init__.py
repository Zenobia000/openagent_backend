"""
認證模組
"""

from .models import (
    User, UserCreate, UserLogin, UserUpdate, UserResponse,
    UserRole, UserStatus, Token, TokenData
)
from .jwt import (
    hash_password, verify_password, create_access_token, decode_token,
    get_current_user, get_current_user_optional, require_role,
    require_admin, require_editor, require_viewer
)
from .service import UserService, get_user_service
from .routes import router as auth_router

__all__ = [
    # Models
    "User", "UserCreate", "UserLogin", "UserUpdate", "UserResponse",
    "UserRole", "UserStatus", "Token", "TokenData",
    # JWT
    "hash_password", "verify_password", "create_access_token", "decode_token",
    "get_current_user", "get_current_user_optional", "require_role",
    "require_admin", "require_editor", "require_viewer",
    # Service
    "UserService", "get_user_service",
    # Router
    "auth_router"
]
