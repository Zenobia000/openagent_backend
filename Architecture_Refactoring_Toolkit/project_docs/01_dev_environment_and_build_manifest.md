# 開發環境與建置清單 (Development Environment & Build Manifest) - OpenCode Platform

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `2026-02-05`

**主要作者 (Lead Author):** `OpenCode Team`

**審核者 (Reviewers):** `架構團隊, DevOps 團隊`

**狀態 (Status):** `已批准 (Approved)`

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
*   本文檔旨在確保所有開發者（包括未來的自己）能在 15 分鐘內搭建出完全一致的開發與建置環境。
*   OpenCode Platform 是一個企業級自主代理系統，實現了多代理架構、RAG 功能和插件系統。

### 1.2 適用範圍 (Scope)
*   適用於 OpenCode Platform 的所有開發、測試與 CI/CD 環境配置。
*   涵蓋後端 API、向量資料庫、沙箱環境和前端應用程式。

---

## 2. 系統依賴 (System Dependencies)

### 2.1 基礎環境 (Base Environment)
*   **OS**: `Ubuntu 22.04 LTS / macOS Sonoma / Windows WSL2`
*   **Runtime**: `Python 3.11+ (必須 >=3.11)`
*   **Package Manager**: `pip 23.0+`
*   **Container Runtime**: `Docker 24.0+ / Docker Desktop`
*   **Compiler/Build Tools**: `gcc, make (for Python packages)`

### 2.2 外部依賴 (External Services)
*本地開發所需的外部服務（使用 docker-compose 管理）*

| 服務名稱 | 版本要求 | Port | 用途 |
| :--- | :--- | :--- | :--- |
| **Qdrant** | `latest` | `6333, 6334` | 向量資料庫，用於 RAG 檢索 |
| **Redis** | `7-alpine (optional)` | `6379` | 分散式快取與 Session 管理 |
| **Sandbox** | `自定義 Docker` | `內部使用` | 安全的程式碼執行環境 |
| **Frontend** | `Vue.js 3` | `80` | Web UI 介面 |

### 2.3 Python 核心套件 (Core Python Packages)

| 類別 | 套件 | 版本 | 用途 |
| :--- | :--- | :--- | :--- |
| **框架** | `fastapi` | `>=0.108.0` | REST API 框架 |
| **非同步** | `aiohttp`, `httpx` | `>=3.9.0, >=0.25.0` | HTTP 客戶端 |
| **AI/LLM** | `openai`, `cohere` | `>=1.0.0, >=5.0.0` | LLM API 整合 |
| **向量DB** | `qdrant-client` | `>=1.7.0` | 向量資料庫客戶端 |
| **文件處理** | `pymupdf`, `python-docx`, `pandas` | 見 requirements.txt | 多模態文件解析 |
| **認證** | `python-jose`, `passlib` | `>=3.3.0, >=1.7.4` | JWT 和密碼處理 |

---

## 3. 環境變數清單 (Environment Variables)

建立 `.env` 檔案於專案根目錄，包含以下設定：

| 變數名稱 | 必填 | 預設值/範例 | 描述 |
| :--- | :---: | :--- | :--- |
| **AI/LLM Services** |
| `OPENAI_API_KEY` | ✅ | `sk-...` | OpenAI API 金鑰 |
| `COHERE_API_KEY` | ❌ | `...` | Cohere API 金鑰（用於嵌入） |
| `GEMINI_API_KEY` | ❌ | `...` | Google Gemini API 金鑰（可選） |
| **Vector Database** |
| `QDRANT_HOST` | ✅ | `localhost` | Qdrant 服務位址 |
| `QDRANT_PORT` | ✅ | `6333` | Qdrant HTTP 端口 |
| `QDRANT_GRPC_PORT` | ❌ | `6334` | Qdrant gRPC 端口 |
| **API Server** |
| `API_HOST` | ❌ | `0.0.0.0` | API 綁定位址 |
| `API_PORT` | ❌ | `8000` | API 服務端口 |
| **Authentication** |
| `JWT_SECRET_KEY` | ✅ | `opencode-secret-key` | JWT 簽名密鑰 |
| `ADMIN_USER` | ❌ | `admin` | 預設管理員帳號 |
| `ADMIN_PASSWORD` | ❌ | `admin123` | 預設管理員密碼 |
| **Sandbox** |
| `SANDBOX_TIMEOUT` | ❌ | `30` | 沙箱執行超時（秒） |
| `DOCKER_HOST` | ❌ | `unix:///var/run/docker.sock` | Docker daemon 連接 |
| **Redis (Optional)** |
| `REDIS_HOST` | ❌ | `localhost` | Redis 服務位址 |
| `REDIS_PORT` | ❌ | `6379` | Redis 端口 |
| **Development** |
| `DEBUG` | ❌ | `False` | 開啟除錯模式 |
| `LOG_LEVEL` | ❌ | `INFO` | 日誌級別 (DEBUG/INFO/WARNING/ERROR) |

---

## 4. 建置與執行指令 (Build & Run Commands)

### 4.1 快速開始 (Quick Start)

