#!/usr/bin/env python3
"""
OpenCode Platform - 單一入口點
使用核心 logger.py 的專業日誌系統
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.engine import RefactoredEngine
from core.models import Request, ProcessingMode
from core.logger import structured_logger as logger
from services.llm import create_llm_client


async def chat_mode():
    """對話模式 - 使用核心 logger"""

    # 初始化 LLM
    logger.info("="*50, "main", "initialize")
    logger.info("🚀 Initializing OpenCode Platform", "main", "initialize")
    logger.info("="*50, "main", "initialize")

    try:
        llm_client = create_llm_client()
    except ValueError as e:
        logger.error(f"❌ {e}", "main", "chat_mode")
        print(f"請在 .env 檔案中設置 LLM API Key (OPENAI_API_KEY, ANTHROPIC_API_KEY, 或 GEMINI_API_KEY)")
        return
    logger.info(f"✅ LLM Client initialized: {llm_client.provider_name}", "main", "initialize")

    engine = RefactoredEngine(llm_client=llm_client)
    await engine.initialize()
    logger.info("✅ AI Engine initialized successfully", "main", "initialize")

    # 模式映射
    modes = {
        "auto": ProcessingMode.AUTO,
        "chat": ProcessingMode.CHAT,
        "think": ProcessingMode.THINKING,
        "thinking": ProcessingMode.THINKING,
        "knowledge": ProcessingMode.KNOWLEDGE,
        "search": ProcessingMode.SEARCH,
        "code": ProcessingMode.CODE,
        "research": ProcessingMode.DEEP_RESEARCH,
        "deep": ProcessingMode.DEEP_RESEARCH,
        "deep_research": ProcessingMode.DEEP_RESEARCH,
    }

    print("\n" + "="*50)
    print("OpenCode Platform - Cognitive AI Engine")
    print("="*50)
    print("命令:")
    print("  /mode <模式> - 切換模式 (auto/chat/thinking/knowledge/search/code/research)")
    print("  /help       - 顯示幫助")
    print("  /exit       - 退出")
    print("-"*50)

    current_mode = ProcessingMode.AUTO
    session_start = datetime.now()
    query_count = 0

    while True:
        try:
            # 顯示提示符
            prompt = f"[{current_mode.value}]> "
            raw_input = input(prompt).strip()
            # Sanitize surrogate characters from WSL2 terminal
            user_input = raw_input.encode('utf-8', errors='replace').decode('utf-8')

            # 處理命令
            if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                session_duration = (datetime.now() - session_start).seconds
                logger.info(
                    f"👋 Session ended: duration={session_duration}s, queries={query_count}",
                    "main", "session_end"
                )
                print("👋 再見！")
                break

            elif user_input.lower() == '/help':
                print("\n可用模式:")
                print("  auto     - 自動分類 (Router 根據查詢內容選擇最佳模式)")
                print("  ─── System 1 (快速回應, 可快取) ───")
                print("  chat     - 一般對話")
                print("  knowledge - 知識檢索 (RAG)")
                print("  ─── System 2 (深度分析, 多步驟) ───")
                print("  thinking - 深度思考")
                print("  search   - 網路搜索")
                print("  code     - 代碼執行 (Docker 沙箱)")
                print("  ─── Agent (有狀態工作流, 自動重試) ───")
                print("  research - 深度研究 (完整研究報告)\n")
                continue

            elif user_input.lower().startswith('/mode'):
                parts = user_input.split()
                if len(parts) > 1 and parts[1] in modes:
                    old_mode = current_mode.value
                    current_mode = modes[parts[1]]
                    logger.info(
                        f"🔄 Mode switched: {old_mode} -> {current_mode.value}",
                        "main", "mode_switch"
                    )
                    print(f"✅ 切換到 {current_mode.value} 模式\n")
                else:
                    logger.warning(
                        f"Invalid mode: {parts[1] if len(parts) > 1 else 'none'}",
                        "main", "mode_switch"
                    )
                    print(f"❌ 無效模式。可用: {', '.join(modes.keys())}\n")
                continue

            elif user_input:
                query_count += 1
                start_time = time.time()

                # 設置追蹤 ID
                request = Request(query=user_input, mode=current_mode)
                logger.set_trace(request.trace_id)

                # 記錄接收請求
                logger.info(
                    f"📥 Received request: mode={current_mode.value}, query='{user_input[:50]}...'",
                    "main", "process"
                )

                # 顯示處理狀態
                logger.info(f"🌐 Processing with mode: {current_mode.value}", "main", "process")

                # 根據模式顯示不同的處理資訊
                if current_mode == ProcessingMode.THINKING:
                    logger.info("🧠 Starting deep thinking process...", "main", "thinking")
                elif current_mode == ProcessingMode.KNOWLEDGE:
                    logger.info("📚 Retrieving from knowledge base...", "main", "knowledge")
                elif current_mode == ProcessingMode.SEARCH:
                    logger.info("🔍 Searching web...", "main", "search")
                elif current_mode == ProcessingMode.CODE:
                    logger.info("💻 Preparing code execution...", "main", "code")
                elif current_mode == ProcessingMode.DEEP_RESEARCH:
                    logger.info("🔬 Starting deep research process...", "main", "deep_research")

                # 使用 logger 的性能測量
                with logger.measure("process_request"):
                    response = await engine.process(request)

                # 計算處理時間
                elapsed_time = (time.time() - start_time) * 1000

                # 記錄完成
                logger.info(
                    f"✅ Processing completed: time={elapsed_time:.0f}ms",
                    "main", "process"
                )

                # 顯示結果
                print("\n" + "="*50)
                print("📊 回應:")
                print("="*50)
                print(response.result)
                print("="*50)

                # 顯示處理資訊
                resolved_mode = response.mode
                cognitive = resolved_mode.cognitive_level
                print(f"\n📈 處理資訊:")
                print(f"  🧠 認知層級: {cognitive} | 模式: {resolved_mode.value}" +
                      (f" (auto -> {resolved_mode.value})" if current_mode == ProcessingMode.AUTO else ""))
                print(f"  ⏱️  處理時間: {elapsed_time:.0f}ms")
                print(f"  📊 Token 使用: {response.tokens_used if response.tokens_used > 0 else 'N/A'}")
                print(f"  🔗 LLM 提供者: {llm_client.provider_name}")
                print(f"  🔍 追蹤 ID: {request.trace_id[:8]}...")
                print()

                # 清除追蹤 ID
                logger.clear_context()

        except KeyboardInterrupt:
            logger.warning("Session interrupted by user", "main", "interrupt")
            print("\n👋 再見！")
            break
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}", "main", "error")
            logger.log_error(e)
            print(f"❌ 錯誤: {e}\n")


async def test_mode():
    """測試模式 - 驗證系統功能"""

    logger.info("🧪 Starting test suite...", "main", "test_mode")

    try:
        llm_client = create_llm_client()
    except ValueError as e:
        logger.error(f"❌ {e}", "main", "test_mode")
        return
    engine = RefactoredEngine(llm_client=llm_client)
    await engine.initialize()

    tests = [
        ("Hello", ProcessingMode.CHAT),
        ("1+1=?", ProcessingMode.THINKING),
        ("What is RAG?", ProcessingMode.KNOWLEDGE),
        ("Explain quantum computing", ProcessingMode.DEEP_RESEARCH),
    ]

    for i, (query, mode) in enumerate(tests, 1):
        logger.info(
            f"Running test {i}/{len(tests)}: query='{query}', mode={mode.value}",
            "main", "test"
        )
        request = Request(query=query, mode=mode)

        with logger.measure(f"test_{i}"):
            response = await engine.process(request)

        logger.info(f"✅ Test {i} passed - {len(response.result)} chars", "main", "test")

    logger.info("✅ All tests completed successfully!", "main", "test_mode")


def main():
    """主函數"""

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "test":
            asyncio.run(test_mode())
        elif command == "help":
            print_help()
        else:
            print(f"未知命令: {command}")
            print_help()
    else:
        # 預設進入對話模式
        asyncio.run(chat_mode())


def print_help():
    """顯示幫助"""
    print("""
OpenCode Platform - Cognitive AI Engine

使用方式:
  python main.py         # 進入對話模式（預設 auto 模式）
  python main.py test    # 運行測試
  python main.py help    # 顯示此幫助

對話模式命令:
  /mode <模式>  - 切換處理模式
  /help        - 顯示可用模式與認知層級
  /exit        - 退出程式

可用模式:
  auto     - 自動分類 (Router 智慧選擇)
  chat     - 一般對話          [System 1]
  knowledge - 知識檢索 (RAG)   [System 1]
  thinking - 深度思考           [System 2]
  search   - 網路搜索           [System 2]
  code     - 代碼執行           [System 2]
  research - 深度研究報告       [Agent]

認知架構:
  System 1 - 快速回應, 可快取
  System 2 - 深度分析, 多步驟
  Agent    - 有狀態工作流, 自動重試

LLM 提供者:
  自動偵測 .env 中可用的 API Key
  Fallback: OpenAI -> Anthropic -> Gemini
    """)


if __name__ == "__main__":
    main()