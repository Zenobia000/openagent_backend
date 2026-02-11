"""Unit tests for Multi-Provider LLM fallback chain."""

import asyncio
import os
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.llm.base import LLMProvider
from services.llm.multi_provider import MultiProviderLLMClient


# ── Helpers ──────────────────────────────────────────────────────

class FakeProvider:
    """Configurable fake LLM provider for testing."""

    def __init__(self, name: str, response: str = "ok", fail: bool = False, error_msg: str = "provider down"):
        self._name = name
        self._response = response
        self._fail = fail
        self._error_msg = error_msg

    @property
    def provider_name(self):
        return self._name

    @property
    def is_available(self):
        return True

    async def generate(self, prompt, **kwargs):
        if self._fail:
            raise ConnectionError(self._error_msg)
        token_info = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        if kwargs.get("return_token_info", False):
            return self._response, token_info
        return self._response

    async def stream(self, prompt, **kwargs):
        if self._fail:
            raise ConnectionError(self._error_msg)
        for word in self._response.split():
            yield word


class BusinessErrorProvider(FakeProvider):
    """Provider that raises a non-retryable business error."""

    async def generate(self, prompt, **kwargs):
        raise ValueError("invalid input format")

    async def stream(self, prompt, **kwargs):
        raise ValueError("invalid input format")
        yield  # noqa: unreachable - makes it a generator


# ── MultiProviderLLMClient tests ─────────────────────────────────

class TestMultiProviderInit:
    def test_requires_at_least_one_provider(self):
        with pytest.raises(ValueError, match="At least one"):
            MultiProviderLLMClient([])

    def test_provider_name_shows_chain(self):
        providers = [FakeProvider("a"), FakeProvider("b")]
        client = MultiProviderLLMClient(providers)
        assert client.provider_name == "multi(a,b)"

    def test_is_available(self):
        client = MultiProviderLLMClient([FakeProvider("a")])
        assert client.is_available is True


class TestMultiProviderGenerate:
    @pytest.mark.asyncio
    async def test_primary_success(self):
        """First provider succeeds — use its result."""
        client = MultiProviderLLMClient([
            FakeProvider("primary", response="hello"),
            FakeProvider("fallback", response="world"),
        ])
        result = await client.generate("test")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """First provider fails — fall through to second."""
        client = MultiProviderLLMClient([
            FakeProvider("primary", fail=True, error_msg="Connection timeout"),
            FakeProvider("fallback", response="recovered"),
        ])
        result = await client.generate("test")
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """All providers fail — raises last error."""
        client = MultiProviderLLMClient([
            FakeProvider("a", fail=True, error_msg="Connection timeout"),
            FakeProvider("b", fail=True, error_msg="Connection timeout b"),
        ])
        with pytest.raises(ConnectionError, match="timeout b"):
            await client.generate("test")

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_fallback(self):
        """Business error should not fall through to next provider."""
        client = MultiProviderLLMClient([
            BusinessErrorProvider("primary"),
            FakeProvider("fallback", response="should not reach"),
        ])
        with pytest.raises(ValueError, match="invalid input"):
            await client.generate("test")

    @pytest.mark.asyncio
    async def test_token_info_passthrough(self):
        """return_token_info=True returns tuple from successful provider."""
        client = MultiProviderLLMClient([
            FakeProvider("primary", response="hello"),
        ])
        result = await client.generate("test", return_token_info=True)
        assert isinstance(result, tuple)
        content, info = result
        assert content == "hello"
        assert info["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_three_provider_chain(self):
        """Falls through two failures to the third provider."""
        client = MultiProviderLLMClient([
            FakeProvider("a", fail=True, error_msg="Connection timeout"),
            FakeProvider("b", fail=True, error_msg="Connection timeout"),
            FakeProvider("c", response="third time"),
        ])
        result = await client.generate("test")
        assert result == "third time"

    @pytest.mark.asyncio
    async def test_soft_error_triggers_fallback(self):
        """OpenAI-style soft error string triggers fallback."""
        soft = FakeProvider("openai", response="[OpenAI Error] rate limit")
        hard = FakeProvider("anthropic", response="ok from claude")
        client = MultiProviderLLMClient([soft, hard])
        result = await client.generate("test")
        assert result == "ok from claude"


class TestMultiProviderStream:
    @pytest.mark.asyncio
    async def test_stream_primary_success(self):
        client = MultiProviderLLMClient([
            FakeProvider("primary", response="hello world"),
        ])
        chunks = [c async for c in client.stream("test")]
        assert chunks == ["hello", "world"]

    @pytest.mark.asyncio
    async def test_stream_fallback(self):
        client = MultiProviderLLMClient([
            FakeProvider("primary", fail=True, error_msg="Connection timeout"),
            FakeProvider("fallback", response="recovered stream"),
        ])
        chunks = [c async for c in client.stream("test")]
        assert chunks == ["recovered", "stream"]

    @pytest.mark.asyncio
    async def test_stream_all_fail(self):
        client = MultiProviderLLMClient([
            FakeProvider("a", fail=True, error_msg="Connection timeout"),
            FakeProvider("b", fail=True, error_msg="Connection timeout b"),
        ])
        with pytest.raises(ConnectionError):
            _ = [c async for c in client.stream("test")]


# ── Factory function tests ───────────────────────────────────────

class TestCreateLLMClient:
    _ENV_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")

    def test_no_keys_raises(self):
        """No API keys at all should raise ValueError."""
        env_clean = {k: "" for k in self._ENV_KEYS}
        with patch.dict("os.environ", env_clean, clear=False):
            for k in self._ENV_KEYS:
                os.environ.pop(k, None)

            from services.llm import create_llm_client
            with pytest.raises(ValueError, match="No LLM provider"):
                create_llm_client()

    def test_single_provider_returns_directly(self):
        """With only OpenAI key, returns OpenAILLMClient directly (not wrapped)."""
        env_clean = {k: "" for k in self._ENV_KEYS}
        with patch.dict("os.environ", env_clean, clear=False):
            for k in self._ENV_KEYS:
                os.environ.pop(k, None)

            from services.llm import create_llm_client
            from services.llm.openai_client import OpenAILLMClient

            client = create_llm_client(openai_key="sk-test-fake-key")
            assert isinstance(client, OpenAILLMClient)

    def test_multiple_providers_returns_multi(self):
        """With multiple keys, returns MultiProviderLLMClient."""
        env_clean = {k: "" for k in self._ENV_KEYS}
        with patch.dict("os.environ", env_clean, clear=False):
            for k in self._ENV_KEYS:
                os.environ.pop(k, None)

            from services.llm import create_llm_client

            client = create_llm_client(
                openai_key="sk-test-key-1",
                anthropic_key="sk-ant-test-key-2",
            )
            assert "multi(" in client.provider_name
            assert "openai" in client.provider_name
            assert "anthropic" in client.provider_name


# ── LLMProvider base class tests ─────────────────────────────────

class TestLLMProviderBase:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            LLMProvider()
