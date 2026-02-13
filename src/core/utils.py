"""
Core utilities
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def get_project_root() -> Path:
    """取得專案根目錄"""
    current = Path(__file__).parent
    while current != current.parent:
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path(__file__).parent.parent.parent


def load_env():
    """載入環境變數"""
    project_root = get_project_root()
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
        return True
    return False


__all__ = ["get_project_root", "load_env"]