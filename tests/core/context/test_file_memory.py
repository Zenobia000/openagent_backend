"""Tests for FileBasedMemory — file system as context (Manus Principle 3)."""

import json
from core.context.file_memory import FileBasedMemory


class TestFileBasedMemory:
    def test_save_and_load(self, tmp_path):
        """Basic save and load."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))
        mem.save("test.md", "hello world")
        assert mem.load("test.md") == "hello world"

    def test_load_nonexistent_returns_empty(self, tmp_path):
        """Loading non-existent file returns empty string."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))
        assert mem.load("nonexistent.md") == ""

    def test_save_creates_subdirectories(self, tmp_path):
        """Save creates parent directories automatically."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))
        mem.save("sub/dir/file.txt", "nested content")
        assert mem.load("sub/dir/file.txt") == "nested content"

    def test_append_log_is_append_only(self, tmp_path):
        """JSONL log is append-only."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))
        mem.append_log("history.jsonl", {"query": "q1"})
        mem.append_log("history.jsonl", {"query": "q2"})

        content = (tmp_path / "history.jsonl").read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["query"] == "q1"
        assert json.loads(lines[1])["query"] == "q2"

    def test_list_files(self, tmp_path):
        """list_files returns files matching pattern."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))
        mem.save("a.md", "a")
        mem.save("b.md", "b")
        mem.save("c.txt", "c")

        md_files = mem.list_files("*.md")
        assert len(md_files) == 2
        assert "a.md" in md_files
        assert "b.md" in md_files

    def test_list_files_all(self, tmp_path):
        """list_files with * returns all files."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))
        mem.save("a.md", "a")
        mem.save("b.txt", "b")

        all_files = mem.list_files("*")
        assert len(all_files) == 2

    def test_overwrite_existing(self, tmp_path):
        """Saving to same file overwrites content."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))
        mem.save("test.md", "version 1")
        mem.save("test.md", "version 2")
        assert mem.load("test.md") == "version 2"
