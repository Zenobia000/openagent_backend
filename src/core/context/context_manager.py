"""
Append-only context manager. KV-Cache friendly.

Manus Principle 1: "Cached tokens are 10x cheaper. Protect the prefix."

Rules:
1. NEVER modify existing entries
2. NEVER delete entries
3. All compression is reversible (write to file, keep reference)
4. System prompt + tool definitions are STABLE prefix
"""

import json
from pathlib import Path
from typing import Optional

from .models import ContextEntry
from ..feature_flags import FeatureFlags, feature_flags as default_flags


class ContextManager:
    """Append-only context manager."""

    def __init__(self, feature_flags: Optional[FeatureFlags] = None):
        self._flags = feature_flags or default_flags
        self._entries: list[ContextEntry] = []

    def append(self, entry: ContextEntry):
        """Append entry. This is the ONLY mutation operation."""
        self._entries.append(entry)

    def append_user(self, content: str):
        """Convenience: append user message."""
        self.append(ContextEntry(role="user", content=content))

    def append_assistant(self, content: str):
        """Convenience: append assistant message."""
        self.append(ContextEntry(role="assistant", content=content))

    def append_error(self, content: str, original_query: str = ""):
        """Convenience: append error (preserved, not hidden)."""
        self.append(ContextEntry(
            role="assistant",
            content=content,
            metadata={"is_error": True, "original_query": original_query},
        ))

    def get_messages(self) -> list[dict[str, str]]:
        """Get context as LLM message list. Read-only."""
        return [e.to_message() for e in self._entries]

    def get_entries(self) -> list[ContextEntry]:
        """Get raw entries. Read-only copy."""
        return list(self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def compress_to_file(self, filepath: str, keep_last: int = 0):
        """Reversible compression: save old entries to file, keep reference.

        The agent can always read the file to recover compressed context.
        This is the ONLY way to "remove" entries — and it's reversible.
        """
        if keep_last <= 0:
            keep_last = self._flags.get_value(
                "context_engineering.compress_keep_last", 10
            )

        if len(self._entries) <= keep_last:
            return

        old_entries = self._entries[:-keep_last]
        kept_entries = self._entries[-keep_last:]

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {"role": e.role, "content": e.content, "timestamp": str(e.timestamp)}
                    for e in old_entries
                ],
                f,
                ensure_ascii=False,
                indent=2,
            )

        self._entries = [
            ContextEntry(
                role="system",
                content=(
                    f"[Previous {len(old_entries)} messages compressed to {filepath}. "
                    f"Read this file if you need earlier context.]"
                ),
            ),
            *kept_entries,
        ]

    def reset(self):
        """Reset for new request. The ONLY destructive operation."""
        self._entries.clear()
