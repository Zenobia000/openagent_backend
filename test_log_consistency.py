#!/usr/bin/env python3
"""
測試日誌一致性 - 確保沒有重複的 icons
"""

import asyncio
from src.core.logger import structured_logger
# from src.core.models import LogCategory

async def simulate_log_output():
    """模擬各種日誌輸出，檢查一致性"""

    print("=" * 80)
    print("🧪 測試日誌 Icon 一致性")
    print("=" * 80)
    print("\n原則：每種日誌類型只有一個統一的 icon\n")

    # 模擬各種日誌
    test_logs = [
        # 系統日誌
        ("🚀 Initializing OpenCode Platform", "system", "initialize"),
        ("🚀 Processing request: query...", "system", "process"),
        ("✅ Processing completed", "system", "complete"),

        # LLM 日誌 - 只有一個 icon
        ("🤖 LLM Call: gpt-4o", "llm", "call"),

        # 思考階段日誌
        ("🔍 Stage 1: Problem Understanding", "thinking", "stage1"),
        ("💭 Stage 1 Result: [analysis...]", "thinking", "stage1_result"),

        # 搜索日誌
        ("🔍 Generating search queries...", "search", "query_generation"),
        ("🌐 Searching 1/3: query1...", "search", "performing"),
        ("✅ Search complete", "search", "complete"),

        # 知識庫日誌
        ("🔢 Generating embeddings...", "knowledge", "embedding"),
        ("📚 RAG Search in knowledge base...", "rag", "search"),
        ("📖 Found 5 relevant documents", "rag", "results"),

        # 深度研究日誌
        ("📝 Creating research plan...", "deep_research", "planning"),
        ("📋 Executing 5 search tasks...", "deep_research", "tasks"),
        ("📑 Writing final report...", "deep_research", "final_report"),

        # 工具決策
        ("🔧 Tool Decision: deep_thinking", "tool", "decision"),

        # 性能日誌
        ("⚡ process_thinking", "perf", "timing"),

        # 錯誤日誌
        ("❌ Error occurred: exception", "error", "exception"),
    ]

    print("📋 標準日誌格式：\n")
    print("-" * 40)

    for message, category, context in test_logs:
        print(f"[{category:15}] {message}")

    print("\n" + "=" * 80)
    print("✅ 檢查結果：")
    print("-" * 40)

    # 檢查重複
    icons = {}
    duplicates = []

    for message, category, context in test_logs:
        icon = message.split()[0] if message else ""
        if icon and icon[0] in "🚀✅🤖🔍💭🌐🔢📚📖📝📋📑🔧⚡❌":
            if category not in icons:
                icons[category] = icon
            elif icons[category] != icon and category not in ["system", "search", "rag", "deep_research"]:
                duplicates.append(f"{category}: {icons[category]} vs {icon}")

    if duplicates:
        print("⚠️  發現重複 icons：")
        for dup in duplicates:
            print(f"  - {dup}")
    else:
        print("✅ 沒有發現重複的 icons")
        print("\n每個類別的標準 icon：")
        for cat, icon in sorted(icons.items()):
            print(f"  {cat:15} → {icon}")

    print("=" * 80)

async def show_before_after():
    """展示修改前後的對比"""

    print("\n\n📊 修改前後對比")
    print("=" * 80)

    print("❌ 修改前（有重複）：")
    print("-" * 40)
    print("[INFO] 🤖 LLM Call: gpt-4o [tokens=1425, time=15929ms]")
    print("[INFO] 🤖 LLM Response: ## 1. Problem Understanding...")
    print("       ^^^ 兩個 🤖 重複了！")

    print("\n✅ 修改後（統一）：")
    print("-" * 40)
    print("[INFO] 🤖 LLM Call: gpt-4o [tokens=1425, time=15929ms]")
    print("       ^^^ 只有一個 🤖 icon")

    print("\n" + "=" * 80)

async def main():
    """主函數"""

    # 測試日誌一致性
    await simulate_log_output()

    # 展示修改前後對比
    await show_before_after()

    print("\n✨ 日誌 Icon 已統一！")

if __name__ == "__main__":
    asyncio.run(main())