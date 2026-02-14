"""
Research Configuration - Search engine and provider settings

Defines search providers and configuration for deep research processor.
Extracted from monolithic processor.py
"""

from enum import Enum
from dataclasses import dataclass
from typing import List


class SearchProviderType(Enum):
    """搜索引擎提供商類型"""
    TAVILY = "tavily"
    EXA = "exa"  # Neural search with semantic understanding
    SERPER = "serper"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    MODEL = "model"  # AI內建搜索


@dataclass
class SearchEngineConfig:
    """搜索引擎配置"""
    primary: SearchProviderType = SearchProviderType.TAVILY
    fallback_chain: List[SearchProviderType] = None
    max_results: int = 10
    timeout: float = 30.0
    parallel_searches: int = 3
    # 平行策略配置
    enable_race_mode: bool = False  # 競速模式：所有引擎同時搜索
    enable_batch_parallel: bool = True  # 批次平行：多個查詢同時執行
    batch_size: int = 3  # 批次大小
    parallel_strategy: str = "batch"  # batch | race | hybrid

    def __post_init__(self):
        if self.fallback_chain is None:
            self.fallback_chain = [
                SearchProviderType.EXA,
                SearchProviderType.SERPER,
                SearchProviderType.DUCKDUCKGO,
                SearchProviderType.MODEL
            ]

        # 根據策略設置對應的標誌
        if self.parallel_strategy == "race":
            self.enable_race_mode = True
            self.enable_batch_parallel = False
        elif self.parallel_strategy == "batch":
            self.enable_race_mode = False
            self.enable_batch_parallel = True
        elif self.parallel_strategy == "hybrid":
            # 混合模式：批次執行 + 每個查詢使用競速
            self.enable_race_mode = True
            self.enable_batch_parallel = True
