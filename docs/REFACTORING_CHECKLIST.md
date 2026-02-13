# OpenCode Platform - 重構檢查清單

**基準文件**: [`REFACTORING_WBS.md`](./REFACTORING_WBS.md)
**建立日期**: `2026-02-11`
**更新方式**: 完成任務後將 `[ ]` 改為 `[x]`

---

## 進度總覽

| Phase | 名稱 | 風險 | 工期 | 任務數 | 完成 |
|-------|------|------|------|--------|------|
| P0 | 準備與標記 | 極低 | 3-5 天 | 14 | **14/14** |
| P1 | 路由層建設 | 低 | 5-7 天 | 13 | **13/13** |
| P2 | Runtime 分離 | 中 | 10-14 天 | 17 | **17/17** |
| P3 | API 層完整實現 | 中 | 7-10 天 | 17 | **17/17** |
| P4 | 管線優化與監控 | 低 | 7-10 天 | 14 | **14/14** |
| P5 | 生產就緒 | 低 | 5-7 天 | 11 | ◻/11 |
| **合計** | | | | **86** | |

**關鍵路徑**: P0 → P1 → P2 → P3 → P5
**可並行**: P3 和 P4 可在 P2 完成後同時進行

---

## Phase 0: 準備與標記（極低風險）

### 0.1 代碼盤點與清理

- [x] **0.1.1** 清理廢棄代碼
  - 已移除 `services/knowledge/service_old.py`（513 行）及 `__pycache__/`
- [x] **0.1.2** 統一 import 路徑
  - 決策：P0 不修改（風險過高），記錄為技術債務（11 處 `sys.path.insert`）
- [x] **0.1.3** 盤點 Processor 清單
  - 決策：`KnowledgeGraphProcessor` 和 `RewritingProcessor` 保留不註冊，未來待實作
- [x] **0.1.4** 盤點服務實現狀態
  - 4 完整（LLM, Search, Browser, Sandbox）、3 部分（Knowledge, Research, Repo）
- [x] **0.1.5** 產出 `docs/CODE_AUDIT_REPORT.md`

**驗收**:
- [x] 零功能變更
- [x] `CODE_AUDIT_REPORT.md` 已產出

---

### 0.2 認知層級標記

- [x] **0.2.1** 為 `ProcessorFactory` 添加 `COGNITIVE_MAPPING` 字典
  - `processor.py:1022-1029`
- [x] **0.2.2** 為 `BaseProcessor` 添加 `_cognitive_level` 屬性
  - `processor.py:24`, `processor.py:1040`
- [x] **0.2.3** 為 `ProcessingMode` 添加 `cognitive_level` property
  - `models.py:29-41`（`CognitiveLevel` class + `cognitive_level` property）

**驗收**:
- [x] 標記為純數據屬性，不影響任何運行邏輯
- [x] `processor._cognitive_level` 在處理器創建時自動設置

---

### 0.3 配置開關骨架

- [x] **0.3.1** 創建 `config/cognitive_features.yaml`
  - 所有開關默認 `false`，包含 system1/system2/routing/metrics 結構
- [x] **0.3.2** 創建 `src/core/feature_flags.py`
  - `FeatureFlags` class: YAML loading, deep merge, `is_enabled()`, `get_value()`, singleton
- [x] **0.3.3** 在 `RefactoredEngine.__init__` 中載入特性開關
  - `engine.py:10` import, `engine.py:36` `self.feature_flags = feature_flags`

**驗收**:
- [x] 所有開關 `false` 時，系統行為與重構前完全一致
- [x] `feature_flags.py` 有完整的類型提示和默認值

---

### 0.4 測試基礎建設

- [x] **0.4.1** 建立測試框架結構
  - 已有 `tests/unit/`, `tests/integration/`, `tests/e2e/`, `conftest.py`
- [x] **0.4.2** 為 `ProcessorFactory` 寫單元測試
  - 4 個認知標記測試加入 `tests/unit/test_processors.py::TestProcessorFactory`
