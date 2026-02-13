# OpenCode Platform - 代碼審計報告

**日期**: `2026-02-11`
**範圍**: `src/` 目錄全量盤點

---

## 1. Processor 清單

| 處理器 | 行數 | 已註冊 | 有 Enum | 實際使用 | 狀態 |
|--------|------|--------|---------|----------|------|
| ChatProcessor | 100-121 | Yes | CHAT | Yes | Active |
| KnowledgeProcessor | 124-207 | Yes | KNOWLEDGE | Yes | Active |
| SearchProcessor | 210-359 | Yes | SEARCH | Yes | Active |
| ThinkingProcessor | 362-543 | Yes | THINKING | Yes | Active |
| KnowledgeGraphProcessor | 546-596 | **No** | **None** | Test only | **Unregistered** |
| CodeProcessor | 599-638 | Yes | CODE | Yes | Active |
| RewritingProcessor | 641-665 | **No** | **None** | **No** | **Dead code** |
| DeepResearchProcessor | 668-1005 | Yes | DEEP_RESEARCH | Yes | Active |

**決策**:
- `KnowledgeGraphProcessor`: 保留不註冊，未來待實作
- `RewritingProcessor`: 保留不註冊，未來待實作

---

## 2. 服務實現狀態

| 服務 | 路徑 | 狀態 | 行數 | 技術棧 |
|------|------|------|------|--------|
| LLM | `services/llm/openai_client.py` | **Complete** | 78 | AsyncOpenAI, gpt-4o |
| Search | `services/search/service.py` | **Complete** | 654 | Tavily, Serper, DuckDuckGo, aiohttp |
| Browser | `services/browser/service.py` | **Complete** | 1096 | Playwright + HTTP fallback |
| Sandbox | `services/sandbox/service.py` | **Complete** | 757 | Docker 容器隔離 |
| Knowledge | `services/knowledge/` | **Partial** | 469+ | Cohere/OpenAI embeddings, Qdrant |
| Research | `services/research/service.py` | **Partial** | 597 | OpenAI gpt-4o, 搜索為 mock |
| Repo | `services/repo/service.py` | **Partial** | 351 | Git CLI subprocess |

**Partial 服務詳情**:
- **Knowledge**: 真實 embedding + Qdrant 集成，但 Qdrant 不可用時 fallback 到 mock
- **Research**: 真實 LLM 調用，但搜索集成使用 placeholder
- **Repo**: 真實 git CLI 命令，但無 GitHub API 集成

---

## 3. Import 路徑現狀

**問題**: 全專案使用 `sys.path.insert(0, "src/")` hack（共 11 處）

| 檔案 | 說明 |
|------|------|
| `main.py:19` | 主入口添加 `src/` 到路徑 |
| `tests/__init__.py:10` | 測試包添加路徑 |
| `tests/conftest.py:11` | pytest 配置添加路徑 |
| `tests/unit/test_*.py` | 各單元測試（4 處） |
| `tests/integration/test_api.py:13` | 整合測試 |
| `tests/e2e/test_*.py` | 端到端測試（2 處） |
| `tests/prompts/test_*.py` | Prompt 測試（1 處） |

**根因**: `src/` 目錄缺少 `__init__.py`，`pyproject.toml` 中 `packages = ["src/opencode"]` 指向不存在的目錄。

**額外問題**: `src/api/routes.py:8` 導入 `from config import API_CONFIG, DEBUG`，但 `config.py` 不存在。此端點在 CLI 模式下不會被觸發，但 API 啟動時會報錯。

**決策**: Phase 0 不修改 import 模式（風險過高），記錄為技術債務，在後續 Phase 處理。

---

## 4. 已清理項目

- [x] 刪除 `services/knowledge/service_old.py`（513 行廢棄代碼）
- [x] 清理 `src/core/__pycache__/` 目錄

---

## 5. 技術債務清單

| 項目 | 嚴重性 | 建議處理時機 |
|------|--------|-------------|
| `sys.path.insert` hack（11 處） | 中 | Phase 5（需要正確設置 Python 包） |
| `config.py` 不存在導致 API 啟動失敗 | 高 | Phase 3（API 層重構時） |
| `pyproject.toml` packages 配置錯誤 | 中 | Phase 5 |
| `RewritingProcessor` dead code | 低 | 隨時可移除 |
| `KnowledgeGraphProcessor` 未註冊 | 低 | 決定是否正式支持後處理 |
