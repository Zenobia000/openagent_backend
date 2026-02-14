"""Cognitive metrics collection.

Tracks request count, latency, success rate per cognitive level.
Controlled by feature flag `metrics.cognitive_metrics`.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class _LevelMetrics:
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return round(self.total_latency_ms / self.request_count, 2) if self.request_count else 0.0

    @property
    def success_rate(self) -> float:
        return round(self.success_count / self.request_count, 4) if self.request_count else 0.0


class CognitiveMetrics:
    """Per-cognitive-level request metrics."""

    def __init__(self):
        self._levels: Dict[str, _LevelMetrics] = {
            "system1": _LevelMetrics(),
            "system2": _LevelMetrics(),
            "agent": _LevelMetrics(),
        }
        # MCP extension metrics
        self._mcp_calls: int = 0
        self._mcp_errors: int = 0
        self._mcp_total_latency: float = 0.0
        # A2A extension metrics
        self._a2a_sent: int = 0
        self._a2a_completed: int = 0
        self._a2a_failed: int = 0
        self._a2a_total_latency: float = 0.0

    def record_request(
        self,
        cognitive_level: str,
        latency_ms: float,
        tokens: int = 0,
        success: bool = True,
    ) -> None:
        """Record a completed request."""
        m = self._levels.get(cognitive_level)
        if m is None:
            return
        m.request_count += 1
        m.total_latency_ms += latency_ms
        m.total_tokens += tokens
        if success:
            m.success_count += 1
        else:
            m.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Return metrics for all cognitive levels."""
        result = {}
        total_requests = 0
        for level, m in self._levels.items():
            total_requests += m.request_count
            result[level] = {
                "request_count": m.request_count,
                "avg_latency_ms": m.avg_latency_ms,
                "success_rate": m.success_rate,
                "total_tokens": m.total_tokens,
            }
        result["total_requests"] = total_requests
        return result

    # ── MCP / A2A extension metrics ──

    def record_mcp_call(self, latency_ms: float, success: bool = True) -> None:
        """Record an MCP tool call."""
        self._mcp_calls += 1
        self._mcp_total_latency += latency_ms
        if not success:
            self._mcp_errors += 1

    def record_a2a_task(self, latency_ms: float, success: bool = True) -> None:
        """Record an A2A task delegation."""
        self._a2a_sent += 1
        self._a2a_total_latency += latency_ms
        if success:
            self._a2a_completed += 1
        else:
            self._a2a_failed += 1

    def get_extension_metrics(self) -> Dict[str, Any]:
        """Return MCP/A2A metrics."""
        return {
            "mcp": {
                "tool_calls": self._mcp_calls,
                "tool_errors": self._mcp_errors,
                "avg_latency_ms": round(self._mcp_total_latency / self._mcp_calls, 2) if self._mcp_calls else 0.0,
            },
            "a2a": {
                "tasks_sent": self._a2a_sent,
                "tasks_completed": self._a2a_completed,
                "tasks_failed": self._a2a_failed,
                "avg_latency_ms": round(self._a2a_total_latency / self._a2a_sent, 2) if self._a2a_sent else 0.0,
            },
        }

    def reset(self) -> None:
        """Clear all metrics."""
        for m in self._levels.values():
            m.request_count = 0
            m.success_count = 0
            m.error_count = 0
            m.total_latency_ms = 0.0
            m.total_tokens = 0
        self._mcp_calls = 0
        self._mcp_errors = 0
        self._mcp_total_latency = 0.0
        self._a2a_sent = 0
        self._a2a_completed = 0
        self._a2a_failed = 0
        self._a2a_total_latency = 0.0
