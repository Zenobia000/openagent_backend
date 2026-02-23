# Dead Code Inventory

> **Date**: 2026-02-23
> **Method**: Import tracing via `grep` across `src/`, `tests/`, `main.py`
> **Criteria**: Zero external importers = dead code

---

## Confirmed Dead Code (7 files, ~2,064 lines)

### 1. `src/core/runtime/workflow.py` (44 lines)

**What it is**: `WorkflowOrchestrator` — multi-step workflow planner.

**Evidence of death**:
- Zero importers across entire codebase
- **Broken import**: `from ..models import WorkflowState, ProcessingContext` — `core/models.py` does not exist (only `core/models_v2.py`)
- Would crash with `ModuleNotFoundError` if anyone tried to import it
- `AgentRuntime` manages workflows directly, making this class redundant

**Why it exists**: Likely created during v3.0 refactoring as a planned abstraction that was never integrated. `AgentRuntime` took a simpler approach.

---

### 2. `src/services/llm_service.py` (87 lines)

**What it is**: `LLMService` — simple OpenAI-only async wrapper + `get_llm_service()` factory.

**Evidence of death**:
- Zero importers across entire codebase
- Architecture docs label it "Legacy LLM service wrapper"
- Completely superseded by `src/services/llm/` package which provides multi-provider support (OpenAI + Anthropic + Gemini)

**Why it exists**: Original single-provider implementation before multi-provider refactoring.

---

### 3. `src/services/knowledge/parser.py` (207 lines)

**What it is**: PDF-only document parser using LlamaIndex DoclingReader/PyMuPDF.

**Evidence of death**:
- Zero importers across entire codebase
- `src/services/knowledge/service.py` imports `multimodal_parser.py` instead (line 19)
- `multimodal_parser.py` handles PDF plus 6 other formats (Word, Excel, CSV, Markdown, JSON, code)

**Why it exists**: Original PDF parser before multimodal support was added.

---

### 4. `src/services/browser/service.py` (1,096 lines) + `__init__.py` (25 lines)

**What it is**: Playwright-based browser automation with `BrowserService`, `SearchService`, `DeepResearchAgent`.

**Evidence of death**:
- `__init__.py` re-exports 8 symbols, but no file outside `services/browser/` imports any of them
- Grep for `BrowserService`, `DeepResearchAgent`, `from.*browser`, `services.browser` — zero external hits
- No test files reference this package

**Why it exists**: Early prototype of deep research via browser automation. The current architecture uses `services/search/` (API-based search) + `core/processors/research/` (processor pipeline) instead of browser scraping.

---

### 5. `src/services/research/service.py` (597 lines) + `__init__.py` (8 lines)

**What it is**: `ResearchService` — deep research with sub-question generation, multi-round search, report integration.

**Evidence of death**:
- `__init__.py` re-exports `ResearchService` and `get_research_service`, but nothing imports them
- Deep research functionality lives in `core/processors/research/processor.py` (2173 lines)
- The processor directly uses `services/search/` and `services/sandbox/`, bypassing this service entirely

**Why it exists**: Older service-layer implementation of deep research. When processors were modularized, the research logic was moved to `core/processors/research/` and this service became orphaned.

**Architecture doc discrepancy**: `03_file_dependencies_template.md` still references `services.research` in the Deep Research dependency path. This is incorrect — the path is `core/processors/research/ -> services/search/ + services/sandbox/`.

---

### 6. `src/services/repo/service.py` (351 lines) + `__init__.py`

**What it is**: `RepoOpsService` — Git/CI operations (clone, status, commit, push, pull, branch, log, diff). Implements `MCPServiceProtocol`.

**Evidence of death**:
- Zero importers anywhere: not in `src/`, not in `tests/`, not in `main.py`
- Not referenced by `service_initializer.py`
- Not in any `__init__.py` outside its own package
- No route exposes git operations

**Why it exists**: Scaffolding for a planned Git integration feature that was never completed.

---

## Questionable Files (3 files, ~704 lines)

### 7. `src/services/sandbox/routes.py` (139 lines)

**What it is**: Standalone FastAPI `APIRouter` with `/sandbox/execute`, `/sandbox/status`, `/sandbox/validate`.

**Evidence**: Zero importers. Never mounted to the main FastAPI app. `src/api/routes.py` already has `/api/v1/sandbox/execute` endpoint with the same functionality.

**Risk of deletion**: Zero — duplicate of existing routes.

---

### 8. `src/services/repo/` (entire directory, 351+ lines)

**Evidence**: Pure scaffolding. See #6 above.

**Risk of deletion**: Zero — no consumers.

---

### 9. `src/services/llm/gpt5_adapter.py` (214 lines)

**What it is**: Adapter for GPT-5 series models with parameter constraints, cost estimates, feature flags.

**Evidence**: Imported by `openai_client.py` (line 10), so technically not dead. But:
- Only activates for model names starting with `gpt-5*`
- No such models exist (speculative code)
- All specs (cost per 1K tokens, context window sizes, constraint values) are fabricated
- Uses `print()` for warnings instead of proper logging

**Risk of deletion**: Low — need to remove the import in `openai_client.py` as well.

---

## Impact Summary

| Action | Files | Lines Recovered | Risk |
|--------|-------|-----------------|------|
| Delete confirmed dead code | 7 files + 2 dirs | ~2,064 | Zero |
| Delete questionable code | 3 files + 1 dir | ~704 | Zero to Low |
| **Total recoverable** | **10+ files** | **~2,768** | |