- [x] **0.4.3** 為 `RefactoredEngine` 寫煙霧測試
  - 已有 `tests/unit/test_refactored_engine.py`（standalone script，pre-existing）
  - 備註：兩個舊測試檔案有 import 錯誤（`core.Engine`, `core.refactored`），屬於既有技術債
- [x] **0.4.4** 為特性開關寫單元測試
  - 新建 `tests/unit/test_feature_flags.py`（12 個測試，全通過）

**驗收**:
- [x] `pytest tests/unit/` — 37 passed, 3 pre-existing failures（與 P0 修改無關）

---

### Phase 0 里程碑 (M0: 基礎就緒) -- COMPLETED 2026-02-11

- [x] 認知標記已添加
- [x] 配置骨架就位
- [x] 核心單元測試通過（37 passed）
- [x] 回滾方案：直接刪除新增檔案

---

## Phase 1: 路由層建設（低風險）

> **前置條件**: Phase 0 完成

### 1.1 Router 組件

- [x] **1.1.1** 定義 `RouterProtocol`
  - `protocols.py:57-68` — `RouterProtocol.route(request) -> RoutingDecision`
- [x] **1.1.2** 定義 `RoutingDecision` 數據模型
  - `models.py` — `RoutingDecision`(mode, cognitive_level, runtime_type, complexity, confidence, reason)
- [x] **1.1.3** 實現 `DefaultRouter`
  - `src/core/router.py` — `DefaultRouter._select_mode()` 遷移自 engine
- [x] **1.1.4** 重構 `RefactoredEngine` 使用 Router
  - `engine.py` — `self.router = DefaultRouter(feature_flags)`, `decision = await self.router.route(request)`
- [x] **1.1.5** Router 單元測試
  - `tests/unit/test_router.py` — 23 個測試全通過

**驗收**:
- [x] `engine._select_mode()` 已刪除
- [x] 所有現有測試通過（60 passed, 3 pre-existing failures）
- [x] Router 可獨立測試

---

### 1.2 ComplexityAnalyzer（可選組件）

- [x] **1.2.1** 定義 `ComplexityScore` 模型
  - `models.py` — `ComplexityScore`(score, factors, recommended_level)
- [x] **1.2.2** 實現 `ComplexityAnalyzer`
  - `router.py:18-71` — 4 因素加權評分（length, multi_step, tool_need, questions）
- [x] **1.2.3** 在 Router 中集成 ComplexityAnalyzer
  - `router.py:104-106` — 受 `routing.complexity_analysis` 開關控制
- [x] **1.2.4** ComplexityAnalyzer 單元測試
  - `test_router.py::TestComplexityAnalyzer` — 6 個測試 + 2 個整合測試

**驗收**:
- [x] 特性開關關閉時，ComplexityAnalyzer 不被調用
- [x] 開啟後，僅附加複雜度信息，不改變最終結果

---

### 1.3 RuntimeDispatcher

- [x] **1.3.1** 定義 `RuntimeType` 枚舉
  - `models.py` — `RuntimeType.MODEL_RUNTIME`, `RuntimeType.AGENT_RUNTIME`
- [x] **1.3.2** 在 `RoutingDecision` 中加入 `runtime_type`
  - `models.py` — `RoutingDecision.runtime_type: RuntimeType`
- [x] **1.3.3** 實現 RuntimeDispatcher 邏輯
  - `router.py:130-133` — `_select_runtime()`: AGENT → AGENT_RUNTIME, 其餘 → MODEL_RUNTIME

**驗收**:
- [x] `RoutingDecision` 包含 `runtime_type` 字段
- [x] Phase 2 前，所有請求仍走同一處理路徑（runtime_type 僅作標記）

---

### Phase 1 里程碑 (M1: 路由獨立) -- COMPLETED 2026-02-11

- [x] Router 組件獨立運行
- [x] 引擎使用 Router
- [x] 所有 mode 行為不變
- [x] 回滾方案：回退 `engine.py` 至 P0 版本

