# API 契約與接口定義 (API Contract & Interface Definition) - [專案/服務名稱]

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `YYYY-MM-DD`

**主要作者 (Lead Author):** `[請填寫]`

**審核者 (Reviewers):** `[列出主要審核人員/團隊]`

**狀態 (Status):** `[例如：草稿 (Draft), 審核中 (In Review), 已批准 (Approved)]`

---

## 目錄 (Table of Contents)

1.  [概述 (Overview)](#1-概述-overview)
2.  [接口總覽 (Interface Overview)](#2-接口總覽-interface-overview)
3.  [關鍵 API 契約 (Critical API Contracts)](#3-關鍵-api-契約-critical-api-contracts)
4.  [錯誤處理規範 (Error Handling Standard)](#4-錯誤處理規範-error-handling-standard)
5.  [變更管理策略 (Change Management)](#5-變更管理策略-change-management)
6.  [SDK / Client 依賴 (SDK & Client Dependencies)](#6-sdk--client-依賴-sdk--client-dependencies)

---

## 1. 概述 (Overview)

### 1.1 文件目的 (Document Purpose)
*   本文檔定義系統的「外部邊界」與契約。
*   在重構內部邏輯時，必須嚴格遵守此契約，確保不破壞前端、手機 App 或第三方整合的相容性。

---

## 2. 接口總覽 (Interface Overview)

*   **協議 (Protocol)**: `[RESTful HTTP / gRPC / GraphQL]`
*   **基礎 URL (Base URL)**: `/api/v1`
*   **認證方式 (Authentication)**: `[Bearer Token / API Key / OAuth2]`
*   **文件標準 (Documentation Standard)**: `[OpenAPI 3.0 / Swagger 2.0 / Protobuf]`

---

## 3. 關鍵 API 契約 (Critical API Contracts)

*列出核心業務最關鍵的 API。如果有的話，連結到自動生成的 Swagger UI。*

### 3.1 認證 (Authentication)
*   **Endpoint**: `POST /auth/login`
*   **Input (Request Body)**:
    ```json
    {
      "email": "user@example.com",
      "password": "secure_password"
    }
    ```
*   **Output (Response Body)**:
    ```json
    {
      "token": "eyJhbGciOiJIUzI1NiIsInR...",
      "expires_in": 3600
    }
    ```
*   **Error 401**: `{ "code": "AUTH_FAILED", "message": "Invalid credentials" }`

### 3.2 核心資源 (Core Resources)
*   **Endpoint**: `GET /orders/{id}`
*   **契約鎖定 (Contract Lock)**:
    *   回傳結構必須包含 `id`, `items[]`, `total_price`。
    *   **注意**: `total_price` 欄位目前是 String，重構時**不可**改為 Number，否則舊版 App 會崩潰。

---

## 4. 錯誤處理規範 (Error Handling Standard)

所有 API 必須遵循統一的錯誤格式：

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Order 123 does not exist",
    "trace_id": "abc-123-xyz"
  }
}
```

*   **HTTP Status Codes**:
    *   `200`: 成功
    *   `400`: 請求格式錯誤 (Bad Request)
    *   `401`: 未認證 (Unauthorized)
    *   `403`: 無權限 (Forbidden)
    *   `404`: 資源不存在 (Not Found)
    *   `500`: 伺服器內部錯誤 (Internal Server Error)

---

## 5. 變更管理策略 (Change Management)

### 5.1 破壞性變更 (Breaking Changes)
*   定義：導致現有客戶端無法正常工作的變更（如移除欄位、修改欄位類型）。
*   **策略**:
    *   必須升級 API 版本號 (e.g., `/api/v2`).
    *   必須保留 v1 接口至少 6 個月，並通知所有消費者。

### 5.2 非破壞性變更 (Non-breaking Changes)
*   定義：向後兼容的變更（如新增選填欄位）。
*   **策略**:
    *   新增欄位 (Additive changes) 是允許的。
    *   移除欄位是**禁止**的。

---

## 6. SDK / Client 依賴 (SDK & Client Dependencies)

*   **Web Client**: `src/api/client.ts` (TypeScript Interface 需同步更新)
*   **Mobile SDK**: `android-sdk-v1.jar`
*   **Third-party Integrations**: `[列出依賴此 API 的外部合作夥伴]`