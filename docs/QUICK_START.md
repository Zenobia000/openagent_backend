# OpenCode Platform - 快速開始指南

## 系統概覽

- **引擎**：RefactoredEngine + Router + 雙執行時分派
- **API**：FastAPI + JWT 認證 + SSE 串流，17 個端點
- **架構**：認知三層架構（System 1 / System 2 / Agent）
- **LLM**：多供應商備援鏈（OpenAI → Anthropic → Gemini）
- **資料模型**：`models_v2.py` — 凍結 dataclass，資料自包含
- **例外層級**：結構化 LLM 錯誤（可重試/不可重試）
- **Feature Flags**：YAML 驅動，所有標記預設關閉
- **擴展**：MCP/A2A 外掛系統，可熱載入外部工具與代理

## 專案結構

```
opencode_backend/
├── main.py                        # CLI 進入點（預設：auto 模式）
├── pyproject.toml                 # 專案元資料與相依套件
├── config/
│   ├── cognitive_features.yaml    # Feature Flag 設定
│   ├── mcp_servers.yaml           # MCP 伺服器定義
│   └── a2a_agents.yaml            # A2A 代理定義
├── packages/
│   ├── weather/                   # MCP 伺服器 — 天氣查詢
│   ├── translator/                # MCP 伺服器 — 翻譯
│   └── stock-analyst/             # A2A 代理 — 股票分析
├── src/
│   ├── core/                      # 核心引擎層
│   │   ├── engine.py              # RefactoredEngine（路由 + 執行時分派）
│   │   ├── router.py              # DefaultRouter + ComplexityAnalyzer
│   │   ├── models_v2.py           # 凍結 dataclass，ProcessingMode 註冊表
│   │   ├── processors/            # 模組化處理器架構
│   │   │   ├── base.py            # BaseProcessor
│   │   │   ├── chat.py            # ChatProcessor
│   │   │   ├── knowledge.py       # KnowledgeProcessor
│   │   │   ├── search.py          # SearchProcessor
│   │   │   ├── thinking.py        # ThinkingProcessor
│   │   │   ├── code.py            # CodeProcessor
│   │   │   ├── factory.py         # ProcessorFactory
│   │   │   └── research/          # DeepResearchProcessor 子模組
│   │   │       ├── processor.py   # 編排器
│   │   │       ├── planner.py     # 研究規劃
│   │   │       ├── search_executor.py  # 並行搜尋
│   │   │       ├── analyzer.py    # 漸進式分析
│   │   │       ├── computation.py # 圖表生成 + 沙箱運算
│   │   │       ├── reporter.py    # 報告產生
│   │   │       └── streaming.py   # SSE 事件管理
│   │   ├── context/               # Context Engineering（Manus 對齊）
│   │   │   ├── context_manager.py # 僅追加上下文（KV-cache 友好）
│   │   │   ├── todo_recitation.py # Todo 背誦模式
│   │   │   ├── error_preservation.py  # 錯誤保留
│   │   │   ├── template_randomizer.py # 結構雜訊注入
│   │   │   └── file_memory.py     # 檔案系統記憶
│   │   ├── routing/
│   │   │   └── tool_mask.py       # 工具可用性遮罩
│   │   ├── runtime/               # 雙執行時系統
│   │   │   ├── model_runtime.py   # System 1+2（無狀態、可快取）
│   │   │   └── agent_runtime.py   # Agent 工作流程（有狀態、重試）
│   │   ├── mcp_client.py          # MCP 客戶端管理器
│   │   ├── a2a_client.py          # A2A 客戶端管理器
│   │   ├── package_manager.py     # 外掛套件管理
│   │   ├── service_initializer.py # 服務初始化（優雅降級）
│   │   ├── feature_flags.py       # FeatureFlags（YAML 驅動）
│   │   ├── cache.py               # ResponseCache
│   │   ├── metrics.py             # CognitiveMetrics
│   │   ├── errors.py              # ErrorClassifier
│   │   ├── prompts.py             # 提示模板
│   │   ├── protocols.py           # 服務/路由/執行時協定
│   │   └── logger.py              # 結構化日誌
│   ├── api/                       # API 層
│   │   ├── routes.py              # FastAPI 應用 + 所有端點
│   │   ├── schemas.py             # Pydantic 請求/回應模型
│   │   ├── streaming.py           # SSE 非同步產生器橋接
│   │   ├── errors.py              # APIError + 錯誤處理器
│   │   └── middleware.py          # 請求日誌中介層
│   ├── auth/                      # 認證
│   │   ├── jwt.py                 # JWT 編碼/解碼
│   │   └── dependencies.py        # get_current_user FastAPI Depends
│   └── services/                  # 服務層
│       ├── llm/                   # 多供應商 LLM
│       │   ├── base.py            # LLMProvider ABC
│       │   ├── errors.py          # 例外層級（LLMError, ProviderError 等）
│       │   ├── openai_client.py   # OpenAI（GPT-4o）
│       │   ├── anthropic_client.py # Anthropic（Claude）
│       │   ├── gemini_client.py   # Gemini
│       │   └── multi_provider.py  # 備援鏈
│       ├── knowledge/             # RAG 知識庫
│       │   ├── service.py         # KnowledgeBaseService
│       │   ├── indexer.py         # 文件分塊 + Qdrant 索引
│       │   ├── retriever.py       # 語意檢索 + Cohere reranking
│       │   └── multimodal_parser.py # 文件解析（docling）
│       ├── search/                # 網路搜尋（多引擎）
│       │   └── service.py         # Tavily, Serper, Brave, Exa, DuckDuckGo, SearXNG
│       └── sandbox/               # Docker 程式碼執行
│           └── service.py         # SandboxService（持久化 + 臨時沙箱）
├── examples/
│   ├── simple_chat.py             # 基本聊天範例
│   ├── multi_provider.py          # 多 LLM 供應商範例
│   └── code_sandbox.py            # 程式碼執行範例
├── scripts/
│   └── measure_kv_cache.py        # KV-cache 命中率量測
├── tests/
│   ├── unit/                      # 單元測試
│   ├── integration/               # 整合測試
│   └── e2e/                       # 端到端測試
├── deploy/
│   ├── docker-compose.yml         # 完整堆疊編排
│   ├── backend/Dockerfile         # 後端映像
│   ├── frontend/                  # 前端 Nginx 映像
│   └── sandbox/                   # 沙箱映像
├── docs/
│   ├── refactoring_v2/            # v2 Linus 風格重構文件
│   └── refactoring_v3/            # v3 架構審計與清理
└── .env                           # 環境變數
```

