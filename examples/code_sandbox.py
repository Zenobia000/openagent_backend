"""
Code Sandbox Example
====================

Demonstrates safe code execution using OpenCode Platform.

This example shows:
- Code generation and execution
- Sandbox safety features
- Error handling
- Result parsing

Requirements:
    - Docker installed and running
    - OPENAI_API_KEY environment variable

Usage:
    python examples/code_sandbox.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.engine import RefactoredEngine
from core.models_v2 import Request
from services.llm.openai_client import OpenAILLMClient


def main():
    """Run code sandbox examples."""

    print("🚀 Code Sandbox Examples\n")

    # Initialize
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        return

    llm_client = OpenAILLMClient(api_key=api_key)
    engine = RefactoredEngine(llm_client=llm_client)

    # Example 1: Simple calculation
    print("=" * 60)
    print("Example 1: Simple Calculation")
    print("=" * 60)

    response1 = engine.process(Request(
        query="Write a Python function to calculate the factorial of a number and test it with factorial(5)",
        mode="code"
    ))

    print("Response:")
    print(response1.content)
    print()

    # Example 2: Data processing
    print("=" * 60)
    print("Example 2: Data Processing")
    print("=" * 60)

    response2 = engine.process(Request(
        query="""
        Create a function that:
        1. Takes a list of numbers
        2. Filters out even numbers
        3. Squares the remaining odd numbers
        4. Returns the sum

        Test with [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        """,
        mode="code"
    ))

    print("Response:")
    print(response2.content)
    print()

    # Example 3: Error handling
    print("=" * 60)
    print("Example 3: Error Handling")
    print("=" * 60)

    response3 = engine.process(Request(
        query="""
        Write a function that safely divides two numbers.
        Handle division by zero gracefully.
        Test with divide(10, 2) and divide(10, 0)
        """,
        mode="code"
    ))

    print("Response:")
    print(response3.content)
    print()

    # Example 4: Algorithm implementation
    print("=" * 60)
    print("Example 4: Algorithm - Quick Sort")
    print("=" * 60)

    response4 = engine.process(Request(
        query="""
        Implement quicksort algorithm in Python.
        Include comments explaining each step.
        Test with [64, 34, 25, 12, 22, 11, 90]
        """,
        mode="code"
    ))

    print("Response:")
    print(response4.content)
    print()

    # Example 5: File operations (within sandbox)
    print("=" * 60)
    print("Example 5: File Operations (Sandbox)")
    print("=" * 60)

    response5 = engine.process(Request(
        query="""
        Write a function that:
        1. Creates a text file in /tmp
        2. Writes 5 lines to it
        3. Reads and prints the content
        4. Returns the line count
        """,
        mode="code"
    ))

    print("Response:")
    print(response5.content)
    print()

    print("=" * 60)
    print("✅ Code sandbox examples completed!")
    print("=" * 60)
    print("\n⚠️  Note: All code executed in isolated Docker containers")
    print("   - No network access")
    print("   - Limited resources (CPU, memory, time)")
    print("   - Read-only filesystem (except /tmp)")


if __name__ == "__main__":
    main()
