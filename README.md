<p align="center">
  <img src="docs/images/logo.png" alt="OpenCode Platform" width="200" />
</p>

<h1 align="center">OpenCode Platform</h1>

<p align="center">
  <strong>認知 AI 引擎 | 雙執行時架構 | RAG 知識庫 | 程式碼沙箱 | MCP/A2A 擴展</strong>
</p>

<p align="center">
  <a href="#-主要特色">特色</a> &bull;
  <a href="#-快速示範">示範</a> &bull;
  <a href="#架構">架構</a> &bull;
  <a href="#快速開始">快速開始</a> &bull;
  <a href="#-效能指標">效能</a> &bull;
  <a href="#-與其他框架比較">比較</a> &bull;
  <a href="#-路線圖">路線圖</a> &bull;
  <a href="#-貢獻">貢獻</a> &bull;
  <a href="#-常見問題">FAQ</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-green.svg" alt="Python" />
  <img src="https://img.shields.io/badge/fastapi-0.108+-009688.svg" alt="FastAPI" />
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/Zenobia000/openagent_backend?style=social" alt="GitHub Stars" />
  <img src="https://img.shields.io/github/forks/Zenobia000/openagent_backend?style=social" alt="GitHub Forks" />
  <img src="https://img.shields.io/github/issues/Zenobia000/openagent_backend" alt="GitHub Issues" />
  <img src="https://img.shields.io/github/last-commit/Zenobia000/openagent_backend" alt="Last Commit" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/LLM-OpenAI%20%7C%20Anthropic%20%7C%20Gemini-blueviolet.svg" alt="Multi-Provider LLM" />
  <img src="https://img.shields.io/badge/architecture-System1%20%7C%20System2%20%7C%20Agent-orange.svg" alt="Cognitive Architecture" />
  <img src="https://img.shields.io/badge/docker-ready-blue.svg?logo=docker" alt="Docker Ready" />
</p>

---

## 概覽

**OpenCode Platform** 是一個基於三層認知架構的 AI 處理引擎，靈感來自雙歷程理論：

- **System 1**（快速）— 快取、低延遲的聊天與知識檢索回應
- **System 2**（分析）— 深度推理的搜尋、程式碼生成與思考任務
- **Agent**（自主）— 具狀態管理、多步驟工作流程與錯誤恢復

引擎使用 Router 分類請求複雜度，然後分派至適當的執行時（ModelRuntime 或 AgentRuntime）進行處理。

---

## ✨ 主要特色

### 認知架構
- **雙歷程理論實作**：System 1（快速直覺）、System 2（分析推理）、Agent（自主代理）
- **智慧路由**：ComplexityAnalyzer 自動依查詢複雜度選擇最佳執行時
- **多層快取**：System 1 回應快取，即時檢索
- **Feature Flags**：YAML 驅動設定，零風險部署

### 多供應商 LLM 韌性
- **自動備援鏈**：OpenAI → Anthropic → Gemini
- **結構化例外處理**：例外層級架構，消除字串錯誤檢測
- **串流支援**：SSE（Server-Sent Events）即時回應串流

### 生產就緒架構
- **模組化設計**：專門化處理器，Linus 風格程式碼品質
- **MCP 整合**：Model Context Protocol 外部工具伺服器
- **A2A 協定**：Agent-to-Agent 多代理委派
- **Context Engineering**：Manus 對齊的上下文工程（v3.1）

### 開發者體驗
- **FastAPI 整合**：自動生成互動式文件 `/docs`
- **雙介面**：CLI 開發模式、REST API 生產模式
- **型別安全**：完整 Python type hints + Pydantic 驗證
- **外掛系統**：MCP/A2A 套件管理器，可擴展的外掛架構

---

## 🎯 使用情境

### 適用對象

**AI 應用開發者**
- 需要內建複雜度路由的認知 AI 引擎
- 想要多供應商 LLM 韌性，無需手動重試邏輯
- 需要生產就緒的錯誤處理與可觀測性

**研究人員與學術界**
- 探索雙歷程 AI 架構
- 測試認知任務分類演算法
- 基準測試 LLM 供應商效能與備援策略

**企業團隊**
- 建構內部 AI 助手，整合 RAG + 搜尋 + 程式碼執行
- 需要 Feature Flag 部署，漸進式上線
- 透過 MCP/A2A 協定整合外部工具與代理

### 實際範例

**對話助手**
```python
# Auto 模式將簡單問題路由至 System 1（快速、快取）
# 複雜問題路由至 System 2（分析推理）
response = engine.process(Request(
    query="如何重設密碼？",  # → System 1
    mode="auto"
))
```

**研究助理**
```python
# 深度研究模式，多步驟學術分析
response = engine.process(Request(
    query="分析 Transformer 架構對 NLP 發展的影響 2017-2026",
    mode="deep_research"  # → Agent runtime，具狀態工作流程
))
```