---

## Phase 2: Runtime 分離（中風險）

> **前置條件**: Phase 1 完成

### 2.1 Runtime 抽象層

- [x] **2.1.1** 定義 `RuntimeProtocol`
  - `protocols.py:75-85` — `execute(context) -> str`, `supports(mode) -> bool`
- [x] **2.1.2** 定義 `ExecutionResult` 模型
  - `models.py` — `ExecutionResult`(result, tokens, duration_ms, metadata)
- [x] **2.1.3** 創建 `src/core/runtime/` 包結構
  - `__init__.py`, `base.py`, `model_runtime.py`, `agent_runtime.py`, `workflow.py`

---

### 2.2 ModelRuntime 實現

- [x] **2.2.1** 實現 `ModelRuntime` 基類
  - `model_runtime.py` — wraps ProcessorFactory, cognitive-level awareness
- [x] **2.2.2** 遷移 System 1 處理器
  - CHAT, KNOWLEDGE 由 ModelRuntime 的 `_MODEL_MODES` 集合管理
- [x] **2.2.3** 遷移 System 2 處理器
  - SEARCH, CODE, THINKING 歸入 ModelRuntime
- [x] **2.2.4** 添加 SystemController
  - 基礎版內建於 ModelRuntime（透過 ProcessorFactory 委派）
- [x] **2.2.5** ModelRuntime 整合測試
  - `tests/integration/test_model_runtime.py` — 9 個測試全通過（含一致性驗證）

---

### 2.3 AgentRuntime 實現

- [x] **2.3.1** 定義 `WorkflowState` 模型
  - `models.py` — steps, current_step, completed_steps, checkpoints, status + advance/complete/checkpoint 方法
- [x] **2.3.2** 實現 `AgentRuntime` 基類
  - `agent_runtime.py` — wraps DeepResearchProcessor + WorkflowState 追蹤
- [x] **2.3.3** 實現 `WorkflowOrchestrator`
  - `workflow.py` — 多步驟 workflow 引擎，支持 checkpoints
- [x] **2.3.4** 遷移 `DeepResearchProcessor` 到 AgentRuntime
  - AgentRuntime 委派 ProcessorFactory 取得 DeepResearchProcessor 執行
- [x] **2.3.5** AgentRuntime 整合測試
  - `tests/integration/test_agent_runtime.py` — 5 個測試（含 workflow_state 驗證）

---

### 2.4 引擎重構

- [x] **2.4.1** 重構 `RefactoredEngine.process()`
  - `engine.py:_execute()` — 根據 `routing.smart_routing` 開關和 `runtime_type` 分派
- [x] **2.4.2** 添加 Runtime 選擇的特性開關
  - 開關關閉時走 ProcessorFactory（legacy），開啟後啟用雙軌 Runtime
- [x] **2.4.3** 保持 `ProcessorFactory` 向後兼容
  - ProcessorFactory 未修改，ModelRuntime/AgentRuntime 均委派給它
- [x] **2.4.4** 端到端回歸測試
  - `tests/e2e/test_all_modes.py` — 29 個測試（legacy + runtime + consistency）

---

### Phase 2 里程碑 (M2: 雙軌運行) -- COMPLETED 2026-02-11

- [x] ModelRuntime + AgentRuntime 通過特性開關控制
- [x] CLI 端到端測試通過（29 passed）
- [x] `main.py` 無需修改
- [x] 回滾方案：關閉特性開關回退至單軌

---

## Phase 3: API 層完整實現（中風險）

> **前置條件**: Phase 2 完成

### 3.1 API 路由完整化

- [x] **3.1.1** 重構 `create_app()`
  - 完全重寫 `routes.py`：移除破損的 `config` import，使用 lifespan 替代 deprecated `on_event`
  - 引擎通過 `create_app(engine=)` 注入，支持測試用 mock
- [x] **3.1.2** 實現 `POST /api/v1/chat`
  - `ChatRequest` → `Request` → `engine.process()` → `ChatResponse`
  - Pydantic 驗證 mode, temperature, max_tokens
