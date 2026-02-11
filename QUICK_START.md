# OpenCode Platform - Quick Start Guide

## System Status

- **Engine**: RefactoredEngine with Router + Dual Runtime dispatch
- **API**: FastAPI with JWT auth, SSE streaming, 11 endpoints
- **Architecture**: Cognitive 3-tier (System 1 / System 2 / Agent)
- **LLM**: Multi-Provider fallback chain (OpenAI -> Anthropic -> Gemini)
- **Feature Flags**: YAML-driven, all flags default OFF for backward compatibility
- **Tests**: 182+ passing (unit / integration / e2e)

## Project Structure

```
openagent_backend/
├── main.py                        # CLI entry point (default: auto mode)
├── config/
│   └── cognitive_features.yaml    # Feature flag config
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
│   │   ├── runtime/               # Dual runtime system
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
│       ├── llm/                   # Multi-Provider LLM
│       │   ├── base.py            # LLMProvider ABC
│       │   ├── openai_client.py   # OpenAI (GPT-4o)
│       │   ├── anthropic_client.py # Anthropic (Claude)
│       │   ├── gemini_client.py   # Gemini
│       │   └── multi_provider.py  # Fallback chain orchestrator
│       ├── knowledge/             # RAG knowledge base
│       ├── search/                # Web search (multi-engine)
│       ├── sandbox/               # Docker code execution
│       ├── research/              # Deep research service
│       ├── browser/               # Web browsing service
│       └── repo/                  # Git operations
├── tests/
│   ├── unit/                      # Unit tests (feature_flags, router, cache, metrics, errors, auth, multi_provider)
│   ├── integration/               # Integration tests (runtimes, API, SSE)
│   └── e2e/                       # End-to-end tests (all modes)
├── docs/
│   ├── REFACTORING_CHECKLIST.md   # Phase tracking (P0-P4 complete)
│   └── CODE_AUDIT_REPORT.md       # Code audit results
└── .env                           # Environment variables
```

## Quick Start

### 1. Environment Setup

```bash
cd openagent_backend

python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set at least one LLM API key:
#   OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY
```

### 2. CLI Mode

```bash
# Interactive chat (default: auto mode, Router selects best mode)
python main.py

# Run tests
python main.py test

# Help
python main.py help
```

### 3. API Server Mode

```bash
cd src && python -c "
import uvicorn
from api.routes import create_app
uvicorn.run(create_app(), host='0.0.0.0', port=8000)
"
```

Then visit:
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. API Usage

```bash
# Get a JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Chat (with token)
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

## Processing Modes

| Mode | Cognitive Level | Runtime | Description |
|------|----------------|---------|-------------|
| `auto` | Router decides | Router decides | Automatic mode selection (default) |
| `chat` | System 1 | ModelRuntime | General conversation (cacheable) |
| `knowledge` | System 1 | ModelRuntime | RAG knowledge retrieval (cacheable) |
| `search` | System 2 | ModelRuntime | Web search with analysis |
| `code` | System 2 | ModelRuntime | Code generation and execution |
| `thinking` | System 2 | ModelRuntime | Deep reasoning and analysis |
| `deep_research` | Agent | AgentRuntime | Multi-step research workflows |

## Manual Test Inputs

Use these inputs to verify each cognitive level. In auto mode, observe the `auto -> xxx` output to confirm Router classification.

### Auto Mode (Router auto-classification)

Enter these directly at the `[auto]>` prompt and check which mode the Router selects:

```
你好
```
```
幫我分析台灣半導體產業的競爭優勢
```
```
寫一個 Python 快速排序的程式碼
```
```
搜尋 2026 年 AI 晶片最新發展趨勢
```

### System 1 — `/mode chat`

```
什麼是機器學習？用簡單的方式說明
```
```
幫我把這段英文翻譯成中文：The architecture follows a strict layered design.
```

### System 1 — `/mode knowledge`

```
根據知識庫的內容，解釋本系統的認知架構設計
```

### System 2 — `/mode thinking`

```
比較 REST API 和 GraphQL 的優缺點，哪種更適合微服務架構？
```
```
為什麼遞迴演算法在某些情況下比迭代慢？請逐步推理
```

### System 2 — `/mode search`

```
2026年台灣有哪些重要的科技政策？
```

### System 2 — `/mode code`

```
寫一個費氏數列的函數並計算前20項
```

### Agent — `/mode research`

```
深度研究台灣在全球 AI 供應鏈中的角色與未來發展方向
```

### What to Observe

- **auto mode**: Check `auto -> xxx` in output — does Router classification match query intent?
- **Cognitive level**: Output shows `system1`, `system2`, or `agent`
- **LLM provider**: Output shows which provider handled the request (e.g., `OpenAI`, `MultiProvider[OpenAI,Anthropic]`)
- **Processing time**: System 1 should be fastest, Agent slowest
- **Token usage**: Higher for thinking/research modes

## API Endpoints

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

## Feature Flags

Edit `config/cognitive_features.yaml` to toggle features:

```yaml
cognitive_features:
  enabled: false          # Master switch
  system1:
    enable_cache: false   # Response cache for CHAT/KNOWLEDGE
  routing:
    smart_routing: false  # Enable dual runtime dispatch
  metrics:
    cognitive_metrics: false  # Per-level request tracking
```

When all flags are OFF, the system behaves identically to pre-refactoring.

## Tests

```bash
# Run all tests (exclude known broken legacy tests)
python3 -m pytest tests/ -o "addopts=" \
  --ignore=tests/unit/test_engine.py \
  --ignore=tests/unit/test_refactored_engine.py

# Run by category
python3 -m pytest tests/unit/ -o "addopts="           # Unit tests
python3 -m pytest tests/integration/ -o "addopts="     # Integration tests
python3 -m pytest tests/e2e/ -o "addopts="             # E2E tests

# Run specific test files
python3 -m pytest tests/unit/test_multi_provider.py -v -o "addopts="
python3 -m pytest tests/integration/test_api.py -v -o "addopts="
```

## Troubleshooting

**No LLM API key**: Create `.env` in project root with at least one of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`.

**`ModuleNotFoundError`**: Make sure you run from project root. The `src/` path is added automatically by `main.py`.

**`pytest-cov` not installed**: Use `-o "addopts="` to override the pyproject.toml coverage flags.

**Import errors in `test_engine.py` / `test_refactored_engine.py`**: These are legacy test files with broken imports. Exclude them with `--ignore`.

**Unicode crash in WSL2**: Fixed in `core/logger.py` and `main.py` with surrogate sanitization. If you still see `UnicodeEncodeError`, clear `__pycache__`: `find src -type d -name __pycache__ -exec rm -rf {} +`
