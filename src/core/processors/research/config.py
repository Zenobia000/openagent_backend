"""
Research Configuration - Search engine and provider settings

Defines search providers and configuration for deep research processor.
Extracted from monolithic processor.py

All values are env-configurable. Dataclass defaults are fallbacks only.
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class SearchProviderType(Enum):
    """搜索引擎提供商類型"""
    TAVILY = "tavily"
    EXA = "exa"  # Neural search with semantic understanding
    SERPER = "serper"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    MODEL = "model"  # AI內建搜索


def _env_int(key: str, default: int) -> int:
    """Read int from env, fallback to default."""
    val = os.environ.get(key)
    return int(val) if val is not None else default


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    return float(val) if val is not None else default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass
class SearchEngineConfig:
    """搜索引擎配置 — all fields read from env, dataclass defaults are fallbacks."""
    primary: SearchProviderType = None
    fallback_chain: List[SearchProviderType] = None
    max_results: int = None
    timeout: float = None
    parallel_searches: int = None
    # Parallel strategy
    enable_race_mode: bool = None
    enable_batch_parallel: bool = None
    batch_size: int = None
    parallel_strategy: str = None
    # Search budget model
    queries_first_iteration: int = None
    queries_followup_iteration: int = None
    max_total_queries: int = None
    urls_per_query: int = None

    def __post_init__(self):
        # -- Search engine settings (from .env) --
        if self.primary is None:
            provider_str = _env_str("SEARCH_PRIMARY_PROVIDER", "tavily")
            try:
                self.primary = SearchProviderType(provider_str)
            except ValueError:
                self.primary = SearchProviderType.TAVILY

        if self.max_results is None:
            self.max_results = _env_int("SEARCH_MAX_RESULTS", 10)
        if self.timeout is None:
            self.timeout = _env_float("SEARCH_TIMEOUT", 30.0)
        if self.parallel_strategy is None:
            self.parallel_strategy = _env_str("SEARCH_PARALLEL_STRATEGY", "batch")
        if self.parallel_searches is None:
            self.parallel_searches = _env_int("DEEP_RESEARCH_PARALLEL_SEARCHES", 3)
        if self.batch_size is None:
            self.batch_size = self.parallel_searches

        # -- Fallback chain --
        if self.fallback_chain is None:
            chain_str = os.environ.get("SEARCH_FALLBACK_CHAIN")
            if chain_str:
                self.fallback_chain = []
                for name in chain_str.split(","):
                    name = name.strip()
                    try:
                        self.fallback_chain.append(SearchProviderType(name))
                    except ValueError:
                        pass
            else:
                self.fallback_chain = [
                    SearchProviderType.EXA,
                    SearchProviderType.SERPER,
                    SearchProviderType.DUCKDUCKGO,
                    SearchProviderType.MODEL,
                ]

        # -- Parallel strategy flags --
        if self.parallel_strategy == "race":
            if self.enable_race_mode is None:
                self.enable_race_mode = True
            if self.enable_batch_parallel is None:
                self.enable_batch_parallel = False
        elif self.parallel_strategy == "batch":
            if self.enable_race_mode is None:
                self.enable_race_mode = False
            if self.enable_batch_parallel is None:
                self.enable_batch_parallel = True
        elif self.parallel_strategy == "hybrid":
            if self.enable_race_mode is None:
                self.enable_race_mode = _env_bool("SEARCH_ENABLE_RACE_MODE", True)
            if self.enable_batch_parallel is None:
                self.enable_batch_parallel = _env_bool("SEARCH_ENABLE_BATCH_PARALLEL", True)
        else:
            if self.enable_race_mode is None:
                self.enable_race_mode = _env_bool("SEARCH_ENABLE_RACE_MODE", False)
            if self.enable_batch_parallel is None:
                self.enable_batch_parallel = _env_bool("SEARCH_ENABLE_BATCH_PARALLEL", True)

        # -- Search budget model (from .env) --
        if self.queries_first_iteration is None:
            self.queries_first_iteration = _env_int("DEEP_RESEARCH_QUERIES_FIRST_ITERATION", 8)
        if self.queries_followup_iteration is None:
            self.queries_followup_iteration = _env_int("DEEP_RESEARCH_QUERIES_FOLLOWUP_ITERATION", 5)
        if self.max_total_queries is None:
            self.max_total_queries = _env_int("DEEP_RESEARCH_MAX_TOTAL_QUERIES", 20)
        if self.urls_per_query is None:
            self.urls_per_query = _env_int("DEEP_RESEARCH_URLS_PER_QUERY", 3)
