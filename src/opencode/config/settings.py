"""
配置管理 - 使用 Pydantic Settings
支援環境變數和配置檔案

環境變數說明:
- API_HOST, API_PORT: API 服務配置
- QDRANT_HOST, QDRANT_PORT: Qdrant 配置
- OPENAI_API_KEY: OpenAI API 密鑰
- COHERE_API_KEY: Cohere API 密鑰
- 詳見 .env.example
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os

# 使用統一的路徑工具
from opencode.core.utils import load_env
load_env()


class RedisSettings(BaseSettings):
    """Redis 配置"""
    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = 0
    password: Optional[str] = None
    
    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"
    
    class Config:
        populate_by_name = True


class QdrantSettings(BaseSettings):
    """Qdrant 配置"""
    host: str = Field(default="localhost", alias="QDRANT_HOST")
    port: int = Field(default=6333, alias="QDRANT_PORT")
    collection: str = Field(default="rag_knowledge_base", alias="QDRANT_COLLECTION")
    
    class Config:
        populate_by_name = True


class EmbeddingSettings(BaseSettings):
    """Embedding 配置"""
    provider: str = Field(default="cohere", alias="EMBEDDING_PROVIDER")
    cohere_model: str = Field(default="embed-multilingual-v3.0", alias="COHERE_EMBED_MODEL")
    openai_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBED_MODEL")
    
    class Config:
        populate_by_name = True


class OpenAISettings(BaseSettings):
    """OpenAI 配置"""
    api_key: str = Field(default="", alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o", alias="LLM_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBED_MODEL")
    temperature: float = 0.7
    max_tokens: int = 4096
    
    class Config:
        populate_by_name = True


class CohereSettings(BaseSettings):
    """Cohere 配置"""
    api_key: str = Field(default="", alias="COHERE_API_KEY")
    embed_model: str = Field(default="embed-multilingual-v3.0", alias="COHERE_EMBED_MODEL")
    
    class Config:
        populate_by_name = True


class SandboxSettings(BaseSettings):
    """沙箱配置"""
    docker_enabled: bool = False
    timeout: int = Field(default=30, alias="SANDBOX_TIMEOUT")
    memory_limit: str = "512m"
    cpu_limit: int = 50000
    working_dir: str = "/tmp/sandbox"
    
    class Config:
        populate_by_name = True


class AuthSettings(BaseSettings):
    """認證配置"""
    jwt_secret_key: str = Field(
        default="opencode-super-secret-key-change-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123", alias="ADMIN_PASSWORD")
    
    class Config:
        populate_by_name = True


class CostSettings(BaseSettings):
    """成本追蹤配置"""
    daily_budget: float = Field(default=10.0, alias="DAILY_BUDGET")
    monthly_budget: float = Field(default=100.0, alias="MONTHLY_BUDGET")
    
    class Config:
        populate_by_name = True


class AuditSettings(BaseSettings):
    """審計配置"""
    retention_days: int = Field(default=30, alias="AUDIT_RETENTION_DAYS")
    
    class Config:
        populate_by_name = True


class PolicySettings(BaseSettings):
    """策略配置"""
    default_risk_level: str = "medium"
    require_approval_tools: List[str] = ["execute_bash", "file_write", "git_push"]
    max_tool_calls_per_session: int = 50


class OpsSettings(BaseSettings):
    """運維配置"""
    enable_tracing: bool = True
    enable_cost_tracking: bool = True
    enable_audit_log: bool = True
    log_retention_days: int = 90


class Settings(BaseSettings):
    """
    主配置類
    
    所有配置都可以通過環境變數設定，例如:
    - API_PORT=8888
    - QDRANT_HOST=localhost
    - OPENAI_API_KEY=sk-xxx
    """
    
    # 應用設定
    app_name: str = "OpenCode Platform"
    version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # API 設定 - 直接從環境變數讀取
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8888, alias="API_PORT")
    api_workers: int = 1
    
    # 子配置
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    cohere: CohereSettings = Field(default_factory=CohereSettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    cost: CostSettings = Field(default_factory=CostSettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)
    policy: PolicySettings = Field(default_factory=PolicySettings)
    ops: OpsSettings = Field(default_factory=OpsSettings)
    
    # 服務設定
    enabled_services: List[str] = [
        "knowledge_base",
        "sandbox",
        "repo_ops",
        "web_search"
    ]
    
    # 插件設定
    plugins: List[str] = []
    
    class Config:
        populate_by_name = True
        extra = "ignore"


# 全域設定實例
settings = Settings()


def get_settings() -> Settings:
    """取得設定實例"""
    return settings


def reload_settings() -> Settings:
    """重新載入設定"""
    global settings
    settings = Settings()
    return settings

