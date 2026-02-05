"""
環境變數載入模組
確保從專案根目錄載入 .env 檔案

注意：此模組為向後兼容保留，實際功能已移至 utils.py
"""

import os

# 從 utils 導入所有功能
from opencode.core.utils import (
    get_project_root,
    get_env_path,
    load_env,
    PROJECT_ROOT,
    ENV_PATH,
)

# 向後兼容的別名
find_project_root = get_project_root
DOTENV_PATH = ENV_PATH


def get_openai_api_key() -> str:
    """取得 OpenAI API Key"""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise ValueError(
            f"OPENAI_API_KEY 未設置！\n"
            f"請確認 .env 檔案存在於: {DOTENV_PATH}\n"
            f"並包含: OPENAI_API_KEY=sk-proj-xxx"
        )
    return key


def ensure_env_loaded():
    """確保環境變數已載入（可重複呼叫）"""
    if not os.getenv("OPENAI_API_KEY"):
        load_env()