## 快速開始

### 1. 環境設定（使用 uv）

```bash
cd opencode_backend

# 安裝 uv（如尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 建立虛擬環境並安裝相依套件
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

uv pip install -e ".[dev]"

# 設定環境變數
cp .env.example .env
# 編輯 .env — 至少設定一個 LLM API key：
#   OPENAI_API_KEY, ANTHROPIC_API_KEY, 或 GEMINI_API_KEY
```

### 2. CLI 模式

```bash
# 互動式聊天（預設：auto 模式，Router 選擇最佳模式）
python main.py

# 執行測試
python main.py test

# 說明
python main.py help
```

### 3. API 伺服器模式

```bash
cd src && python -c "
import uvicorn
from api.routes import create_app
uvicorn.run(create_app(), host='0.0.0.0', port=8000)
"
```

然後造訪：
- API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

### 4. API 使用

```bash
# 取得 JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# 聊天（使用 token）
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "你好", "mode": "chat"}'

# SSE 串流
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "解釋量子計算", "mode": "thinking"}'
```

## 處理模式

| 模式 | 認知層級 | 執行時 | 說明 |
|------|---------|--------|------|
| `auto` | Router 決定 | Router 決定 | 自動模式選擇（預設） |
| `chat` | System 1 | ModelRuntime | 一般對話（可快取） |
| `knowledge` | System 1 | ModelRuntime | RAG 知識檢索（可快取） |
| `search` | System 2 | ModelRuntime | 網路搜尋與分析 |
| `code` | System 2 | ModelRuntime | 程式碼生成與執行 |
| `thinking` | System 2 | ModelRuntime | 深度推理與分析 |
| `deep_research` | Agent | AgentRuntime | 多步驟研究工作流程 |

## 手動測試輸入

