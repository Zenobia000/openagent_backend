# 專案結構指南 (Project Structure Guide) - OpenCode Platform

---

**文件版本 (Document Version):** `v1.1`
**最後更新 (Last Updated):** `2026-02-10`
**主要作者 (Lead Author):** `Gemini AI Architect`
**狀態 (Status):** `修訂中 (Revising)`

---

## 目錄 (Table of Contents)

- [1. 指南目的 (Purpose of This Guide)](#1-指南目的-purpose-of-this-guide)
- [2. 核心設計原則 (Core Design Principles)](#2-核心設計原則-core-design-principles)
- [3. 頂層目錄結構 (Top-Level Directory Structure)](#3-頂層目錄結構-top-level-directory-structure)
- [4. `src` 目錄詳解 (Detailed `src` Breakdown)](#4-src-目錄詳解-detailed-src-breakdown)
  - [4.1 `src/api/` - API 層](#41-srcapi---api-層)
  - [4.2 `src/core/` - 核心模組](#42-srccore---核心模組)
  - [4.3 `src/services/` - 服務層](#43-srcservices---服務層)
- [5. 其他關鍵目錄 (Other Key Directories)](#5-其他關鍵目錄-other-key-directories)
- [6. 文件命名約定 (File Naming Conventions)](#6-文件命名約定-file-naming-conventions)

---

## 1. 指南目的 (Purpose of This Guide)

*   為 OpenCode Platform 提供一個標準化、可擴展且易於理解的目錄和文件結構。
*   確保團隊成員能夠快速定位代碼、配置文件和文檔，降低新成員的上手成本。
*   促進代碼的模塊化和關注點分離，提高可維護性。

## 2. 核心設計原則 (Core Design Principles)

*   **分層架構 (Layered Architecture):** 嚴格區分 API 層、核心業務邏輯層和服務層。
*   **關注點分離 (Separation of Concerns):** 每個模組只做一件事並把它做好。例如，`core` 處理業務流程，`services` 處理外部交互。
*   **配置優於硬編碼 (Configuration over Hardcoding):** 系統行為應由配置文件（如 `logging_config.yaml`）和環境變數驅動。
*   **協議驅動 (Protocol-Driven):** 組件間的依賴應基於抽象接口（`protocols.py`），而非具體實現。

## 3. 頂層目錄結構 (Top-Level Directory Structure)

```plaintext
opencode_backend/
├── docker/                     # Docker 相關配置 (Dockerfile, docker-compose.yml)
├── docs/                       # 專案級文檔 (如架構、日誌設計)
├── logs/                       # (如果啟用文件日誌) 應用程式日誌
├── plugins/                    # 插件目錄
├── src/                        # 主要原始碼目錄
│   ├── api/                    # API 層
│   ├── core/                   # 核心業務邏輯
│   └── services/               # 外部服務和具體功能實現
├── tests/                      # 測試套件
├── .env.example                # 環境變數範本
├── .gitignore                  # Git 忽略配置
├── main.py                     # 主應用程式入口 (FastAPI app)
├── pyproject.toml              # Python 專案配置 (PEP 621)
└── requirements.txt            # Python 依賴清單
```

## 4. `src` 目錄詳解 (Detailed `src` Breakdown)

這是專案的核心，實現了 OpenCode Platform 的所有功能。

### 4.1 `src/api/` - API 層

**職責**: 處理 HTTP 請求，驗證輸入，並調用核心業務邏輯。這是系統的入口點。

```plaintext
src/api/
├── __init__.py
├── middleware.py           # API 中介軟體 (例如，日誌、認證)
└── routes.py               # API 路由定義，將端點映射到核心功能
```

### 4.2 `src/core/` - 核心模組

**職責**: 實現平台的核心業務邏輯和處理流程。此層不應直接與外部服務（如資料庫、LLM API）交互，而是通過 `services` 層的抽象來完成。

```plaintext
src/core/
├── __init__.py
├── engine.py              # 核心引擎，協調處理流程
├── logger.py              # 應用程式日誌的配置和初始化
├── logging_config.yaml    # `structlog` 的配置文件
├── models.py              # 核心數據模型 (Pydantic models)
├── processor.py           # 處理器基類和工廠，實現策略模式
├── prompts.py             # Prompt 模板管理
├── protocols.py           # 服務層的抽象接口定義 (Protocol)
├── sre_logger.py          # SRE 相關的日誌功能
└── utils.py               # 核心層級的共用工具函數
```

### 4.3 `src/services/` - 服務層

**職責**: 封裝所有與外部世界的交互，提供具體的工具或功能實現。每個子目錄代表一個獨立的服務。

```plaintext
src/services/
├── __init__.py
├── llm_service.py          # LLM 服務的抽象或高層協調
│
├── browser/                # 瀏覽器自動化服務 (網頁抓取)
│   └── service.py
│
├── knowledge/              # 知識庫/RAG 服務
│   ├── indexer.py          # 建立索引
│   ├── multimodal_parser.py# 多模態文件解析
│   ├── parser.py           # 文件解析基類
│   ├── retriever.py        # 從向量資料庫檢索
│   ├── service.py          # 知識庫服務主入口
│   └── service_old.py      # 舊版服務 (待移除)
│
├── llm/                    # 具體的 LLM API 客戶端實現
│   └── openai_client.py    # OpenAI API 客戶端
│
├── repo/                   # Git 倉庫操作服務
│   └── service.py
│
├── research/               # 研究/分析服務
│   └── service.py
│
├── sandbox/                # 安全程式碼執行沙箱服務
│   ├── routes.py           # 沙箱服務專屬的 API 路由
│   └── service.py          # 通過 Docker 實現沙箱
│
└── search/                 # 網路搜尋服務
    └── service.py
```

## 5. 其他關鍵目錄 (Other Key Directories)

### `tests/` - 測試代碼

測試結構應與 `src/` 目錄對應，以保持清晰。

```plaintext
tests/
├── conftest.py                # Pytest 全局配置和 fixtures
├── requirements-test.txt      # 測試專用的依賴
│
├── unit/                      # 單元測試 (針對單個函數或類)
│   ├── test_engine.py
│   └── test_processors.py
│
├── integration/               # 整合測試 (測試模組間的交互)
│   └── test_api.py
│
└── e2e/                       # 端到端測試 (模擬真實用戶場景)
    ├── test_main.py
    └── test_with_api.py
```

### `docker/` - 容器化配置

```plaintext
docker/
├── docker-compose.yml       # (備用) Docker Compose 配置
├── Dockerfile               # (備用) 通用 Dockerfile
│
├── backend/
│   └── Dockerfile            # 後端服務映像
│
├── frontend/
│   ├── Dockerfile           # 前端服務映像
│   └── nginx.conf          # Nginx 配置
│
└── sandbox/
    ├── Dockerfile          # 沙箱環境映像
    ├── build.sh            # 沙箱建置腳本
    └── runner.py           # 在沙箱內執行程式碼的腳本
```

## 6. 文件命名約定 (File Naming Conventions)

| 文件類型 | 命名規則 | 範例 |
| :--- | :--- | :--- |
| **Python 模組** | `snake_case.py` | `llm_service.py`, `openai_client.py` |
| **Python 類別** | `PascalCase` | `class KnowledgeService`, `class OpenAiClient` |
| **測試文件** | `test_*.py` | `test_engine.py`, `test_api.py` |
| **配置文件** | `kebab-case.yml` 或 `snake_case.yaml` | `docker-compose.yml`, `logging_config.yaml`|
| **Markdown 文檔** | `UPPER_CASE.md` 或 `PascalCase.md` | `README.md`, `QuickStart.md` |
| **環境變數** | `UPPER_SNAKE_CASE` | `OPENAI_API_KEY`, `QDRANT_HOST` |