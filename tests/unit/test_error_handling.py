"""Unit tests for error classification, retry, and fallback."""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.errors import ErrorClassifier, ErrorCategory, retry_with_backoff, llm_fallback


class TestErrorClassifier:
    def test_network_timeout(self):
        assert ErrorClassifier.classify(Exception("Connection timeout")) == ErrorCategory.NETWORK

    def test_network_dns(self):
        assert ErrorClassifier.classify(Exception("DNS resolution failed")) == ErrorCategory.NETWORK

    def test_llm_rate_limit(self):
        assert ErrorClassifier.classify(Exception("rate_limit exceeded")) == ErrorCategory.LLM

    def test_llm_context_length(self):
        assert ErrorClassifier.classify(Exception("context_length exceeded")) == ErrorCategory.LLM

    def test_resource_oom(self):
        assert ErrorClassifier.classify(MemoryError("out of memory")) == ErrorCategory.RESOURCE_LIMIT

    def test_business_value_error(self):
        assert ErrorClassifier.classify(ValueError("invalid input")) == ErrorCategory.BUSINESS

    def test_business_key_error(self):
        assert ErrorClassifier.classify(KeyError("missing_key")) == ErrorCategory.BUSINESS

    def test_unknown_error(self):
        assert ErrorClassifier.classify(RuntimeError("something broke")) == ErrorCategory.UNKNOWN

    def test_retryable_network(self):
        assert ErrorClassifier.is_retryable(Exception("Connection timeout")) is True

    def test_retryable_llm(self):
        assert ErrorClassifier.is_retryable(Exception("rate limit")) is True

    def test_not_retryable_business(self):
        assert ErrorClassifier.is_retryable(ValueError("bad value")) is False

    def test_not_retryable_unknown(self):
        assert ErrorClassifier.is_retryable(RuntimeError("crash")) is False


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Connection timeout")
            return "recovered"

        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_business_error(self):
        async def fn():
            raise ValueError("invalid")

        with pytest.raises(ValueError, match="invalid"):
            await retry_with_backoff(fn, max_retries=3, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        async def fn():
            raise Exception("Connection timeout")

        with pytest.raises(Exception, match="timeout"):
            await retry_with_backoff(fn, max_retries=2, base_delay=0.01)


class TestLLMFallback:
    @pytest.mark.asyncio
    async def test_primary_success(self):
        async def primary():
            return "primary result"

        async def fallback():
            return "fallback result"

        result = await llm_fallback(primary, fallback)
        assert result == "primary result"

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        async def primary():
            raise Exception("primary failed")

        async def fallback():
            return "fallback result"

        result = await llm_fallback(primary, fallback)
        assert result == "fallback result"

    @pytest.mark.asyncio
    async def test_fallback_also_fails(self):
        async def primary():
            raise Exception("primary failed")

        async def fallback():
            raise Exception("fallback also failed")

        with pytest.raises(Exception, match="fallback also failed"):
            await llm_fallback(primary, fallback)
