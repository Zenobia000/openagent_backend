"""
File system as agent memory — no Vector DB needed.

Manus Principle 3: "The file system is the most underrated form of context.
It's unlimited, persistent, and agent-manipulable."

Implementation deferred to Phase 2.
"""

import json
from pathlib import Path
from typing import Optional

from ..feature_flags import FeatureFlags, feature_flags as default_flags


class FileBasedMemory:
    """File-based persistent memory. Agent reads/writes its own memory."""

    def __init__(
        self,
        workspace_dir: str = ".agent_workspace",
        feature_flags: Optional[FeatureFlags] = None,
    ):
        self._flags = feature_flags or default_flags
        self._workspace = Path(workspace_dir)
        self._workspace.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: str) -> str:
        """Save content to workspace file."""
        filepath = self._workspace / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def load(self, filename: str) -> str:
        """Load content from workspace file."""
        filepath = self._workspace / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return ""

    def append_log(self, filename: str, entry: dict):
        """Append to JSONL log (append-only)."""
        filepath = self._workspace / filename
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_files(self, pattern: str = "*") -> list[str]:
        """List files in workspace."""
        return [str(p.relative_to(self._workspace)) for p in self._workspace.glob(pattern)]
