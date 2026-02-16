"""
Tool availability mask — constrain tool selection via masking, not removal.

Manus Principle 2: "Never dynamically add/remove tools mid-execution.
All tools stay in the prompt (stable KV-Cache prefix).
Use logit masking to constrain which tools the model can invoke."
"""

from typing import Optional

from ..feature_flags import FeatureFlags, feature_flags as default_flags


class ToolAvailabilityMask:
    """All tools always defined. Mode only affects which are ALLOWED."""

    TOOL_GROUPS: dict[str, list[str]] = {
        "chat": ["respond"],
        "code": ["respond", "code_execute", "code_analyze"],
        "search": ["respond", "web_search", "web_fetch"],
        "thinking": ["respond", "web_search", "code_analyze"],
        "knowledge": ["respond", "web_search"],
        "deep_research": ["respond", "web_search", "web_fetch", "code_execute"],
    }

    def __init__(self, feature_flags: Optional[FeatureFlags] = None):
        self._flags = feature_flags or default_flags

    def get_allowed_tools(self, mode_name: str) -> list[str]:
        """Get list of allowed tool names for this mode."""
        return self.TOOL_GROUPS.get(mode_name, ["respond"])

    def is_tool_allowed(self, mode_name: str, tool_name: str) -> bool:
        """Check if a specific tool is allowed for this mode."""
        return tool_name in self.get_allowed_tools(mode_name)

    def apply_mask(self, mode_name: str, available_tools: list[dict]) -> list[dict]:
        """Filter tool list based on mode mask.

        Input: All available tools (stable, always the same)
        Output: Only allowed tools for this mode

        The key insight: the INPUT never changes (stable KV-Cache prefix).
        Only the OUTPUT (what the model can actually call) is filtered.
        """
        allowed = set(self.get_allowed_tools(mode_name))
        return [t for t in available_tools if t.get("name") in allowed]
