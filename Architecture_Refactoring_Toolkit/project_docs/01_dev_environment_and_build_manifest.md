# Development Environment & Build Manifest - OpenCode Platform

---

**Document Version:** `v2.2`
**Last Updated:** `2026-02-16`
**Status:** `Current (v3.0 + Context Engineering)`

---

## 1. Overview

This document ensures all developers can set up a consistent development environment within 15 minutes. OpenCode Platform is a cognitive AI engine with a 3-tier architecture (System 1 / System 2 / Agent), dual runtime dispatch, multi-provider LLM fallback chain, and Manus-aligned Context Engineering (v3.1).

---

## 2. System Dependencies

### 2.1 Base Environment

- **OS**: Ubuntu 22.04 LTS / macOS / Windows WSL2
- **Runtime**: Python >= 3.11
- **Package Manager**: pip
- **Container Runtime**: Docker 24.0+ (optional, for sandbox and Qdrant)

### 2.2 External Services (via docker-compose)

| Service | Image | Port | Purpose |
|:---|:---|:---|:---|
| **Qdrant** | `qdrant/qdrant:latest` | `6333` | Vector DB for RAG retrieval |
| **Sandbox** | `build from docker/sandbox/Dockerfile` | internal | Isolated code execution |
| **Redis** | `redis:7-alpine` (optional) | `6379` | Distributed cache |

### 2.3 Core Python Packages

| Category | Key Packages | Version | Purpose |
|:---|:---|:---|:---|
| **Core Framework** | `pydantic`, `pydantic-settings`, `python-dotenv` | `>=2.0.0` | Validation, config, env loading |
| **Web Framework** | `fastapi`, `uvicorn`, `sse-starlette`, `python-multipart` | `>=0.108.0` | REST API, SSE streaming |
| **Async HTTP** | `aiohttp`, `httpx` | `>=3.9.0`, `>=0.25.0` | HTTP clients |
| **LLM Providers** | `openai`, `anthropic`, `google-genai` | `>=1.0.0`, `>=0.40.0`, `>=1.0.0` | Multi-provider LLM (OpenAI, Claude, Gemini) |
| **Embeddings** | `cohere` | `>=5.0.0` | Multilingual embeddings + reranking |
| **Vector DB** | `qdrant-client` | `>=1.7.0` | Vector database client |
| **Document Processing** | `pymupdf`, `PyPDF2`, `python-docx`, `pandas`, `openpyxl`, `pillow`, `pyyaml` | see `requirements.txt` | Multimodal document parsing |
| **Authentication** | `python-jose[cryptography]`, `passlib`, `email-validator` | `>=3.3.0`, `>=1.7.4`, `>=2.0.0` | JWT auth |
| **Web Search** | `duckduckgo-search`, `beautifulsoup4`, `wikipedia` | `>=6.0.0`, `>=4.12.0`, `>=1.4.0` | Web search engines |
| **Container** | `docker` | `>=7.0.0` | Sandbox code execution |
| **CLI** | `typer`, `rich` | `>=0.9.0`, `>=13.0.0` | CLI interface |
| **Logging** | `structlog` | `>=23.0.0` | Structured logging |

---

## 3. Environment Variables

Create `.env` in project root (reference `.env.example`).

| Variable | Required | Default | Description |
|:---|:---:|:---|:---|
| **LLM Providers** |
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key (primary LLM) |
| `ANTHROPIC_API_KEY` | No | - | Anthropic API key (fallback LLM) |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | No | - | Google Gemini API key (fallback LLM) |
| `LLM_MODEL` | No | `gpt-4o-mini` | Default OpenAI model |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-5-20250929` | Default Claude model |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Default Gemini model |
| **Embeddings** |
| `COHERE_API_KEY` | No | - | Cohere embedding/reranking |
| `EMBEDDING_PROVIDER` | No | `cohere` | `cohere` or `openai` |
| **Authentication** |
| `JWT_SECRET_KEY` | No | `dev-secret-key-change-in-production` | JWT signing secret |
| `JWT_EXPIRE_MINUTES` | No | `60` | Token expiry (minutes) |
| **Vector Database** |
| `QDRANT_HOST` | No | `localhost` | Qdrant server address |
| `QDRANT_PORT` | No | `6333` | Qdrant HTTP port |
| **Web Search** |
| `TAVILY_API_KEY` | No | - | Tavily search API key |
| `SERPAPI_KEY` | No | - | SerpAPI key |
| `SERPER_API_KEY` | No | - | Serper API key |
| **Server** |
| `API_HOST` | No | `0.0.0.0` | API bind address |
| `API_PORT` | No | `8888` | API server port |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |
| **Debug** |
| `DEBUG` | No | `false` | Debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |

*At least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY is required.

---

## 4. Build & Run Commands

### 4.1 Quick Start (Local)

```bash
cd openagent_backend

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with at least one LLM API key
```

### 4.2 CLI Mode

```bash
python main.py          # Interactive chat
python main.py test     # Run tests
python main.py help     # Help
```

### 4.3 API Server Mode

```bash
cd src && python -c "
import uvicorn
from api.routes import create_app
uvicorn.run(create_app(), host='0.0.0.0', port=8000)
"
```

The API server auto-creates the engine from env vars via `create_llm_client()`.

### 4.4 Docker Development

```bash
docker-compose up -d qdrant        # Start vector DB
docker-compose up -d --build       # Start all services
docker-compose logs -f backend     # View logs
```

### 4.5 Testing

```bash
# Run all tests
python3 -m pytest tests/ -o "addopts="

# By category
python3 -m pytest tests/unit/ -o "addopts="
python3 -m pytest tests/integration/ -o "addopts="
python3 -m pytest tests/e2e/ -o "addopts="

# Context Engineering tests
python3 -m pytest tests/core/context/ -o "addopts="     # CE unit tests
python3 -m pytest tests/core/routing/ -o "addopts="     # Tool mask tests
python3 -m pytest tests/performance/ -o "addopts="       # Performance benchmarks
python3 -m pytest tests/integration/test_context_engineering.py -o "addopts="
```

---

## 5. Troubleshooting

| Problem | Solution |
|:---|:---|
| No LLM API key | Set at least one of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` in `.env` |
| `ModuleNotFoundError` | Run from project root; `main.py` adds `src/` to path automatically |
| `pytest-cov` not installed | Use `-o "addopts="` to override pyproject.toml coverage flags |
| Unicode crash in WSL2 | Fixed in `core/logger.py` (surrogate sanitization) |
| Context Engineering not active | All CE flags default OFF in `config/cognitive_features.yaml`. Enable `context_engineering.enabled` master switch first, then individual flags |

---

## 6. IDE Setup

### VSCode Recommended Settings

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests", "-o", "addopts="],
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.formatOnSave": true
    }
}
```

### Recommended Extensions

- `ms-python.python`
- `ms-python.vscode-pylance`
- `ms-azuretools.vscode-docker`
- `charliermarsh.ruff`
