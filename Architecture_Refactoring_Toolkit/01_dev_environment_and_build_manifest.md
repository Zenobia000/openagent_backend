# 開發環境與建置清單 (Development Environment & Build Manifest) - [專案/服務名稱]

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `YYYY-MM-DD`

**主要作者 (Lead Author):** `[請填寫]`

**審核者 (Reviewers):** `[列出主要審核人員/團隊]`

**狀態 (Status):** `[例如：草稿 (Draft), 審核中 (In Review), 已批准 (Approved)]`

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
*   解決 "It works on my machine" 問題，統一團隊開發基準。

### 1.2 適用範圍 (Scope)
*   適用於本專案的所有開發、測試與 CI/CD 環境配置。

---

## 2. 系統依賴 (System Dependencies)

### 2.1 基礎環境 (Base Environment)
*   **OS**: `[e.g., Ubuntu 22.04 LTS / macOS Sonoma]`
*   **Runtime**: `[e.g., Python 3.11.4 / Node.js 18.17.0]` (精確到 Patch 版本)
*   **Compiler/Build Tools**: `[e.g., GCC 11, Make, CMake 3.20+]`

### 2.2 外部依賴 (External Services)
*本地開發所需的外部服務（建議使用 docker-compose）*

| 服務名稱 | 版本要求 | Port | 用途 |
| :--- | :--- | :--- | :--- |
| **Database** | `[e.g., PostgreSQL 15.3]` | `5432` | 核心資料儲存 |
| **Cache** | `[e.g., Redis 7.0]` | `6379` | 快取與 Session |
| **Message Queue** | `[e.g., RabbitMQ 3.12]` | `5672` | 異步任務隊列 |

---

## 3. 環境變數清單 (Environment Variables)

| 變數名稱 | 必填 | 預設值/範例 | 描述 |
| :--- | :---: | :--- | :--- |
| `DB_HOST` | ✅ | `localhost` | 資料庫連線位址 |
| `API_KEY` | ❌ | `sk_test_...` | 第三方服務金鑰 (Dev mode 可留空) |
| `DEBUG` | ✅ | `True` | 開啟除錯模式，顯示詳細日誌 |
| `SECRET_KEY` | ✅ | `dev_secret` | 應用程式加密密鑰 (生產環境需更換) |

---

## 4. 建置與執行指令 (Build & Run Commands)

### 4.1 安裝依賴 (Install Dependencies)
```bash
# Python
pip install -r requirements-dev.txt

# Node.js
npm ci  # 使用 ci 而非 install 以確保鎖定版本
```

### 4.2 啟動本地環境 (Start Local Environment)
```bash
# 啟動依賴服務
docker-compose up -d db redis

# 執行 Database Migration
alembic upgrade head

# 啟動應用程式
python main.py
```

### 4.3 建置發布包 (Production Build)
```bash
# 描述如何產生最終的 Docker Image 或 Binary
docker build -t my-app:latest .
```

---

## 5. 除錯指南 (Debugging Guide)

### 5.1 日誌與監控 (Logs & Monitoring)
*   **Log 位置**: `./logs/dev.log`
*   **Log Level**: 開發環境預設為 `DEBUG`，生產環境為 `INFO`。

### 5.2 常見問題排除 (Troubleshooting)
*   **Error X**:
    *   **症狀**: `Module not found error...`
    *   **解法**: 執行 `make clean && pip install -r requirements.txt`
*   **Error Y**:
    *   **症狀**: `Connection refused to port 5432`
    *   **解法**: 檢查 docker 容器是否運行 `docker ps`，確認端口映射。

### 5.3 Debug Port
*   **Port**: `5678` (支援 VSCode Attach)

---

## 6. IDE 配置建議 (IDE Setup)

### 6.1 推薦插件 (Recommended Extensions)
*   **VSCode**:
    *   `Pylance` (Python 語言支援)
    *   `Docker` (容器管理)
    *   `ESLint` (JS 代碼檢查)

### 6.2 格式化與 Linting (Formatter & Linter)
*   **Python**: 使用 `Black` 與 `Ruff`。
*   **JavaScript**: 使用 `Prettier`。
*   **設定**: 請開啟 "Format On Save" 功能，確保代碼風格一致。