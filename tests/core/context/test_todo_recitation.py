"""Tests for TodoRecitation — todo.md recitation pattern (Manus Principle 4)."""

from core.context.todo_recitation import TodoRecitation


class TestTodoRecitation:
    def test_creates_initial_plan(self):
        """Creates a plan from user query."""
        tr = TodoRecitation()
        plan = tr.create_initial_plan("Write a factorial function")

        assert "factorial" in plan.lower()
        assert "- [ ]" in plan

    def test_plan_includes_mode(self):
        """Plan includes the mode."""
        tr = TodoRecitation()
        plan = tr.create_initial_plan("test query", mode="code")
        assert "code" in plan.lower()

    def test_recitation_prefix_pushes_plan_to_recent(self):
        """Recitation prefix includes current plan."""
        tr = TodoRecitation()
        tr.create_initial_plan("test query")

        prefix = tr.build_recitation_prefix()
        assert "[CURRENT_PLAN]" in prefix
        assert "test query" in prefix
        assert "unchecked" in prefix.lower()

    def test_empty_plan_returns_empty_prefix(self):
        """No plan = no prefix (don't pollute context)."""
        tr = TodoRecitation()
        assert tr.build_recitation_prefix() == ""

    def test_update_from_output(self):
        """Extracts plan updates from LLM output."""
        tr = TodoRecitation()
        tr.create_initial_plan("test")

        llm_output = "Here's my work:\n- [x] Analyzed\n- [ ] Need to verify"
        tr.update_from_output(llm_output)

        assert "[x] Analyzed" in tr.current_plan
        assert "[ ] Need to verify" in tr.current_plan

    def test_update_ignores_output_without_checklist(self):
        """Output without checklist items doesn't change plan."""
        tr = TodoRecitation()
        original = tr.create_initial_plan("test")

        tr.update_from_output("Just a regular response with no checklist.")
        assert tr.current_plan == original

    def test_reset_clears_plan(self):
        """Reset clears the plan."""
        tr = TodoRecitation()
        tr.create_initial_plan("test")
        tr.reset()
        assert tr.current_plan == ""
        assert tr.build_recitation_prefix() == ""

    def test_current_plan_property(self):
        """current_plan property returns the plan."""
        tr = TodoRecitation()
        assert tr.current_plan == ""
        tr.create_initial_plan("query")
        assert "query" in tr.current_plan
