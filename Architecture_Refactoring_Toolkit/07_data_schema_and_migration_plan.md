# 數據模型與遷移計畫 (Data Schema & Migration Plan) - [專案/服務名稱]

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `YYYY-MM-DD`

**主要作者 (Lead Author):** `[請填寫]`

**審核者 (Reviewers):** `[列出主要審核人員/團隊]`

**狀態 (Status):** `[例如：草稿 (Draft), 審核中 (In Review), 已批准 (Approved)]`

---

## 目錄 (Table of Contents)

1.  [概述 (Overview)](#1-概述-overview)
2.  [現有架構 (Current Schema Snapshot)](#2-現有架構-current-schema-snapshot)
3.  [遷移規劃 (Migration Plan)](#3-遷移規劃-migration-plan)
4.  [遷移腳本管理 (Migration Scripts)](#4-遷移腳本管理-migration-scripts)
5.  [回滾與備份策略 (Rollback & Backup Strategy)](#5-回滾與備份策略-rollback--backup-strategy)

---

## 1. 概述 (Overview)

### 1.1 文件目的 (Document Purpose)
*   本文檔用於管理資料庫結構的變更。
*   重構代碼往往伴隨著資料模型的優化，此文件確保數據在遷移過程中不丟失、不毀損，並可回滾。

---

## 2. 現有架構 (Current Schema Snapshot)

*在此處貼上關鍵表的 ER Diagram 或 Schema 定義 (DDL)。*

### 2.1 核心資料表 (Core Tables)
*   `users`: 用戶基本資料。
*   `orders`: 訂單主表。
*   `order_items`: 訂單明細。

### 2.2 遺留資料表 (Legacy Tables)
*   `temp_logs`: 舊版日誌 (建議刪除)。
*   `user_meta_v1`: 舊版用戶擴充欄位。

### 2.3 已知問題 (Known Issues)
*   **效能問題**: `users` 表沒有 Index，查詢很慢。
*   **設計缺陷**: `orders.status` 使用魔術數字 (1, 2, 3)，需重構為 Enum (PENDING, PAID, SHIPPED)。

---

## 3. 遷移規劃 (Migration Plan)

### 3.1 階段性變更 (Phased Changes)

為確保服務不中斷，我們採用「擴充-遷移-切換」三步走策略：

#### Phase 1: 擴充 (Expand)
*   **目標**: 新增欄位或新表，確保新舊代碼共存。
*   **操作**: Add column `status_enum` to `orders`.
*   **相容性**: 舊代碼仍寫入舊欄位，但透過 Trigger 或應用層雙寫 (Dual Write) 到新欄位。

#### Phase 2: 遷移 (Migrate)
*   **目標**: 將舊數據全部搬移到新結構。
*   **操作**: 執行數據清洗腳本。
*   **腳本**: `scripts/db/migrate_status_202510.sql`
*   **驗證**: 檢查 `status_enum` 與 `status` 的數據總數與對應關係一致。

#### Phase 3: 切換 (Contract)
*   **目標**: 移除舊欄位，完成重構。
*   **操作**: 
    1. 部署新版代碼 (僅讀取 `status_enum`)。
    2. Drop column `status` from `orders`.

---

## 4. 遷移腳本管理 (Migration Scripts)

*   **工具**: `[Alembic / Flyway / Liquidbase]`
*   **存放位置**: `./migrations/versions/`
*   **命名規範**: `YYYYMMDD_HHMM_description.sql`

---

## 5. 回滾與備份策略 (Rollback & Backup Strategy)

### 5.1 回滾機制 (Rollback Mechanism)
每個遷移腳本 (Up) 必須對應一個回滾腳本 (Down)。

*   **Up**: `CREATE TABLE new_feature ...`
*   **Down**: `DROP TABLE new_feature;`

> **切記**: 涉及刪除數據 (DROP COLUMN/TABLE) 的操作，必須先備份數據，並在 Staging 環境演練後方可執行。

### 5.2 數據備份與恢復 (Backup & Recovery)
*   **備份頻率**: `重構期間每小時 / 每次部署前`
*   **恢復指令**: 
    ```bash
    pg_restore -d mydb latest_backup.dump
    ```