- [x] **3.1.3** 實現 `POST /api/v1/chat/stream`
  - `EventSourceResponse` + `engine_event_generator()` 真正異步串流
- [x] **3.1.4** 實現 `POST /api/v1/documents/upload`
  - `UploadFile` + in-memory task store（TODO: background worker）
- [x] **3.1.5** 實現 `GET /api/v1/documents/status/{task_id}`
  - 查詢上傳任務狀態，404 使用 `APIError` 結構化錯誤
- [x] **3.1.6** 實現 `POST /api/v1/search`
  - 委派 engine SEARCH mode，返回 `SearchResponse`
- [x] **3.1.7** 實現 `POST /api/v1/sandbox/execute`
  - 委派 `SandboxService`，支持 python/bash，使用 `APIError` 錯誤
- [x] **3.1.8** 統一錯誤響應格式
  - `src/api/errors.py`: `APIError` + `ErrorResponse`(error_code, message, trace_id, detail)
  - `register_error_handlers()` 處理 APIError + unhandled Exception
- [x] **3.1.9** API 整合測試
  - `tests/integration/test_api.py` — 14 個測試全通過（httpx.AsyncClient + ASGITransport）

---

### 3.2 SSE 串流實現

- [x] **3.2.1** 實現 SSE 串流管道
  - `src/api/streaming.py`: `engine_event_generator()` 使用 asyncio.Queue 橋接
- [x] **3.2.2** 重構 `engine.process_stream()`
  - 改為真正的異步生成器：asyncio.Queue + asyncio.Event + background task
- [x] **3.2.3** 定義 SSE 事件協議
  - `models.py:EventType` 新增：START, TOKEN, TOOL_CALL, SOURCE, END
- [x] **3.2.4** SSE 串流測試
  - `tests/integration/test_sse.py` — 3 個測試全通過（content-type, events, auth）

---

### 3.3 認證授權

- [x] **3.3.1** 實現 JWT 認證中間件
  - `src/auth/jwt.py`: `encode_token()`, `decode_token()` 使用 python-jose
  - `src/auth/dependencies.py`: `get_current_user()`, `get_optional_user()` FastAPI Depends
- [x] **3.3.2** 實現 `/api/v1/auth/token` 端點
  - `POST /api/v1/auth/token` 接受 username/password，返回 JWT（TODO: real user store）
- [x] **3.3.3** 為需要認證的端點添加 `Depends`
  - chat, stream, documents, search, sandbox 均需 `get_current_user`
  - `/`, `/health`, `/api/status`, `/api/v1/auth/token` 為公開端點
- [x] **3.3.4** 認證測試
  - `tests/unit/test_auth.py` — 10 個測試全通過（encode/decode/expired/tampered/roundtrip）

---

### Phase 3 里程碑 (M3: API 完整) -- COMPLETED 2026-02-11

- [x] 所有 API 端點可用（8 個端點）
- [x] SSE 串流正常（EventSourceResponse + 真正異步生成器）
- [x] 認證生效（JWT Bearer token + Depends）
- [x] 回滾方案：API 層獨立於核心，可單獨回退
- [x] 27 個新測試全通過（10 auth + 14 API + 3 SSE）

---

## Phase 4: 管線優化與監控（低風險）

> **前置條件**: Phase 2 完成（可與 Phase 3 並行）

### 4.1 響應緩存（System 1 優化）

- [x] **4.1.1** 實現 `ResponseCache`
  - `src/core/cache.py`: SHA-256 hash key, TTL eviction, LRU-style oldest eviction
- [x] **4.1.2** 在 ModelRuntime 中集成緩存
  - `model_runtime.py`: CHAT/KNOWLEDGE mode cache check before processor, cache put after
- [x] **4.1.3** 配置開關集成
  - 受 `system1.enable_cache` 控制，關閉時完全跳過 cache 邏輯
  - TTL/max_size 從 feature_flags 讀取
