# 架構重構工作流指南 (Architecture Refactoring Workflow Guide)

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `YYYY-MM-DD`

**主要作者 (Lead Author):** `[請填寫]`

**審核者 (Reviewers):** `[列出主要審核人員/團隊]`

**狀態 (Status):** `[例如：草稿 (Draft), 審核中 (In Review), 已批准 (Approved)]`

---

## 目錄 (Table of Contents)

1.  [概述 (Overview)](#1-概述-overview)
2.  [重構階段總覽 (Refactoring Phases Overview)](#2-重構階段總覽-refactoring-phases-overview)
3.  [Phase 0: 戰場偵查 (Discovery)](#3-phase-0-戰場偵查-discovery)
4.  [Phase 1: 建立防線 (Protection)](#4-phase-1-建立防線-protection)
5.  [Phase 2: 繪製地圖 (Mapping)](#5-phase-2-繪製地圖-mapping)
6.  [Phase 3: 外科手術 (Execution)](#6-phase-3-外科手術-execution)
7.  [快速檢核表 (Checklist)](#7-快速檢核表-checklist)

---

## 1. 概述 (Overview)

### 1.1 指南目的 (Guide Purpose)
*   本指南將引導您使用 `Architecture Refactoring Toolkit` 中的 10 份文件，將專案從「一團混亂」轉變為「完全掌控」。
*   透過結構化的流程，像外科醫生一樣精準地進行重構。

---

## 2. 重構階段總覽 (Refactoring Phases Overview)

我們將重構視為一場戰役，分為四個階段。請依序執行，切勿跳步。

| 階段 | 名稱 | 目標 | 關鍵文件 |
| :---: | :--- | :--- | :--- |
| **Phase 0** | **戰場偵查 (Discovery)** | 讓程式跑起來，並搞清楚現狀。 | `01`, `02`, `03` |
| **Phase 1** | **建立防線 (Protection)** | 確保修改不會導致系統崩潰。 | `04`, `05` |
| **Phase 2** | **繪製地圖 (Mapping)** | 理解架構，找出痛點與解決方案。 | `06`, `07`, `08` |
| **Phase 3** | **外科手術 (Execution)** | 實際修改代碼與數據遷移。 | `09`, `10`, `07` |

---

## 3. Phase 0: 戰場偵查 (Discovery)

*先別急著改代碼。如果連跑都跑不起來，重構就無從談起。*

### 3.1 搞定環境
*   **文件**: `01_dev_environment_and_build_manifest.md`
*   **任務**:
    *   試著在本地 `docker-compose up` 或 `npm start`。
    *   **記錄每一個失敗**。缺什麼套件？版本對不對？把它們填入文件中。
    *   **目標**：讓任何人（包括下週的你）都能在 15 分鐘內啟動專案。

### 3.2 盤點資產
*   **文件**: `02_project_structure_guide.md`
*   **任務**:
    *   比對專案目前的目錄結構與標準結構。
    *   標記出「奇怪的資料夾」或「放置錯誤的檔案」。這些是未來的重構目標。

### 3.3 分析依賴
*   **文件**: `03_file_dependencies_template.md`
*   **任務**:
    *   找出「上帝類別」(God Class) — 那些被所有人依賴的巨大檔案。
    *   找出「循環依賴」(Circular Dependency)。
    *   **警告**：這些是地雷區，標記出來，之後要小心處理。

---

## 4. Phase 1: 建立防線 (Protection)

*有了環境後，下一步是確保「改了不會壞」。*

### 4.1 鎖定接口
*   **文件**: `04_api_contract_and_interface_definition.md`
*   **任務**:
    *   列出所有**對外**的 API (REST/GraphQL) 和 SDK 方法。
    *   記錄它們的 Input/Output 範例。
    *   **鐵律**：重構期間，這些接口的行為**絕對不能變**。

### 4.2 測試覆蓋
*   **文件**: `05_legacy_test_coverage_and_strategy.md`
*   **任務**:
    *   執行現有的測試套件。全過了嗎？
    *   如果沒有測試，針對核心流程（如：登入、下單）寫 **「黃金範本測試 (Golden Master Test)」**。
    *   *不看內部邏輯，只錄製 Input 和 Output，確保重構後 Output 位元級一致。*

---

## 5. Phase 2: 繪製地圖 (Mapping)

*現在安全了，開始規劃怎麼改。*

### 5.1 逆向架構
*   **文件**: `06_architecture_and_design_document.md`
*   **任務**:
    *   嘗試畫出目前的 C4 架構圖。
    *   填寫「系統情境」和「容器圖」。
    *   這能幫助你理解數據流向。

### 5.2 數據盤點
*   **文件**: `07_data_schema_and_migration_plan.md`
*   **任務**:
    *   匯出資料庫 Schema (ER Diagram)。
    *   標記出需要正規化、拆分或廢棄的 Table。

### 5.3 決策記錄
*   **文件**: `08_architecture_decision_record_template.md`
*   **任務**:
    *   當你決定「我們要換掉這個 ORM」或「我們要拆分這個 Service」時，**先寫 ADR**。
    *   記錄：為什麼要改？有什麼風險？替代方案是什麼？

---

## 6. Phase 3: 外科手術 (Execution)

*規劃完成，動刀！*

### 6.1 定義規格
*   **文件**: `09_module_specification_and_tests.md`
*   **任務**:
    *   在重寫某個模組前，先定義好它的新介面和單元測試案例。
    *   這就是 TDD (測試驅動開發) 的精神。

### 6.2 執行重構
*   **文件**: `10_code_review_and_refactoring_guide.md`
*   **任務**:
    *   依照指南中的 "Refactoring Strategies" 進行修改。
    *   遵守 Code Review 標準。
    *   **小步快跑**：改一點 -> 跑測試 -> Commit。

### 6.3 數據遷移
*   **文件**: `07_data_schema_and_migration_plan.md`
*   **任務**:
    *   執行 Migration Script。
    *   驗證數據完整性。

---

## 7. 快速檢核表 (Checklist)

*   [ ] **Phase 0**: 環境能跑了嗎？ (`01`)
*   [ ] **Phase 1**: 接口鎖定沒？核心流程有測試保護嗎？ (`04`, `05`)
*   [ ] **Phase 2**: 架構圖畫了嗎？重大決定寫 ADR 了嗎？ (`06`, `08`)
*   [ ] **Phase 3**: 模組規格定義了嗎？Code Review 通過了嗎？ (`09`, `10`)