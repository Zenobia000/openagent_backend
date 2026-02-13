#!/usr/bin/env python3
"""測試新的回答生成系統"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import Engine


async def test_queries():
    """測試各種查詢"""
    engine = Engine()
    await engine.initialize()

    # 測試查詢列表
    queries = [
        "你好",
        "北極熊吃甚麼? 深度分析",
        "系統狀態",
        "功能",
        "什麼是 AI?",
        "深度分析: 氣候變化的影響"
    ]

    for query in queries:
        print(f"\n{'=' * 60}")
        print(f"查詢: {query}")
        print(f"{'=' * 60}")

        result = await engine.process(query)
        print(f"回應:\n{result}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(test_queries())