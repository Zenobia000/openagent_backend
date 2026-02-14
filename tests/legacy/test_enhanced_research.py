#!/usr/bin/env python
"""
測試增強版 DeepResearchProcessor
演示 SSE Streaming、多搜索引擎配置和事件驅動架構
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.enhanced_deep_research import (
    EnhancedDeepResearchProcessor,
    SearchEngineConfig,
    SearchProviderType,
    ResearchEvent
)
from core.models import ProcessingContext, Request, Response, ProcessingMode


class ResearchEventHandler:
    """研究事件處理器 - 模擬前端事件處理"""

    def __init__(self):
        self.events = []
        self.start_time = None

    async def handle_event(self, event: ResearchEvent):
        """處理研究事件"""
        if self.start_time is None:
            self.start_time = datetime.now()

        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.events.append(event)

        # 根據事件類型處理
        if event.type == "progress":
            print(f"\n⏱️ [{elapsed:.1f}s] Progress: {event.step} - {event.data.get('status')}")
            if 'message' in event.data:
                print(f"   📢 {event.data['message']}")

        elif event.type == "message":
            content = event.data.get('content', '')
            if len(content) > 200:
                print(f"\n📝 [{elapsed:.1f}s] {event.step}: {content[:200]}...")
            else:
                print(f"\n📝 [{elapsed:.1f}s] {event.step}: {content}")

        elif event.type == "reasoning":
            print(f"\n🤔 [{elapsed:.1f}s] Reasoning: {event.data.get('message')}")

        elif event.type == "search_result":
            print(f"\n🔍 [{elapsed:.1f}s] Search Result:")
            print(f"   Query: {event.data.get('query')}")
            print(f"   Sources: {event.data.get('sources_count')}")

        elif event.type == "error":
            print(f"\n❌ [{elapsed:.1f}s] Error: {event.data}")


async def test_streaming_research():
    """測試 SSE Streaming 功能"""
    print("=" * 60)
    print("Testing SSE Streaming Support")
    print("=" * 60)

    # 創建事件處理器
    event_handler = ResearchEventHandler()

    # 配置搜索引擎（模擬）
    search_config = SearchEngineConfig(
        primary=SearchProviderType.TAVILY,
        fallback_chain=[
            SearchProviderType.SERPER,
            SearchProviderType.DUCKDUCKGO,
            SearchProviderType.MODEL
        ],
        max_results=5,
        parallel_searches=2
    )

    # 創建處理器
    processor = EnhancedDeepResearchProcessor(
        llm_client=None,  # 模擬模式
        services={},  # 無真實服務
        search_config=search_config,
        event_callback=event_handler.handle_event
    )

    # 啟用 streaming
    processor.enable_streaming(True)

    # 測試查詢
    test_query = "What are the latest breakthroughs in quantum computing?"
    context = ProcessingContext(
        request=Request(query=test_query),
        response=Response(
            result="",
            mode=ProcessingMode.DEEP_RESEARCH,
            trace_id="test-001"
        )
    )

    print(f"\n🚀 Starting research: {test_query}")
    print("-" * 50)

    try:
        # 模擬 streaming 處理
        async for sse_event in processor.process_with_streaming(context):
            # 這裡會輸出 SSE 格式的事件
            if sse_event.startswith("data:"):
                print(f"\n📡 SSE Event: {sse_event[:100]}...")

    except Exception as e:
        print(f"\n❌ Error during streaming: {e}")

    # 打印事件統計
    print("\n" + "=" * 60)
    print("Event Statistics:")
    print("-" * 50)
    event_types = {}
    for event in event_handler.events:
        event_types[event.type] = event_types.get(event.type, 0) + 1

    for event_type, count in event_types.items():
        print(f"  {event_type}: {count} events")

    print(f"\nTotal events: {len(event_handler.events)}")
    print(f"Total time: {(datetime.now() - event_handler.start_time).total_seconds():.1f}s")


async def test_search_engine_fallback():
    """測試搜索引擎降級機制"""
    print("\n" + "=" * 60)
    print("Testing Search Engine Fallback")
    print("=" * 60)

    # 配置搜索引擎鏈
    search_config = SearchEngineConfig(
        primary=SearchProviderType.TAVILY,  # 假設這個會失敗
        fallback_chain=[
            SearchProviderType.SERPER,    # 第一備選
            SearchProviderType.BRAVE,      # 第二備選
            SearchProviderType.MODEL       # 最終降級到模型
        ],
        max_results=3,
        timeout=5.0
    )

    # 創建處理器
    processor = EnhancedDeepResearchProcessor(
        llm_client=None,  # 會觸發 MODEL fallback
        services={},  # 無真實搜索服務，會觸發 fallback
        search_config=search_config
    )

    print(f"\n📋 Search Configuration:")
    print(f"  Primary: {search_config.primary.value}")
    print(f"  Fallback chain: {[p.value for p in search_config.fallback_chain]}")
    print(f"  Timeout: {search_config.timeout}s")

    # 測試搜索
    test_query = "quantum computing applications"
    search_result = await processor._perform_deep_search(
        query=test_query,
        goal="Find practical applications"
    )

    print(f"\n✅ Search completed:")
    print(f"  Provider: {search_result.get('provider', 'unknown')}")
    print(f"  Sources: {len(search_result.get('sources', []))}")
    print(f"  Has summary: {'summary' in search_result}")


async def test_parallel_search_execution():
    """測試並行搜索執行"""
    print("\n" + "=" * 60)
    print("Testing Parallel Search Execution")
    print("=" * 60)

    # 配置並行搜索
    search_config = SearchEngineConfig(
        primary=SearchProviderType.MODEL,
        parallel_searches=3,  # 同時執行3個搜索
        max_results=5
    )

    # 創建處理器
    processor = EnhancedDeepResearchProcessor(
        llm_client=None,
        services={},
        search_config=search_config
    )

    # 創建多個搜索任務
    search_tasks = [
        {"query": "quantum computing basics", "researchGoal": "Understand fundamentals", "priority": 1},
        {"query": "quantum algorithms", "researchGoal": "Learn about algorithms", "priority": 2},
        {"query": "quantum hardware", "researchGoal": "Explore hardware", "priority": 1},
        {"query": "quantum applications", "researchGoal": "Find applications", "priority": 3},
        {"query": "quantum challenges", "researchGoal": "Identify challenges", "priority": 2},
    ]

    print(f"\n📋 Test Setup:")
    print(f"  Total tasks: {len(search_tasks)}")
    print(f"  Parallel limit: {search_config.parallel_searches}")
    print(f"  Expected batches: {(len(search_tasks) + search_config.parallel_searches - 1) // search_config.parallel_searches}")

    context = ProcessingContext(
        request=Request(query="test"),
        response=Response(
            result="",
            mode=ProcessingMode.DEEP_RESEARCH,
            trace_id="test-002"
        )
    )

    start_time = datetime.now()
    results = await processor._execute_search_tasks(context, search_tasks)
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n✅ Execution completed:")
    print(f"  Time taken: {elapsed:.2f}s")
    print(f"  Results: {len(results)}")
    print(f"  Success rate: {sum(1 for r in results if r['result'].get('sources')) / len(results) * 100:.1f}%")


async def test_event_callback_system():
    """測試事件回調系統"""
    print("\n" + "=" * 60)
    print("Testing Event Callback System")
    print("=" * 60)

    # 自定義事件處理器
    class CustomEventProcessor:
        def __init__(self):
            self.plan_events = []
            self.search_events = []
            self.report_events = []

        def process_event(self, event: ResearchEvent):
            """分類處理事件"""
            if event.step == "plan":
                self.plan_events.append(event)
                print(f"📝 Plan Event: {event.type}")
            elif "search" in event.step:
                self.search_events.append(event)
                print(f"🔍 Search Event: {event.type} - {event.step}")
            elif event.step == "final_report":
                self.report_events.append(event)
                print(f"📑 Report Event: {event.type}")

    # 創建事件處理器
    event_processor = CustomEventProcessor()

    # 創建處理器並設置回調
    processor = EnhancedDeepResearchProcessor(
        llm_client=None,
        services={},
        event_callback=event_processor.process_event
    )

    # 模擬發送事件
    test_events = [
        ResearchEvent(type="progress", step="plan", data={"status": "start"}),
        ResearchEvent(type="message", step="plan", data={"content": "Test plan"}),
        ResearchEvent(type="progress", step="search", data={"status": "start"}),
        ResearchEvent(type="search_result", step="search", data={"sources_count": 5}),
        ResearchEvent(type="progress", step="final_report", data={"status": "start"}),
        ResearchEvent(type="message", step="final_report", data={"content": "Test report"}),
    ]

    print("\n📡 Sending test events...")
    for event in test_events:
        await processor._emit_event(event)

    # 等待事件處理
    await asyncio.sleep(0.1)

    print(f"\n📊 Event Statistics:")
    print(f"  Plan events: {len(event_processor.plan_events)}")
    print(f"  Search events: {len(event_processor.search_events)}")
    print(f"  Report events: {len(event_processor.report_events)}")


async def main():
    """主測試函數"""
    print("\n🚀 Enhanced Deep Research Processor Tests")
    print("=" * 80)

    # Test 1: Streaming
    # await test_streaming_research()

    # Test 2: Search Engine Fallback
    await test_search_engine_fallback()

    # Test 3: Parallel Search
    await test_parallel_search_execution()

    # Test 4: Event Callbacks
    await test_event_callback_system()

    print("\n" + "=" * 80)
    print("🎉 All Tests Completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())