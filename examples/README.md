# OpenCode Platform - Examples

This directory contains practical examples demonstrating key features of OpenCode Platform.

## 📋 Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **uv** installed
3. **Dependencies** installed: `uv pip install -e ".[dev]"`
4. **API Keys** configured in `.env` file

### Setup

```bash
# From project root
cd opencode_backend

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Ensure .env file exists with API keys
cp .env.example .env
# Edit .env and add your keys
```

---

## 📚 Examples

### 1. Simple Chat (`simple_chat.py`)

**What it demonstrates:**
- Basic engine initialization
- Auto mode routing (System 1 vs System 2)
- Explicit mode selection
- Context passing

**Run:**
```bash
python examples/simple_chat.py
```

**Expected output:**
```
🚀 Initializing OpenCode Platform...
✅ Engine initialized

============================================================
Example 1: Simple Chat (Auto → System 1)
============================================================
Query: What is machine learning?

Selected Mode: chat
Cognitive Level: system1
Response:
Machine learning is a subset of artificial intelligence...
```

**Learn:**
- How the router classifies query complexity
- Difference between System 1 (fast) and System 2 (analytical)
- Basic request/response handling

---

### 2. Code Sandbox (`code_sandbox.py`)

**What it demonstrates:**
- Safe code generation and execution
- Docker sandbox isolation
- Algorithm implementation
- File operations within sandbox

**Run:**
```bash
python examples/code_sandbox.py
```

**Prerequisites:**
- Docker installed and running
- Sufficient permissions to run Docker containers

**Expected output:**
```
🚀 Code Sandbox Examples

============================================================
Example 1: Simple Calculation
============================================================
Response:
Here's a factorial function:

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Test
print(factorial(5))  # Output: 120
```

**Learn:**
- Code generation workflow
- Sandbox safety features
- Error handling in code execution

---

### 3. Multi-Provider (`multi_provider.py`)

**What it demonstrates:**
- Multi-provider fallback chain
- Automatic retry on errors
- Cost optimization strategies
- Error classification (retryable vs non-retryable)

**Run:**
```bash
python examples/multi_provider.py
```

**Prerequisites:**
- At least one LLM API key configured
- Recommended: Configure all 3 providers (OpenAI, Anthropic, Gemini)

**Expected output:**
```
🚀 Multi-Provider LLM Example

✅ OpenAI configured
✅ Anthropic configured
✅ Gemini configured

📊 Active providers: 3

============================================================
Example 1: Normal Operation (Primary Provider)
============================================================
Response: Quantum computing uses quantum mechanics...
Provider Used: OpenAILLMClient
```

**Learn:**
- How fallback chain works
- Provider priority configuration
- Cost optimization techniques
- 99.5% availability through redundancy

---

## 🎯 Coming Soon

### 4. RAG Knowledge Base (`rag_qa.py`) - Q2 2026

**Will demonstrate:**
- Document upload and indexing
- Vector database setup (Qdrant)
- Semantic search
- RAG-based question answering

### 5. Deep Research (`research_assistant.py`) - Q2 2026

**Will demonstrate:**
- Multi-step research workflows
- Agent runtime with stateful execution
- SSE streaming for real-time updates
- Report generation

### 6. Custom Processor (`custom_processor/`) - Q3 2026

**Will demonstrate:**
- Creating custom processors
- Registering with ProcessorFactory
- Implementing BaseProcessor interface
- Testing custom processors

### 7. Production Deployment (`docker-compose/`) - Q3 2026

**Will demonstrate:**
- Full stack deployment
- Docker Compose configuration
- Environment variable management
- Reverse proxy setup (nginx)
- Monitoring and logging

---

## 🛠️ Troubleshooting

### Common Issues

**1. `ModuleNotFoundError: No module named 'src'`**

**Cause:** Running from wrong directory

**Fix:**
```bash
# Run from project root
cd /path/to/openagent_backend
python examples/simple_chat.py
```

**2. `Error: OPENAI_API_KEY environment variable not set`**

**Cause:** Missing API key in environment

**Fix:**
```bash
# Add to .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Or export directly
export OPENAI_API_KEY=sk-your-key-here
```

**3. Docker not running (for `code_sandbox.py`)**

**Cause:** Docker daemon not started

**Fix:**
```bash
# Linux
sudo systemctl start docker

# Mac
# Start Docker Desktop

# Windows
# Start Docker Desktop
```

**4. Rate limit errors**

**Cause:** Exceeded LLM provider rate limit

**Fix:**
```bash
# Configure multiple providers for automatic fallback
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

---

## 📖 Next Steps

After running these examples:

1. **Read the Documentation**
   - [README.md](../README.md) - Full overview
   - [QUICK_START.md](../QUICK_START.md) - Detailed setup guide
   - [API Reference](http://localhost:8000/docs) - When server running

2. **Explore the Code**
   - `src/core/engine.py` - Main engine logic
   - `src/core/processors/` - Processor implementations
   - `src/services/llm/` - LLM integrations

3. **Build Your Own**
   - Modify these examples
   - Create custom processors
   - Integrate with your applications

4. **Contribute**
   - See [CONTRIBUTING.md](../CONTRIBUTING.md)
   - Submit examples you've created
   - Help improve documentation

---

## 💬 Need Help?

- 📚 [Full Documentation](https://docs.opencode.ai)
- 💬 [GitHub Discussions](https://github.com/Zenobia000/openagent_backend/discussions)
- 🐛 [Report Issues](https://github.com/Zenobia000/openagent_backend/issues)
- 📧 Email: support@opencode.ai

---

## 📄 License

All examples are MIT licensed - free to use in your projects.
