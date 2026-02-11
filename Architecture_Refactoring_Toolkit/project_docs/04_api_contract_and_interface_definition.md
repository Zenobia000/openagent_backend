# API Contract & Interface Definition - OpenCode Platform

---

**Document Version:** `v2.0`
**Last Updated:** `2026-02-12`
**Status:** `Current (Implemented)`

---

## 1. Overview

This document defines the **implemented** API contracts of OpenCode Platform. All endpoints listed below are fully functional with JWT authentication, Pydantic validation, and structured error responses.

### Design Principles

- **RESTful**: Follows REST conventions.
- **Versioned**: All data endpoints under `/api/v1/`.
- **Authenticated**: Data endpoints require Bearer JWT token.
- **Documented**: Auto-generated OpenAPI docs at `/docs`.

---

## 2. Endpoint Summary

| Method | Endpoint | Auth | Description |
|:---|:---|:---:|:---|
| `GET` | `/` | No | Platform info |
| `GET` | `/health` | No | Health check |
| `GET` | `/api/status` | No | Engine readiness status |
| `POST` | `/api/v1/auth/token` | No | Issue JWT token |
| `POST` | `/api/v1/chat` | Yes | Synchronous chat |
| `POST` | `/api/v1/chat/stream` | Yes | SSE streaming chat |
| `POST` | `/api/v1/documents/upload` | Yes | Upload document for indexing |
| `GET` | `/api/v1/documents/status/{task_id}` | Yes | Check indexing status |
| `POST` | `/api/v1/search` | Yes | Semantic search |
| `POST` | `/api/v1/sandbox/execute` | Yes | Execute code in sandbox |
| `GET` | `/api/v1/metrics` | Yes | Cognitive metrics summary |

---

## 3. Detailed API Contracts

### 3.1 Authentication

#### POST `/api/v1/auth/token`

**Request:**
```json
{
  "username": "user",
  "password": "pass"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

Use the token in subsequent requests: `Authorization: Bearer <token>`

### 3.2 Chat

#### POST `/api/v1/chat`

**Request:**
```json
{
  "query": "Explain quantum computing",
  "mode": "thinking",
  "temperature": 0.7,
  "max_tokens": 4096,
  "metadata": {}
}
```

**Fields:**
- `query` (required, min 1 char): User message.
- `mode` (optional, default `"auto"`): One of `auto`, `chat`, `knowledge`, `search`, `code`, `thinking`, `deep_research`.
- `temperature`, `max_tokens`, `metadata`: Optional overrides.

**Response (200):**
```json
{
  "result": "Quantum computing uses quantum-mechanical phenomena...",
  "mode": "thinking",
  "trace_id": "4c45cdfd-...",
  "tokens_used": 789,
  "time_ms": 6995,
  "events": []
}
```

### 3.3 Streaming Chat (SSE)

#### POST `/api/v1/chat/stream`

Same request body as `/api/v1/chat`. Returns `text/event-stream`:

```
data: {"event": "start", "data": {"trace_id": "abc123"}}

data: {"event": "token", "data": {"content": "Quantum"}}

data: {"event": "token", "data": {"content": " computing"}}

data: {"event": "tool_call", "data": {"tool": "search", "status": "executing"}}

data: {"event": "source", "data": {"title": "...", "url": "..."}}

data: {"event": "end", "data": {"tokens_used": 789, "time_ms": 6995}}
```

### 3.4 Document Upload

#### POST `/api/v1/documents/upload`

**Request:** Multipart form with `file` field.

**Response (200):**
```json
{
  "task_id": "abc123",
  "filename": "report.pdf",
  "status": "completed",
  "message": "Indexed"
}
```

#### GET `/api/v1/documents/status/{task_id}`

**Response (200):**
```json
{
  "task_id": "abc123",
  "status": "completed",
  "progress": 1.0,
  "message": "Indexed"
}
```

### 3.5 Semantic Search

#### POST `/api/v1/search`

**Request:**
```json
{
  "query": "OpenCode architecture",
  "top_k": 5
}
```

**Response (200):**
```json
{
  "query": "OpenCode architecture",
  "results": [{"content": "..."}],
  "trace_id": "...",
  "time_ms": 2500
}
```

### 3.6 Code Sandbox

#### POST `/api/v1/sandbox/execute`

**Request:**
```json
{
  "code": "print('Hello')",
  "language": "python",
  "timeout": 30,
  "context": {}
}
```

**Response (200):**
```json
{
  "success": true,
  "stdout": "Hello\n",
  "stderr": "",
  "return_value": null,
  "execution_time": 0.15,
  "error": null
}
```

### 3.7 Cognitive Metrics

#### GET `/api/v1/metrics`

**Response (200):**
```json
{
  "total_requests": 42,
  "system1": {
    "request_count": 30,
    "avg_latency_ms": 150,
    "success_rate": 0.97,
    "total_tokens": 15000
  },
  "system2": {
    "request_count": 10,
    "avg_latency_ms": 3500,
    "success_rate": 0.90,
    "total_tokens": 8000
  },
  "agent": {
    "request_count": 2,
    "avg_latency_ms": 15000,
    "success_rate": 1.0,
    "total_tokens": 5000
  }
}
```

---

## 4. Error Response Format

All errors follow a unified structure via `APIError` + `register_error_handlers()`:

```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "Task abc123 not found",
  "trace_id": "req_xyz",
  "detail": null
}
```

| HTTP Status | Error Code | Description |
|:---|:---|:---|
| `400` | `INVALID_REQUEST` | Bad request body or parameters |
| `401` | `UNAUTHORIZED` | Missing or invalid JWT token |
| `404` | `TASK_NOT_FOUND` / `RESOURCE_NOT_FOUND` | Resource does not exist |
| `422` | (Pydantic) | Validation error (auto-generated) |
| `500` | `INTERNAL_ERROR` | Unexpected server error |
| `503` | `ENGINE_NOT_READY` / `SANDBOX_UNAVAILABLE` | Service not initialized |

---

## 5. Change Management

- **URL versioning**: `/api/v1/...`. Breaking changes require `/api/v2/`.
- **Non-breaking changes allowed**: New endpoints, new optional request fields, new response fields.
- **Breaking changes forbidden in v1**: Removing fields, changing types, renaming endpoints.

---

## 6. Testing

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Chat
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello","mode":"chat"}'

# Stream
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain AI","mode":"thinking"}'

# Metrics
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/metrics
```
