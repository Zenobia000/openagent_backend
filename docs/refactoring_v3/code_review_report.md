# Code Review Report — `src/` Complete Analysis

> **Version**: v3.0
> **Date**: 2026-02-23
> **Scope**: All `.py` files under `src/`, `src/core/`, `src/services/`

---

## 1. Architecture Overview

The codebase implements a **Cognitive 3-Tier Processing Engine**:

| Tier | Modes | Runtime | Characteristics |
|------|-------|---------|-----------------|
| System 1 | CHAT, KNOWLEDGE | ModelRuntime (cached) | Fast, stateless, 1-2 LLM calls |
| System 2 | SEARCH, CODE, THINKING | ModelRuntime (no cache) | Multi-step, analytical, 1-8 LLM calls |
| Agent | DEEP_RESEARCH | AgentRuntime (stateful) | Workflow-tracked, retry-wrapped, 3+ LLM calls |

**Request Flow**: `API routes -> Engine -> Router -> Runtime -> Processor -> Services -> Response`

**Design Principles**:
- Protocol-driven (abstractions in `protocols.py`)
- Strict dependency direction: `API -> Core -> Services` (DAG, no cycles)
- Feature-flag controlled Context Engineering
- Multi-provider LLM with automatic failover

---

## 2. File Inventory by Directory

### `src/api/` — HTTP Boundary (6 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `routes.py` | 380 | ESSENTIAL | FastAPI routes, all 11 endpoints |
| `schemas.py` | — | ESSENTIAL | Pydantic request/response models |
| `streaming.py` | — | ESSENTIAL | SSE streaming implementation |
| `errors.py` | — | ESSENTIAL | Unified API error format |
| `middleware.py` | — | ESSENTIAL | CORS, request logging |
| `__init__.py` | — | ESSENTIAL | Package init |

**Verdict**: Clean, no issues. Every file serves a clear purpose.

---

### `src/auth/` — Authentication (3 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `jwt.py` | — | ESSENTIAL | JWT encode/decode |
| `dependencies.py` | — | ESSENTIAL | FastAPI auth dependency injection |
| `__init__.py` | — | ESSENTIAL | Re-exports |

**Verdict**: Minimal and correct.

---

### `src/core/` — Business Logic (20 files at root)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `engine.py` | 423 | ESSENTIAL | Central orchestrator, CE integration |
| `router.py` | — | ESSENTIAL | Mode routing, cognitive classification |
| `models_v2.py` | 533 | ESSENTIAL | Domain models (ProcessingMode, Modes, ProcessingContext, WorkflowState) |
| `protocols.py` | 278 | ESSENTIAL | Protocol abstractions (RuntimeProtocol, LLMProvider, etc.) |
| `prompts.py` | 883 | ESSENTIAL | All prompt templates |
| `errors.py` | — | ESSENTIAL | ErrorClassifier, ErrorCategory, retry_with_backoff |
| `error_handler.py` | — | ESSENTIAL | @enhanced_error_handler decorator |
| `cache.py` | — | ESSENTIAL | ResponseCache (System 1) |
| `metrics.py` | — | ESSENTIAL | Cognitive metrics collection |
| `logger.py` | 508 | ESSENTIAL | Structured logging |
| `feature_flags.py` | — | ESSENTIAL | Feature flag system |
| `utils.py` | — | ESSENTIAL | get_project_root(), load_env() |
| `service_initializer.py` | — | ESSENTIAL | Service bootstrap with graceful degradation |
| `a2a_client.py` | 531 | ESSENTIAL | A2A Protocol client (lazy-loaded by service_initializer) |
| `mcp_client.py` | 317 | ESSENTIAL | MCP client (lazy-loaded by service_initializer) |
| `package_manager.py` | — | ESSENTIAL | Plugin/package scanner |
| `package_manifest.py` | — | ESSENTIAL | Package YAML models |
| `__init__.py` | — | ESSENTIAL | Package init |

**Notes**:
- `errors.py` and `error_handler.py` are NOT redundant — `errors.py` = primitives, `error_handler.py` = decorator wrapper.
- `prompts.py` at 883 lines is the second-largest core file. Well-organized as static method templates.

---

### `src/core/processors/` — Processing Pipeline (11 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `base.py` | — | ESSENTIAL | BaseProcessor abstract class |
| `factory.py` | — | ESSENTIAL | ProcessorFactory (strategy pattern) |
| `chat.py` | — | ESSENTIAL | ChatProcessor (System 1) |
| `knowledge.py` | — | ESSENTIAL | KnowledgeProcessor (System 1, RAG) |
| `search.py` | 338 | ESSENTIAL | SearchProcessor (System 2, iterative) |
| `code.py` | — | ESSENTIAL | CodeProcessor (System 2, sandbox) |
| `thinking.py` | — | ESSENTIAL | ThinkingProcessor (System 2, 5-stage) |
| `research/processor.py` | **2173** | ESSENTIAL but OVERSIZED | DeepResearchProcessor (Agent) |
| `research/config.py` | — | ESSENTIAL | SearchEngineConfig, SearchProviderType |
| `research/events.py` | — | ESSENTIAL | ResearchEvent SSE dataclass |
| `research/__init__.py` | — | ESSENTIAL | Re-exports |

