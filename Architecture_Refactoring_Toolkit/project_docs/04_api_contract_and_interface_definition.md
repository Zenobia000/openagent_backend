# API 契約與接口定義 (API Contract & Interface Definition) - OpenCode Platform

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `2026-02-05`

**主要作者 (Lead Author):** `OpenCode API 團隊`

**審核者 (Reviewers):** `前端團隊, 產品團隊, QA 團隊`

**狀態 (Status):** `已批准 (Approved)`

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
*   本文檔定義 OpenCode Platform 的「外部邊界」與契約。
*   在重構內部邏輯時，必須嚴格遵守此契約，確保不破壞前端、手機 App 或第三方整合的相容性。
*   所有 API 變更必須遵循版本管理和向後兼容原則。

### 1.2 API 設計原則
*   **RESTful 風格:** 遵循 REST 架構風格
*   **一致性:** 統一的命名規範和響應格式
*   **版本化:** 明確的版本管理策略
*   **安全性:** 所有端點預設需要認證
*   **文檔化:** 自動生成的 OpenAPI 文檔

---

## 2. 接口總覽 (Interface Overview)

*   **協議 (Protocol)**: `RESTful HTTP` + `Server-Sent Events (SSE)` + `WebSocket`
*   **基礎 URL (Base URL)**: `/api/v1`
*   **認證方式 (Authentication)**: `Bearer Token (JWT)` / `API Key`
*   **文件標準 (Documentation Standard)**: `OpenAPI 3.0`
*   **自動文檔 (Auto Docs)**: `/docs` (Swagger UI), `/redoc` (ReDoc)

### 2.1 API 分類

| 類別 | 路徑前綴 | 描述 | 認證需求 |
| :--- | :--- | :--- | :--- |
| **核心聊天** | `/chat` | AI 對話功能 | Optional |
| **知識庫** | `/documents` | 文檔管理與檢索 | Optional |
| **搜尋** | `/search` | 語義搜尋功能 | Optional |
| **沙箱** | `/sandbox` | 代碼執行環境 | Required |
| **插件** | `/plugins` | 插件管理 | Admin Only |
| **認證** | `/auth` | 用戶認證授權 | Public |
| **控制平面** | `/admin` | 系統管理 | Admin Only |
| **健康檢查** | `/health` | 服務狀態 | Public |

---

## 3. 關鍵 API 契約 (Critical API Contracts)

### 3.1 核心聊天 API

#### 3.1.1 同步聊天 (Synchronous Chat)
*   **Endpoint**: `POST /api/v1/chat`
*   **描述**: 發送消息並等待完整回應
*   **Input (Request Body)**:
    ```json
    {
      "message": "你好，請介紹一下 OpenCode",
      "context_id": "optional-session-id",
      "model": "gpt-4o",
      "temperature": 0.7,
      "max_tokens": 2000,
      "tools": ["web_search", "code_execution"],
      "files": [
        {
          "name": "document.pdf",
          "content": "base64_encoded_content",
          "type": "application/pdf"
        }
      ]
    }
    ```
*   **Output (Response Body)**:
    ```json
    {
      "response": "OpenCode 是一個企業級的智能代理平台...",
      "context_id": "session-123",
      "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 250,
        "total_tokens": 400
      },
      "sources": [
        {
          "document": "opencode-manual.pdf",
          "page": 5,
          "relevance": 0.92
        }
      ],
      "tools_used": ["knowledge_base"],
      "execution_time": 2.35
    }
    ```
*   **Error Responses**:
    - `400`: 請求格式錯誤
    - `401`: 未授權（如果啟用認證）
    - `429`: 速率限制
    - `500`: 內部錯誤

#### 3.1.2 串流聊天 (Streaming Chat)
*   **Endpoint**: `POST /api/v1/chat/stream`
*   **描述**: 使用 Server-Sent Events 串流回應
*   **Input**: 與同步聊天相同
*   **Output (SSE Stream)**:
    ```
    data: {"type": "start", "context_id": "session-123"}

    data: {"type": "token", "content": "OpenCode"}

    data: {"type": "token", "content": " 是"}

    data: {"type": "tool_call", "tool": "knowledge_base", "status": "searching"}

    data: {"type": "source", "document": "manual.pdf", "relevance": 0.92}

    data: {"type": "end", "usage": {...}, "execution_time": 2.35}
    ```

### 3.2 知識庫管理 API

#### 3.2.1 上傳文檔
*   **Endpoint**: `POST /api/v1/documents/upload`
*   **描述**: 上傳並索引文檔（支援多模態）
*   **Input (Multipart Form)**:
    ```
    - file: 檔案 (PDF, DOCX, TXT, Images)
    - metadata: JSON 物件（可選）
    - chunking_strategy: "auto" | "fixed" | "semantic"
    - embedding_model: "cohere" | "openai"
    ```