```bash
# 1. 克隆專案
git clone <repository-url>
cd opencode_backend

# 2. 創建虛擬環境
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 填入必要的 API 金鑰

# 5. 啟動服務（Docker Compose）
docker-compose up -d

# 6. 驗證服務狀態
curl http://localhost:8000/health
```

### 4.2 開發模式 (Development Mode)

```bash
# 啟動向量資料庫
docker-compose up -d qdrant

# 本地執行後端（支援熱重載）
cd src
uvicorn opencode.api.main:app --reload --host 0.0.0.0 --port 8000

# 安裝開發工具
pip install -e ".[dev]"

# 執行程式碼格式化
black src/
ruff check --fix src/

# 執行測試
pytest tests/ -v --cov=opencode
```

### 4.3 Docker 容器建置 (Container Build)

```bash
# 建置所有服務映像
docker-compose build

# 建置單一服務
docker-compose build backend

# 使用自定義配置
docker-compose --env-file .env.production up -d

# 查看容器日誌
docker-compose logs -f backend
docker-compose logs -f qdrant

# 清理所有容器和卷
docker-compose down -v
```

### 4.4 生產環境部署 (Production Deployment)

```bash
# 建置生產映像
docker build -f docker/backend/Dockerfile -t opencode-backend:latest .

# 使用生產配置啟動
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 健康檢查
curl http://localhost:8000/health
curl http://localhost:6333/health  # Qdrant
```

---

## 5. 除錯指南 (Debugging Guide)

### 5.1 日誌與監控 (Logs & Monitoring)
*   **應用日誌位置**: `./data/logs/opencode.log`
*   **Docker 日誌**: `docker-compose logs -f [service-name]`
*   **Log Level**: 開發環境預設為 `DEBUG`，生產環境為 `INFO`
*   **結構化日誌**: 使用 structlog，支援 JSON 格式輸出

### 5.2 常見問題排除 (Troubleshooting)

#### 問題 1: Qdrant 連接失敗
*   **症狀**: `Connection refused to port 6333`
*   **解法**:
    ```bash
    # 檢查 Qdrant 容器狀態
    docker ps | grep qdrant
    # 重啟 Qdrant
    docker-compose restart qdrant
    # 檢查健康狀態
    curl http://localhost:6333/health
    ```

#### 問題 2: OpenAI API 錯誤
*   **症狀**: `Invalid API Key` 或 `Rate limit exceeded`
*   **解法**:
    - 確認 `.env` 中的 `OPENAI_API_KEY` 正確
    - 檢查 API 配額和計費狀態
    - 實施重試機制和速率限制

#### 問題 3: Docker 權限問題
*   **症狀**: `Permission denied while trying to connect to Docker daemon`
*   **解法**:
    ```bash
    # Linux: 將用戶加入 docker 群組
    sudo usermod -aG docker $USER
    # 重新登入或執行
    newgrp docker
    ```

#### 問題 4: Python 套件安裝失敗
*   **症狀**: `error: Microsoft Visual C++ 14.0 is required` (Windows)
*   **解法**:
    - Windows: 安裝 Visual Studio Build Tools
    - macOS: 安裝 Xcode Command Line Tools
    - Linux: `sudo apt-get install build-essential`

### 5.3 Debug 工具與端點
*   **健康檢查**: `GET /health`
*   **API 文檔**: `GET /docs` (Swagger UI)
*   **重新載入插件**: `POST /plugins/reload`
*   **沙箱測試**: `POST /sandbox/execute`
*   **向量資料庫狀態**: `GET http://localhost:6333/dashboard`

---

## 6. IDE 配置建議 (IDE Setup)

### 6.1 VSCode 推薦設定

**.vscode/settings.json**:
```json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

### 6.2 推薦插件 (Recommended Extensions)
*   **VSCode**:
    *   `ms-python.python` - Python 語言支援
    *   `ms-python.vscode-pylance` - Python 語言伺服器
    *   `ms-azuretools.vscode-docker` - Docker 管理
    *   `redhat.vscode-yaml` - YAML 支援
    *   `esbenp.prettier-vscode` - 程式碼格式化
    *   `github.copilot` - AI 程式碼助手

### 6.3 開發工作流程 (Development Workflow)

1. **程式碼風格檢查**:
   ```bash
   # 執行 linting
   ruff check src/

   # 自動修復
   ruff check --fix src/

   # 格式化
   black src/
   ```

2. **型別檢查**:
   ```bash
   mypy src/opencode
   ```

3. **Pre-commit Hooks** (建議設定):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **測試覆蓋率**:
   ```bash
   pytest --cov=opencode --cov-report=html
   # 開啟 htmlcov/index.html 查看覆蓋率報告
   ```

---

## 附錄：快速參考命令 (Quick Reference)

```bash
# === 環境設定 ===
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# === Docker 操作 ===
docker-compose up -d                 # 啟動所有服務
docker-compose down                  # 停止服務
docker-compose logs -f backend       # 查看日誌
docker-compose restart qdrant        # 重啟特定服務

# === 開發指令 ===
uvicorn opencode.api.main:app --reload  # 開發模式執行
pytest tests/ -v                        # 執行測試
black src/ && ruff check src/           # 程式碼檢查

# === 健康檢查 ===
curl http://localhost:8000/health       # API 健康狀態
curl http://localhost:6333/health       # Qdrant 狀態
```