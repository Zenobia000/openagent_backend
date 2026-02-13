# 遺留測試覆蓋與策略 (Legacy Test Coverage & Strategy) - [專案/服務名稱]

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `YYYY-MM-DD`

**主要作者 (Lead Author):** `[請填寫]`

**審核者 (Reviewers):** `[列出主要審核人員/團隊]`

**狀態 (Status):** `[例如：草稿 (Draft), 審核中 (In Review), 已批准 (Approved)]`

---

## 目錄 (Table of Contents)

1.  [概述 (Overview)](#1-概述-overview)
2.  [現狀盤點 (Current State Audit)](#2-現狀盤點-current-state-audit)
3.  [測試策略 (Testing Strategy for Refactoring)](#3-測試策略-testing-strategy-for-refactoring)
4.  [測試環境 (Test Environment)](#4-測試環境-test-environment)
5.  [CI 集成 (CI Integration)](#5-ci-集成-ci-integration)

---

## 1. 概述 (Overview)

### 1.1 文件目的 (Document Purpose)
*   本文檔用於評估現有專案的測試狀態，並制定「重構保護網」策略。
*   目標是確保重構過程中的修改不會引入回歸錯誤 (Regressions)。

---

## 2. 現狀盤點 (Current State Audit)

### 2.1 模組測試覆蓋率 (Module Test Coverage)

| 模組/功能 | 測試類型 | 覆蓋率估算 | 測試檔案位置 | 可靠性 (Flakiness) |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | Unit | 80% | `tests/unit/auth/` | 高 |
| **Order Processing** | Integration | **10%** (危險) | `tests/int/orders/` | 低 (依賴外部 DB) |
| **Payment** | None | 0% | - | - |
| **Utils** | Unit | 90% | `tests/unit/utils/` | 高 |

### 2.2 風險評估 (Risk Assessment)
*   **主要風險點**: 支付模組 (Payment) 完全無測試，重構時極易出錯，需優先建立防護。
*   **不可靠測試**: 訂單整合測試經常因測試數據污染而失敗，需優化。

---

## 3. 測試策略 (Testing Strategy for Refactoring)

### 3.1 黃金範本測試 (Golden Master Testing)
*針對無測試的遺留代碼 (Legacy Code) 的首要策略。*
*   **適用範圍**: 複雜的計算邏輯、報表生成、核心數據處理。
*   **執行步驟**:
    1.  捕捉真實生產環境的 Input 和 Output。
    2.  將 Output 存為「黃金範本」檔案。
    3.  重構後，執行相同 Input，比對 Output 是否與範本**位元級一致**。

### 3.2 冒煙測試 (Smoke Testing)
*每次 Commit 後必須通過的最小測試集。*
*   [ ] 系統能成功啟動。
*   [ ] 用戶能登入。
*   [ ] 能讀取首頁數據。
*   [ ] 健康檢查 Endpoint (`/health`) 回傳 200 OK。

### 3.3 新增測試規範 (New Test Standards)
*   **新代碼**: 必須包含 Unit Test，覆蓋率 > 90%。
*   **Bug Fix**: 必須先寫一個會 Fail 的 Test 重現 Bug，修復後該 Test Pass (TDD)。

---

## 4. 測試環境 (Test Environment)

### 4.1 Mocking 策略
*   **原則**: 單元測試中不應發出真實網絡請求。
*   **外部 API**: (Payment, SMS) 必須使用 Mock Object 或 Fake Service。
*   **時間依賴**: 使用 `freeze_time` 等工具固定時間。

### 4.2 資料庫策略 (Database Strategy)
*   **隔離性**: 每個測試 Case 啟動前 Rollback Transaction 或重建 SQLite In-memory DB。
*   **數據工廠**: 使用 Factory Pattern (e.g., FactoryBoy) 生成測試數據，避免依賴固定 Fixture。

---

## 5. CI 集成 (CI Integration)

*   **當前 CI 狀態**: `[GitHub Actions / Jenkins / None]`
*   **重構目標**:
    *   建立自動化 Pipeline。
    *   Pull Request 必須通過所有 Unit Tests。
    *   每日排程執行 Integration Tests。