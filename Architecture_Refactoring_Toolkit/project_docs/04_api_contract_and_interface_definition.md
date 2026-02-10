# API 契約與接口定義 (API Contract & Interface Definition) - OpenCode Platform

---

**文件版本 (Document Version):** `v1.1`
**最後更新 (Last Updated):** `2026-02-10`
**主要作者 (Lead Author):** `Gemini AI Architect`
**審核者 (Reviewers):** `前端團隊, 產品團隊, QA 團隊`
**狀態 (Status):** `修訂中 (Revising)`

---

## 1. 概述 (Overview)

### 1.1 文件目的 (Document Purpose)
*   本文檔定義 OpenCode Platform 的 **目標 API 架構**。它作為前後端分離、第三方整合的開發藍圖。
*   所有未來的 API 開發都應遵循此契約，以確保系統的外部一致性和向後兼容性。

### 1.2 **[重要] 當前實現狀態**
*   當前專案 (`v1.0`) 的主要交互方式是通過 **命令行界面 (CLI)**，定義於 `main.py`。
*   HTTP API (`src/api/routes.py`) 目前僅為一個 **基礎存根 (basic stub)**，其實現的端點非常有限，主要用於健康檢查和狀態顯示。
*   以下文檔描述的 **詳細 API 契約 (如 `/chat`, `/documents`, `/sandbox`) 代表了未來的目標設計**，而非當前已實現的功能。開發時應以此為指導，逐步實現這些接口。

### 1.3 API 設計原則
*   **RESTful 風格:** 遵循 REST 架構風格。
*   **一致性:** 統一的命名規範和響應格式。
*   **版本化:** 所有 API 路徑都應包含版本號，如 `/api/v1`。
*   **安全性:** 所有涉及數據操作的端點預設需要認證。
*   **文檔化:** 通過 FastAPI 自動生成 OpenAPI (Swagger) 文檔。

---

## 2. 當前已實現的 API (v1.0)

以下是目前在 `src/api/routes.py` 中實際實現的端點。

| Method | Endpoint | 描述 |
| :--- | :--- | :--- |
| `GET` | `/` | 返回 API 的基本信息和運行狀態。 |
| `GET` | `/health` | 提供簡單的健康檢查，返回服務是否 "healthy"。 |
| `GET` | `/api/status`| 提供一個靜態的 API 狀態，表明各服務 "ready"。|
| `POST` | `/api/process`| 一個極簡的測試端點，接收一個 `query` 字符串並原樣返回。**無實際業務邏輯**。 |

---

## 3. 目標 API 契約 (Target API Contracts - Future Implementation)

以下各節詳細描述了計劃實現的 API 接口。

### 3.1 核心聊天 API (Target)

#### 3.1.1 串流聊天 (Streaming Chat)
*   **Endpoint**: `POST /api/v1/chat/stream`
*   **描述**: 使用 Server-Sent Events (SSE) 實時串流回應，提供最佳的用戶體驗。
*   **Input (Request Body)**:
    ```json
    {
      "message": "你好，請介紹一下 OpenCode",
      "mode": "knowledge", // 對應 ProcessingMode
      "context_id": "optional-session-id",
      "model": "gpt-4o", // 可選
      "temperature": 0.7, // 可選
      "files": [ // 可選，用於上傳文件進行單次對話
        {
          "name": "document.pdf",
          "content": "base64_encoded_content"
        }
      ]
    }
    ```
*   **Output (SSE Stream)**:
    ```
    data: {"type": "start", "context_id": "session-123"}

    data: {"type": "token", "content": "OpenCode"}

    data: {"type": "token", "content": " 是..."}

    data: {"type": "tool_call", "tool": "knowledge_service", "status": "searching"}

    data: {"type": "source", "document": "manual.pdf", "relevance": 0.92}

    data: {"type": "end", "usage": {"prompt_tokens": 150, "completion_tokens": 250}, "execution_time": 2.35}
    ```

### 3.2 知識庫管理 API (Target)

