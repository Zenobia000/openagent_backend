# Project Structure Guide - OpenCode Platform

---

**Document Version:** `v2.1`
**Last Updated:** `2026-02-13`
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
├── plugins/                    # Plugin system (3 example plugins)
│   ├── PLUGIN_DEV_GUIDE.md     # Plugin development guide
│   ├── example-translator/     # Example: translation plugin
│   ├── stock-analyst/          # Example: stock analysis plugin
│   └── weather-tool/           # Example: weather tool plugin
├── src/                        # Main source code
│   ├── api/                    # API layer (HTTP boundary)
│   ├── auth/                   # Authentication (JWT)
│   ├── core/                   # Core business logic + engine
│   └── services/               # External service integrations
├── tests/                      # Test suite
│   ├── conftest.py             # Shared test fixtures
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
├── errors.py              # ErrorClassifier, ErrorCategory, retry_with_backoff, llm_fallback
├── error_handler.py       # Decorator-based error handling (enhanced_error_handler, robust_processor)
├── protocols.py           # LLMClientProtocol, RouterProtocol, RuntimeProtocol
├── runtime/
│   ├── __init__.py        # Exports ModelRuntime, AgentRuntime
│   ├── base.py            # BaseRuntime (abstract base for all runtimes)
│   ├── model_runtime.py   # ModelRuntime (System 1+2, stateless, cached)
│   ├── agent_runtime.py   # AgentRuntime (Agent level, stateful, retry)
│   └── workflow.py        # WorkflowOrchestrator
├── prompts.py             # Prompt templates (system instruction, output guidelines, etc.)
├── logger.py              # StructuredLogger (console + file, SSE callback, surrogate-safe)
├── sre_logger.py          # SRE-compliant logging (structured JSON, log categories, rotation)
└── utils.py               # Utilities (get_project_root, load_env)
```

### 4.4 `src/services/` - Service Layer

**Responsibility**: Encapsulates all external interactions. Each subdirectory is a self-contained service. Services do NOT import from `core` or `api`.

```plaintext
src/services/
├── __init__.py
├── llm_service.py             # Legacy LLM service wrapper
├── llm/                       # Multi-provider LLM client
│   ├── __init__.py            # create_llm_client() factory
│   ├── base.py                # LLMProvider ABC (generate, stream, provider_name, is_available)
│   ├── openai_client.py       # OpenAILLMClient (GPT-4o, GPT-4o-mini)
│   ├── anthropic_client.py    # AnthropicLLMClient (Claude)
│   ├── gemini_client.py       # GeminiLLMClient (Gemini, google-genai SDK)
│   └── multi_provider.py      # MultiProviderLLMClient (fallback chain orchestrator)
│
├── knowledge/                 # RAG knowledge base service
│   ├── __init__.py
│   ├── indexer.py             # Document chunking + embedding + Qdrant indexing
│   ├── multimodal_parser.py   # PDF/DOCX/image parsing
│   ├── parser.py              # Base document parser
│   ├── retriever.py           # Vector similarity search
│   └── service.py             # KnowledgeBaseService entry point
│
├── search/                    # Web search (multi-engine)
│   ├── __init__.py
│   └── service.py             # Tavily > Serper > DuckDuckGo fallback
│
├── sandbox/                   # Docker code execution
│   ├── __init__.py
│   ├── routes.py              # Sandbox-specific API routes
│   └── service.py             # Docker container management + CodeSecurityFilter
│
├── research/                  # Deep research service
│   ├── __init__.py
│   └── service.py             # Multi-step research pipeline
│
├── browser/                   # Web content extraction
│   ├── __init__.py
│   └── service.py             # Page fetching and parsing
│
└── repo/                      # Git operations
    ├── __init__.py
    └── service.py
```

## 5. Plugin Structure

**Responsibility**: Extensible plugin system for custom agents, tools, services, and hooks. Not yet integrated into the main `src/` codebase (planned feature).

```plaintext
plugins/
├── PLUGIN_DEV_GUIDE.md            # Plugin development guide (Chinese)
├── example-translator/            # Example: translation agent plugin
│   ├── plugin.json                # Plugin metadata (id, type, config_schema, permissions)
│   └── main.py                    # PluginImpl class
├── stock-analyst/                 # Example: stock analysis agent plugin
│   ├── plugin.json
│   ├── main.py                    # StockAnalystPlugin class
│   └── requirements.txt           # yfinance, pandas
└── weather-tool/                  # Example: weather tool plugin
    ├── plugin.json
    └── main.py
```

**Plugin Types**: `agent` (dispatcher-assigned tasks), `tool` (new tools for agents), `service` (background service), `hook` (event listener).

**Plugin Manifest** (`plugin.json`): `id`, `name`, `version`, `description`, `author`, `type`, `entry_point`, `class_name`, `config_schema`, `permissions`, `dependencies`, `tags`.

## 6. Test Structure

```plaintext
tests/
├── conftest.py                    # Shared test fixtures
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
│   ├── test_model_runtime.py      # ModelRuntime dispatch tests
│   └── test_agent_runtime.py      # AgentRuntime workflow tests
│
└── e2e/                           # End-to-end tests (all modes)
    └── test_all_modes.py          # Full pipeline tests for all processing modes
```

## 7. File Naming Conventions

| Type | Rule | Example |
|:---|:---|:---|
| **Python module** | `snake_case.py` | `openai_client.py`, `multi_provider.py` |
| **Python class** | `PascalCase` | `MultiProviderLLMClient`, `ResponseCache` |
| **Test file** | `test_*.py` | `test_multi_provider.py` |
| **Config file** | `snake_case.yaml` | `cognitive_features.yaml` |
| **Environment var** | `UPPER_SNAKE_CASE` | `ANTHROPIC_API_KEY` |
