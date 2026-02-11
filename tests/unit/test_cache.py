"""Unit tests for ResponseCache."""

import time
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.cache import ResponseCache


class TestCacheBasics:
    def test_put_and_get(self):
        c = ResponseCache()
        c.put("hello", "chat", "world")
        assert c.get("hello", "chat") == "world"

    def test_miss_returns_none(self):
        c = ResponseCache()
        assert c.get("missing", "chat") is None

    def test_different_modes_are_separate(self):
        c = ResponseCache()
        c.put("hello", "chat", "chat-result")
        c.put("hello", "search", "search-result")
        assert c.get("hello", "chat") == "chat-result"
        assert c.get("hello", "search") == "search-result"

    def test_case_insensitive_query(self):
        c = ResponseCache()
        c.put("Hello World", "chat", "result")
        assert c.get("hello world", "chat") == "result"

    def test_whitespace_trimmed(self):
        c = ResponseCache()
        c.put("  hello  ", "chat", "result")
        assert c.get("hello", "chat") == "result"


class TestCacheTTL:
    def test_expired_entry_returns_none(self):
        c = ResponseCache(ttl=0)  # immediate expiry
        c.put("hello", "chat", "world")
        time.sleep(0.01)
        assert c.get("hello", "chat") is None

    def test_non_expired_entry_returns_value(self):
        c = ResponseCache(ttl=60)
        c.put("hello", "chat", "world")
        assert c.get("hello", "chat") == "world"


class TestCacheEviction:
    def test_evicts_oldest_when_full(self):
        c = ResponseCache(max_size=2)
        c.put("q1", "chat", "r1")
        c.put("q2", "chat", "r2")
        c.put("q3", "chat", "r3")  # should evict q1
        assert c.get("q1", "chat") is None
        assert c.get("q2", "chat") == "r2"
        assert c.get("q3", "chat") == "r3"


class TestCacheInvalidate:
    def test_invalidate_existing(self):
        c = ResponseCache()
        c.put("hello", "chat", "world")
        assert c.invalidate("hello", "chat") is True
        assert c.get("hello", "chat") is None

    def test_invalidate_nonexistent(self):
        c = ResponseCache()
        assert c.invalidate("missing", "chat") is False


class TestCacheClear:
    def test_clear_empties_cache(self):
        c = ResponseCache()
        c.put("q1", "chat", "r1")
        c.put("q2", "chat", "r2")
        c.clear()
        assert c.get("q1", "chat") is None
        assert c.get("q2", "chat") is None


class TestCacheStats:
    def test_stats_initial(self):
        c = ResponseCache()
        s = c.stats
        assert s["size"] == 0
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["hit_rate"] == 0.0

    def test_stats_after_operations(self):
        c = ResponseCache()
        c.put("q1", "chat", "r1")
        c.get("q1", "chat")  # hit
        c.get("q1", "chat")  # hit
        c.get("q2", "chat")  # miss
        s = c.stats
        assert s["size"] == 1
        assert s["hits"] == 2
        assert s["misses"] == 1
        assert s["hit_rate"] == pytest.approx(2 / 3, abs=0.01)