**Critical Issue**: `research/processor.py` is 2173 lines — the largest file in the codebase. Single class doing too many things: query generation, search execution, quality evaluation, chart planning, sandbox execution, report generation, reference formatting. Candidate for further decomposition.

---

### `src/core/runtime/` — Dual Runtime (5 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `base.py` | 23 | ESSENTIAL | BaseRuntime abstract |
| `model_runtime.py` | 83 | ESSENTIAL | System 1+2 stateless runtime |
| `agent_runtime.py` | 72 | ESSENTIAL | Agent stateful runtime with retry |
| `workflow.py` | 44 | **DEAD + BROKEN** | WorkflowOrchestrator (never imported, broken import) |
| `__init__.py` | 9 | ESSENTIAL | Re-exports ModelRuntime + AgentRuntime |

**Critical Issue**: `workflow.py` imports from `..models` which resolves to `core.models` — a module that **does not exist** (only `core/models_v2.py` exists). This file would crash at import time. Zero external importers confirm it's dead code.

---

### `src/core/context/` — Context Engineering (7 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `__init__.py` | — | ESSENTIAL | Re-exports all 5 CE components |
| `models.py` | — | ESSENTIAL | ContextEntry, ContextRole dataclasses |
| `context_manager.py` | — | ESSENTIAL | Append-only context (KV-Cache friendly) |
| `todo_recitation.py` | — | ESSENTIAL | Plan recitation (combat "lost in the middle") |
| `error_preservation.py` | — | ESSENTIAL | Failed attempt preservation |
| `template_randomizer.py` | — | ESSENTIAL | Prompt template randomization |
| `file_memory.py` | — | ESSENTIAL | File system agent memory |

**Verdict**: All imported and used by `engine.py`. Full test coverage. Well-designed module.

---

### `src/core/routing/` — Tool Masking (2 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `tool_mask.py` | — | ESSENTIAL | ToolAvailabilityMask per mode |
| `__init__.py` | — | ESSENTIAL | Re-export |

**Verdict**: Used by `router.py`. Tested.

---

### `src/services/llm/` — Multi-Provider LLM (8 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `base.py` | — | ESSENTIAL | LLMProvider abstract base |
| `openai_client.py` | — | ESSENTIAL | OpenAI provider |
| `anthropic_client.py` | — | ESSENTIAL | Anthropic provider |
| `gemini_client.py` | — | ESSENTIAL | Gemini provider |
| `multi_provider.py` | — | ESSENTIAL | Fallback chain orchestrator |
| `errors.py` | — | ESSENTIAL | LLM-specific errors |
| `gpt5_adapter.py` | 214 | **QUESTIONABLE** | Speculative adapter for non-existent GPT-5 models |
| `__init__.py` | — | ESSENTIAL | Re-exports, create_llm_client() |

**Note on `gpt5_adapter.py`**: Imported by `openai_client.py` but only activates for model names starting with `gpt-5*`. All specs (cost, context window, constraints) are speculative. Harmless but premature code.

---

### `src/services/search/` — Search Engine Integration (2 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `service.py` | 684 | ESSENTIAL | Multi-engine search (Tavily, Serper, DuckDuckGo, Exa) |
| `__init__.py` | — | ESSENTIAL | Re-export |

**Verdict**: Core service used by SearchProcessor and DeepResearchProcessor.

---

### `src/services/sandbox/` — Docker Sandbox (3 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `service.py` | 1010 | ESSENTIAL | SandboxService, _PersistentSandbox, CodeSecurityFilter |
| `routes.py` | 139 | **DEAD** | Standalone FastAPI router, never mounted |
| `__init__.py` | — | ESSENTIAL | Re-exports SandboxService |

**Issue**: `routes.py` defines its own `APIRouter` with `/sandbox/execute`, `/sandbox/status`, `/sandbox/validate` endpoints, but it's never included in the main app. `src/api/routes.py` already has `/api/v1/sandbox/execute`. Pure duplication.

---

### `src/services/knowledge/` — RAG Pipeline (6 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `service.py` | 469 | ESSENTIAL | KnowledgeService orchestrator |
| `retriever.py` | 654 | ESSENTIAL | Vector DB retrieval |
| `indexer.py` | 483 | ESSENTIAL | Document indexing |
| `multimodal_parser.py` | 683 | ESSENTIAL | Multi-format document parser |
| `parser.py` | 207 | **DEAD** | Legacy PDF-only parser, superseded |
| `__init__.py` | — | ESSENTIAL | Re-exports |