*   **Output**:
    ```json
    {
      "document_id": "doc_abc123",
      "filename": "report.pdf",
      "status": "processing",
      "pages": 42,
      "chunks": 156,
      "estimated_time": 30
    }
    ```
*   **契約鎖定**: `document_id` 格式必須保持 `doc_` 前綴

#### 3.2.2 列出文檔
*   **Endpoint**: `GET /api/v1/documents`
*   **Query Parameters**:
    - `page`: 頁碼（預設 1）
    - `limit`: 每頁數量（預設 20，最大 100）
    - `sort`: 排序欄位（name, date, size）
    - `order`: asc | desc
*   **Output**:
    ```json
    {
      "documents": [
        {
          "id": "doc_abc123",
          "name": "report.pdf",
          "size": 2048576,
          "pages": 42,
          "chunks": 156,
          "created_at": "2024-01-15T10:30:00Z",
          "indexed": true
        }
      ],
      "pagination": {
        "page": 1,
        "limit": 20,
        "total": 42,
        "pages": 3
      }
    }
    ```

### 3.3 語義搜尋 API

#### 3.3.1 搜尋知識庫
*   **Endpoint**: `POST /api/v1/search`
*   **Input**:
    ```json
    {
      "query": "OpenCode 的架構設計",
      "top_k": 5,
      "threshold": 0.7,
      "filters": {
        "document_ids": ["doc_abc123"],
        "date_from": "2024-01-01",
        "date_to": "2024-12-31"
      },
      "rerank": true,
      "include_content": true
    }
    ```
*   **Output**:
    ```json
    {
      "results": [
        {
          "document_id": "doc_abc123",
          "document_name": "architecture.pdf",
          "chunk_id": "chunk_456",
          "content": "OpenCode 採用分層架構設計...",
          "score": 0.92,
          "page": 15,
          "metadata": {
            "section": "Architecture Overview"
          }
        }
      ],
      "total_results": 5,
      "query_embedding_time": 0.05,
      "search_time": 0.12
    }
    ```

### 3.4 代碼沙箱 API

#### 3.4.1 執行代碼
*   **Endpoint**: `POST /api/v1/sandbox/execute`
*   **Input**:
    ```json
    {
      "language": "python",
      "code": "print('Hello, World!')\nimport numpy as np\nprint(np.array([1,2,3]))",
      "timeout": 30,
      "memory_limit": "512M",
      "packages": ["numpy", "pandas"]
    }
    ```
*   **Output**:
    ```json
    {
      "execution_id": "exec_789xyz",
      "status": "success",
      "stdout": "Hello, World!\n[1 2 3]",
      "stderr": "",
      "exit_code": 0,
      "execution_time": 0.256,
      "memory_used": "45M",
      "figures": []
    }
    ```
*   **安全限制**:
    - 禁止網路訪問（除白名單）
    - 禁止文件系統寫入（除 /tmp）
    - CPU 和記憶體限制
    - 執行超時自動終止

### 3.5 插件管理 API

#### 3.5.1 列出插件
*   **Endpoint**: `GET /api/v1/plugins`
*   **Output**:
    ```json
    {
      "plugins": [
        {
          "id": "translator",
          "name": "Universal Translator",
          "version": "1.0.0",
          "type": "tool",
          "status": "enabled",
          "description": "多語言翻譯工具",
          "author": "OpenCode Team",
          "dependencies": ["openai"],
          "config_schema": {...}
        }
      ],
      "total": 3
    }
    ```

#### 3.5.2 安裝插件
*   **Endpoint**: `POST /api/v1/plugins/install`
*   **Input**:
    ```json
    {
      "source": "github",
      "repository": "https://github.com/opencode/plugin-example",
      "version": "latest",
      "config": {
        "api_key": "optional-key"
      }
    }
    ```
*   **Output**:
    ```json
    {
      "plugin_id": "example-plugin",
      "status": "installed",
      "message": "Plugin installed successfully",
      "requires_restart": false
    }
    ```

---

## 4. 錯誤處理規範 (Error Handling Standard)

### 4.1 統一錯誤格式

所有 API 錯誤響應必須遵循以下格式：

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Document doc_xyz123 does not exist",
    "details": {
      "document_id": "doc_xyz123",
      "search_index": "knowledge_base"
    },
    "trace_id": "req_abc123xyz",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 4.2 錯誤代碼規範

| HTTP Status | Error Code | 描述 | 處理建議 |
| :--- | :--- | :--- | :--- |
| `400` | `INVALID_REQUEST` | 請求格式錯誤 | 檢查請求參數 |
| `401` | `UNAUTHORIZED` | 未提供認證信息 | 提供有效 Token |
| `403` | `FORBIDDEN` | 無權限訪問 | 檢查用戶權限 |
| `404` | `RESOURCE_NOT_FOUND` | 資源不存在 | 確認資源 ID |
| `409` | `CONFLICT` | 資源衝突 | 處理並發問題 |
| `429` | `RATE_LIMITED` | 速率限制 | 延遲重試 |
| `500` | `INTERNAL_ERROR` | 服務器錯誤 | 聯繫支援 |
| `503` | `SERVICE_UNAVAILABLE` | 服務不可用 | 稍後重試 |

