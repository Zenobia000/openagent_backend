"""Tests for TemplateRandomizer — structural noise (Manus Principle 6)."""

from core.context.template_randomizer import TemplateRandomizer


class TestTemplateRandomizer:
    def test_wraps_instruction(self):
        """Should wrap instruction in a template."""
        tr = TemplateRandomizer()
        result = tr.wrap_instruction("Write hello world")
        assert "hello world" in result.lower()

    def test_preserves_instruction_content(self):
        """The original instruction must appear in the output."""
        tr = TemplateRandomizer()
        instruction = "Calculate the Fibonacci sequence"
        result = tr.wrap_instruction(instruction)
        assert instruction in result

    def test_varies_output(self):
        """Multiple calls should produce different wrappers (probabilistic)."""
        tr = TemplateRandomizer()
        results = set()
        for _ in range(50):
            results.add(tr.wrap_instruction("test"))
        # With 4 wrappers * 4 suffixes = 16 combinations,
        # 50 tries should hit at least 2 distinct results
        assert len(results) > 1

    def test_never_empty(self):
        """Output should never be empty."""
        tr = TemplateRandomizer()
        for _ in range(20):
            result = tr.wrap_instruction("test")
            assert len(result.strip()) > 0
