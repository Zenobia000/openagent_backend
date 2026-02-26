"""
QuitCode Platform 測試套件
"""

import sys
from pathlib import Path

# 將 src 添加到 Python 路徑
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))