**程式碼助手**
```python
# 程式碼生成 + 沙箱執行 + 安全檢查
response = engine.process(Request(
    query="寫一個計算費氏數列的函數並測試它",
    mode="code"  # → System 2 + 沙箱
))
```

---

## 架構

```
                         Request
                           |
                           v
                   +---------------+
                   |   API Layer   |   FastAPI + JWT Auth + SSE Streaming
                   |   (routes)    |   17 版本化端點
                   +-------+-------+
                           |
                           v
                +----------+----------+
                |  RefactoredEngine   |   Router + 雙執行時分派
                |  (Metrics, Flags)   |   Feature Flag 認知特性
                +----------+----------+
                           |
                    +------+------+
                    |   Router    |   ComplexityAnalyzer (智慧路由)
                    +------+------+
                           |
              +------------+------------+
              |                         |
     +--------v--------+      +--------v--------+
     |  ModelRuntime    |      |  AgentRuntime   |
     |  (System 1 + 2) |      |  (Agent level)  |
     |  無狀態           |      |  有狀態          |
     |  可快取           |      |  重試 + 恢復     |
     +--------+---------+      +--------+---------+
              |                         |
     +--------v--------+      +--------v--------+
     | ProcessorFactory |      | DeepResearch    |
     | 模式處理器        |      | 多步驟研究       |
     +---------+--------+      +--------+--------+
               |                        |
               v                        v
     +---------+---------+    +---------+---------+
     |   Services Layer  |    |   Extension Layer |
     | LLM | RAG | Search|    | MCP | A2A         |
     | Sandbox           |    | PackageManager    |
     +-------------------+    +-------------------+
```

### 三個認知層級

| 層級 | 模式 | 執行時 | 特性 |
|------|------|--------|------|
| **System 1** | `chat`, `knowledge` | ModelRuntime | 快速、可快取、低延遲 |
| **System 2** | `search`, `code`, `thinking` | ModelRuntime | 分析、多步推理 |
| **Agent** | `deep_research` | AgentRuntime | 有狀態工作流程、重試、錯誤恢復 |

---

## 📊 效能指標

**System 1（快速）**：45ms 平均 | 可快取查詢
**System 2（分析）**：0.8-2.3s 平均 | 完整推理
**Agent（自主）**：8.5s 平均 | 多步驟工作流程

---

## 🔍 與其他框架比較

**vs. LangChain**：生產 API + 自動路由 + 內建快取
**vs. Haystack**：不僅是 RAG — 程式碼執行、研究工作流程、多模態
**vs. AutoGPT**：簡單查詢快 10 倍 + 智慧路由

詳細比較表與遷移指南：[比較指南](docs/COMPARISON.md)

---

## 🚀 快速示範

### 互動式 CLI 示範

```bash
$ python main.py

🚀 OpenCode Platform - 互動模式
模式：auto（Router 將選擇最佳處理層級）

[auto]> 法國的首都是什麼？
🔄 分析複雜度... → System 1 (chat)
💬 法國的首都是巴黎。

[auto]> 比較資本主義和社會主義的經濟體系
🔄 分析複雜度... → System 2 (thinking)
🧠 深度分析模式
📊 [詳細比較分析...]

[auto]> /mode research
✅ 已切換至 deep_research 模式（Agent runtime）

[research]> 分析 AI 對就業的影響 2020-2026
🤖 Agent 工作流程啟動...
📡 步驟 1/5：蒐集資料來源...
📡 步驟 2/5：分析趨勢...
📡 步驟 3/5：綜合發現...
📡 步驟 4/5：批判性評估...
📡 步驟 5/5：生成報告...
✅ 研究完成
```

### API 範例

```bash
# 取得 token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# 使用 auto 路由聊天
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "解釋量子計算", "mode": "auto"}'
```

---

## 專案結構

```
opencode_backend/
├── main.py                # CLI 進入點
├── pyproject.toml         # 專案元資料與相依套件
├── config/
│   ├── cognitive_features.yaml  # Feature Flag 設定
│   ├── mcp_servers.yaml         # MCP 伺服器定義
│   └── a2a_agents.yaml          # A2A 代理定義
├── src/
│   ├── core/              # 引擎 + 路由 + 處理器 + Context Engineering
│   │   ├── engine.py      # RefactoredEngine
│   │   ├── router.py      # DefaultRouter + ComplexityAnalyzer
│   │   ├── models_v2.py   # 凍結 dataclass 資料模型
│   │   ├── processors/    # 模式處理器
│   │   │   ├── base.py, chat.py, knowledge.py
│   │   │   ├── search.py, thinking.py, code.py
│   │   │   ├── factory.py
│   │   │   └── research/  # DeepResearchProcessor 子模組
│   │   ├── runtime/       # ModelRuntime + AgentRuntime
│   │   ├── context/       # Context Engineering（Manus 對齊）
│   │   ├── mcp_client.py  # MCP 客戶端管理器
│   │   ├── a2a_client.py  # A2A 客戶端管理器
│   │   └── package_manager.py  # 外掛套件管理
│   ├── api/               # FastAPI + JWT + SSE 串流
│   ├── auth/              # JWT 認證
│   └── services/          # LLM | Knowledge | Search | Sandbox
├── packages/              # 可插拔擴展套件
│   ├── weather/           # MCP 伺服器 — 天氣查詢
│   ├── translator/        # MCP 伺服器 — 翻譯
│   └── stock-analyst/     # A2A 代理 — 股票分析
├── examples/              # 範例程式碼
├── scripts/               # 工具腳本
├── tests/                 # 測試套件
├── deploy/                # Docker 設定
└── docs/                  # 完整文件
```

