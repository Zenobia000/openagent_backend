#!/usr/bin/env python3
"""
Test script for parallel search optimization
"""

import asyncio
import time
from typing import List, Dict
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模擬搜索配置
from dataclasses import dataclass
from enum import Enum


class SearchProviderType(Enum):
    TAVILY = "tavily"
    EXA = "exa"
    SERPER = "serper"
    DUCKDUCKGO = "duckduckgo"
    BING = "bing"


@dataclass
class SearchEngineConfig:
    """搜索引擎配置"""
    primary: SearchProviderType = SearchProviderType.TAVILY
    fallback_chain: List[SearchProviderType] = None
    max_results: int = 10
    timeout: float = 30.0
    parallel_searches: int = 3
    enable_race_mode: bool = False
    enable_batch_parallel: bool = True
    batch_size: int = 3
    parallel_strategy: str = "batch"  # batch | race | hybrid

    def __post_init__(self):
        if self.fallback_chain is None:
            self.fallback_chain = [
                SearchProviderType.EXA,
                SearchProviderType.SERPER,
                SearchProviderType.DUCKDUCKGO
            ]

        # 根據策略設置對應的標誌
        if self.parallel_strategy == "race":
            self.enable_race_mode = True
            self.enable_batch_parallel = False
        elif self.parallel_strategy == "batch":
            self.enable_race_mode = False
            self.enable_batch_parallel = True
        elif self.parallel_strategy == "hybrid":
            self.enable_race_mode = True
            self.enable_batch_parallel = True


# 模擬搜索函數
async def mock_search_provider(provider: str, query: str, delay: float = 1.0) -> Dict:
    """模擬搜索提供商"""
    start_time = time.time()
    await asyncio.sleep(delay)  # 模擬網絡延遲

    return {
        "provider": provider,
        "query": query,
        "sources": [f"Result {i} from {provider}" for i in range(3)],
        "time": time.time() - start_time
    }


async def test_batch_parallel_search(queries: List[str], config: SearchEngineConfig):
    """測試批次平行搜索"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing BATCH PARALLEL search")
    logger.info(f"Queries: {queries}")
    logger.info(f"Batch size: {config.batch_size}")
    logger.info(f"{'='*60}")

    start_time = time.time()
    results = []

    # 分批執行
    for i in range(0, len(queries), config.batch_size):
        batch = queries[i:i+config.batch_size]
        logger.info(f"\nBatch {i//config.batch_size + 1}: {batch}")

        # 並行執行批次內的搜索
        batch_tasks = [
            mock_search_provider("tavily", query, delay=1.0)
            for query in batch
        ]

        batch_results = await asyncio.gather(*batch_tasks)
        results.extend(batch_results)

        for result in batch_results:
            logger.info(f"  ✅ {result['query']} - {result['provider']} - {result['time']:.2f}s")

    total_time = time.time() - start_time
    logger.info(f"\n📊 Batch Parallel Summary:")
    logger.info(f"  Total queries: {len(queries)}")
    logger.info(f"  Total time: {total_time:.2f}s")
    logger.info(f"  Average time per query: {total_time/len(queries):.2f}s")

    return results


async def test_race_mode_search(query: str, config: SearchEngineConfig):
    """測試競速模式搜索"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing RACE MODE search")
    logger.info(f"Query: {query}")
    logger.info(f"Providers: {[p.value for p in [config.primary] + config.fallback_chain]}")
    logger.info(f"{'='*60}")

    start_time = time.time()

    # 創建所有搜索任務（不同延遲模擬不同速度）
    providers = [config.primary] + config.fallback_chain
    search_tasks = [
        asyncio.create_task(
            mock_search_provider(provider.value, query, delay=(i+1)*0.5)
        )
        for i, provider in enumerate(providers)
    ]

    logger.info(f"\n🏁 Starting race with {len(providers)} providers...")

    # 使用 as_completed 獲取第一個完成的結果
    done, pending = await asyncio.wait(search_tasks, return_when=asyncio.FIRST_COMPLETED)

    # 獲取第一個完成的結果
    result = await list(done)[0]
    total_time = time.time() - start_time
    logger.info(f"\n🏆 Winner: {result['provider']} - {result['time']:.2f}s")
    logger.info(f"Total race time: {total_time:.2f}s")

    # 取消其他未完成的任務
    for task in pending:
        task.cancel()

    return result

    return None


async def test_hybrid_mode(queries: List[str], config: SearchEngineConfig):
    """測試混合模式：批次執行 + 每個查詢使用競速"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing HYBRID MODE search")
    logger.info(f"Queries: {queries}")
    logger.info(f"Batch size: {config.batch_size}")
    logger.info(f"Race mode per query: True")
    logger.info(f"{'='*60}")

    start_time = time.time()
    results = []

    # 分批執行
    for i in range(0, len(queries), config.batch_size):
        batch = queries[i:i+config.batch_size]
        logger.info(f"\nBatch {i//config.batch_size + 1}: {batch}")

        # 每個查詢都使用競速模式
        batch_tasks = []
        for query in batch:
            # 為每個查詢創建競速任務
            providers = [config.primary] + config.fallback_chain[:2]  # 限制提供商數量
            race_tasks = [
                mock_search_provider(provider.value, query, delay=(j+1)*0.3)
                for j, provider in enumerate(providers)
            ]
            batch_tasks.append(asyncio.create_task(
                get_first_result(query, race_tasks)
            ))

        batch_results = await asyncio.gather(*batch_tasks)
        results.extend(batch_results)

        for result in batch_results:
            logger.info(f"  ✅ {result['query']} - Winner: {result['provider']} - {result['time']:.2f}s")

    total_time = time.time() - start_time
    logger.info(f"\n📊 Hybrid Mode Summary:")
    logger.info(f"  Total queries: {len(queries)}")
    logger.info(f"  Total time: {total_time:.2f}s")
    logger.info(f"  Average time per query: {total_time/len(queries):.2f}s")

    return results


async def get_first_result(query: str, race_tasks: List):
    """獲取第一個完成的結果"""
    # 創建任務
    tasks = [asyncio.create_task(t) for t in race_tasks]

    # 等待第一個完成
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    # 獲取結果
    if done:
        result = await list(done)[0]
        # 取消其他任務
        for task in pending:
            task.cancel()
        return result
    return None


async def main():
    """主測試函數"""

    # 測試查詢
    test_queries = [
        "Python asyncio best practices",
        "React hooks tutorial",
        "Machine learning algorithms",
        "Docker containerization",
        "GraphQL vs REST API",
        "TypeScript generics"
    ]

    # 1. 測試批次平行搜索
    batch_config = SearchEngineConfig(parallel_strategy="batch", batch_size=3)
    await test_batch_parallel_search(test_queries, batch_config)

    # 2. 測試競速模式
    race_config = SearchEngineConfig(parallel_strategy="race")
    await test_race_mode_search(test_queries[0], race_config)

    # 3. 測試混合模式
    hybrid_config = SearchEngineConfig(parallel_strategy="hybrid", batch_size=2)
    await test_hybrid_mode(test_queries[:4], hybrid_config)

    logger.info(f"\n{'='*60}")
    logger.info(f"All tests completed successfully! ✅")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())