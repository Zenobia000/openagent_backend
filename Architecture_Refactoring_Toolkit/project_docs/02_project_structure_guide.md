# Project Structure Guide - QuitCode Platform

---

**Document Version:** `v2.4`
**Last Updated:** `2026-02-23`
**Status:** `Current (v3.0 + Context Engineering + Persistent Sandbox + Dead Code Cleanup)`

---

## 1. Purpose

Provide a standardized, accurate map of the project's directory and file structure to help developers locate code quickly and understand architectural boundaries.

## 2. Core Design Principles

- **Layered Architecture**: Strict separation of API -> Core -> Services.
- **Cognitive 3-Tier**: System 1 (fast/cached) / System 2 (analytical) / Agent (stateful workflows).
- **Protocol-Driven**: Components depend on abstractions (`protocols.py`), not concrete implementations.
- **Feature Flags**: All cognitive features gated by `config/cognitive_features.yaml`, default OFF.
- **Data Self-Containment**: `ProcessingMode` is a frozen dataclass with all data embedded (no dictionary mappings). Use `Modes.CHAT`, `Modes.from_name("chat")`.
- **Context Engineering**: Manus-aligned append-only context, KV-Cache friendly. 6 components under `src/core/context/` and `src/core/routing/`.

## 3. Top-Level Directory Structure

