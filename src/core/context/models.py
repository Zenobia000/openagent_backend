"""
Context data model - frozen, immutable entry for append-only context.

Manus Principle 1: KV-Cache friendly — once created, never modified.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ContextEntry:
    """Single entry in the append-only context.

    Frozen: once created, never modified.
    This ensures KV-Cache prefix stability.
    """
    role: str           # "system", "user", "assistant", "tool_result"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> dict[str, str]:
        """Convert to LLM message format."""
        return {"role": self.role, "content": self.content}
