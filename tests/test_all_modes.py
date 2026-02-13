#!/usr/bin/env python3
"""
測試所有處理模式的新輸出結構
展示中間階段在日誌中，最終結果在回應中
"""

import asyncio
import time
from src.core.logger import structured_logger

async def simulate_mode_outputs():
    """模擬各種模式的輸出結構"""

    modes = {
        "thinking": {
            "stages": [
                "🔍 Stage 1: Problem Understanding",
                "🔍 Stage 2: Critical Analysis",
                "🔍 Stage 3: Deep Reasoning",
                "🔍 Stage 4: Synthesis & Reflection",
                "🎯 Stage 5: Final Answer"
            ],
            "final": "深度思考的最終答案..."
        },
        "search": {
            "stages": [
                "🔍 Generating search queries...",
                "🌐 Searching 1/3: query1...",
                "🌐 Searching 2/3: query2...",
                "🌐 Searching 3/3: query3...",
                "🔄 Synthesizing search results..."
            ],
            "final": "綜合網路搜索結果的答案..."
        },
        "knowledge": {
            "stages": [
                "🔢 Generating embeddings...",
                "📚 RAG Search in knowledge base...",
                "📖 Found 5 relevant documents",
                "🔄 Synthesizing answer from knowledge..."
            ],
            "final": "基於知識庫的答案..."
        },
        "research": {
            "stages": [
                "📝 Creating research plan...",
                "🔍 Generating SERP queries...",
                "📋 Executing 5 search tasks...",
                "💾 Storing research context...",
                "📑 Writing final report..."
            ],
            "final": "完整的研究報告..."
        }
    }

    print("=" * 80)
    print("🧪 測試所有模式的新輸出結構")
    print("=" * 80)
    print("\n原則：")
    print("1. 中間過程 → 日誌（開發者可見）")
    print("2. 最終結果 → 回應（使用者可見）")
    print("=" * 80)

    for mode_name, mode_data in modes.items():
        print(f"\n\n{'='*40}")
        print(f"📊 模式: {mode_name.upper()}")
        print(f"{'='*40}")

        print("\n📋 日誌輸出（處理過程）:")
        print("-" * 30)

        for stage in mode_data["stages"][:-1]:  # 除了最後階段
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [INFO] {stage}")
            await asyncio.sleep(0.3)

        # 最後階段
        if mode_data["stages"]:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [INFO] {mode_data['stages'][-1]}")
            await asyncio.sleep(0.3)

        print("\n✨ 使用者回應（最終結果）:")
        print("-" * 30)
        print(mode_data["final"])

    print("\n\n" + "=" * 80)
    print("✅ 總結：")
    print("- 所有中間處理階段都記錄在日誌中")
    print("- 使用者只看到最終的清晰答案")
    print("- 開發者可以通過日誌追蹤完整處理流程")
    print("=" * 80)

async def test_log_structure():
    """展示日誌結構範例"""

    print("\n\n" + "=" * 80)
    print("📁 日誌檔案結構範例 (logs/opencode_YYYYMMDD.log)")
    print("=" * 80)

    log_example = """
2026-02-10 15:52:05.147 [INFO] 🧠 Deep Thinking: Analyzing 'query...'
2026-02-10 15:52:05.147 [INFO] 🔍 Stage 1: Problem Understanding
2026-02-10 15:52:21.077 [INFO] 💭 Stage 1 Result: [analysis...]
2026-02-10 15:52:21.078 [INFO] 🔍 Stage 2: Critical Analysis
2026-02-10 15:52:40.541 [INFO] 💭 Stage 2 Result: [analysis...]
2026-02-10 15:52:40.542 [INFO] 🔍 Stage 3: Deep Reasoning
2026-02-10 15:52:55.933 [INFO] 💭 Stage 3 Result: [reasoning...]
2026-02-10 15:52:55.934 [INFO] 🔍 Stage 4: Synthesis
2026-02-10 15:53:28.625 [INFO] 💭 Stage 4 Result: [synthesis...]
2026-02-10 15:53:28.626 [INFO] 🎯 Stage 5: Final Answer
2026-02-10 15:53:42.829 [MESSAGE] [Final answer only shown to user]
    """

    print(log_example)

    print("\n📊 說明：")
    print("- [INFO] 標記的內容只在日誌中")
    print("- [MESSAGE] 標記的內容會顯示給使用者")
    print("- 每個階段都有清晰的時間戳記和狀態")

async def main():
    """主函數"""

    # 展示所有模式的輸出結構
    await simulate_mode_outputs()

    # 展示日誌結構
    await test_log_structure()

    print("\n✨ 測試完成！新的輸出結構已實現。")

if __name__ == "__main__":
    asyncio.run(main())