---

## 快速開始

### 前置需求

- **Python** 3.11+
- **uv**（推薦的套件管理器）
- **Docker**（選用，用於沙箱與 Qdrant）

### 1. 安裝 uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 環境設定

```bash
cd opencode_backend

# 建立虛擬環境並安裝相依套件
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

uv pip install -e ".[dev]"

# 設定環境變數
cp .env.example .env
# 編輯 .env，至少設定一個 LLM API key：
#   OPENAI_API_KEY, ANTHROPIC_API_KEY, 或 GEMINI_API_KEY
```

### 安裝選項

| 安裝指令 | 用途 |
|---------|------|
| `uv pip install -e ".[dev]"` | 開發環境（測試、linting） |
| `uv pip install -e ".[production]"` | 生產環境（含 Anthropic、Gemini、Cohere、Knowledge、Docker） |
| `uv pip install -e ".[all]"` | 全部功能（生產 + 開發 + OCR） |
| `uv pip install -e ".[anthropic]"` | 僅 Anthropic LLM |
| `uv pip install -e ".[google]"` | 僅 Gemini LLM |
| `uv pip install -e ".[knowledge]"` | 文件解析（PyMuPDF、docx、pandas） |
| `uv pip install -e ".[docling]"` | Docling（含 torch/CUDA，很大） |
| `uv pip install -e ".[ocr]"` | OCR（pytesseract、easyocr） |

### 3. CLI 模式

```bash
python main.py          # 互動式聊天
python main.py test     # 執行測試
python main.py help     # 說明
```

### 4. API 伺服器

```bash
cd src && python -c "
import uvicorn
from api.routes import create_app
uvicorn.run(create_app(), host='0.0.0.0', port=8000)
"
```

- API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

### 5. Docker Compose（完整堆疊）

```bash
docker-compose up -d    # 啟動所有服務（Qdrant、Backend、Frontend、Sandbox）
```

### 6. 啟用 Docker Sandbox（可選）

Sandbox 預設使用 local execution（無隔離）。如需 Docker 隔離執行：

```bash
# 1. 確保 Docker daemon 運行中（WSL2 需要 Docker Desktop 或 dockerd）
docker info

# 2. 建置 sandbox image
cd deploy/sandbox && ./build.sh

# 3. 在 .env 中啟用
SANDBOX_ENABLED=true
```

### 7. API 使用

```bash
# 取得 JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# 聊天
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

---

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

伺服器運行時可在 `/docs` 查看完整互動式文件。

---

## 處理模式

| 模式 | 認知層級 | 執行時 | 說明 |
|------|---------|--------|------|
| `chat` | System 1 | ModelRuntime | 一般對話（可快取） |
| `knowledge` | System 1 | ModelRuntime | RAG 知識檢索（可快取） |
| `search` | System 2 | ModelRuntime | 網路搜尋與分析 |
| `code` | System 2 | ModelRuntime | 程式碼生成與執行 |
| `thinking` | System 2 | ModelRuntime | 深度推理與分析 |
| `deep_research` | Agent | AgentRuntime | 多步驟研究工作流程 |
| `auto` | — | Router 決定 | 自動模式選擇 |

---

## Feature Flags

所有認知特性預設 **關閉**，零風險部署。透過 `config/cognitive_features.yaml` 啟用：

```yaml
cognitive_features:
  enabled: false           # 主開關
  system1.enable_cache: false     # 快取節省成本
  routing.smart_routing: false    # 自動模式路由
  metrics.cognitive_metrics: false # 效能追蹤
```

---

## 環境變數

| 變數 | 必要 | 說明 | 預設值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | 至少一個 | OpenAI API key（主要） | — |
| `ANTHROPIC_API_KEY` | 至少一個 | Anthropic API key（備援） | — |
| `GEMINI_API_KEY` | 至少一個 | Google Gemini API key（備援） | — |
| `JWT_SECRET` | 否 | JWT 簽名密鑰 | `dev-secret-key` |
| `JWT_ALGORITHM` | 否 | JWT 演算法 | `HS256` |
| `JWT_EXPIRE_MINUTES` | 否 | Token 過期時間 | `1440` |
| `LOG_LEVEL` | 否 | 日誌等級 | `INFO` |

**注意**：系統使用備援鏈（OpenAI → Anthropic → Gemini），至少需要一個 LLM API key。

---

## 測試

```bash
# 執行所有測試
uv run pytest tests/ -v

# 快速測試
uv run pytest tests/unit/ -v
```

---

## 服務

| 服務 | 說明 |
|------|------|
| **LLM（多供應商）** | 備援鏈：OpenAI → Anthropic → Gemini，結構化錯誤處理 |
| **Knowledge（RAG）** | 文件上傳、索引、語意檢索（Qdrant + Cohere reranking） |
| **Search** | 多引擎網路搜尋（Tavily、Serper、Brave、Exa、DuckDuckGo、SearXNG） |
| **Sandbox** | Docker 隔離 Python/Bash 程式碼執行，支援持久化沙箱（見下方啟用步驟） |
| **Deep Research** | 多步驟深度研究，含圖表生成與報告產出 |

---

## 版本歷史

### v3.2（2026-02）— 持久化沙箱 + 圖表管線
- 持久化 Docker 沙箱（`_PersistentSandbox`）
- 圖表規劃管線（每份報告最多 5 張圖表）
- CJK 字體支援鏈
- 搜尋預算模型

### v3.1（2026-02）— Context Engineering
- 6 個 Manus 對齊的上下文工程元件
- Context Manager、Todo Recitation、Error Preservation
- Template Randomizer、File Memory、Tool Mask
- 全部 Feature Flag 控制，預設關閉

### v3.0（2026-02）— 死程式碼清理 + 單體分解
- 移除 10 個死程式碼檔案（約 2,555 行）
- DeepResearchProcessor 分解為 7 個專注模組
- MCP/A2A 客戶端整合
- 外掛套件管理器

### v2.0（2026-02）— Linus 風格重構
- 2611 行單體 → 12 個模組化檔案
- 字串錯誤檢測 → 結構化例外
- 測試覆蓋率 22% → 52%

完整版本歷史：[變更日誌](docs/CHANGELOG.md)

---

## 📚 文件

### 核心指南
- [效能基準](docs/PERFORMANCE.md) — 延遲、吞吐量、成本最佳化
- [與其他框架比較](docs/COMPARISON.md) — vs LangChain、Haystack、AutoGPT
- [路線圖](docs/ROADMAP.md) — 未來計畫
- [常見問題](docs/FAQ.md) — 常見問題解答
- [架構深入探討](docs/refactoring_v2/) — 設計決策與重構
- [v3 架構審計](docs/refactoring_v3/) — 程式碼審查與清理

### 入門
- [快速開始指南](docs/QUICK_START.md) — 詳細設定教學
- [範例程式碼](examples/) — 可運行的程式碼範例
- [貢獻指南](docs/CONTRIBUTING.md) — 如何貢獻
- [安全政策](docs/SECURITY.md) — 安全準則
- [變更日誌](docs/CHANGELOG.md) — 版本歷史

---

## 疑難排解

**沒有 LLM API key**：在專案根目錄建立 `.env`，至少設定以下之一：
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

**`ModuleNotFoundError`**：請從專案根目錄執行。`src/` 路徑由 `main.py` 自動新增。

**`pytest-cov` 未安裝**：使用 `-o "addopts="` 覆蓋 pyproject.toml 的覆蓋率選項。

**Import errors in `test_engine.py` / `test_refactored_engine.py`**：這些是遺留測試檔案，使用 `--ignore` 排除。

**WSL2 Unicode 崩潰**：已在 `core/logger.py` 和 `main.py` 中修復。如仍遇到 `UnicodeEncodeError`，清除 `__pycache__`：`find src -type d -name __pycache__ -exec rm -rf {} +`

---

## 🤝 貢獻

歡迎社群貢獻！

**我們需要幫助的領域**：
- 文件與教學
- 測試覆蓋率（目標：80%）
- [Bug 修復](https://github.com/Zenobia000/openagent_backend/labels/good%20first%20issue)
- [新功能](docs/ROADMAP.md)

**貢獻指南**：請參閱 [CONTRIBUTING.md](docs/CONTRIBUTING.md)

---

## 💬 社群

- [Discussions](https://github.com/Zenobia000/openagent_backend/discussions) — 問題與想法
- [Issues](https://github.com/Zenobia000/openagent_backend/issues) — Bug 回報

---

## 授權

MIT License — 詳見 [LICENSE](LICENSE)。

---

<p align="center">
  <sub>Built by OpenCode Team</sub>
</p>
