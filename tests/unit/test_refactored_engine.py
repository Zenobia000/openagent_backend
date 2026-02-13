#!/usr/bin/env python3
"""
測試重構版引擎
展示簡化後的架構如何運作
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 導入重構版組件
from core.refactored import (
    RefactoredEngine,
    Request,
    ProcessingMode,
    structured_logger
)

# 嘗試導入 OpenAI 客戶端
try:
    from services.llm.openai_client import OpenAILLMClient
    HAS_OPENAI = True
except:
    HAS_OPENAI = False
    print("⚠️ OpenAI 客戶端不可用，使用 Mock 模式")


class MockLLMClient:
    """模擬 LLM 客戶端"""

    async def generate(self, prompt: str) -> str:
        """生成模擬響應"""
        await asyncio.sleep(0.1)  # 模擬延遲

        if "代碼" in prompt or "code" in prompt.lower():
            return """def hello_world():
    print("Hello, World!")
    return "Success"
"""
        elif "搜尋" in prompt or "search" in prompt.lower():
            return "根據搜索結果，這是關於您查詢內容的詳細資訊..."
        elif "知識" in prompt or "knowledge" in prompt.lower():
            return "根據知識庫，這是一個詳細的解釋..."
        elif "深度" in prompt or "thinking" in prompt.lower():
            return "經過深度分析，得出以下結論..."
        else:
            return f"這是對您問題的回應: {prompt[:50]}..."


async def test_basic_modes():
    """測試基本處理模式"""
    print("\n" + "="*60)
    print("測試基本處理模式")
    print("="*60)

    # 創建引擎
    if HAS_OPENAI:
        try:
            llm_client = OpenAILLMClient()
            print("✅ 使用 OpenAI 客戶端")
        except:
            llm_client = MockLLMClient()
            print("⚠️ OpenAI 初始化失敗，使用 Mock 客戶端")
    else:
        llm_client = MockLLMClient()

    engine = RefactoredEngine(llm_client=llm_client)
    await engine.initialize()

    # 測試不同模式
    test_cases = [
        ("你好，今天天氣如何？", ProcessingMode.CHAT),
        ("什麼是量子計算？", ProcessingMode.KNOWLEDGE),
        ("搜尋最新的 AI 新聞", ProcessingMode.SEARCH),
        ("深度分析氣候變化的影響", ProcessingMode.THINKING),
        ("寫一個快速排序的代碼", ProcessingMode.CODE),
    ]

    for query, mode in test_cases:
        print(f"\n--- 測試: {mode.value} ---")
        print(f"查詢: {query}")

        request = Request(query=query, mode=mode)
        response = await engine.process(request)

        print(f"響應: {response.result[:100]}...")
        print(f"耗時: {response.time_ms:.2f}ms")


async def test_auto_mode():
    """測試自動模式選擇"""
    print("\n" + "="*60)
    print("測試自動模式選擇")
    print("="*60)

    engine = RefactoredEngine(llm_client=MockLLMClient())
    await engine.initialize()

    queries = [
        "請寫一個 Python 函數",
        "搜尋量子計算的最新進展",
        "解釋什麼是機器學習",
        "深度分析區塊鏈的未來",
        "你好，很高興認識你",
    ]

    for query in queries:
        print(f"\n查詢: {query}")

        request = Request(query=query, mode=ProcessingMode.AUTO)
        response = await engine.process(request)

        print(f"自動選擇模式: {response.mode.value}")
        print(f"響應: {response.result[:80]}...")


async def test_sse_streaming():
    """測試 SSE 流式處理"""
    print("\n" + "="*60)
    print("測試 SSE 流式處理")
    print("="*60)

    engine = RefactoredEngine(llm_client=MockLLMClient())
    await engine.initialize()

    request = Request(
        query="深度分析人工智慧的發展",
        mode=ProcessingMode.THINKING,
        stream=True
    )

    print(f"查詢: {request.query}")
    print("\nSSE 事件流:")

    # 收集事件
    events = []

    def sse_callback(signal, data):
        events.append({"signal": signal, "data": data})
        print(f"  [{signal}] {str(data)[:60]}...")

    structured_logger.set_sse_callback(sse_callback)

    # 處理請求
    response = await engine.process(request)

    print(f"\n最終響應: {response.result[:100]}...")
    print(f"收集到 {len(events)} 個 SSE 事件")


async def test_error_handling():
    """測試錯誤處理"""
    print("\n" + "="*60)
    print("測試錯誤處理")
    print("="*60)

    # 創建一個會失敗的 LLM 客戶端
    class FailingLLMClient:
        async def generate(self, prompt: str) -> str:
            raise Exception("模擬的 LLM 錯誤")

    engine = RefactoredEngine(llm_client=FailingLLMClient())
    await engine.initialize()

    request = Request(query="這會觸發錯誤", mode=ProcessingMode.CHAT)

    try:
        response = await engine.process(request)
        print(f"響應: {response.result}")

        # 檢查錯誤事件
        error_events = [e for e in response.events if e["type"] == "error"]
        if error_events:
            print(f"捕獲到錯誤事件: {error_events}")
    except Exception as e:
        print(f"捕獲異常: {e}")


async def main():
    """主測試函數"""
    print("\n" + "="*60)
    print("OpenCode Platform - 重構版引擎測試")
    print("="*60)

    # 運行所有測試
    await test_basic_modes()
    await test_auto_mode()
    await test_sse_streaming()
    await test_error_handling()

    print("\n" + "="*60)
    print("測試完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())