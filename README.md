<p align="center">
  <img src="docs/images/logo.png" alt="OpenCode Platform" width="200" />
</p>

<h1 align="center">OpenCode Platform</h1>

<p align="center">
  <strong>Cognitive AI Engine | Dual Runtime Architecture | RAG Knowledge Base | Code Sandbox</strong>
</p>

<p align="center">
  <a href="#architecture">Architecture</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#api-reference">API Reference</a> &bull;
  <a href="#processing-modes">Processing Modes</a> &bull;
  <a href="#feature-flags">Feature Flags</a> &bull;
  <a href="#testing">Testing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python" />
  <img src="https://img.shields.io/badge/fastapi-0.128+-009688.svg" alt="FastAPI" />
  <img src="https://img.shields.io/badge/tests-165%2B_passing-brightgreen.svg" alt="Tests" />
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License" />
</p>

---

## Overview

**OpenCode Platform** is a cognitive AI processing engine built on a 3-tier architecture inspired by dual-process theory:

- **System 1** (Fast) -- Cached, low-latency responses for chat and knowledge retrieval
- **System 2** (Analytical) -- Deep reasoning for search, code generation, and thinking tasks
- **Agent** (Autonomous) -- Stateful, multi-step workflows with retry and error recovery

The engine uses a Router to classify request complexity, then dispatches to the appropriate runtime (ModelRuntime or AgentRuntime) for execution.

---

## Architecture

```
                         Request
                           |
                           v
                   +---------------+
                   |   API Layer   |   FastAPI + JWT Auth + SSE Streaming
                   |   (routes)    |   11 versioned endpoints
                   +-------+-------+
                           |
                           v
                +----------+----------+
                |  RefactoredEngine   |   Router + Dual Runtime dispatch
                |  (Metrics, Flags)   |   Feature-flagged cognitive features
                +----------+----------+
                           |
                    +------+------+
                    |   Router    |   ComplexityAnalyzer (smart routing)
                    +------+------+
                           |
              +------------+------------+
              |                         |
     +--------v--------+      +--------v--------+
     |  ModelRuntime    |      |  AgentRuntime   |
     |  (System 1 + 2) |      |  (Agent level)  |
     |  Stateless       |      |  Stateful       |
     |  Cached          |      |  Retry + Recovery|
     +--------+---------+      +--------+---------+
              |                         |
     +--------v--------+      +--------v--------+
     | ProcessorFactory |      | WorkflowOrch.  |
     | 6 Processors     |      | Multi-step     |
     +---------+--------+      +--------+--------+
               |                        |
               v                        v
     +---------+---------+    +---------+---------+
     |   Services Layer  |    |   Services Layer  |
     | LLM | RAG | Search|    | LLM | Research    |
     | Sandbox | Browser |    | Browser | Repo    |
     +-------------------+    +-------------------+
```

### Three Cognitive Levels

| Level | Modes | Runtime | Characteristics |
|-------|-------|---------|-----------------|
| **System 1** | `chat`, `knowledge` | ModelRuntime | Fast, cacheable, low-latency |
| **System 2** | `search`, `code`, `thinking` | ModelRuntime | Analytical, multi-step reasoning |
| **Agent** | `deep_research` | AgentRuntime | Stateful workflows, retry, error recovery |

---

## Project Structure

```
openagent_backend/
├── main.py                        # CLI entry point
├── config/
│   └── cognitive_features.yaml    # Feature flag configuration
├── src/
│   ├── core/                      # Core engine layer
│   │   ├── engine.py              # RefactoredEngine (router + runtime dispatch)
│   │   ├── router.py              # DefaultRouter + ComplexityAnalyzer
│   │   ├── processor.py           # ProcessorFactory + 6 processors
│   │   ├── models.py              # Request, Response, ProcessingContext, EventType
│   │   ├── feature_flags.py       # FeatureFlags (YAML-driven)
│   │   ├── cache.py               # ResponseCache (TTL, eviction, stats)
│   │   ├── metrics.py             # CognitiveMetrics (per-level tracking)
│   │   ├── errors.py              # ErrorClassifier, retry, fallback
│   │   ├── protocols.py           # Service/Router/Runtime protocols
│   │   ├── runtime/
│   │   │   ├── model_runtime.py   # System 1+2 (stateless, cached)
│   │   │   ├── agent_runtime.py   # Agent workflows (stateful, retry)
│   │   │   └── workflow.py        # WorkflowOrchestrator
│   │   ├── prompts.py             # 17 prompt templates
│   │   └── logger.py              # Structured logging
│   ├── api/                       # API layer
│   │   ├── routes.py              # FastAPI app + all endpoints
│   │   ├── schemas.py             # Pydantic request/response models
│   │   ├── streaming.py           # SSE async generator bridge
│   │   ├── errors.py              # APIError + error handlers
│   │   └── middleware.py          # Request logging middleware
│   ├── auth/                      # Authentication
│   │   ├── jwt.py                 # JWT encode/decode (python-jose)
│   │   └── dependencies.py        # get_current_user FastAPI Depends
│   └── services/                  # Service layer
│       ├── llm/openai_client.py   # OpenAI LLM client
│       ├── knowledge/             # RAG knowledge base
│       ├── search/                # Web search (multi-engine)
│       ├── sandbox/               # Docker code execution
│       ├── research/              # Deep research service
│       ├── browser/               # Web browsing service
│       └── repo/                  # Git operations
├── tests/
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── e2e/                       # End-to-end tests
├── plugins/                       # Plugin directory
├── docs/                          # Documentation
└── .env                           # Environment variables
```

---

## Quick Start

