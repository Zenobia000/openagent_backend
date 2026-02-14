"""LLM service layer — multi-provider with automatic fallback.

Usage:
    from services.llm import create_llm_client
    client = create_llm_client()  # auto-detects available providers from env
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def create_llm_client(
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    gemini_key: Optional[str] = None,
):
    """Build an LLM client from available API keys.

    Returns a MultiProviderLLMClient if multiple providers are available,
    or a single provider client if only one is configured.
    Raises ValueError if no provider is available.
    """
    providers = []

    # OpenAI (primary)
    oai_key = openai_key or os.getenv("OPENAI_API_KEY")
    if oai_key:
        try:
            from .openai_client import OpenAILLMClient
            model = os.getenv("LLM_MODEL", "gpt-4o-mini")
            providers.append(OpenAILLMClient(api_key=oai_key, model=model))
            logger.info("LLM provider registered: openai (%s)", model)
        except Exception as e:
            logger.warning("Failed to initialize OpenAI: %s", e)

    # Anthropic (fallback)
    ant_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
    if ant_key:
        try:
            from .anthropic_client import AnthropicLLMClient
            model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
            providers.append(AnthropicLLMClient(api_key=ant_key, model=model))
            logger.info("LLM provider registered: anthropic (%s)", model)
        except Exception as e:
            logger.warning("Failed to initialize Anthropic: %s", e)

    # Gemini (fallback)
    gem_key = gemini_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gem_key:
        try:
            from .gemini_client import GeminiLLMClient
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            providers.append(GeminiLLMClient(api_key=gem_key, model=model))
            logger.info("LLM provider registered: gemini (%s)", model)
        except Exception as e:
            logger.warning("Failed to initialize Gemini: %s", e)

    if not providers:
        raise ValueError(
            "No LLM provider available. "
            "Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY"
        )

    if len(providers) == 1:
        return providers[0]

    from .multi_provider import MultiProviderLLMClient
    chain = " -> ".join(p.provider_name for p in providers)
    logger.info("LLM fallback chain: %s", chain)
    return MultiProviderLLMClient(providers)
