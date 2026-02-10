#!/usr/bin/env python3
"""
API 整合測試
"""

import sys
import asyncio
import aiohttp
import json
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


async def test_api_health():
    """測試 API 健康檢查"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health Check: {data}")
                    return True
                else:
                    print(f"❌ Health Check 失敗: {response.status}")
                    return False
        except Exception as e:
            print(f"⚠️ API 未啟動: {e}")
            return False


async def test_api_query():
    """測試 API 查詢"""
    async with aiohttp.ClientSession() as session:
        test_queries = [
            {"query": "什麼是 Docker?", "mode": "chat"},
            {"query": "搜尋 AI 最新發展", "mode": "search"},
            {"query": "解釋機器學習", "mode": "auto"},
        ]

        for test_data in test_queries:
            try:
                async with session.post(
                    "http://localhost:8000/api/query",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Query [{test_data['mode']}]: {data.get('result', '')[:100]}...")
                    else:
                        print(f"❌ Query 失敗: {response.status}")
                        text = await response.text()
                        print(f"   錯誤: {text}")
            except Exception as e:
                print(f"⚠️ Query 請求失敗: {e}")


async def test_api_sse():
    """測試 SSE 端點"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/api/sse") as response:
                if response.status == 200:
                    # 讀取一些 SSE 事件
                    data = await response.text()
                    print(f"✅ SSE Endpoint: {data[:200]}")
                else:
                    print(f"❌ SSE 失敗: {response.status}")
        except Exception as e:
            print(f"⚠️ SSE 請求失敗: {e}")


async def main():
    """主測試函數"""
    print("=" * 50)
    print("API 整合測試")
    print("=" * 50)
    print("\n注意: 請先啟動 API 服務器")
    print("執行: python src/main_refactored.py --mode api\n")

    # 測試健康檢查
    print("\n=== 健康檢查 ===")
    is_healthy = await test_api_health()

    if is_healthy:
        # 測試查詢
        print("\n=== 查詢測試 ===")
        await test_api_query()

        # 測試 SSE
        print("\n=== SSE 測試 ===")
        await test_api_sse()
    else:
        print("\n⚠️ API 服務器未運行，跳過其他測試")

    print("\n" + "=" * 50)
    print("測試完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())