"""LLM service exception hierarchy.

Provides structured exception types for all LLM operations, enabling proper
error handling and retry logic in multi_provider.py and ErrorClassifier.
"""


class LLMError(Exception):
    """Base exception for all LLM service errors.

    All LLM-related exceptions inherit from this, allowing callers to catch
    any LLM failure with a single except clause.
    """
    pass


class ProviderError(LLMError):
    """Provider-specific errors that are typically retryable.

    These errors are usually transient (rate limits, timeouts, temporary
    service issues) and should trigger fallback to the next provider in the chain.
    """
    retryable = True


class ValidationError(LLMError):
    """Input validation errors that are non-retryable.

    These errors indicate bad input (invalid prompt, unsupported parameters)
    and should NOT trigger fallback since all providers will fail with the same error.
    """
    retryable = False


class OpenAIError(ProviderError):
    """OpenAI-specific errors (rate limits, API failures, etc.)."""
    pass


class AnthropicError(ProviderError):
    """Anthropic Claude-specific errors (rate limits, API failures, etc.)."""
    pass


class GeminiError(ProviderError):
    """Google Gemini-specific errors (rate limits, API failures, etc.)."""
    pass
