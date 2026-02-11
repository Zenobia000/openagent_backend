"""Cognitive metrics collection.

Tracks request count, latency, success rate per cognitive level.
Controlled by feature flag `metrics.cognitive_metrics`.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import CognitiveLevel


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
            CognitiveLevel.SYSTEM1: _LevelMetrics(),
            CognitiveLevel.SYSTEM2: _LevelMetrics(),
            CognitiveLevel.AGENT: _LevelMetrics(),
        }

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

    def reset(self) -> None:
        """Clear all metrics."""
        for m in self._levels.values():
            m.request_count = 0
            m.success_count = 0
            m.error_count = 0
            m.total_latency_ms = 0.0
            m.total_tokens = 0
