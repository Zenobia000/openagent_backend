"""Unit tests for CognitiveMetrics."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.metrics import CognitiveMetrics


class TestCognitiveMetrics:
    def test_initial_summary_all_zero(self):
        m = CognitiveMetrics()
        s = m.get_summary()
        assert s["total_requests"] == 0
        for level in ("system1", "system2", "agent"):
            assert s[level]["request_count"] == 0

    def test_record_request(self):
        m = CognitiveMetrics()
        m.record_request("system1", latency_ms=50, tokens=100)
        s = m.get_summary()
        assert s["system1"]["request_count"] == 1
        assert s["system1"]["avg_latency_ms"] == 50
        assert s["system1"]["success_rate"] == 1.0
        assert s["total_requests"] == 1

    def test_record_failure(self):
        m = CognitiveMetrics()
        m.record_request("system2", latency_ms=200, success=False)
        s = m.get_summary()
        assert s["system2"]["success_rate"] == 0.0
        assert s["system2"]["request_count"] == 1

    def test_mixed_success_failure(self):
        m = CognitiveMetrics()
        m.record_request("agent", latency_ms=100, success=True)
        m.record_request("agent", latency_ms=200, success=True)
        m.record_request("agent", latency_ms=300, success=False)
        s = m.get_summary()
        assert s["agent"]["request_count"] == 3
        assert s["agent"]["success_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert s["agent"]["avg_latency_ms"] == 200

    def test_multiple_levels(self):
        m = CognitiveMetrics()
        m.record_request("system1", latency_ms=10)
        m.record_request("system2", latency_ms=100)
        m.record_request("agent", latency_ms=500)
        s = m.get_summary()
        assert s["total_requests"] == 3

    def test_unknown_level_ignored(self):
        m = CognitiveMetrics()
        m.record_request("nonexistent_level", latency_ms=10)
        s = m.get_summary()
        assert s["total_requests"] == 0

    def test_reset(self):
        m = CognitiveMetrics()
        m.record_request("system1", latency_ms=50)
        m.reset()
        s = m.get_summary()
        assert s["total_requests"] == 0

    def test_token_tracking(self):
        m = CognitiveMetrics()
        m.record_request("system1", latency_ms=10, tokens=500)
        m.record_request("system1", latency_ms=20, tokens=300)
        s = m.get_summary()
        assert s["system1"]["total_tokens"] == 800
