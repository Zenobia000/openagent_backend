#!/usr/bin/env python3
"""
測試 Thinking 模式 - 驗證分階段在日誌中輸出，最終只返回結果
"""

import asyncio
from src.core.engine import RefactoredEngine
from src.services.llm.openai_client import OpenAILLMClient
from src.core.models import ProcessingMode, Request
from src.core.logger import structured_logger
import os
import time

async def test_thinking_mode():
    """測試 thinking 模式的新輸出結構"""

    print("=" * 80)
    print("🧪 測試 Thinking 模式 - 分階段日誌 + 最終結果輸出")
    print("=" * 80)

    # 初始化 LLM 客戶端
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  使用模擬模式 (無 API Key)")
        llm_client = None
    else:
        print("✅ 使用真實 OpenAI API")
        llm_client = OpenAILLMClient(api_key=api_key)

    # 初始化引擎
    engine = RefactoredEngine(llm_client=llm_client)

    # 準備測試查詢
    test_query = "什麼是量子計算？"

    print(f"\n📝 測試查詢: {test_query}")
    print("-" * 80)

    # 創建請求
    request = Request(
        query=test_query,
        mode=ProcessingMode.THINKING,
        context={}
    )

    # 模擬監聽日誌輸出
    class LogMonitor:
        def __init__(self):
            self.logs = []

        def capture(self, message):
            timestamp = time.strftime("%H:%M:%S")
            self.logs.append(f"[{timestamp}] {message}")
            # 即時顯示日誌
            print(f"📋 LOG: {message[:100]}..." if len(message) > 100 else f"📋 LOG: {message}")

    monitor = LogMonitor()

    print("\n🚀 開始處理...")
    print("-" * 80)
    print("📊 思考過程將在日誌中顯示:")
    print()

    try:
        # 處理請求
        start_time = time.time()
        response = await engine.process_request(request)
        end_time = time.time()

        print("\n" + "=" * 80)
        print("✨ 最終回應 (只包含結果):")
        print("=" * 80)
        print(response.response)

        print("\n" + "=" * 80)
        print("📊 處理統計:")
        print(f"  - 總 Token 使用: {response.context.total_tokens}")
        print(f"  - 處理時間: {end_time - start_time:.2f} 秒")
        print("=" * 80)

        # 顯示日誌摘要
        print("\n📝 思考階段日誌摘要:")
        print("-" * 80)
        # 這裡應該從實際的日誌文件讀取，展示各階段的日誌
        log_file = f"logs/opencode_{time.strftime('%Y%m%d')}.log"
        if os.path.exists(log_file):
            print(f"詳細日誌請查看: {log_file}")
        else:
            print("(日誌文件未找到)")

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

async def simulate_output_structure():
    """模擬展示理想的輸出結構"""

    print("\n" + "=" * 80)
    print("📖 理想輸出結構示範")
    print("=" * 80)

    # 模擬日誌輸出
    stages = [
        ("🔍 Stage 1: Problem Understanding", "分析問題核心要素..."),
        ("💭 Stage 1 Result", "問題理解完成，識別出關鍵概念..."),
        ("🔍 Stage 2: Critical Analysis", "進行批判性分析..."),
        ("💭 Stage 2 Result", "多角度分析完成，發現潛在議題..."),
        ("🔍 Stage 3: Deep Reasoning", "深度推理進行中..."),
        ("💭 Stage 3 Result", "推理鏈建立完成..."),
        ("🔍 Stage 4: Synthesis", "綜合所有分析..."),
        ("💭 Stage 4 Result", "反思與改進完成..."),
        ("🎯 Stage 5: Final Answer", "生成最終答案...")
    ]

    print("\n📋 日誌輸出 (顯示思考過程):")
    print("-" * 40)
    for stage, desc in stages[:-1]:  # 除了最後一個階段
        print(f"[LOG] {stage}: {desc}")
        await asyncio.sleep(0.5)

    print("\n" + "=" * 40)
    print("✨ 最終回應 (使用者看到的):")
    print("=" * 40)
    print("""
量子計算是一種基於量子力學原理的計算方式，與傳統計算有本質區別：

1. **基本單位**：使用量子位（qubit）而非傳統位元
2. **核心特性**：
   - 疊加態：量子位可同時處於 0 和 1 的狀態
   - 糾纏：多個量子位可相互關聯
   - 量子干涉：利用波函數特性優化計算

3. **應用領域**：密碼學、藥物研發、材料科學、人工智慧等

量子計算有望解決傳統計算機難以處理的複雜問題。
""")

async def main():
    """主函數"""

    # 首先展示理想的輸出結構
    await simulate_output_structure()

    # 詢問是否要測試實際功能
    print("\n" + "=" * 80)
    print("是否要測試實際的 Thinking 模式？(需要 OpenAI API Key)")
    print("輸入 'y' 繼續，其他任何輸入跳過")

    if input("> ").lower() == 'y':
        await test_thinking_mode()
    else:
        print("跳過實際測試")

    print("\n✨ 測試完成！")

if __name__ == "__main__":
    asyncio.run(main())