使用以下輸入驗證各認知層級。在 auto 模式下，觀察 `auto -> xxx` 輸出以確認 Router 分類。

### Auto 模式（Router 自動分類）

在 `[auto]>` 提示符下直接輸入以下內容，檢查 Router 選擇了哪個模式：

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

### System 1 — `/mode knowledge`

```
根據知識庫的內容，解釋本系統的認知架構設計
```

### System 2 — `/mode thinking`

```
比較 REST API 和 GraphQL 的優缺點，哪種更適合微服務架構？
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

### 觀察重點

- **auto 模式**：檢查輸出中的 `auto -> xxx` — Router 分類是否符合查詢意圖？
- **認知層級**：輸出顯示 `system1`、`system2` 或 `agent`
- **LLM 供應商**：輸出顯示哪個供應商處理了請求
- **處理時間**：System 1 最快，Agent 最慢
- **Token 使用量**：thinking/research 模式較高

## API 端點

| 端點 | 方法 | 認證 | 說明 |
|------|------|------|------|
| `/` | GET | 否 | 平台資訊 |
| `/health` | GET | 否 | 健康檢查 |
| `/api/status` | GET | 否 | 引擎狀態 |
| `/api/v1/auth/token` | POST | 否 | 取得 JWT token |
| `/api/v1/chat` | POST | 是 | 同步聊天 |
| `/api/v1/chat/stream` | POST | 是 | SSE 串流聊天 |
| `/api/v1/documents/upload` | POST | 是 | 上傳文件 |
| `/api/v1/documents/status/{id}` | GET | 是 | 查詢上傳狀態 |
| `/api/v1/search` | POST | 是 | 語意搜尋 |
| `/api/v1/sandbox/execute` | POST | 是 | 執行程式碼 |
| `/api/v1/metrics` | GET | 是 | 認知指標 |
| `/api/v1/mcp/servers` | GET | 是 | 列出 MCP 伺服器 |
| `/api/v1/mcp/tools` | GET | 是 | 列出 MCP 工具 |
| `/api/v1/a2a/agents` | GET | 是 | 列出 A2A 代理 |
| `/api/v1/packages` | GET | 是 | 列出已安裝套件 |
| `/api/v1/packages/{id}/start` | POST | 是 | 啟動套件 |
| `/api/v1/packages/{id}/stop` | POST | 是 | 停止套件 |

## Feature Flags

編輯 `config/cognitive_features.yaml` 切換功能：

```yaml
cognitive_features:
  enabled: false          # 主開關
  system1:
    enable_cache: false   # CHAT/KNOWLEDGE 回應快取
  routing:
    smart_routing: false  # 啟用雙執行時分派
  metrics:
    cognitive_metrics: false  # 每層級請求追蹤
```

所有標記關閉時，系統行為與重構前完全相同。

## 測試

```bash
# 執行所有測試（排除已知損壞的遺留測試）
uv run pytest tests/ -o "addopts=" \
  --ignore=tests/unit/test_engine.py \
  --ignore=tests/unit/test_refactored_engine.py

# 依類別執行
uv run pytest tests/unit/ -o "addopts="           # 單元測試
uv run pytest tests/integration/ -o "addopts="     # 整合測試
uv run pytest tests/e2e/ -o "addopts="             # 端到端測試

# 執行特定測試檔案
uv run pytest tests/unit/test_multi_provider.py -v -o "addopts="
```

## 疑難排解

**沒有 LLM API key**：在專案根目錄建立 `.env`，至少設定 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 或 `GEMINI_API_KEY` 之一。

**`ModuleNotFoundError`**：請從專案根目錄執行。`src/` 路徑由 `main.py` 自動新增。

**`pytest-cov` 未安裝**：使用 `-o "addopts="` 覆蓋 pyproject.toml 的覆蓋率選項。

**`test_engine.py` / `test_refactored_engine.py` 匯入錯誤**：這些是遺留測試檔案，使用 `--ignore` 排除。

**WSL2 Unicode 崩潰**：已在 `core/logger.py` 和 `main.py` 中修復。如仍遇到 `UnicodeEncodeError`，清除 `__pycache__`：`find src -type d -name __pycache__ -exec rm -rf {} +`