#### 3.2.1 上傳文檔
*   **Endpoint**: `POST /api/v1/documents/upload`
*   **描述**: 上傳並異步索引文檔。
*   **Input (Multipart Form)**:
    - `file`: 一個或多個文件 (PDF, DOCX, TXT, etc.)
    - `metadata`: (可選) 關於文件的 JSON 字符串
*   **Output (Response Body)**:
    ```json
    {
      "task_id": "process_doc_abc123",
      "message": "Document processing started.",
      "files_received": [
        {"filename": "report.pdf", "size": 2048576}
      ]
    }
    ```

#### 3.2.2 獲取文檔處理狀態
*   **Endpoint**: `GET /api/v1/documents/status/{task_id}`
*   **描述**: 查詢文檔索引任務的狀態。
*   **Output**:
    ```json
    {
      "task_id": "process_doc_abc123",
      "status": "completed", // pending, processing, completed, failed
      "document_id": "doc_xyz789",
      "details": "Successfully indexed 156 chunks from report.pdf."
    }
    ```

### 3.3 語義搜尋 API (Target)

*   **Endpoint**: `POST /api/v1/search`
*   **描述**: 在已索引的知識庫中執行語義搜尋。
*   **Input**:
    ```json
    {
      "query": "OpenCode 的架構設計",
      "top_k": 5,
      "filters": {
        "document_id": "doc_xyz789"
      }
    }
    ```
*   **Output**:
    ```json
    {
      "results": [
        {
          "document_id": "doc_xyz789",
          "chunk_id": "chunk_456",
          "content": "OpenCode 採用分層架構設計...",
          "score": 0.92
        }
      ]
    }
    ```

### 3.4 代碼沙箱 API (Target)

*   **Endpoint**: `POST /api/v1/sandbox/execute`
*   **描述**: 安全地執行程式碼片段。
*   **Input**:
    ```json
    {
      "language": "python",
      "code": "print('Hello, World!')",
      "timeout": 30
    }
    ```
*   **Output**:
    ```json
    {
      "status": "success",
      "stdout": "Hello, World!\n",
      "stderr": "",
      "exit_code": 0,
      "execution_time": 0.15
    }
    ```

---

## 4. 錯誤處理規範 (Error Handling Standard)

所有 API 錯誤響應應遵循統一格式。

```json
{
  "detail": {
    "error_code": "RESOURCE_NOT_FOUND",
    "message": "Document doc_xyz123 does not exist.",
    "trace_id": "req_abc123xyz"
  }
}
```

| HTTP Status | Error Code | 描述 |
| :--- | :--- | :--- |
| `400` | `INVALID_REQUEST` | 請求格式或參數錯誤 |
| `401` | `UNAUTHORIZED` | 未提供或無效的認證信息 |
| `403` | `FORBIDDEN` | 無權限訪問該資源 |
| `404` | `RESOURCE_NOT_FOUND` | 請求的資源不存在 |
| `429` | `RATE_LIMITED` | 超出速率限制 |
| `500` | `INTERNAL_SERVER_ERROR`| 服務器內部發生未知錯誤 |
| `503` | `SERVICE_UNAVAILABLE`| 依賴的服務暫時不可用 |

---

## 5. 變更管理策略 (Change Management)

### 5.1 API 版本策略
*   **URL 格式**: `/api/v{version}/endpoint` (e.g., `/api/v1/...`)
*   **向後兼容**: 在一個主版本內（如 `v1`），只允許非破壞性變更。
*   **破壞性變更**: 任何破壞性變更（如刪除字段、修改字段類型）都必須在新的主版本中引入（如 `v2`）。

### 5.2 非破壞性變更 (Allowed Changes in v1)
- 新增 API 端點。
- 為現有端點的請求體新增可選字段。
- 為現有端點的響應體新增字段。

---
## 附錄：API 測試指南 (Target)

當 API 實現後，可使用 `cURL` 或 Postman 進行測試。

```bash
# 目標：測試聊天端點
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Hello OpenCode",
    "mode": "chat"
  }'

# 目標：測試代碼執行
curl -X POST http://localhost:8000/api/v1/sandbox/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "language": "python",
    "code": "print(1+1)"
  }'
```
