#!/usr/bin/env python3
"""
測試 LLM Call 和 LLM Response 的區別
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.core.processor import ThinkingProcessor
from src.core.models import Request, Response, ProcessingContext
from src.core.logger import structured_logger

async def test_llm_logging():
    """測試 LLM 日誌輸出"""

    print("=" * 80)
    print("🧪 測試 LLM Call 和 LLM Response 日誌")
    print("=" * 80)
    print()

    # 創建 mock LLM client
    mock_llm = AsyncMock()

    # 模擬 LLM 回應
    mock_response = """## Deep Analysis of the Query

This is a comprehensive response from the LLM that includes:
1. Problem understanding
2. Critical analysis
3. Deep reasoning
4. Synthesis and conclusion

The response demonstrates how the LLM processes and responds to queries with detailed analysis and structured output."""

    # 設置 mock 返回值 (包含 token 資訊)
    mock_llm.generate.return_value = (
        mock_response,
        {
            "prompt_tokens": 125,
            "completion_tokens": 89,
            "total_tokens": 214
        }
    )

    # 創建處理器
    processor = ThinkingProcessor(structured_logger)
    processor.llm_client = mock_llm

    # 創建請求上下文
    request = Request(query="測試查詢：LLM 日誌區別", mode="thinking")
    response = Response(result="", mode="thinking", trace_id="test-trace-123")
    context = ProcessingContext(request=request, response=response)

    print("📝 發送測試查詢...")
    print("-" * 40)

    # 調用 _call_llm
    response = await processor._call_llm("Test prompt for LLM logging", context)

    print("\n" + "=" * 80)
    print("✅ 測試結果說明：")
    print("-" * 40)
    print()
    print("你應該看到兩種不同的日誌：")
    print()
    print("1. 🤖 LLM Call: gpt-4o")
    print("   - 顯示 token 數量 (tokens=214)")
    print("   - 顯示執行時間 (time=XXXms)")
    print("   - 用於性能監控")
    print()
    print("2. 💬 LLM Response: ## Deep Analysis...")
    print("   - 顯示實際生成的內容（前500字符）")
    print("   - 用於調試和追蹤 LLM 輸出")
    print()
    print("這兩種日誌服務不同的目的，都是調試和監控所必需的。")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_llm_logging())