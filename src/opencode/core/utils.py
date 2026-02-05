"""
OpenCode Platform - 路徑和環境工具

提供統一的專案根目錄取得方法
"""

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """
    取得專案根目錄
    
    從當前檔案往上找，直到找到包含 pyproject.toml 的目錄
    """
    current = Path(__file__).resolve()
    
    # 往上找直到找到 pyproject.toml
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    
    # 如果找不到，使用 src 的父目錄
    # src/opencode/core/utils.py → src → opencode-platform
    return Path(__file__).resolve().parent.parent.parent.parent


def get_env_path() -> Path:
    """取得 .env 檔案路徑"""
    return get_project_root() / ".env"


def get_data_dir() -> Path:
    """取得資料目錄"""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_raw_dir() -> Path:
    """取得原始檔案目錄"""
    raw_dir = get_data_dir() / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


def load_env():
    """載入環境變數"""
    env_path = get_env_path()
    if env_path.exists():
        load_dotenv(env_path, override=True)
        return True
    return False


# 自動載入環境變數
load_env()


# 方便的全域變數
PROJECT_ROOT = get_project_root()
ENV_PATH = get_env_path()
DATA_DIR = get_data_dir()
RAW_DIR = get_raw_dir()
