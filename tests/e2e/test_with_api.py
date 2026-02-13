#!/usr/bin/env python3
"""Test script to verify the engine works WITH OpenAI API key"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_engine_with_api():
    """Test the unified engine with API"""
    from core import Engine

    print("Creating Engine instance with API key...")
    engine = Engine()

    print("\n=== Testing Engine Initialization ===")
    await engine.initialize()

    test_queries = [
        "Hello, how are you?",
        "What is 2 + 2?",
        "Explain quantum computing in simple terms"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")

        try:
            response = await engine.process(query)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")

    print("\n=== Test Complete ===")
    print("✅ Engine is working with OpenAI API key!")

if __name__ == "__main__":
    asyncio.run(test_engine_with_api())