```plaintext
openagent_backend/
├── config/                     # Feature flag configuration
│   └── cognitive_features.yaml
├── deploy/                     # Docker configs (Dockerfile, compose); runner.py supports --persistent flag for persistent REPL mode
├── docs/                       # Project-level documentation
├── logs/                       # Application logs (auto-created); research_data/{trace_id}_{timestamp}/search_results.json
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

**Responsibility**: Business logic orchestration. Router, dual runtime dispatch, processors, caching, metrics, error classification, and Context Engineering. Does not call external APIs directly -- delegates to `services` layer.

```plaintext
src/core/
├── __init__.py
├── engine.py              # RefactoredEngine (router + runtime dispatch + CE integration + metrics)
├── router.py              # DefaultRouter + ComplexityAnalyzer + ToolAvailabilityMask integration
├── models_v2.py           # Request, Response, ProcessingContext, ProcessingMode (frozen dataclass), Modes, Event, RuntimeType
├── feature_flags.py       # FeatureFlags (YAML-driven, all default OFF)
├── cache.py               # ResponseCache (SHA-256 key, TTL, LRU eviction, stats)
├── metrics.py             # CognitiveMetrics (per-level latency, success rate, tokens)
├── errors.py              # ErrorClassifier, ErrorCategory, retry_with_backoff, llm_fallback
├── error_handler.py       # Decorator-based error handling (enhanced_error_handler, robust_processor)
├── protocols.py           # LLMClientProtocol, RouterProtocol, RuntimeProtocol
├── processors/            # Modular processor implementations (Linus-style refactored)
│   ├── __init__.py
│   ├── base.py            # BaseProcessor (abstract base class)
│   ├── factory.py         # ProcessorFactory (strategy pattern, no dict mappings)
│   ├── chat.py            # ChatProcessor (System 1)
│   ├── knowledge.py       # KnowledgeProcessor (System 1, RAG pipeline)
│   ├── search.py          # SearchProcessor (System 2, iterative search)
│   ├── thinking.py        # ThinkingProcessor (System 2, 5-stage deep thinking)
│   ├── code.py            # CodeProcessor (System 2, sandbox execution)
│   └── research/          # DeepResearchProcessor (Agent level)
│       ├── __init__.py
│       ├── processor.py   # Main research processor
│       ├── config.py      # Research configuration
│       └── events.py      # Research event types
├── context/               # Context Engineering (Manus-aligned, ~240 lines)
│   ├── __init__.py        # Exports: ContextManager, TodoRecitation, ErrorPreservation, etc.
│   ├── models.py          # ContextEntry (frozen dataclass, KV-Cache friendly)
│   ├── context_manager.py # Append-only context manager (~102 lines)
│   ├── todo_recitation.py # todo.md recitation pattern (~60 lines)
│   ├── error_preservation.py # Error preservation for retry (~39 lines)
│   ├── template_randomizer.py # Structural noise injection (~40 lines)
│   └── file_memory.py     # File system as agent memory (~51 lines)
├── routing/               # Routing components
│   ├── __init__.py
│   └── tool_mask.py       # ToolAvailabilityMask - logit masking (~47 lines)
├── runtime/
│   ├── __init__.py        # Exports ModelRuntime, AgentRuntime
│   ├── base.py            # BaseRuntime (abstract base for all runtimes)
│   ├── model_runtime.py   # ModelRuntime (System 1+2, stateless, cached)
│   └── agent_runtime.py   # AgentRuntime (Agent level, stateful, retry)
├── service_initializer.py # Graceful service initialization
├── prompts.py             # Prompt templates (system instruction, output guidelines, etc.)
├── logger.py              # StructuredLogger (console + file, SSE callback, surrogate-safe)
└── utils.py               # Utilities (get_project_root, load_env)
```

### 4.4 `src/services/` - Service Layer

**Responsibility**: Encapsulates all external interactions. Each subdirectory is a self-contained service. Services do NOT import from `core` or `api`.

```plaintext
src/services/
├── __init__.py
├── llm/                       # Multi-provider LLM client
│   ├── __init__.py            # create_llm_client() factory
│   ├── base.py                # LLMProvider ABC (generate, stream, provider_name, is_available)
│   ├── openai_client.py       # OpenAILLMClient (GPT-4o, GPT-4o-mini)
│   ├── anthropic_client.py    # AnthropicLLMClient (Claude)
│   ├── gemini_client.py       # GeminiLLMClient (Gemini, google-genai SDK)
│   ├── gpt5_adapter.py        # GPT5Adapter (GPT-5 series parameter constraints)
│   ├── errors.py              # LLM-specific error types
│   └── multi_provider.py      # MultiProviderLLMClient (fallback chain orchestrator)
│
├── knowledge/                 # RAG knowledge base service
│   ├── __init__.py
│   ├── indexer.py             # Document chunking + embedding + Qdrant indexing
│   ├── multimodal_parser.py   # Multi-format document parser (PDF, DOCX, Excel, CSV, Markdown, JSON, code)
│   ├── retriever.py           # Vector similarity search
│   └── service.py             # KnowledgeBaseService entry point
│
├── search/                    # Web search (multi-engine)
│   ├── __init__.py
│   └── service.py             # Tavily > Serper > DuckDuckGo > Exa fallback
│
└── sandbox/                   # Docker code execution
    ├── __init__.py
    └── service.py             # Docker container management + CodeSecurityFilter + _PersistentSandbox (thread-safe Docker REPL)
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
├── conftest.py                    # Shared test fixtures (adds src/ to sys.path)
├── core/                          # Context Engineering & Routing tests
│   ├── context/
│   │   ├── test_context_manager.py     # Append-only context tests
│   │   ├── test_todo_recitation.py     # todo.md recitation tests
│   │   ├── test_error_preservation.py  # Error preservation tests
│   │   ├── test_template_randomizer.py # Structural noise tests
│   │   └── test_file_memory.py         # File-based memory tests
│   └── routing/
│       └── test_tool_mask.py           # Tool availability mask tests
│
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
│   ├── test_context_engineering.py # Full CE integration tests (19 tests)
│   ├── test_api.py                # All API endpoints via httpx AsyncClient
│   ├── test_sse.py                # SSE streaming tests
│   ├── test_model_runtime.py      # ModelRuntime dispatch tests
│   └── test_agent_runtime.py      # AgentRuntime workflow tests
│
├── performance/                   # Performance benchmarks
│   └── test_context_overhead.py   # CE overhead < 50ms verification
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
