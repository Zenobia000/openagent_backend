#!/usr/bin/env python3
"""
主程式測試
"""

import sys
import asyncio
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import (
    RefactoredEngine,
    Request,
    ProcessingMode,
    structured_logger
)
from services.llm_service import get_llm_service


async def test_engine():
    """測試引擎基本功能"""
    print("\n=== 測試引擎初始化 ===")

    try:
        # 初始化 LLM 服務
        llm_service = get_llm_service()
        print(f"✅ LLM 服務: {llm_service.__class__.__name__}")

        # 初始化引擎
        engine = RefactoredEngine(llm_client=llm_service)
        await engine.initialize()
        print("✅ 引擎初始化成功")

        # 測試不同模式
        test_cases = [
            ("什麼是 Python？", ProcessingMode.CHAT),
            ("搜尋 OpenAI GPT-4 最新消息", ProcessingMode.SEARCH),
            ("如何使用 Docker？", ProcessingMode.AUTO),
        ]

        for query, mode in test_cases:
            print(f"\n=== 測試: {mode.value} 模式 ===")
            print(f"問題: {query}")

            request = Request(query=query, mode=mode)
            response = await engine.process(request)

            print(f"回應模式: {response.mode}")
            print(f"執行時間: {response.time_ms:.2f}ms")
            print(f"回應: {response.result[:200]}...")

        print("\n✅ 所有測試完成")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_services():
    """測試各個服務"""
    print("\n=== 測試服務整合 ===")

    try:
        # 測試 Knowledge Service
        from services.knowledge import KnowledgeService
        kb_service = KnowledgeService()
        await kb_service.initialize()
        print("✅ Knowledge Service 初始化成功")

        # 測試 Research Service
        from services.research import get_research_service
        research_service = await get_research_service()
        print("✅ Research Service 初始化成功")

        # 測試 Sandbox Service
        from services.sandbox import SandboxService
        sandbox = SandboxService()
        result = await sandbox.execute_python("print('Hello from sandbox!')")
        print(f"✅ Sandbox Service: {result.get('stdout', '').strip()}")

    except Exception as e:
        print(f"⚠️ 服務測試警告: {e}")


async def main():
    """主測試函數"""
    print("=" * 50)
    print("OpenCode Platform 測試")
    print("=" * 50)

    # 測試引擎
    await test_engine()

    # 測試服務
    await test_services()

    print("\n" + "=" * 50)
    print("測試完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())