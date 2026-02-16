"""Tests for ToolAvailabilityMask — logit masking (Manus Principle 2)."""

from core.routing.tool_mask import ToolAvailabilityMask


class TestToolAvailabilityMask:
    def test_chat_mode_only_respond(self):
        """CHAT mode should only allow respond tool."""
        mask = ToolAvailabilityMask()
        allowed = mask.get_allowed_tools("chat")
        assert allowed == ["respond"]

    def test_code_mode_includes_code_tools(self):
        """CODE mode should include code tools."""
        mask = ToolAvailabilityMask()
        allowed = mask.get_allowed_tools("code")
        assert "code_execute" in allowed
        assert "code_analyze" in allowed
        assert "respond" in allowed

    def test_search_mode_includes_web_tools(self):
        """SEARCH mode should include web tools."""
        mask = ToolAvailabilityMask()
        allowed = mask.get_allowed_tools("search")
        assert "web_search" in allowed
        assert "web_fetch" in allowed

    def test_deep_research_has_all_key_tools(self):
        """DEEP_RESEARCH mode should have the broadest tool set."""
        mask = ToolAvailabilityMask()
        allowed = mask.get_allowed_tools("deep_research")
        assert "respond" in allowed
        assert "web_search" in allowed
        assert "web_fetch" in allowed
        assert "code_execute" in allowed

    def test_unknown_mode_defaults_to_respond(self):
        """Unknown mode defaults to respond only."""
        mask = ToolAvailabilityMask()
        allowed = mask.get_allowed_tools("nonexistent")
        assert allowed == ["respond"]

    def test_is_tool_allowed(self):
        """is_tool_allowed checks correctly."""
        mask = ToolAvailabilityMask()
        assert mask.is_tool_allowed("code", "code_execute")
        assert not mask.is_tool_allowed("chat", "code_execute")

    def test_apply_mask_filters_tools(self):
        """apply_mask should filter tools based on mode."""
        mask = ToolAvailabilityMask()
        all_tools = [
            {"name": "respond"},
            {"name": "web_search"},
            {"name": "code_execute"},
        ]
        filtered = mask.apply_mask("chat", all_tools)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "respond"

    def test_apply_mask_preserves_all_for_research(self):
        """apply_mask should keep all tools for deep_research."""
        mask = ToolAvailabilityMask()
        all_tools = [
            {"name": "respond"},
            {"name": "web_search"},
            {"name": "web_fetch"},
            {"name": "code_execute"},
        ]
        filtered = mask.apply_mask("deep_research", all_tools)
        assert len(filtered) == 4
