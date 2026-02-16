"""Tests for ErrorPreservation — keep failures in context (Manus Principle 5)."""

from core.context.error_preservation import ErrorPreservation


class TestErrorPreservation:
    def test_retry_prompt_includes_failure(self):
        """Retry prompt must include the failed attempt."""
        prompt = ErrorPreservation.build_retry_prompt(
            original_query="What is 2+2?",
            failed_result="I'm not sure.",
        )
        assert "I'm not sure" in prompt
        assert "2+2" in prompt
        assert "improved" in prompt.lower()

    def test_retry_prompt_includes_error_info(self):
        """Retry prompt includes error info when provided."""
        prompt = ErrorPreservation.build_retry_prompt(
            original_query="test",
            failed_result="bad result",
            error_info="TimeoutError",
        )
        assert "TimeoutError" in prompt

    def test_retry_prompt_no_error_info(self):
        """Retry prompt works without error info."""
        prompt = ErrorPreservation.build_retry_prompt(
            original_query="test",
            failed_result="bad result",
        )
        assert "Error encountered" not in prompt

    def test_should_retry_for_empty_result(self):
        """Empty results should trigger retry."""
        assert ErrorPreservation.should_retry("", max_retries=1, current_retry=0)

    def test_should_retry_for_short_result(self):
        """Very short results (< 10 chars) should trigger retry."""
        assert ErrorPreservation.should_retry("short", max_retries=1, current_retry=0)

    def test_should_not_retry_after_max(self):
        """Respects max retry limit."""
        assert not ErrorPreservation.should_retry("", max_retries=1, current_retry=1)

    def test_should_not_retry_for_good_result(self):
        """Good results should not trigger retry."""
        assert not ErrorPreservation.should_retry(
            "This is a detailed and helpful response about the topic.",
            max_retries=1,
            current_retry=0,
        )

    def test_should_retry_respects_whitespace(self):
        """Whitespace-only results should trigger retry."""
        assert ErrorPreservation.should_retry("   \n  ", max_retries=1, current_retry=0)
