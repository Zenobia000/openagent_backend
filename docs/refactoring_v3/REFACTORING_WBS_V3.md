# Refactoring V3 — Work Breakdown Structure

> **Version**: v3.0
> **Date**: 2026-02-23
> **Goal**: Dead code cleanup + architecture doc sync
> **Principle**: "Good taste means eliminating special cases, not adding them."

---

## Phase 0: Baseline Verification (Pre-flight)

| # | Task | Risk | Est. |
|---|------|------|------|
| 0.1 | Run existing test suite, record pass/fail baseline | None | 2 min |
| 0.2 | `git stash` or commit any uncommitted changes | None | 1 min |
| 0.3 | Create feature branch `refactor/v3-dead-code-cleanup` | None | 1 min |

**Exit Criteria**: Clean branch, test baseline recorded.

---

## Phase 1: Delete Confirmed Dead Code (Zero Risk)

7 files / 2 directories / ~2,064 lines. Zero importers, zero test references.

| # | Target | Lines | Evidence | Action |
|---|--------|-------|----------|--------|
| 1.1 | `src/core/runtime/workflow.py` | 44 | Zero importers + broken import (`core.models` DNE) | `rm` |
| 1.2 | `src/services/llm_service.py` | 87 | Zero importers. Superseded by `services/llm/` | `rm` |
| 1.3 | `src/services/knowledge/parser.py` | 207 | Zero importers. Superseded by `multimodal_parser.py` | `rm` |
| 1.4 | `src/services/browser/` (entire dir) | 1,121 | Zero external importers. Early prototype | `rm -rf` |
| 1.5 | `src/services/research/` (entire dir) | 605 | Zero external importers. Orphaned service | `rm -rf` |

**Exit Criteria**: 5 deletions complete. Test suite still passes (no regressions).

---

## Phase 2: Delete Questionable Code (Low Risk)

3 files / 1 directory / ~490 lines. Zero importers, duplicate or scaffolding.

| # | Target | Lines | Evidence | Action |
|---|--------|-------|----------|--------|
| 2.1 | `src/services/sandbox/routes.py` | 139 | Never mounted. Duplicates `api/routes.py` sandbox endpoint | `rm` |
| 2.2 | `src/services/repo/` (entire dir) | 351+ | Zero importers. Pure scaffolding | `rm -rf` |

**Exit Criteria**: 2 deletions complete. Test suite still passes.

---

## Phase 3: Update Architecture Documentation

Sync docs with actual codebase state.

| # | Target File | Change |
|---|-------------|--------|
| 3.1 | `02_project_structure_guide.md` | Remove `services/browser/`, `services/research/`, `services/repo/`, `llm_service.py` entries |
| 3.2 | `03_file_dependencies_template.md` | Fix Deep Research path: remove `services.research`, add actual path via `services/search/` + `services/sandbox/` |
| 3.3 | `06_architecture_and_design_document.md` | Remove dead module references if present |
| 3.4 | `07_deep_research_sequential_flow.md` | Verify accuracy (likely no changes needed) |

**Exit Criteria**: Architecture docs match actual code. No references to deleted modules.

---

## Phase 4: Post-Cleanup Verification

| # | Task | Purpose |
|---|------|---------|
| 4.1 | Run full test suite | Confirm zero regressions |
| 4.2 | Grep for any remaining references to deleted modules | Catch stale imports |
| 4.3 | Verify `import` works for all remaining `__init__.py` | No broken re-exports |

**Exit Criteria**: All tests pass. Zero stale references. Clean imports.

---

## Phase 5: Commit

| # | Task |
|---|------|
| 5.1 | Stage all deletions + doc updates |
| 5.2 | Commit: `refactor(cleanup): remove dead code — 7 files, ~2,500 lines` |

---

## Out of Scope (Future Work)

These items are identified but NOT part of this WBS:

| Item | Rationale |
|------|-----------|
| Decompose `research/processor.py` (2173 lines) | Significant refactor, needs separate WBS |
| Evaluate `gpt5_adapter.py` (speculative code) | Actively used by `openai_client.py`, harmless |
| Move `core/utils.py` to fix layer violation | Minor violation, infrastructure-only functions |
| Rename `models_v2.py` to `models.py` | Touches all importers, risk/reward doesn't justify |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Deleted file was actually used | Near zero | Medium | grep verification in Phase 4 |
| Test regression | Near zero | Low | Test suite run before/after |
| Doc update misses a reference | Low | Low | Full-text search for deleted module names |

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Total `.py` files in `src/` | 80 | 70 |
| Dead code files | 10 | 0 |
| Total lines in dead files | ~2,554 | 0 |
| Test pass rate | Baseline | Same |
