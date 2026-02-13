"""Unit tests for LLM exception hierarchy integration with ErrorClassifier."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.errors import ErrorCategory, ErrorClassifier
from services.llm.errors import (
    AnthropicError,
    GeminiError,
    LLMError,
    OpenAIError,
    ProviderError,
    ValidationError,
)


class TestLLMErrorHierarchy:
    """Test that LLM exception hierarchy has correct attributes."""

    def test_provider_error_is_retryable(self):
        """ProviderError should be retryable."""
        assert ProviderError.retryable is True

    def test_validation_error_not_retryable(self):
        """ValidationError should not be retryable."""
        assert ValidationError.retryable is False

    def test_provider_specific_errors_are_retryable(self):
        """OpenAIError, AnthropicError, GeminiError inherit retryable=True."""
        assert OpenAIError.retryable is True
        assert AnthropicError.retryable is True
        assert GeminiError.retryable is True

    def test_exception_instances_have_retryable_attribute(self):
        """Exception instances should have retryable attribute."""
        openai_error = OpenAIError("rate limit")
        assert hasattr(openai_error, "retryable")
        assert openai_error.retryable is True

        validation_error = ValidationError("bad input")
        assert hasattr(validation_error, "retryable")
        assert validation_error.retryable is False


class TestErrorClassifierIntegration:
    """Test ErrorClassifier recognizes LLM exception hierarchy."""

    def test_classify_provider_error(self):
        """ProviderError should be classified as LLM error."""
        error = ProviderError("API temporarily unavailable")
        category = ErrorClassifier.classify(error)
        assert category == ErrorCategory.LLM

    def test_classify_openai_error(self):
        """OpenAIError should be classified as LLM error."""
        error = OpenAIError("rate limit exceeded")
        category = ErrorClassifier.classify(error)
        assert category == ErrorCategory.LLM

    def test_classify_anthropic_error(self):
        """AnthropicError should be classified as LLM error."""
        error = AnthropicError("API error")
        category = ErrorClassifier.classify(error)
        assert category == ErrorCategory.LLM

    def test_classify_gemini_error(self):
        """GeminiError should be classified as LLM error."""
        error = GeminiError("quota exceeded")
        category = ErrorClassifier.classify(error)
        assert category == ErrorCategory.LLM

    def test_classify_validation_error(self):
        """ValidationError should be classified as BUSINESS error."""
        error = ValidationError("invalid prompt format")
        category = ErrorClassifier.classify(error)
        assert category == ErrorCategory.BUSINESS

    def test_is_retryable_provider_error(self):
        """ProviderError should be retryable."""
        error = ProviderError("temporary failure")
        assert ErrorClassifier.is_retryable(error) is True

    def test_is_retryable_openai_error(self):
        """OpenAIError should be retryable."""
        error = OpenAIError("rate limit")
        assert ErrorClassifier.is_retryable(error) is True

    def test_is_not_retryable_validation_error(self):
        """ValidationError should not be retryable."""
        error = ValidationError("bad input")
        assert ErrorClassifier.is_retryable(error) is False

    def test_retryable_uses_attribute_first(self):
        """ErrorClassifier.is_retryable should use error.retryable attribute first."""
        # Create a custom error with retryable attribute
        class CustomError(Exception):
            retryable = False

        error = CustomError("custom error")
        # Even though it's not in any category, retryable attribute should be respected
        assert ErrorClassifier.is_retryable(error) is False

        # Test with retryable=True
        class RetryableCustomError(Exception):
            retryable = True

        error2 = RetryableCustomError("custom retryable")
        assert ErrorClassifier.is_retryable(error2) is True


class TestExceptionInheritance:
    """Test exception inheritance chain."""

    def test_openai_error_is_provider_error(self):
        """OpenAIError should inherit from ProviderError."""
        assert issubclass(OpenAIError, ProviderError)
        assert issubclass(OpenAIError, LLMError)
        assert issubclass(OpenAIError, Exception)

    def test_anthropic_error_is_provider_error(self):
        """AnthropicError should inherit from ProviderError."""
        assert issubclass(AnthropicError, ProviderError)
        assert issubclass(AnthropicError, LLMError)

    def test_gemini_error_is_provider_error(self):
        """GeminiError should inherit from ProviderError."""
        assert issubclass(GeminiError, ProviderError)
        assert issubclass(GeminiError, LLMError)

    def test_validation_error_is_llm_error(self):
        """ValidationError should inherit from LLMError."""
        assert issubclass(ValidationError, LLMError)
        assert issubclass(ValidationError, Exception)

    def test_catch_all_llm_errors(self):
        """Can catch all LLM errors with LLMError base class."""
        errors = [
            OpenAIError("openai"),
            AnthropicError("anthropic"),
            GeminiError("gemini"),
            ValidationError("validation"),
            ProviderError("provider"),
        ]

        for error in errors:
            try:
                raise error
            except LLMError:
                pass  # Should catch all
            except Exception:
                pytest.fail(f"Failed to catch {type(error).__name__} with LLMError")
