"""Authentication module - JWT token handling and FastAPI dependencies."""

from .jwt import encode_token, decode_token, TokenData, UserRole
from .dependencies import get_current_user, get_optional_user

__all__ = [
    "encode_token",
    "decode_token",
    "TokenData",
    "UserRole",
    "get_current_user",
    "get_optional_user",
]
