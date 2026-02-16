"""Tests for ContextManager — append-only context (Manus Principle 1)."""

import json
import pytest
from pathlib import Path

from core.context.models import ContextEntry
from core.context.context_manager import ContextManager


class TestContextManager:
    def test_append_only(self):
        """Context entries can only be appended, never modified."""
        cm = ContextManager()
        cm.append_user("hello")
        cm.append_assistant("world")

        messages = cm.get_messages()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "hello"}
        assert messages[1] == {"role": "assistant", "content": "world"}

    def test_entry_count(self):
        """entry_count tracks the number of entries."""
        cm = ContextManager()
        assert cm.entry_count == 0
        cm.append_user("msg1")
        assert cm.entry_count == 1
        cm.append_assistant("msg2")
        assert cm.entry_count == 2

    def test_no_mutation_on_frozen_entry(self):
        """ContextEntry is frozen — cannot be modified after creation."""
        entry = ContextEntry(role="user", content="original")
        with pytest.raises(AttributeError):
            entry.content = "modified"

    def test_get_entries_returns_copy(self):
        """get_entries returns a copy, not a reference."""
        cm = ContextManager()
        cm.append_user("test")
        entries = cm.get_entries()
        entries.clear()
        assert cm.entry_count == 1  # original unaffected

    def test_append_error_preserves_metadata(self):
        """Errors are appended with is_error metadata."""
        cm = ContextManager()
        cm.append_user("question")
        cm.append_error("failed answer", original_query="question")

        entries = cm.get_entries()
        assert len(entries) == 2
        assert entries[1].metadata.get("is_error") is True
        assert entries[1].metadata.get("original_query") == "question"

    def test_compress_to_file_is_reversible(self, tmp_path):
        """Compression writes to file and keeps reference."""
        cm = ContextManager()
        for i in range(20):
            cm.append_user(f"message {i}")

        filepath = str(tmp_path / "compressed.json")
        cm.compress_to_file(filepath, keep_last=5)

        # File was written
        assert Path(filepath).exists()
        data = json.loads(Path(filepath).read_text())
        assert len(data) == 15  # 20 - 5

        # Reference exists in context
        messages = cm.get_messages()
        assert any("compressed" in m["content"].lower() for m in messages)

        # 1 reference + 5 kept
        assert cm.entry_count == 6

    def test_compress_noop_when_too_few(self):
        """Compression does nothing when entries <= keep_last."""
        cm = ContextManager()
        cm.append_user("only one")
        cm.compress_to_file("/tmp/should_not_exist.json", keep_last=5)
        assert cm.entry_count == 1

    def test_reset_clears_all(self):
        """Reset clears all entries."""
        cm = ContextManager()
        cm.append_user("msg")
        cm.append_assistant("reply")
        cm.reset()
        assert cm.entry_count == 0
        assert cm.get_messages() == []

    def test_append_raw_entry(self):
        """Can append a raw ContextEntry."""
        cm = ContextManager()
        entry = ContextEntry(role="system", content="system prompt")
        cm.append(entry)
        assert cm.entry_count == 1
        assert cm.get_messages()[0]["role"] == "system"
