# Architecture Documentation vs Reality — Discrepancy Report

> **Date**: 2026-02-23
> **Documents Reviewed**: 01, 02, 03, 04, 06, 07, 11
> **Code Reviewed**: All 80 `.py` files under `src/`

---

## Overall Assessment

**Architecture docs are ~90% accurate**. The core design (cognitive 3-tier, dual runtime, protocol-driven, CE integration) matches reality precisely. Discrepancies are limited to dead code references and minor structural details.

---

## Discrepancies Found

### 1. Deep Research Dependency Path (Doc 03)

**Document says**:
> Deep Research path: `... -> DeepResearchProcessor -> services.research + services.search + services.llm -> ...`

**Reality**:
- `services/research/service.py` has **zero importers** — it's dead code
- `DeepResearchProcessor` directly uses `services/search/` and `services/sandbox/`
- The correct path is: `DeepResearchProcessor -> services.search + services.llm + services.sandbox`

**Fix**: Update dependency diagram in `03_file_dependencies_template.md`.

---

### 2. Project Structure (Doc 02) Lists Dead Modules

**Document lists**:
- `src/services/browser/` — "Browser automation for deep research"
- `src/services/research/` — "Deep research service"
- `src/services/repo/` — "Git/CI operations"
- `src/services/llm_service.py` — "Legacy LLM service wrapper"

**Reality**: All four are dead code with zero external importers. They should be removed from the structure guide or explicitly marked as deprecated/scaffolding.

**Fix**: Update `02_project_structure_guide.md` after cleanup.

---

### 3. WorkflowOrchestrator (Doc 06 references, code is broken)

**Document implies**: `WorkflowOrchestrator` exists in `core/runtime/workflow.py` for multi-step workflow planning.

**Reality**: The file exists but has a **broken import** (`from ..models import ...` — `core/models.py` doesn't exist). Zero importers. `AgentRuntime` handles workflow orchestration directly with a simpler approach.

**Fix**: Remove references to `WorkflowOrchestrator` from architecture docs, or note it was superseded by inline AgentRuntime logic.

---

### 4. `core/utils.py` Crosses Layer Boundary

**Document says** (Doc 03):
> "services never imports from core or api"

**Reality**: Multiple `services/` files import from `core/utils.py`:
- `services/knowledge/service.py`
- `services/knowledge/retriever.py`
- `services/knowledge/indexer.py`
- `services/research/service.py`
- `services/search/service.py`
- `services/browser/service.py`

`utils.py` only provides `get_project_root()` and `load_env()` (infrastructure utilities, not business logic), so the violation is minor. But it contradicts the strict layering rule.

**Possible fixes**:
1. Move `utils.py` to a shared `src/common/` or `src/infra/` package
2. Or accept the pragmatic exception and document it

---

### 5. Sandbox Routes Duplication

**Document says** (Doc 04): Sandbox execution is at `POST /api/v1/sandbox/execute`.

**Reality**: This endpoint exists in `src/api/routes.py` (correct). But a **separate** `src/services/sandbox/routes.py` also defines `/sandbox/execute`, `/sandbox/status`, `/sandbox/validate` — an unmounted router that duplicates functionality.

**Fix**: Delete `services/sandbox/routes.py` after cleanup.

---

### 6. `models_v2.py` Naming

**Current state**: The only models file is `core/models_v2.py`. There is no `core/models.py` (v1 was deleted during v3.0 refactoring).

**Issue**: The `_v2` suffix is now meaningless — there's no v1 to distinguish from. The dead `workflow.py` still references the old `core.models` path, confirming v1 was removed but some references weren't updated.

**Recommendation**: Consider renaming `models_v2.py` to `models.py` in a future cleanup, updating all imports. This would also fix the pattern issue where new code might try `from core.models import ...` and fail.

---

## Discrepancies NOT Found (Confirmed Accurate)

These architectural claims were verified against actual code:

- ProcessingMode is a frozen dataclass with embedded cognitive_level — **correct**
- Modes accessed via `Modes.CHAT`, `Modes.from_name()` — **correct**
- ProcessorFactory creates 6 concrete processors — **correct**
- ModelRuntime handles System 1 + 2, AgentRuntime handles Agent — **correct**
- ResponseCache uses SHA-256 key, TTL configurable — **correct**
- ErrorClassifier has 5 categories, only NETWORK/LLM retryable — **correct**
- Context Engineering all 5 components imported/used by engine.py — **correct**
- ToolAvailabilityMask used by router.py — **correct**
- Multi-provider LLM fallback chain with auto-detection — **correct**
- Persistent sandbox with ephemeral fallback — **correct**
- Deep Research chart pipeline with early abort — **correct**
- All CE features controlled by feature flags, default OFF — **correct**
- JWT authentication on data endpoints — **correct**
- SSE streaming for chat/stream endpoint — **correct**

---

## Priority Actions

| Priority | Action | Files to Update |
|----------|--------|-----------------|
| P0 | Delete dead code | See `dead_code_inventory.md` |
| P1 | Fix dependency diagram | `03_file_dependencies_template.md` |
| P1 | Update project structure | `02_project_structure_guide.md` |
| P2 | Address `utils.py` layer violation | `src/core/utils.py` or docs |
| P3 | Consider `models_v2.py` rename | `src/core/models_v2.py` + all importers |
