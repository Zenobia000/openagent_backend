"""
Error preservation — keep failed attempts in context.

Manus Principle 5: "Never remove failed actions from context.
The model learns implicitly from seeing its own mistakes."
"""


class ErrorPreservation:
    """Prompt builder for retry with preserved errors. Stateless."""

    @staticmethod
    def build_retry_prompt(
        original_query: str,
        failed_result: str,
        error_info: str = "",
    ) -> str:
        """Build a retry prompt that INCLUDES the failed attempt.

        The failed attempt stays in context (append-only).
        The retry prompt references it explicitly.
        """
        error_section = f"\nError encountered: {error_info}" if error_info else ""
        return (
            f'My previous attempt to answer "{original_query}":\n\n'
            f"{failed_result}\n"
            f"{error_section}\n\n"
            f"The above attempt was incomplete or incorrect. "
            f"Please provide an improved answer, learning from the issues above.\n"
        )

    @staticmethod
    def should_retry(
        result: str, max_retries: int = 1, current_retry: int = 0
    ) -> bool:
        """Simple retry heuristic. No complex scoring."""
        if current_retry >= max_retries:
            return False
        return len(result.strip()) < 10
