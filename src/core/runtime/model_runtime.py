"""
ModelRuntime - Stateless execution for System 1 and System 2 processors.
Wraps ProcessorFactory, adds cognitive-level awareness and optional cache.
"""

from typing import Optional, Set

from .base import BaseRuntime
from ..models_v2 import ProcessingContext, Modes
from ..processors.factory import ProcessorFactory
from ..logger import structured_logger
from ..cache import ResponseCache
from ..feature_flags import feature_flags


# Modes handled by ModelRuntime (everything except AGENT-level)
_MODEL_MODES = {
    Modes.CHAT,
    Modes.KNOWLEDGE,
    Modes.SEARCH,
    Modes.CODE,
    Modes.THINKING,
}

# System 1 modes eligible for caching
_CACHEABLE_MODES = {
    Modes.CHAT,
    Modes.KNOWLEDGE,
}


class ModelRuntime(BaseRuntime):
    """Stateless runtime for System 1 (fast) and System 2 (deep) processors.

    Delegates to ProcessorFactory for actual execution.
    System 1 cache: enabled by feature flag `system1.enable_cache`.
    """

    def __init__(self, llm_client=None, processor_factory: ProcessorFactory = None):
        super().__init__(llm_client)
        self._factory = processor_factory or ProcessorFactory(llm_client)
        self._logger = structured_logger
        ttl = feature_flags.get_value("system1.cache_ttl", 300)
        max_size = feature_flags.get_value("system1.cache_max_size", 1000)
        self._cache = ResponseCache(ttl=ttl, max_size=max_size)

    def supports(self, mode) -> bool:
        return mode in _MODEL_MODES

    async def execute(self, context: ProcessingContext) -> str:
        """Execute via the appropriate processor, with optional cache."""
        mode = context.request.mode
        cognitive = mode.cognitive_level
        query = context.request.query

        self._logger.info(
            f"ModelRuntime executing: {mode} (cognitive={cognitive})",
        )

        # Cache check (System 1 only, when flag is on)
        use_cache = (
            feature_flags.is_enabled("system1.enable_cache")
            and mode in _CACHEABLE_MODES
        )

        if use_cache:
            cached = self._cache.get(query, str(mode))
            if cached is not None:
                self._logger.info(f"Cache HIT for {mode}")
                return cached

        processor = self._factory.get_processor(mode)
        result = await processor.process(context)

        if use_cache:
            self._cache.put(query, str(mode), result)

        return result

    @property
    def cache_stats(self):
        return self._cache.stats
