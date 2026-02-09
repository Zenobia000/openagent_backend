"""輔助函數"""
from pathlib import Path
from typing import Dict, Any

def load_env_file(env_path: Path) -> Dict[str, str]:
    """載入環境變數文件"""
    env_vars = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value.strip('"')
    return env_vars

def format_bytes(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"
