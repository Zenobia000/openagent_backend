#!/usr/bin/env python3
"""Test the code extraction fix"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.processor import CodeProcessor
from core.models_v2 import ProcessingContext, Request, Modes

async def test_code_extraction():
    """Test the code extraction from LLM response"""

    processor = CodeProcessor(llm_client=None, services={})

    # Test case 1: Response with ```python block
    test_response1 = """可以使用 Python 來生成費波那契數列（Fibonacci sequence）的前 20 項。以下是一個簡單的函數來完成這個任務：

```python
def fibonacci_sequence(n):
    # 檢查輸入的值是否有效
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    # 初始化序列的前兩項
    sequence = [0, 1]

    # 計算序列的其餘部分
    for i in range(2, n):
        next_value = sequence[i-1] + sequence[i-2]
        sequence.append(next_value)

    return sequence

# 計算前 20 項的費波那契數列
fibonacci_20 = fibonacci_sequence(20)
print(fibonacci_20)
```

這個函數會返回一個包含前 20 項費波那契數列的列表。"""

    extracted = processor._extract_code_from_response(test_response1)
    print("Test 1 - Response with ```python block:")
    print("-" * 40)
    print(extracted)
    print("-" * 40)

    # Verify the extracted code doesn't contain the Chinese explanation
    assert "可以使用" not in extracted
    assert "def fibonacci_sequence" in extracted
    print("✓ Test 1 passed\n")

    # Test case 2: Response with plain ``` block
    test_response2 = """Here's the code:

```
def hello():
    print("Hello, world!")

hello()
```

This will print Hello, world!"""

    extracted = processor._extract_code_from_response(test_response2)
    print("Test 2 - Response with plain ``` block:")
    print("-" * 40)
    print(extracted)
    print("-" * 40)

    assert "Here's the code" not in extracted
    assert "def hello" in extracted
    print("✓ Test 2 passed\n")

    # Test case 3: Response without code blocks
    test_response3 = """以下是程式碼：

def test_function():
    return 42

result = test_function()
print(result)"""

    extracted = processor._extract_code_from_response(test_response3)
    print("Test 3 - Response without code blocks:")
    print("-" * 40)
    print(extracted)
    print("-" * 40)

    assert "以下是程式碼" not in extracted
    assert "def test_function" in extracted
    print("✓ Test 3 passed\n")

    # Test that the extracted code can be compiled
    try:
        compile(extracted, '<test>', 'exec')
        print("✓ All extracted code is valid Python\n")
    except SyntaxError as e:
        print(f"✗ Syntax error in extracted code: {e}\n")
        return False

    return True

if __name__ == "__main__":
    if asyncio.run(test_code_extraction()):
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)