- [x] **4.1.4** 緩存命中率指標
  - `ResponseCache.stats` property: size, hits, misses, hit_rate
  - `ModelRuntime.cache_stats` property 暴露
- [x] **4.1.5** 緩存測試
  - `tests/unit/test_cache.py` — 13 個測試全通過（put/get/TTL/eviction/invalidate/clear/stats）

**驗收**:
- [x] 緩存命中時直接返回（零 LLM 調用）
- [x] 配置關閉時不影響現有行為

---

### 4.2 認知監控指標

- [x] **4.2.1** 實現 `CognitiveMetrics` 類
  - `src/core/metrics.py`: per-level request_count, avg_latency, success_rate, total_tokens
- [x] **4.2.2** 在 Engine 中集成指標收集
  - `engine.py`: process() 成功/失敗時 record_request()，受 `metrics.cognitive_metrics` 控制
- [x] **4.2.3** 新增 `/api/v1/metrics` 端點
  - `routes.py`: `GET /api/v1/metrics` 返回 `engine.metrics` (需認證)
- [x] **4.2.4** 配置開關集成
  - 受 `metrics.cognitive_metrics` 控制，關閉時不記錄

---

### 4.3 錯誤處理增強

- [x] **4.3.1** 實現錯誤分類器
  - `src/core/errors.py`: `ErrorClassifier.classify()` → NETWORK/LLM/RESOURCE_LIMIT/BUSINESS/UNKNOWN
- [x] **4.3.2** 實現 LLM Fallback 機制
  - `errors.py`: `llm_fallback(primary_fn, fallback_fn)` — 通用 async fallback
- [x] **4.3.3** 實現指數退避重試
  - `errors.py`: `retry_with_backoff()` — 2^n 秒，最多 3 次，僅重試 retryable 錯誤
- [x] **4.3.4** AgentRuntime 智能重試
  - `agent_runtime.py`: 使用 `retry_with_backoff(processor.process, ...)` 包裹執行
  - 失敗時記錄 `error_category` 到 workflow_state
- [x] **4.3.5** 錯誤處理測試
  - `tests/unit/test_error_handling.py` — 19 個測試（classifier + retry + fallback）

---

### Phase 4 里程碑 (M4: 優化上線) -- COMPLETED 2026-02-11

- [x] 緩存命中率可觀測（ResponseCache.stats）
- [x] 認知指標可觀測（/api/v1/metrics 端點）
- [x] 錯誤處理覆蓋 5 大類別（network/llm/resource/business/unknown）
- [x] 回滾方案：通過配置開關關閉所有優化特性
- [x] 40 個新測試全通過（13 cache + 8 metrics + 19 error handling）

---

## Phase 5: 生產就緒（低風險）

> **前置條件**: Phase 3 + Phase 4 完成

### 5.1 性能優化

- [ ] **5.1.1** 服務連接池化
  - LLM 客戶端、Qdrant 客戶端使用連接池
  - 涉及：`src/services/`
  - 依賴：P4
- [ ] **5.1.2** 異步併發優化
  - 搜索任務並行執行（`asyncio.gather`）
  - 涉及：`src/core/processor.py`
  - 依賴：P4
- [ ] **5.1.3** Prompt 長度優化
  - 減少不必要的 prompt 內容，降低 token 消耗
  - 涉及：`src/core/prompts.py`
  - 依賴：P4
- [ ] **5.1.4** 性能基準測試
  - 建立各模式的延遲基準線
  - 新建：`tests/performance/test_benchmarks.py`
  - 依賴：5.1.2

---

### 5.2 部署完善

- [ ] **5.2.1** 更新 `docker-compose.yml`
  - 新增配置卷掛載、健康檢查、資源限制
  - 涉及：`docker-compose.yml`
  - 依賴：P3
- [ ] **5.2.2** 更新 Backend Dockerfile
  - 多階段構建、生產優化
  - 涉及：`docker/backend/Dockerfile`
  - 依賴：5.2.1
