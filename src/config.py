"""
Unified Configuration
統一配置文件
"""

import os
from pathlib import Path

# === 基本配置 ===
PROJECT_ROOT = Path(__file__).parent.parent
ENV = os.getenv("ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# === API 配置 ===
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", 8000)),
    "cors_origins": ["*"] if DEBUG else ["https://yourdomain.com"],
    "docs_enabled": DEBUG,
    "title": "OpenCode Platform API",
    "version": "1.0.0"
}

# === 服務配置 ===
SERVICES = {
    "knowledge": {
        "enabled": True,
        "provider": "qdrant",
        "host": os.getenv("QDRANT_HOST", "localhost"),
        "port": int(os.getenv("QDRANT_PORT", 6333))
    },
    "sandbox": {
        "enabled": True,
        "timeout": 30,
        "max_memory": "512M"
    },
    "search": {
        "enabled": True,
        "provider": os.getenv("SEARCH_PROVIDER", "duckduckgo"),
        "max_results": 10
    },
    "repo": {
        "enabled": True,
        "default_branch": "main",
        "max_file_size": "10M"
    }
}

# === Actor 系統配置 ===
ACTOR_CONFIG = {
    "thinker_pool_size": int(os.getenv("THINKER_POOL", 3)),
    "executor_pool_size": int(os.getenv("EXECUTOR_POOL", 5)),
    "max_thinking_depth": 10,
    "thinking_timeout": 30
}

# === 思考系統配置 ===
THINKING_CONFIG = {
    "max_depth": 10,
    "default_depth": 5,
    "enable_reflection": True,
    "enable_critique": True,
    "confidence_threshold": 0.85
}

# === 認證配置 ===
AUTH_CONFIG = {
    "jwt_secret": os.getenv("JWT_SECRET", "change-me-in-production"),
    "jwt_algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7
}

# === LLM 配置 ===
LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openai"),
    "model": os.getenv("LLM_MODEL", "gpt-4"),
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "temperature": float(os.getenv("LLM_TEMPERATURE", 0.7)),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", 4000))
}

# === 性能配置 ===
PERFORMANCE = {
    "cache_enabled": not DEBUG,
    "cache_ttl": 3600,
    "max_concurrent_requests": 100,
    "request_timeout": 60
}

# === 日誌配置 ===
LOGGING = {
    "level": "DEBUG" if DEBUG else "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}
