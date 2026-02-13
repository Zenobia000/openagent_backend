"""JWT token encoding/decoding using python-jose."""

import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

# Config from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class TokenData(BaseModel):
    """Decoded token payload."""
    user_id: str
    username: str
    role: UserRole = UserRole.USER
    exp: Optional[datetime] = None


def encode_token(
    user_id: str,
    username: str,
    role: UserRole = UserRole.USER,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT token."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token. Returns None on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(
            user_id=payload["sub"],
            username=payload["username"],
            role=UserRole(payload.get("role", "user")),
            exp=datetime.utcfromtimestamp(payload["exp"]) if "exp" in payload else None,
        )
    except (JWTError, KeyError, ValueError):
        return None
