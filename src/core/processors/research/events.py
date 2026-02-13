"""
Research Events - Event-driven architecture for streaming

Defines event types and SSE formatting for deep research processor.
Extracted from monolithic processor.py
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ResearchEvent:
    """研究事件"""
    type: str  # progress, message, reasoning, error, search_result
    step: str  # plan, search, synthesize
    data: Any
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_sse(self) -> str:
        """轉換為 SSE 格式"""
        event_data = {
            "type": self.type,
            "step": self.step,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
