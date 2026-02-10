# 開發環境與建置清單 (Development Environment & Build Manifest) - OpenCode Platform

---

**文件版本 (Document Version):** `v1.1`

**最後更新 (Last Updated):** `2026-02-10`

**主要作者 (Lead Author):** `Gemini AI Architect`

**審核者 (Reviewers):** `架構團隊, DevOps 團隊`

**狀態 (Status):** `修訂中 (Revising)`

---

## 目錄 (Table of Contents)

1.  [概述 (Overview)](#1-概述-overview)
2.  [系統依賴 (System Dependencies)](#2-系統依賴-system-dependencies)
3.  [環境變數清單 (Environment Variables)](#3-環境變數清單-environment-variables)
4.  [建置與執行指令 (Build & Run Commands)](#4-建置與執行指令-build--run-commands)
5.  [除錯指南 (Debugging Guide)](#5-除錯指南-debugging-guide)
6.  [IDE 配置建議 (IDE Setup)](#6-ide-配置建議-ide-setup)

---

## 1. 概述 (Overview)

### 1.1 文件目的 (Document Purpose)
*   本文檔旨在確保所有開發者能在 15 分鐘內搭建出完全一致的開發與建置環境。
*   OpenCode Platform 是一個企業級自主代理系統，實現了多代理架構、RAG 功能和插件系統。

### 1.2 適用範圍 (Scope)
*   適用於 OpenCode Platform 的所有開發、測試與 CI/CD 環境配置。
*   涵蓋後端 API、向量資料庫、沙箱環境和前端應用程式。

---

## 2. 系統依賴 (System Dependencies)

### 2.1 基礎環境 (Base Environment)
*   **OS**: `Ubuntu 22.04 LTS / macOS Sonoma / Windows WSL2`
*   **Runtime**: `Python >=3.11` (根據 `pyproject.toml`)
*   **Package Manager**: `pip`
*   **Container Runtime**: `Docker 24.0+ / Docker Desktop`

### 2.2 外部依賴 (External Services)
*本地開發所需的外部服務（使用 `docker-compose.yml` 管理）*

| 服務名稱 | 映像 | Port | 用途 |
| :--- | :--- | :--- | :--- |
| **Qdrant** | `qdrant/qdrant:latest` | `${QDRANT_PORT:-6333}` | 向量資料庫，用於 RAG 檢索 |
| **Backend** | `build from docker/backend/Dockerfile`| `${API_PORT:-8000}` | 核心後端服務 |
| **Frontend**| `build from docker/frontend/Dockerfile`| `${FRONTEND_PORT:-80}` | Web UI 介面 |
| **Sandbox** | `build from docker/sandbox/Dockerfile`| `內部使用` | 安全的程式碼執行環境 |
| **Redis** | `redis:7-alpine (可選)` | `${REDIS_PORT:-6379}` | 分散式快取 |

### 2.3 Python 核心套件 (Core Python Packages)

核心依賴定義於 `pyproject.toml` 和 `requirements.txt`。

| 類別 | 關鍵套件 | 版本 | 用途 |
| :--- | :--- | :--- | :--- |
| **Web 框架** | `fastapi`, `uvicorn`, `sse-starlette` | `>0.108.0` | REST API 框架, 伺服器, SSE |
| **異步 HTTP** | `aiohttp`, `httpx` | `>=3.9.0`, `>=0.25.0` | 異步 HTTP 客戶端 |
| **AI/LLM** | `openai`, `cohere`, `google-generativeai` | `>=1.0.0`, `>=5.0.0`, `>=0.3.0` | LLM API 整合 (包含 Gemini) |
| **向量DB** | `qdrant-client` | `>=1.7.0` | 向量資料庫客戶端 |
| **文件處理** | `pymupdf`, `python-docx`, `pandas`, `pillow` | 見 `requirements.txt` | 多模態文件解析 |
| **認證** | `python-jose`, `passlib` | `>=3.3.0`, `>=1.7.4` | JWT 和密碼處理 |
| **網路搜尋** | `duckduckgo-search`, `beautifulsoup4` | `>=6.0.0`, `>=4.12.0` | 網頁解析與搜尋 |
| **容器管理** | `docker` | `>=7.0.0` | Docker 引擎互動 |
| **日誌** | `structlog` | `>=23.0.0` | 結構化日誌 |
| **數據模型** | `pydantic`, `pydantic-settings` | `>=2.0.0` | 數據驗證與設定管理 |

---

## 3. 環境變數清單 (Environment Variables)

建立 `.env` 檔案於專案根目錄，參考 `.env.example`。

| 變數名稱 | 必填 | `docker-compose.yml` 中預設值/範例 | 描述 |
| :--- | :---: | :--- | :--- |
| **AI/LLM Services** |
| `OPENAI_API_KEY` | ✅ | - | OpenAI API 金鑰 |
| `COHERE_API_KEY` | ❌ | - | Cohere API 金鑰 |
| `JWT_SECRET_KEY` | ✅ | `opencode-docker-secret` | JWT 簽名密鑰 |
| **Vector Database** |
| `QDRANT_HOST` | ✅ | `qdrant` (in-docker) | Qdrant 服務位址 |
| `QDRANT_PORT` | ✅ | `6333` | Qdrant HTTP 端口 |
| `QDRANT_GRPC_PORT`| ❌ | `6334` | Qdrant gRPC 端口 |
| **API Server** |
| `API_HOST` | ❌ | `0.0.0.0` | API 綁定位址 |
| `API_PORT` | ❌ | `8000` | API 服務端口 |
| **Frontend** |
| `FRONTEND_PORT` | ❌ | `80` | 前端服務端口 |
| **Sandbox** |
| `SANDBOX_TIMEOUT` | ❌ | `30` | 沙箱執行超時（秒） |
| **Redis (Optional)** |
| `REDIS_PORT` | ❌ | `6379` | Redis 端口 |

---

## 4. 建置與執行指令 (Build & Run Commands)

### 4.1 快速開始 (Quick Start with Docker)

```bash
# 1. 克隆專案
git clone <repository-url>
cd opencode_backend

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入必要的 API 金鑰 (OPENAI_API_KEY)

# 3. 啟動所有服務
docker-compose up -d --build

# 4. 驗證服務狀態
echo "Waiting for services to be healthy..."
sleep 15
curl http://localhost:8000/health
curl http://localhost:6333/health
```

### 4.2 本地開發模式 (Local Development)

```bash
# 1. (首次) 啟動依賴的服務
docker-compose up -d qdrant

# 2. 創建並激活 Python 虛擬環境
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 執行後端 (支援熱重載)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4.3 測試與品質保證

```bash
# 安裝開發依賴
pip install -r tests/requirements-test.txt

# 執行測試
pytest tests/

# 執行程式碼格式化與檢查 (需安裝 black, ruff)
pip install black ruff
black .
ruff check . --fix
```

---

## 5. 除錯指南 (Debugging Guide)

### 5.1 日誌與監控 (Logs & Monitoring)
*   **應用日誌位置**: 預設輸出到 `stdout/stderr`，在 Docker 環境中通過 `docker-compose logs` 查看。
*   **Docker 日誌**: `docker-compose logs -f [service-name]` (e.g., `backend`, `qdrant`)
*   **Log Level**: 可通過環境變數 `LOG_LEVEL` 控制 (e.g., `DEBUG`, `INFO`)

### 5.2 常見問題排除 (Troubleshooting)

#### 問題 1: Qdrant 連接失敗
*   **症狀**: `Connection refused to port 6333`
*   **解法**:
    ```bash
    # 檢查 Qdrant 容器狀態
    docker-compose ps
    # 查看 Qdrant 日誌
    docker-compose logs qdrant
    # 重啟 Qdrant
    docker-compose restart qdrant
    ```

#### 問題 2: `main:app` 找不到
*   **症狀**: `ERROR: No application 'app' found in module 'main'.`
*   **解法**:
    - 確保在專案根目錄下執行 `uvicorn`。
    - 檢查 `main.py` 中 `app` 物件是否正確定義。

---

## 6. IDE 配置建議 (IDE Setup)

### 6.1 VSCode 推薦設定

**.vscode/settings.json**:
```json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    }
}
```

### 6.2 推薦插件 (Recommended Extensions)
*   **VSCode**:
    *   `ms-python.python`
    *   `ms-python.vscode-pylance`
    *   `ms-azuretools.vscode-docker`
    *   `charliermarsh.ruff`
    *   `ms-python.black-formatter`
    *   `github.copilot`

---

## 附錄：快速參考命令 (Quick Reference)

```bash
# === Docker 操作 ===
docker-compose up -d --build  # 首次啟動或代碼變更後
docker-compose up -d          # 日常啟動
docker-compose down -v        # 停止並移除數據卷
docker-compose logs -f backend# 查看後端日誌

# === 本地開發指令 ===
uvicorn main:app --reload     # 開發模式執行
pytest                      # 執行測試
black . && ruff check .       # 程式碼檢查

# === 健康檢查 ===
curl http://localhost:8000/health
curl http://localhost:6333
```