- [ ] **5.2.3** 建立 CI 配置
  - GitHub Actions: lint + test + build
  - 新建：`.github/workflows/ci.yml`
  - 依賴：5.2.1
- [ ] **5.2.4** 環境變數文檔更新
  - 更新 `.env.example` 包含所有新增的配置項
  - 涉及：`.env.example`
  - 依賴：5.2.1

---

### 5.3 文檔更新

- [ ] **5.3.1** 更新架構文檔
  - 反映 Runtime 分離後的實際架構
  - 涉及：`Architecture_Refactoring_Toolkit/`
  - 依賴：P5
- [ ] **5.3.2** API 文檔自動生成
  - 確保 FastAPI OpenAPI 文檔完整（docstrings）
  - 涉及：`src/api/routes.py`
  - 依賴：3.1.9
- [ ] **5.3.3** 運維手冊
  - 配置說明、監控指南、故障排除
  - 新建：`docs/OPERATIONS_GUIDE.md`
  - 依賴：5.2.3

---

### Phase 5 里程碑 (M5: 生產就緒)

- [ ] 性能基準達標
- [ ] Docker 部署正常
- [ ] 文檔完整
- [ ] CI Pipeline 正常運行

---

## 風險追蹤

- [ ] **R1** Runtime 分離破壞現有處理邏輯 → 緩解：特性開關 + 完整回歸測試
- [ ] **R2** API 層變更影響前端集成 → 緩解：新端點使用 `/v1/` 前綴，舊端點保留
- [ ] **R3** AgentRuntime 狀態管理複雜度超預期 → 緩解：先實現最小版本（僅 DeepResearch）
- [ ] **R4** 性能回退 → 緩解：每階段做性能基準測試對比
- [ ] **R5** 認知路由分析準確度不足 → 緩解：初期僅用於監控標記，不影響實際路由

---

## 新增檔案追蹤

- [x] `config/cognitive_features.yaml` — P0
- [x] `src/core/feature_flags.py` — P0
- [x] `src/core/router.py` — P1
- [x] `src/core/runtime/__init__.py` — P2
- [x] `src/core/runtime/base.py` — P2
- [x] `src/core/runtime/model_runtime.py` — P2
- [x] `src/core/runtime/agent_runtime.py` — P2
- [x] `src/core/runtime/workflow.py` — P2
- [x] `src/api/streaming.py` — P3
- [x] `src/api/errors.py` — P3
- [x] `src/api/schemas.py` — P3
- [x] `src/auth/__init__.py` — P3
- [x] `src/auth/jwt.py` — P3
- [x] `src/auth/dependencies.py` — P3
- [x] `src/core/cache.py` — P4
- [x] `src/core/metrics.py` — P4
- [x] `src/core/errors.py` — P4
- [ ] `.github/workflows/ci.yml` — P5
- [x] `docs/CODE_AUDIT_REPORT.md` — P0
- [ ] `docs/OPERATIONS_GUIDE.md` — P5

---

## 修改檔案追蹤

- [x] `src/core/processor.py` — P0 (認知標記) ✓, P2 (處理器遷移)
- [x] `src/core/models.py` — P0 (認知屬性) ✓, P1 (RoutingDecision), P2 (WorkflowState)
- [x] `src/core/engine.py` — P0 (特性開關) ✓, P1 (Router), P2 (Runtime 分派), P3 (SSE)
- [x] `src/core/protocols.py` — P1 (RouterProtocol) ✓, P2 (RuntimeProtocol)
- [x] `src/api/routes.py` — P3 (完整 API: 8 端點 + lifespan + engine injection)
- [x] `src/api/middleware.py` — P3 (RequestLoggingMiddleware 替換破損的 AuditMiddleware)
- [x] `src/core/runtime/model_runtime.py` — P4 (Cache integration)
- [x] `src/core/runtime/agent_runtime.py` — P4 (Smart retry)
- [x] `src/core/engine.py` — P4 (Metrics integration)
- [ ] `docker-compose.yml` — P5
- [ ] `.env.example` — P5