### Prerequisites

- **Python** 3.10+
- **Docker** (optional, for sandbox and Qdrant)

### 1. Environment Setup

```bash
cd openagent_backend

python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

### 2. CLI Mode

```bash
python main.py          # Interactive chat
python main.py test     # Run tests
python main.py help     # Help
```

### 3. API Server

```bash
cd src && python -c "
import uvicorn
from api.routes import create_app
from core.engine import RefactoredEngine
from services.llm.openai_client import OpenAILLMClient
import os

llm = OpenAILLMClient(api_key=os.getenv('OPENAI_API_KEY'))
engine = RefactoredEngine(llm_client=llm)
app = create_app(engine=engine)
uvicorn.run(app, host='0.0.0.0', port=8000)
"
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. API Usage

```bash
# Get a JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Chat
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello", "mode": "chat"}'

# Stream (SSE)
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain quantum computing", "mode": "thinking"}'
```

---

## API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Platform info |
| `/health` | GET | No | Health check |
| `/api/status` | GET | No | Engine status |
| `/api/v1/auth/token` | POST | No | Get JWT token |
| `/api/v1/chat` | POST | Yes | Sync chat |
| `/api/v1/chat/stream` | POST | Yes | SSE streaming chat |
| `/api/v1/documents/upload` | POST | Yes | Upload document |
| `/api/v1/documents/status/{id}` | GET | Yes | Check upload status |
| `/api/v1/search` | POST | Yes | Semantic search |
| `/api/v1/sandbox/execute` | POST | Yes | Execute code |
| `/api/v1/metrics` | GET | Yes | Cognitive metrics |

Full interactive docs available at `/docs` when the server is running.

---

## Processing Modes

| Mode | Cognitive Level | Runtime | Description |
|------|----------------|---------|-------------|
| `chat` | System 1 | ModelRuntime | General conversation (cacheable) |
| `knowledge` | System 1 | ModelRuntime | RAG knowledge retrieval (cacheable) |
| `search` | System 2 | ModelRuntime | Web search with analysis |
| `code` | System 2 | ModelRuntime | Code generation and execution |
| `thinking` | System 2 | ModelRuntime | Deep reasoning and analysis |
| `deep_research` | Agent | AgentRuntime | Multi-step research workflows |
| `auto` | -- | Router decides | Automatic mode selection |

---

## Feature Flags

All cognitive features are controlled via `config/cognitive_features.yaml` and default to **OFF** for backward compatibility:

```yaml
cognitive_features:
  enabled: false          # Master switch
  system1:
    enable_cache: false   # Response cache for CHAT/KNOWLEDGE
  routing:
    smart_routing: false  # Dual runtime dispatch via ComplexityAnalyzer
  metrics:
    cognitive_metrics: false  # Per-level request tracking
```

When all flags are OFF, the system behaves identically to pre-refactoring.

### Key Components

| Component | Flag | Description |
|-----------|------|-------------|
| **ResponseCache** | `system1.enable_cache` | SHA-256 keyed cache with TTL and LRU eviction |
| **CognitiveMetrics** | `metrics.cognitive_metrics` | Per-level latency, success rate, token tracking |
| **SmartRouting** | `routing.smart_routing` | ComplexityAnalyzer-based runtime dispatch |
| **ErrorClassifier** | Always active | 5-category classification with retry/fallback |

---

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | Yes | OpenAI API key | -- |
| `JWT_SECRET` | No | JWT signing secret | `dev-secret-key` |
| `JWT_ALGORITHM` | No | JWT algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | No | Token expiry | `1440` |
| `LOG_LEVEL` | No | Logging level | `INFO` |

---

## Testing

```bash
# Run all tests (exclude known legacy tests)
python3 -m pytest tests/ -o "addopts=" \
  --ignore=tests/unit/test_engine.py \
  --ignore=tests/unit/test_refactored_engine.py

# Run by category
python3 -m pytest tests/unit/ -o "addopts="           # Unit tests
python3 -m pytest tests/integration/ -o "addopts="     # Integration tests
python3 -m pytest tests/e2e/ -o "addopts="             # E2E tests

# Run specific test files
python3 -m pytest tests/unit/test_cache.py -v -o "addopts="
python3 -m pytest tests/integration/test_api.py -v -o "addopts="
```

### Test Coverage

| Category | Tests | Covers |
|----------|-------|--------|
| Unit | 90+ | Feature flags, router, cache, metrics, errors, auth, processors |
| Integration | 20+ | API endpoints, SSE streaming, runtime dispatch |
| E2E | 50+ | All processing modes end-to-end |

---

## Services

| Service | Description |
|---------|-------------|
| **LLM (OpenAI)** | GPT model client with streaming support |
| **Knowledge (RAG)** | Document upload, indexing, semantic retrieval |
| **Search** | Multi-engine web search (DuckDuckGo, Wikipedia, arXiv) |
| **Sandbox** | Docker-based Python/Bash code execution |
| **Research** | Deep multi-step research with report generation |
| **Browser** | Web page fetching and content extraction |
| **Repo** | Git repository operations |

---

## Troubleshooting

**`OPENAI_API_KEY` not set**: Create `.env` in project root with `OPENAI_API_KEY=sk-...`

**`ModuleNotFoundError`**: Run from project root. The `src/` path is added automatically by `main.py`.

**`pytest-cov` not installed**: Use `-o "addopts="` to override pyproject.toml coverage flags.

**Import errors in `test_engine.py` / `test_refactored_engine.py`**: Legacy test files with broken imports. Exclude them with `--ignore`.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built by OpenCode Team</sub>
</p>