**Issue**: `parser.py` is the old PDF parser. `multimodal_parser.py` handles PDF plus Word, Excel, CSV, Markdown, JSON, code files. Zero importers for `parser.py`.

---

### `src/services/browser/` — Browser Automation (2 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `service.py` | 1096 | **DEAD** | Playwright browser service, zero consumers |
| `__init__.py` | 25 | **DEAD** | Re-exports (nothing imports from this package) |

**Issue**: Complete Playwright-based browser automation (1096 lines!) with `BrowserService`, `SearchService`, `DeepResearchAgent`. Zero external importers anywhere in `src/`, `tests/`, or `main.py`. Likely an early prototype of deep research that was replaced by the current search service + processor pipeline approach.

---

### `src/services/research/` — Legacy Research Service (2 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `service.py` | 597 | **DEAD** | ResearchService with sub-question generation |
| `__init__.py` | 8 | **DEAD** | Re-exports (nothing imports from this package) |

**Issue**: An older deep research implementation. The current Deep Research functionality lives entirely in `core/processors/research/processor.py` which directly uses `services/search/` and `services/sandbox/`. This service layer is orphaned.

---

### `src/services/repo/` — Git Operations (2 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `service.py` | 351 | **DEAD** | Git/CI operations (clone, commit, push, etc.) |
| `__init__.py` | — | **DEAD** | Re-exports (nothing imports) |

**Issue**: Pure scaffolding. Implements `MCPServiceProtocol` but zero importers anywhere. No engine integration, no route, no test.

---

### `src/services/` Root (2 files)

| File | Lines | Status | Role |
|------|-------|--------|------|
| `llm_service.py` | 87 | **DEAD** | Legacy OpenAI-only LLM wrapper |
| `__init__.py` | — | ESSENTIAL | Package init |

**Issue**: `llm_service.py` is the old single-provider LLM service. Completely superseded by `services/llm/` multi-provider package. Zero importers.

---

## 3. Quality Observations

### Top 5 Largest Files

| # | File | Lines | Concern |
|---|------|-------|---------|
| 1 | `core/processors/research/processor.py` | 2173 | God class — candidate for decomposition |
| 2 | `services/browser/service.py` | 1096 | Dead code |
| 3 | `services/sandbox/service.py` | 1010 | Large but necessary (persistent sandbox is complex) |
| 4 | `core/prompts.py` | 883 | Large but acceptable (prompt templates) |
| 5 | `services/search/service.py` | 684 | Reasonable for multi-engine search |

### Dependency Direction Verification

- `services/` never imports from `core/` or `api/` — **VERIFIED CORRECT**
- `core/` never imports from `api/` — **VERIFIED CORRECT**
- No circular dependencies detected
- `core/utils.py` is imported by `services/` — this is a minor violation of the strict layering (services importing from core). However, `utils.py` only provides `get_project_root()` and `load_env()` which are infrastructure utilities, not business logic.

### Code Patterns

- **Strategy Pattern**: ProcessorFactory + 6 processors — clean implementation
- **Protocol-Driven**: RuntimeProtocol, LLMProvider, MCPServiceProtocol — good abstraction
- **Feature Flags**: All CE features default OFF, controlled by YAML — safe degradation
- **Error Handling**: 2-layer design (classification + decorator) — appropriate for the complexity level

---

## 4. Recommendations

### Immediate Cleanup (Zero Risk)

Delete these 7 files / 2 directories (~2,064 lines):

```
src/core/runtime/workflow.py          # 44 lines, broken import, zero usage
src/services/llm_service.py           # 87 lines, fully superseded
src/services/knowledge/parser.py      # 207 lines, fully superseded
src/services/browser/                 # 1,121 lines, zero consumers
src/services/research/                # 605 lines, zero consumers
```

### Recommended Cleanup (Low Risk)

Delete these 3 files / 1 directory (~490 lines):

```
src/services/sandbox/routes.py        # 139 lines, unmounted duplicate routes
src/services/repo/                    # 351 lines, pure scaffolding
```

### Evaluate

- `src/services/llm/gpt5_adapter.py` (214 lines) — speculative code for non-existent models

### Long-Term

- Decompose `research/processor.py` (2173 lines) into focused modules:
  - `query_generator.py` — search query generation
  - `search_executor.py` — parallel search orchestration
  - `chart_pipeline.py` — chart planning + sandbox execution
  - `report_writer.py` — final report generation + reference formatting
  - `processor.py` — orchestrator that composes the above

### Documentation Sync

- Update `03_file_dependencies_template.md`: Deep Research path references `services.research` but actually uses `core/processors/research/` + `services/search/` + `services/sandbox/`
- Remove `services/browser/` and `services/research/` from `02_project_structure_guide.md`
