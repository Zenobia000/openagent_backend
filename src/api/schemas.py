"""Pydantic request/response schemas for API endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Chat ──

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=50000)
    mode: str = Field("auto", pattern="^(auto|chat|knowledge|search|code|thinking|deep_research)$")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    stream: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    result: str
    mode: str
    trace_id: str
    tokens_used: int = 0
    time_ms: float = 0
    events: List[Dict[str, Any]] = []


# ── Documents ──

class DocumentUploadResponse(BaseModel):
    task_id: str
    filename: str
    status: str = "processing"
    message: str = "Document queued for indexing"


class DocumentStatusResponse(BaseModel):
    task_id: str
    status: str  # processing, completed, failed
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None


# ── Search ──

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    max_results: int = Field(5, ge=1, le=20)


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    trace_id: str
    time_ms: float = 0


# ── Sandbox ──

class SandboxExecuteRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field("python", pattern="^(python|bash)$")
    timeout: int = Field(60, ge=1, le=120)
    context: Optional[Dict[str, Any]] = None


class SandboxExecuteResponse(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time: float = 0.0
    error: Optional[str] = None


# ── Auth ──

class TokenRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
