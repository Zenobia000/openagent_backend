"""
Package Manifest — package.yaml 的 Pydantic 模型與載入邏輯
"""

import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, field_validator


class PackageManifest(BaseModel):
    """package.yaml 的結構定義"""
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    type: Literal["mcp-server", "a2a-agent"]
    # MCP server fields
    transport: Optional[str] = None  # "stdio" | "sse"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    # A2A agent fields
    port: Optional[int] = None
    auth_token: Optional[str] = None
    # Lifecycle
    auto_start: bool = True
    max_restarts: int = 3
    dependencies: List[str] = []
    tags: List[str] = []

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ("mcp-server", "a2a-agent"):
            raise ValueError(f"type must be 'mcp-server' or 'a2a-agent', got '{v}'")
        return v


class PackageStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"


class PackageInfo(BaseModel):
    manifest: PackageManifest
    path: Path
    status: PackageStatus = PackageStatus.STOPPED
    error: Optional[str] = None
    restart_count: int = 0

    model_config = {"arbitrary_types_allowed": True}


def _expand_env_vars(value: str) -> str:
    """展開 ${VAR_NAME} 格式的環境變數"""
    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return re.sub(r'\$\{(\w+)\}', replacer, value)


def _expand_config_env(data: Any) -> Any:
    """遞迴展開設定中的環境變數"""
    if isinstance(data, str):
        return _expand_env_vars(data)
    if isinstance(data, dict):
        return {k: _expand_config_env(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_config_env(item) for item in data]
    return data


def load_package_manifest(path: Path) -> PackageManifest:
    """從 package.yaml 載入並驗證 manifest

    Args:
        path: package.yaml 的路徑

    Returns:
        PackageManifest 實例

    Raises:
        FileNotFoundError: 檔案不存在
        ValueError: 格式錯誤
    """
    if not path.exists():
        raise FileNotFoundError(f"Package manifest not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    expanded = _expand_config_env(raw)
    return PackageManifest(**expanded)
