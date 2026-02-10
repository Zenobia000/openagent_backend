"""
Pytest 配置和共用 fixtures
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def async_mock():
    """提供 AsyncMock 工具"""
    return AsyncMock


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """自動設置測試環境"""
    # 設置測試環境變數
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def test_data_dir():
    """測試數據目錄"""
    return Path(__file__).parent / "test_data"


# 配置 pytest-asyncio
pytest_plugins = ('pytest_asyncio',)