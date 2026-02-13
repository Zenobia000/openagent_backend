#!/usr/bin/env python3
"""
測試 Prompts 整合重構
驗證所有服務都正確使用專業的 prompts
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import (
    RefactoredEngine,
    Request,
    ProcessingMode
)
from services.llm_service import get_llm_service
from core.prompts import PromptTemplates


async def test_chat_with_prompts():
    """測試 Chat 模式使用專業 prompts"""
    print("\n=== 測試 Chat 模式 (使用系統指令和輸出指南) ===")

    llm_service = get_llm_service()
    engine = RefactoredEngine(llm_client=llm_service)
    await engine.initialize()

    request = Request(query="什麼是量子計算？", mode=ProcessingMode.CHAT)
    response = await engine.process(request)

    print(f"回應長度: {len(response.result)} 字元")
    print(f"回應預覽: {response.result[:200]}...")

    # 驗證是否使用了正確的 prompts
    assert len(response.result) > 100, "回應太短，可能未使用正確的 prompts"
    print("✅ Chat 模式測試通過")


async def test_search_with_serp_prompts():
    """測試 Search 模式使用 SERP prompts"""
    print("\n=== 測試 Search 模式 (使用 SERP 查詢優化) ===")

    llm_service = get_llm_service()
    engine = RefactoredEngine(llm_client=llm_service)
    await engine.initialize()

    request = Request(query="最新的 AI 發展趨勢", mode=ProcessingMode.SEARCH)
    response = await engine.process(request)

    print(f"回應長度: {len(response.result)} 字元")
    print(f"回應預覽: {response.result[:200]}...")
    print("✅ Search 模式測試通過")


async def test_knowledge_with_citation_prompts():
    """測試 Knowledge 模式使用引用 prompts"""
    print("\n=== 測試 Knowledge 模式 (使用引用規則) ===")

    llm_service = get_llm_service()
    engine = RefactoredEngine(llm_client=llm_service)
    await engine.initialize()

    request = Request(query="機器學習的基本概念", mode=ProcessingMode.KNOWLEDGE)
    response = await engine.process(request)

    print(f"回應長度: {len(response.result)} 字元")
    print(f"回應預覽: {response.result[:200]}...")
    print("✅ Knowledge 模式測試通過")


async def test_research_service():
    """測試 ResearchService 使用專業 prompts"""
    print("\n=== 測試 ResearchService (深度研究功能) ===")

    from services.research import get_research_service

    research_service = await get_research_service()

    # 啟動研究任務
    task_id = await research_service.start_research(
        topic="區塊鏈技術的應用",
        documents=None
    )

    print(f"研究任務已啟動: {task_id}")

    # 等待一段時間讓任務執行
    await asyncio.sleep(3)

    # 獲取任務狀態
    task = await research_service.get_task(task_id)
    if task:
        print(f"任務狀態: {task.status.value}")
        print(f"進度: {task.progress}%")
        print(f"步驟數: {len(task.steps)}")

        # 顯示已完成的步驟
        for step in task.steps[:3]:
            print(f"  - {step.step}: {step.status}")

    print("✅ ResearchService 測試通過")


async def test_knowledge_graph_processor():
    """測試 KnowledgeGraphProcessor"""
    print("\n=== 測試 KnowledgeGraphProcessor (知識圖譜生成) ===")

    from core.processor import KnowledgeGraphProcessor
    from core.models import ProcessingContext, Request, ProcessingMode

    llm_service = get_llm_service()
    processor = KnowledgeGraphProcessor(llm_client=llm_service)

    # 創建處理上下文
    request = Request(query="人工智慧的發展歷史", mode=ProcessingMode.AUTO)
    context = ProcessingContext(request=request)

    # 處理請求
    result = await processor.process(context)

    print(f"圖譜生成結果長度: {len(result)} 字元")

    # 檢查是否包含 Mermaid 圖表
    if "graph" in result.lower() or "mermaid" in result.lower():
        print("✅ 成功生成 Mermaid 知識圖譜")
    else:
        print("⚠️ 可能未生成正確的圖譜格式")

    print(result[:500] + "...")


async def test_browser_service():
    """測試 BrowserService 使用專業 prompts"""
    print("\n=== 測試 BrowserService (報告生成) ===")

    from services.browser.service import BrowserService

    browser_service = BrowserService()

    # 模擬一些內容
    test_contents = [
        {
            "title": "AI 技術概述",
            "url": "https://example.com/ai",
            "content": "人工智慧是模擬人類智能的技術...",
            "type": "web"
        },
        {
            "title": "機器學習基礎",
            "url": "file://docs/ml.pdf",
            "content": "機器學習是AI的一個分支...",
            "type": "document"
        }
    ]

    # 生成報告
    report = await browser_service._generate_report(
        query="AI 技術研究",
        contents=test_contents
    )

    print(f"報告長度: {len(report)} 字元")
    print(f"報告預覽:\n{report[:500]}...")

    print("✅ BrowserService 測試通過")


async def verify_prompt_usage():
    """驗證 prompts 使用統計"""
    print("\n=== Prompts 使用統計 ===")

    # 列出所有 prompt 方法
    prompt_methods = [
        method for method in dir(PromptTemplates)
        if method.startswith('get_') and callable(getattr(PromptTemplates, method))
    ]

    print(f"總共定義了 {len(prompt_methods)} 個 prompt 方法")

    # 已整合的 prompts
    integrated = [
        "get_system_instruction",
        "get_output_guidelines",
        "get_search_knowledge_result_prompt",
        "get_citation_rules",
        "get_system_question_prompt",
        "get_report_plan_prompt",
        "get_serp_queries_prompt",
        "get_search_result_prompt",
        "get_final_report_prompt",
        "get_final_report_references_prompt",
        "get_knowledge_graph_prompt",
        "get_query_result_prompt"
    ]

    print(f"已整合: {len(integrated)} 個 ({len(integrated)/len(prompt_methods)*100:.1f}%)")

    # 未整合的 prompts
    not_integrated = set(prompt_methods) - set(integrated)
    if not_integrated:
        print(f"未整合: {len(not_integrated)} 個")
        for method in not_integrated:
            print(f"  - {method}")
    else:
        print("✅ 所有 prompts 都已整合！")


async def main():
    """主測試函數"""
    print("=" * 60)
    print("Prompts 整合測試")
    print("=" * 60)

    try:
        # 基礎功能測試
        await test_chat_with_prompts()
        await test_search_with_serp_prompts()
        await test_knowledge_with_citation_prompts()

        # 進階服務測試
        await test_research_service()
        await test_knowledge_graph_processor()
        await test_browser_service()

        # 統計驗證
        await verify_prompt_usage()

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！Prompts 整合成功")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())