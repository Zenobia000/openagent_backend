#!/usr/bin/env python3
"""測試深度研究的 LLM 生成（無 token 限制）"""

import asyncio
import os
import sys
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

async def test_deep_research():
    """測試深度研究的長文本生成"""
    from src.services.llm import create_llm_client

    # 獲取 LLM client
    client = create_llm_client()

    print(f"Testing LLM client: {client.__class__.__name__}")
    print(f"Model: {getattr(client, 'model', 'unknown')}")

    # 測試深度研究的複雜 prompt
    research_prompt = """Based on the following research context, generate a comprehensive academic report.

Research Context:
- AI agents and cognitive architectures
- Neural system integration
- Human-like thinking patterns
- Memory consolidation mechanisms
- Attention and executive control

Requirements:
1. Write in academic style with clear sections
2. Make the report comprehensive and detailed (aim for 1000+ words)
3. Structure with clear headings using ## for main sections

Generate a detailed report about how AI agents can integrate neural system principles to achieve human-like cognitive capabilities:"""

    try:
        print("\n測試深度研究報告生成（無 token 限制）...")
        print("正在生成報告...")

        response = await client.generate(research_prompt, return_token_info=True)

        if isinstance(response, tuple):
            report, token_info = response
            print(f"\n生成的報告長度: {len(report)} 字符")
            print(f"Token 使用情況: {token_info}")
            print(f"\n報告前 500 字符預覽:")
            print("-" * 50)
            print(report[:500])
            print("-" * 50)

            # 檢查是否為空響應
            if not report or report.strip() == "":
                print("⚠️ 警告：生成了空響應！")
            elif len(report) < 100:
                print(f"⚠️ 警告：響應太短 ({len(report)} 字符)")
            else:
                print(f"✅ 成功生成報告：{len(report)} 字符")
        else:
            print(f"Response: {response}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deep_research())