#!/usr/bin/env python3
"""測試 LLM API 連接"""

import asyncio
import os
import sys
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

async def test_llm():
    """測試 LLM 連接"""
    from src.services.llm import create_llm_client

    # 獲取 LLM client
    client = create_llm_client()

    print(f"Testing LLM client: {client.__class__.__name__}")
    print(f"Model: {getattr(client, 'model', 'unknown')}")

    # 測試簡單查詢
    test_prompt = "Say 'Hello, World!' and nothing else."

    try:
        print("\n測試基本生成（沒有指定 max_tokens）...")
        response = await client.generate(test_prompt)
        print(f"Response: {response}")

        print("\n測試帶 token 信息的生成（沒有指定 max_tokens）...")
        response_with_tokens = await client.generate(test_prompt, return_token_info=True)
        if isinstance(response_with_tokens, tuple):
            response, token_info = response_with_tokens
            print(f"Response: {response}")
            print(f"Token info: {token_info}")
        else:
            print(f"Response: {response_with_tokens}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm())