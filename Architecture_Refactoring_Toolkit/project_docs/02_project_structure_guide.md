# 專案結構指南 (Project Structure Guide) - OpenCode Platform

---

**文件版本 (Document Version):** `v1.0`
**最後更新 (Last Updated):** `2026-02-05`
**主要作者 (Lead Author):** `OpenCode 架構團隊`
**狀態 (Status):** `活躍 (Active)`

---

## 目錄 (Table of Contents)

- [1. 指南目的 (Purpose of This Guide)](#1-指南目的-purpose-of-this-guide)
- [2. 核心設計原則 (Core Design Principles)](#2-核心設計原則-core-design-principles)
- [3. 頂層目錄結構 (Top-Level Directory Structure)](#3-頂層目錄結構-top-level-directory-structure)
- [4. 目錄詳解 (Directory Breakdown)](#4-目錄詳解-directory-breakdown)
  - [4.1 `src/opencode/` - 應用程式原始碼](#41-srcopencode---應用程式原始碼)
  - [4.2 `plugins/` - 插件系統](#42-plugins---插件系統)
  - [4.3 `tests/` - 測試代碼](#43-tests---測試代碼)
  - [4.4 `docker/` - 容器化配置](#44-docker---容器化配置)
- [5. 文件命名約定 (File Naming Conventions)](#5-文件命名約定-file-naming-conventions)
- [6. 演進原則 (Evolution Principles)](#6-演進原則-evolution-principles)

---

## 1. 指南目的 (Purpose of This Guide)

*   為 OpenCode Platform 提供一個標準化、可擴展且易於理解的目錄和文件結構。
*   確保團隊成員能夠快速定位代碼、配置文件和文檔，降低新成員的上手成本。
*   促進代碼的模塊化和關注點分離，提高可維護性。
*   支援插件架構和企業級功能的擴展。

## 2. 核心設計原則 (Core Design Principles)

*   **Actor 模型架構 (Actor Model Architecture):** 使用 Actor 模型實現並發和分散式計算，確保系統的可擴展性。
*   **協議驅動設計 (Protocol-Driven Design):** 透過明確定義的協議（Protocols）確保組件間的鬆耦合。
*   **服務層次分離 (Service Layer Separation):** 核心引擎、服務層、控制平面各司其職，職責明確。
*   **插件化擴展 (Plugin-Based Extension):** 支援熱插拔的插件系統，無需修改核心代碼即可擴展功能。
*   **企業級治理 (Enterprise Governance):** 內建審計、成本控制、策略管理等企業級功能。

## 3. 頂層目錄結構 (Top-Level Directory Structure)

```plaintext
opencode_backend/
├── .github/                    # GitHub Actions CI/CD 配置
├── Architecture_Refactoring_Toolkit/  # 架構重構工具包文檔
├── data/                       # 運行時數據目錄
│   ├── documents/             # 上傳的文檔存儲
│   ├── logs/                  # 應用程式日誌
│   └── sessions/              # 會話數據
├── docker/                     # Docker 相關配置
│   ├── backend/               # 後端 Dockerfile
│   ├── frontend/              # 前端 Dockerfile
│   └── sandbox/               # 沙箱環境 Dockerfile
├── docs/                       # 專案文檔
├── frontend/                   # Vue.js 前端應用
├── plugins/                    # 插件目錄
│   ├── example-translator/    # 翻譯工具插件範例
│   ├── stock-analyst/         # 股票分析代理插件
│   └── weather-tool/          # 天氣查詢工具插件
├── src/                        # 主要原始碼目錄
│   └── opencode/              # OpenCode 核心套件
├── tests/                      # 測試套件
├── .env.example                # 環境變數範本
├── .gitignore                  # Git 忽略配置
├── docker-compose.yml          # Docker Compose 配置
├── LICENSE                     # MIT 授權條款
├── pyproject.toml              # Python 專案配置 (PEP 621)
├── README.md                   # 專案說明文檔
└── requirements.txt            # Python 依賴清單
```

## 4. 目錄詳解 (Directory Breakdown)

### 4.1 `src/opencode/` - 應用程式原始碼

這是專案的核心，實現了完整的 OpenCode Platform 功能。

```plaintext
src/opencode/
├── __init__.py                 # 套件初始化，版本定義
│
├── core/                       # 核心引擎模組
│   ├── __init__.py
│   ├── engine.py              # 主引擎類，管理生命週期
│   ├── protocols.py           # 類型協議定義（介面）
│   ├── events.py              # 事件系統實現
│   ├── context.py            # 用戶上下文管理
│   └── utils.py              # 共用工具函數
│
├── orchestrator/               # 智能編排系統（Actor 模型）
│   ├── __init__.py
│   ├── actors/                # Actor 實現
│   │   ├── orchestrator.py   # 主編排器 Actor
│   │   ├── planner.py        # 任務規劃 Actor
│   │   ├── router.py         # 路由決策 Actor
│   │   ├── executor.py       # 任務執行 Actor
│   │   └── memory/           # 記憶管理子系統
│   │       ├── session.py    # 會話記憶
│   │       ├── skill.py      # 技能記憶
│   │       └── longterm.py   # 長期記憶
│   └── protocols/             # 編排器協議定義
│
├── services/                   # 服務層（具體功能實現）
│   ├── __init__.py
│   ├── knowledge_base/        # RAG 知識庫服務
│   │   ├── __init__.py
│   │   ├── parser.py         # 多模態文檔解析
│   │   ├── embedder.py       # 向量嵌入生成
│   │   ├── retriever.py      # 語義檢索
│   │   └── generator.py      # 答案生成
│   ├── sandbox/               # 代碼沙箱服務
│   │   ├── __init__.py
│   │   ├── docker_sandbox.py # Docker 隔離執行
│   │   └── security.py       # 安全策略
│   ├── web_search/            # 網路搜尋服務
│   │   ├── __init__.py
│   │   ├── duckduckgo.py    # DuckDuckGo 整合
│   │   └── wikipedia.py      # Wikipedia API
│   ├── browser/               # 瀏覽器自動化服務
│   ├── mcp/                   # MCP 協議服務
│   │   ├── __init__.py
│   │   ├── registry.py       # 服務註冊表
│   │   └── client.py         # MCP 客戶端
│   ├── repo_ops/              # Git 倉庫操作服務
│   └── data_services/         # 數據服務（DB、外部API）
│
├── control_plane/              # 企業級控制平面
│   ├── __init__.py
│   ├── audit/                 # 審計日誌系統
│   │   ├── logger.py         # 審計記錄器
│   │   └── manager.py        # 審計管理器
│   ├── cost/                  # 成本追蹤系統
│   │   ├── tracker.py        # Token 使用追蹤
│   │   └── budget.py         # 預算管理
│   ├── policy/                # 策略引擎
│   │   ├── rbac.py          # 角色權限控制
│   │   ├── risk.py          # 風險評估
│   │   └── permissions.py    # 工具權限管理
│   └── ops/                   # 運維監控
│       ├── health.py         # 健康檢查
│       └── tracing.py        # 分散式追蹤
│
├── plugins/                    # 插件系統核心
│   ├── __init__.py
│   ├── manager.py             # 插件生命週期管理
│   ├── sandbox.py             # 插件沙箱隔離
│   └── routes.py              # 插件 API 端點
│
├── api/                        # REST API 層
│   ├── __init__.py
│   ├── main.py               # FastAPI 應用入口
│   ├── middleware/            # 中介軟體
│   │   ├── __init__.py
│   │   └── audit.py         # 審計中介軟體
│   └── routes/                # API 路由
│       ├── __init__.py
│       ├── chat.py           # 聊天端點
│       ├── documents.py      # 文檔管理
│       ├── search.py         # 搜尋端點
│       └── sandbox.py        # 沙箱執行
│
├── cli/                        # 命令列介面
│   ├── __init__.py
│   ├── main.py               # CLI 入口（typer）
│   └── commands/             # CLI 指令集
│
├── config/                     # 配置管理
│   ├── __init__.py
│   ├── settings.py           # Pydantic 設定
│   └── schemas/              # 配置 Schema
│
├── agents/                     # AI 代理實現
├── auth/                       # 認證授權模組
├── gateway/                    # API 閘道
├── marketplace/                # 插件市場
├── tools/                      # 工具集合
└── workflow/                   # 工作流引擎
```

### 4.2 `plugins/` - 插件系統

插件目錄包含所有可擴展的插件，每個插件都是獨立的模組。

```plaintext
plugins/
├── PLUGIN_DEV_GUIDE.md         # 插件開發指南
├── {plugin-name}/              # 單個插件目錄結構
│   ├── plugin.json            # 插件清單檔案
│   ├── main.py               # 插件主程式
│   ├── requirements.txt      # 插件依賴
│   ├── README.md             # 插件說明文檔
│   └── tests/                # 插件測試
│
├── example-translator/         # 範例：翻譯工具插件
│   ├── plugin.json
│   ├── main.py
│   └── README.md
│
├── stock-analyst/             # 範例：股票分析代理
│   ├── plugin.json
│   ├── main.py
│   ├── requirements.txt
│   └── tools/
│       └── yahoo_finance.py
│
└── weather-tool/              # 範例：天氣查詢工具
    ├── plugin.json
    └── main.py
```

#### 插件類型支援：
- **Agent Plugins**: 自定義 AI 代理
- **Tool Plugins**: 新工具和整合
- **Service Plugins**: MCP 服務
- **Processor Plugins**: 文檔處理器
- **UI Plugins**: 前端組件
- **Hook Plugins**: 事件監聽器

### 4.3 `tests/` - 測試代碼

測試結構與原始碼目錄對應，便於維護。

```plaintext
tests/
├── __init__.py
├── conftest.py                # Pytest 全局配置和 fixtures
├── unit/                      # 單元測試
│   ├── core/
│   │   ├── test_engine.py
│   │   └── test_protocols.py
│   ├── services/
│   │   ├── test_knowledge_base.py
│   │   └── test_sandbox.py
│   └── plugins/
│       └── test_manager.py
├── integration/               # 整合測試
│   ├── test_api_endpoints.py
│   ├── test_orchestrator.py
│   └── test_plugin_system.py
└── e2e/                      # 端到端測試
    ├── test_chat_flow.py
    └── test_document_pipeline.py
```

### 4.4 `docker/` - 容器化配置

```plaintext
docker/
├── backend/
│   ├── Dockerfile            # 後端服務映像
│   └── entrypoint.sh        # 容器啟動腳本
├── frontend/
│   ├── Dockerfile           # 前端服務映像
│   └── nginx.conf          # Nginx 配置
├── sandbox/
│   ├── Dockerfile          # 沙箱環境映像
│   └── requirements.txt    # 沙箱預裝套件
└── docker-compose.yml       # 開發環境編排
```

## 5. 文件命名約定 (File Naming Conventions)

| 文件類型 | 命名規則 | 範例 |
| :--- | :--- | :--- |
| **Python 模組** | `snake_case.py` | `knowledge_base.py`, `docker_sandbox.py` |
| **Python 類別** | `PascalCase` | `class OpenCodeEngine`, `class PluginManager` |
| **測試文件** | `test_` 前綴 | `test_engine.py`, `test_api_endpoints.py` |
| **配置文件** | `kebab-case` 或 `.` 分隔 | `docker-compose.yml`, `.env.example` |
| **Markdown 文檔** | `UPPER_CASE` 或 `kebab-case` | `README.md`, `plugin-dev-guide.md` |
| **插件目錄** | `kebab-case` | `example-translator`, `stock-analyst` |
| **環境變數** | `UPPER_SNAKE_CASE` | `OPENAI_API_KEY`, `QDRANT_HOST` |

## 6. 演進原則 (Evolution Principles)

### 6.1 模組化擴展原則
*   新功能優先考慮以插件形式實現，避免修改核心代碼
*   服務層的新服務應實現對應的 Protocol 介面
*   保持 Actor 模型的純粹性，業務邏輯應在服務層實現

### 6.2 向後兼容原則
*   API 端點遵循版本化策略（`/api/v1/`, `/api/v2/`）
*   插件介面變更需要提供適配層
*   配置文件格式變更需要提供遷移工具

### 6.3 文檔同步原則
*   任何結構變更都應更新本文檔
*   新增插件必須包含完整的 README.md
*   API 變更需要更新 OpenAPI 規範

### 6.4 測試覆蓋原則
*   新增模組必須包含對應的單元測試
*   關鍵流程需要整合測試覆蓋
*   插件需要提供測試案例

### 6.5 安全第一原則
*   所有外部輸入都需要驗證
*   敏感資訊不得硬編碼
*   插件執行必須在沙箱環境中

---

## 附錄：快速導航 (Quick Navigation)

| 我想要... | 查看目錄 |
| :--- | :--- |
| 了解核心架構 | `src/opencode/core/` |
| 開發新插件 | `plugins/PLUGIN_DEV_GUIDE.md` |
| 添加 API 端點 | `src/opencode/api/routes/` |
| 實現新服務 | `src/opencode/services/` |
| 查看 Actor 實現 | `src/opencode/orchestrator/actors/` |
| 配置環境變數 | `.env.example` |
| 執行測試 | `tests/` |
| 部署應用 | `docker/`, `docker-compose.yml` |