"""緩存工具"""
from typing import Any, Optional
from config import PERFORMANCE

class Cache:
    """簡單的內存緩存"""

    def __init__(self):
        self._cache = {}
        self.enabled = PERFORMANCE["cache_enabled"]
        self.ttl = PERFORMANCE["cache_ttl"]

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        return self._cache.get(key)

    def set(self, key: str, value: Any):
        if self.enabled:
            self._cache[key] = value

cache = Cache()
