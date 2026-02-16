"""
todo.md recitation pattern — replaces MetacognitiveGovernor.

Manus Principle 4: "Agents lose focus in long contexts.
Have the agent update a todo.md at each step. This pushes goals
into the most recent context position (highest attention)."
"""

from typing import Optional

from ..feature_flags import FeatureFlags, feature_flags as default_flags


class TodoRecitation:
    """Push goals into recent context to combat 'lost in the middle'."""

    def __init__(self, feature_flags: Optional[FeatureFlags] = None):
        self._flags = feature_flags or default_flags
        self._current_plan: str = ""

    def create_initial_plan(self, query: str, mode: str = "chat") -> str:
        """Create initial task plan from user query."""
        self._current_plan = (
            f"## Task: {query}\n"
            f"## Mode: {mode}\n"
            f"## Steps:\n"
            f"- [ ] Analyze the request\n"
            f"- [ ] Generate response\n"
            f"- [ ] Verify quality\n"
        )
        return self._current_plan

    def build_recitation_prefix(self) -> str:
        """Build prefix to inject before LLM call.

        Pushes the plan into the most recent context position.
        """
        if not self._current_plan:
            return ""
        return (
            "[CURRENT_PLAN]\n"
            f"{self._current_plan}\n"
            "[/CURRENT_PLAN]\n\n"
            "Review the plan above. Continue working on unchecked items.\n"
        )

    def update_from_output(self, llm_output: str):
        """Extract updated plan from LLM output if present."""
        lines = llm_output.split("\n")
        plan_lines = [line for line in lines if line.strip().startswith("- [")]
        if plan_lines:
            self._current_plan = "\n".join(plan_lines)

    @property
    def current_plan(self) -> str:
        return self._current_plan

    def reset(self):
        """Reset plan for new request."""
        self._current_plan = ""
