# Project Structure Guide - OpenCode Platform

---

**Document Version:** `v2.0`
**Last Updated:** `2026-02-12`
**Status:** `Current`

---

## 1. Purpose

Provide a standardized, accurate map of the project's directory and file structure to help developers locate code quickly and understand architectural boundaries.

## 2. Core Design Principles

- **Layered Architecture**: Strict separation of API -> Core -> Services.
- **Cognitive 3-Tier**: System 1 (fast/cached) / System 2 (analytical) / Agent (stateful workflows).
- **Protocol-Driven**: Components depend on abstractions (`protocols.py`), not concrete implementations.
- **Feature Flags**: All cognitive features gated by `config/cognitive_features.yaml`, default OFF.

## 3. Top-Level Directory Structure

```plaintext
openagent_backend/
├── config/                     # Feature flag configuration
│   └── cognitive_features.yaml
├── docker/                     # Docker configs (Dockerfile, compose)
├── docs/                       # Project-level documentation
├── logs/                       # Application logs (auto-created)
├── plugins/                    # Plugin directory
├── src/                        # Main source code
│   ├── api/                    # API layer (HTTP boundary)
│   ├── auth/                   # Authentication (JWT)
│   ├── core/                   # Core business logic + engine
│   └── services/               # External service integrations
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── .env.example                # Environment variable template
├── main.py                     # CLI entry point
├── pyproject.toml              # Python project config
└── requirements.txt            # Python dependencies
```

## 4. `src` Directory Breakdown

### 4.1 `src/api/` - API Layer

**Responsibility**: HTTP boundary. Receives requests, validates input, delegates to core engine, formats responses.

```plaintext
src/api/
├── __init__.py
├── errors.py              # APIError exception + register_error_handlers()
├── middleware.py           # RequestLoggingMiddleware (method, path, status, duration)
├── routes.py              # FastAPI app + 11 endpoints (create_app with lifespan)
├── schemas.py             # Pydantic request/response models (ChatRequest, etc.)
└── streaming.py           # SSE async generator bridge (engine_event_generator)
```

### 4.2 `src/auth/` - Authentication

**Responsibility**: JWT token encoding/decoding and FastAPI dependency injection.

```plaintext
src/auth/
├── __init__.py            # Exports: encode_token, decode_token, get_current_user
├── jwt.py                 # JWT encode/decode, UserRole enum, TokenData model
└── dependencies.py        # get_current_user, get_optional_user (FastAPI Depends)
```

### 4.3 `src/core/` - Core Engine

**Responsibility**: Business logic orchestration. Router, dual runtime dispatch, processors, caching, metrics, error classification. Does not call external APIs directly -- delegates to `services` layer.

```plaintext
src/core/
├── __init__.py
├── engine.py              # RefactoredEngine (router + runtime dispatch + metrics)
├── router.py              # DefaultRouter + ComplexityAnalyzer
├── processor.py           # ProcessorFactory + BaseProcessor + 6 concrete processors
├── models.py              # Request, Response, ProcessingContext, ProcessingMode, EventType, CognitiveLevel
├── feature_flags.py       # FeatureFlags (YAML-driven, all default OFF)
├── cache.py               # ResponseCache (SHA-256 key, TTL, LRU eviction, stats)
├── metrics.py             # CognitiveMetrics (per-level latency, success rate, tokens)
├── errors.py              # ErrorClassifier, retry_with_backoff, llm_fallback
├── protocols.py           # LLMClientProtocol, service abstractions
├── runtime/
│   ├── model_runtime.py   # ModelRuntime (System 1+2, stateless, cached)
│   ├── agent_runtime.py   # AgentRuntime (Agent level, stateful, retry)
│   └── workflow.py        # WorkflowOrchestrator
├── prompts.py             # 17 prompt templates
└── logger.py              # StructuredLogger (console + file, surrogate-safe)
```

### 4.4 `src/services/` - Service Layer

**Responsibility**: Encapsulates all external interactions. Each subdirectory is a self-contained service. Services do NOT import from `core` or `api`.

```plaintext
src/services/
├── llm/                       # Multi-provider LLM client
│   ├── __init__.py            # create_llm_client() factory
│   ├── base.py                # LLMProvider ABC (generate, stream, provider_name, is_available)
│   ├── openai_client.py       # OpenAILLMClient (GPT-4o, GPT-4o-mini)
│   ├── anthropic_client.py    # AnthropicLLMClient (Claude)
│   ├── gemini_client.py       # GeminiLLMClient (Gemini)
│   └── multi_provider.py      # MultiProviderLLMClient (fallback chain orchestrator)
│
├── knowledge/                 # RAG knowledge base service
│   ├── indexer.py             # Document chunking + embedding + Qdrant indexing
│   ├── multimodal_parser.py   # PDF/DOCX/image parsing
│   ├── parser.py              # Base document parser
│   ├── retriever.py           # Vector similarity search
│   ├── service.py             # Knowledge service entry point
│   └── service_old.py         # Legacy (to be removed)
│
├── search/                    # Web search (multi-engine)
│   └── service.py             # Tavily > Serper > DuckDuckGo fallback
│
├── sandbox/                   # Docker code execution
│   ├── routes.py              # Sandbox-specific API routes
│   └── service.py             # Docker container management
│
├── research/                  # Deep research service
│   └── service.py             # Multi-step research pipeline
│
├── browser/                   # Web content extraction
│   └── service.py             # Page fetching and parsing
│
└── repo/                      # Git operations
    └── service.py
```

## 5. Test Structure

```plaintext
tests/
├── unit/                          # Unit tests (isolated, no external deps)
│   ├── test_feature_flags.py      # Feature flag loading/defaults
│   ├── test_router.py             # Router + ComplexityAnalyzer
│   ├── test_processors.py         # Processor creation and mock execution
│   ├── test_cache.py              # ResponseCache TTL/eviction/stats
│   ├── test_metrics.py            # CognitiveMetrics per-level tracking
│   ├── test_error_handling.py     # ErrorClassifier, retry, fallback
│   ├── test_auth.py               # JWT encode/decode/expiry
│   └── test_multi_provider.py     # Multi-provider LLM fallback chain
│
├── integration/                   # Integration tests (module interactions)
│   ├── test_api.py                # All API endpoints via httpx AsyncClient
│   ├── test_sse.py                # SSE streaming tests
│   └── test_runtime.py            # Runtime dispatch tests
│
└── e2e/                           # End-to-end tests (all modes)
    ├── test_main.py
    └── test_with_api.py
```

## 6. File Naming Conventions

| Type | Rule | Example |
|:---|:---|:---|
| **Python module** | `snake_case.py` | `openai_client.py`, `multi_provider.py` |
| **Python class** | `PascalCase` | `MultiProviderLLMClient`, `ResponseCache` |
| **Test file** | `test_*.py` | `test_multi_provider.py` |
| **Config file** | `snake_case.yaml` | `cognitive_features.yaml` |
| **Environment var** | `UPPER_SNAKE_CASE` | `ANTHROPIC_API_KEY` |