### 4.3 速率限制

*   **Header 資訊**:
    ```
    X-RateLimit-Limit: 100
    X-RateLimit-Remaining: 45
    X-RateLimit-Reset: 1642258800
    ```
*   **限制策略**:
    - 匿名用戶: 100 請求/小時
    - 認證用戶: 1000 請求/小時
    - Admin 用戶: 無限制

---

## 5. 變更管理策略 (Change Management)

### 5.1 API 版本策略

*   **當前版本**: `v1` (生產環境)
*   **URL 格式**: `/api/v{version}/endpoint`
*   **版本生命週期**:
    - **Alpha**: 內部測試，可能有破壞性變更
    - **Beta**: 公開測試，儘量避免破壞性變更
    - **Stable**: 生產環境，只允許向後兼容變更
    - **Deprecated**: 準備棄用，提供遷移指南
    - **Sunset**: 已棄用，返回 410 Gone

### 5.2 破壞性變更 (Breaking Changes)

**定義**: 導致現有客戶端無法正常工作的變更

**禁止的變更**（在同一版本內）:
- 移除或重命名端點
- 移除或重命名必填欄位
- 改變欄位類型（如 string → number）
- 改變錯誤代碼格式
- 改變認證方式

**處理策略**:
1. 必須創建新版本（v2）
2. 保持舊版本至少 6 個月
3. 提供詳細的遷移文檔
4. 在響應頭中加入棄用警告:
   ```
   Sunset: Sat, 31 Dec 2024 23:59:59 GMT
   Deprecation: true
   Link: </api/v2/docs>; rel="successor-version"
   ```

### 5.3 非破壞性變更 (Non-breaking Changes)

**允許的變更**:
- 新增可選欄位
- 新增端點
- 新增可選查詢參數
- 返回額外的元數據
- 改善錯誤訊息（保持代碼不變）

**通知機制**:
- 在 `/api/changelog` 端點列出所有變更
- 發送郵件通知註冊開發者
- 在文檔中標記 "New" 標籤

---

## 6. SDK / Client 依賴 (SDK & Client Dependencies)

### 6.1 官方 SDK

| 平台 | 套件名稱 | 版本 | 維護狀態 |
| :--- | :--- | :--- | :--- |
| **Python** | `opencode-sdk` | `1.0.0` | Active |
| **JavaScript** | `@opencode/client` | `1.0.0` | Active |
| **TypeScript** | `@opencode/client` | `1.0.0` | Active |
| **Go** | `github.com/opencode/go-sdk` | `1.0.0` | Planned |

### 6.2 前端整合

**TypeScript 介面定義**:
```typescript
// src/api/types.ts
interface ChatRequest {
  message: string;
  contextId?: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  tools?: string[];
  files?: FileAttachment[];
}

interface ChatResponse {
  response: string;
  contextId: string;
  usage: TokenUsage;
  sources?: Source[];
  toolsUsed?: string[];
  executionTime: number;
}
```

### 6.3 第三方整合

| 整合方 | 使用端點 | 認證方式 | 聯絡人 |
| :--- | :--- | :--- | :--- |
| **Slack Bot** | Chat, Search | API Key | integration@example.com |
| **Teams App** | Chat, Documents | OAuth 2.0 | teams@example.com |
| **Zapier** | All Public APIs | API Key | zapier@example.com |

### 6.4 WebSocket 連接

**連接端點**: `ws://localhost:8000/ws/chat`

**訊息格式**:
```json
// Client -> Server
{
  "type": "message",
  "data": {
    "content": "Hello",
    "context_id": "session-123"
  }
}

// Server -> Client
{
  "type": "response",
  "data": {
    "content": "Hi there!",
    "partial": false
  }
}
```

---

## 附錄：API 測試指南

### 使用 cURL 測試

```bash
# 健康檢查
curl http://localhost:8000/health

# 聊天請求
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Hello OpenCode",
    "model": "gpt-4o"
  }'

# 上傳文檔
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F 'metadata={"category":"manual"}'

# 語義搜尋
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "architecture design",
    "top_k": 5
  }'
```

### Postman Collection

匯入 `docs/postman/opencode-api.json` 獲得完整的 API 測試集合。

### 契約測試

使用 Pact 或 Postman Contract Tests 確保 API 契約的一致性：

```javascript
// contract-test.js
pm.test("Response has required fields", function () {
    const response = pm.response.json();
    pm.expect(response).to.have.property('response');
    pm.expect(response).to.have.property('context_id');
    pm.expect(response).to.have.property('usage');
});
```