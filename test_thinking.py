#!/usr/bin/env python3
"""
測試 Thinking 模式的分階段輸出
"""

import asyncio
import sys
from src.core.engine import RefactoredEngine
from src.services.llm.openai_client import OpenAILLMClient
from src.core.models import ProcessingMode, Request
import os

async def test_thinking_mode():
    """測試 thinking 模式的分階段輸出"""

    print("=" * 60)
    print("🧪 測試 Thinking 模式分階段輸出")
    print("=" * 60)

    # 初始化 LLM 客戶端
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  警告: 未設置 OPENAI_API_KEY，使用模擬模式")
        llm_client = None
    else:
        llm_client = OpenAILLMClient(api_key=api_key)

    # 初始化引擎
    engine = RefactoredEngine(llm_client=llm_client)

    # 準備測試查詢
    test_query = "分析 AI 對未來教育的影響"

    print(f"\n📝 測試查詢: {test_query}")
    print("-" * 60)

    # 創建請求
    request = Request(
        query=test_query,
        mode=ProcessingMode.THINKING,
        context={}
    )

    # 處理請求並即時顯示輸出
    print("\n🚀 開始處理...\n")

    try:
        # 處理請求
        response = await engine.process_request(request)

        # 最終結果已經在處理過程中透過 logger.message 輸出
        # 這裡只顯示統計信息
        print("\n" + "=" * 60)
        print("📊 處理統計:")
        print(f"  - 總 Token 使用: {response.context.total_tokens}")
        print(f"  - 處理時間: {response.metadata.get('processing_time', 0):.2f} 秒")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

async def test_streaming_output():
    """測試串流輸出效果"""

    print("\n" + "=" * 60)
    print("🧪 測試串流輸出效果")
    print("=" * 60)

    # 模擬分階段輸出
    stages = [
        ("【Stage 1: Problem Understanding】", "分析問題的核心要素..."),
        ("【Stage 2: Critical Analysis】", "從多個角度進行批判性分析..."),
        ("【Stage 3: Deep Reasoning】", "進行深度推理和邏輯分析..."),
        ("【Stage 4: Synthesis】", "綜合所有分析結果..."),
        ("【Stage 5: Final Answer】", "生成最終答案...")
    ]

    for title, content in stages:
        print(f"\n### {title}")
        print(content)
        await asyncio.sleep(1)  # 模擬處理延遲

    print("\n✅ 串流輸出測試完成")

async def main():
    """主函數"""

    # 測試串流輸出效果
    await test_streaming_output()

    # 測試實際的 thinking 模式
    print("\n" + "=" * 60)
    print("是否要測試實際的 Thinking 模式？(需要 OpenAI API Key)")
    print("輸入 'y' 繼續，其他任何輸入跳過")

    if input("> ").lower() == 'y':
        await test_thinking_mode()
    else:
        print("跳過實際測試")

    print("\n✨ 測試完成！")

if __name__ == "__main__":
    asyncio.run(main())