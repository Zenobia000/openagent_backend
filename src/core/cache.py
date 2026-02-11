"""Response cache for System 1 processors.

Hash-based in-memory cache with TTL eviction.
Controlled by feature flag `system1.enable_cache`.
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    value: str
    created_at: float
    hit_count: int = 0


class ResponseCache:
    """Simple in-memory cache keyed on query hash."""

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        self._ttl = ttl
        self._max_size = max_size
        self._store: Dict[str, CacheEntry] = {}
        # Metrics
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash_key(query: str, mode: str) -> str:
        raw = f"{mode}:{query.strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, query: str, mode: str) -> Optional[str]:
        """Look up a cached response. Returns None on miss."""
        key = self._hash_key(query, mode)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if time.time() - entry.created_at > self._ttl:
            del self._store[key]
            self._misses += 1
            return None
        entry.hit_count += 1
        self._hits += 1
        return entry.value

    def put(self, query: str, mode: str, value: str) -> None:
        """Store a response in the cache."""
        if len(self._store) >= self._max_size:
            self._evict_oldest()
        key = self._hash_key(query, mode)
        self._store[key] = CacheEntry(value=value, created_at=time.time())

    def invalidate(self, query: str, mode: str) -> bool:
        """Remove a specific entry. Returns True if it existed."""
        key = self._hash_key(query, mode)
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        self._store.clear()

    def _evict_oldest(self) -> None:
        """Remove the oldest entry to make room."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].created_at)
        del self._store[oldest_key]

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
        }
