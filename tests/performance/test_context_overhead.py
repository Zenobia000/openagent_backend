"""
Performance tests for Context Engineering.

Verifies that CE components add <50ms overhead per operation.
"""

import time
import pytest
from core.context.context_manager import ContextManager
from core.context.todo_recitation import TodoRecitation
from core.context.error_preservation import ErrorPreservation
from core.context.template_randomizer import TemplateRandomizer
from core.context.file_memory import FileBasedMemory
from core.routing.tool_mask import ToolAvailabilityMask


class TestContextEngineeringOverhead:
    """Performance benchmarks for all CE components."""

    def test_context_manager_append_overhead(self):
        """1000 appends should complete in <50ms."""
        cm = ContextManager()
        start = time.time()
        for i in range(1000):
            cm.append_user(f"message {i}")
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 50, f"1000 appends took {elapsed_ms:.1f}ms (limit: 50ms)"

    def test_context_manager_get_messages_overhead(self):
        """get_messages on 1000 entries should complete in <10ms."""
        cm = ContextManager()
        for i in range(1000):
            cm.append_user(f"message {i}")

        start = time.time()
        for _ in range(100):
            cm.get_messages()
        elapsed_ms = (time.time() - start) * 1000
        per_call = elapsed_ms / 100
        assert per_call < 10, f"get_messages took {per_call:.1f}ms (limit: 10ms)"

    def test_todo_recitation_overhead(self):
        """Full todo cycle should complete in <1ms."""
        tr = TodoRecitation()
        start = time.time()
        for _ in range(1000):
            tr.create_initial_plan("test query", "chat")
            tr.build_recitation_prefix()
            tr.update_from_output("- [x] Done\n- [ ] Next")
            tr.reset()
        elapsed_ms = (time.time() - start) * 1000
        per_cycle = elapsed_ms / 1000
        assert per_cycle < 1, f"Todo cycle took {per_cycle:.2f}ms (limit: 1ms)"

    def test_error_preservation_overhead(self):
        """Retry prompt building should complete in <1ms."""
        start = time.time()
        for _ in range(1000):
            ErrorPreservation.build_retry_prompt("query", "failed result", "error")
            ErrorPreservation.should_retry("short", max_retries=1, current_retry=0)
        elapsed_ms = (time.time() - start) * 1000
        per_call = elapsed_ms / 1000
        assert per_call < 1, f"Error preservation took {per_call:.2f}ms (limit: 1ms)"

    def test_tool_mask_overhead(self):
        """Tool masking should complete in <1ms."""
        mask = ToolAvailabilityMask()
        tools = [{"name": f"tool_{i}"} for i in range(20)]

        start = time.time()
        for _ in range(1000):
            mask.get_allowed_tools("code")
            mask.apply_mask("code", tools)
        elapsed_ms = (time.time() - start) * 1000
        per_call = elapsed_ms / 1000
        assert per_call < 1, f"Tool mask took {per_call:.2f}ms (limit: 1ms)"

    def test_template_randomizer_overhead(self):
        """Template randomization should complete in <1ms."""
        tr = TemplateRandomizer()
        start = time.time()
        for _ in range(1000):
            tr.wrap_instruction("test instruction")
        elapsed_ms = (time.time() - start) * 1000
        per_call = elapsed_ms / 1000
        assert per_call < 1, f"Randomizer took {per_call:.2f}ms (limit: 1ms)"

    def test_file_memory_overhead(self, tmp_path):
        """File I/O should complete in <5ms per operation."""
        mem = FileBasedMemory(workspace_dir=str(tmp_path))

        start = time.time()
        for i in range(100):
            mem.save(f"file_{i}.txt", f"content {i}")
        save_ms = (time.time() - start) * 1000
        per_save = save_ms / 100

        start = time.time()
        for i in range(100):
            mem.load(f"file_{i}.txt")
        load_ms = (time.time() - start) * 1000
        per_load = load_ms / 100

        assert per_save < 5, f"Save took {per_save:.1f}ms (limit: 5ms)"
        assert per_load < 5, f"Load took {per_load:.1f}ms (limit: 5ms)"

    def test_combined_overhead_per_request(self):
        """Full CE pipeline overhead per request should be <50ms."""
        cm = ContextManager()
        tr = TodoRecitation()
        tmpl = TemplateRandomizer()
        mask = ToolAvailabilityMask()

        start = time.time()
        for _ in range(100):
            # Simulate one request through the CE pipeline
            cm.reset()
            cm.append_user("test query")
            tr.reset()
            tr.create_initial_plan("test query", "chat")
            prefix = tr.build_recitation_prefix()
            wrapped = tmpl.wrap_instruction("test query")
            allowed = mask.get_allowed_tools("chat")
            cm.append_assistant("test response")
            tr.update_from_output("- [x] Done")
            ErrorPreservation.should_retry("test response")
        elapsed_ms = (time.time() - start) * 1000
        per_request = elapsed_ms / 100

        assert per_request < 50, f"Full pipeline took {per_request:.1f}ms (limit: 50ms)"
