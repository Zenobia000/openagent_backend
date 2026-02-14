"""
Simple Chat Example
===================

Demonstrates basic chat interaction with OpenCode Platform.

This example shows:
- Engine initialization
- Simple chat queries
- Auto mode routing
- Response handling

Usage:
    python examples/simple_chat.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.engine import RefactoredEngine
from core.models import Request
from services.llm.openai_client import OpenAILLMClient


def main():
    """Run simple chat examples."""

    # Initialize
    print("🚀 Initializing OpenCode Platform...")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Set it in .env file or export OPENAI_API_KEY=your-key")
        return

    llm_client = OpenAILLMClient(api_key=api_key)
    engine = RefactoredEngine(llm_client=llm_client)

    print("✅ Engine initialized\n")

    # Example 1: Simple chat (System 1)
    print("=" * 60)
    print("Example 1: Simple Chat (Auto → System 1)")
    print("=" * 60)

    query1 = "What is machine learning?"
    print(f"Query: {query1}")

    response1 = engine.process(Request(
        query=query1,
        mode="auto"  # Let router decide
    ))

    print(f"\nSelected Mode: {response1.metadata.get('selected_mode', 'N/A')}")
    print(f"Cognitive Level: {response1.metadata.get('cognitive_level', 'N/A')}")
    print(f"Response:\n{response1.content[:200]}...\n")

    # Example 2: Complex query (System 2)
    print("=" * 60)
    print("Example 2: Analytical Question (Auto → System 2)")
    print("=" * 60)

    query2 = "Compare supervised and unsupervised learning approaches"
    print(f"Query: {query2}")

    response2 = engine.process(Request(
        query=query2,
        mode="auto"
    ))

    print(f"\nSelected Mode: {response2.metadata.get('selected_mode', 'N/A')}")
    print(f"Cognitive Level: {response2.metadata.get('cognitive_level', 'N/A')}")
    print(f"Response:\n{response2.content[:200]}...\n")

    # Example 3: Explicit mode selection
    print("=" * 60)
    print("Example 3: Explicit Mode (Chat)")
    print("=" * 60)

    query3 = "Hello, how are you?"
    print(f"Query: {query3}")

    response3 = engine.process(Request(
        query=query3,
        mode="chat"  # Explicitly use chat mode
    ))

    print(f"\nSelected Mode: chat")
    print(f"Cognitive Level: {response3.metadata.get('cognitive_level', 'N/A')}")
    print(f"Response:\n{response3.content}\n")

    # Example 4: With context
    print("=" * 60)
    print("Example 4: Chat with Context")
    print("=" * 60)

    response4 = engine.process(Request(
        query="What was my previous question?",
        mode="chat",
        context={"previous_query": query3}
    ))

    print(f"Response:\n{response4.content}\n")

    print("=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
