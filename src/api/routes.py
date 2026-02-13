"""
API Routes - complete API layer with versioned endpoints.
Integrates with RefactoredEngine, auth, SSE streaming, and services.
"""

import os
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from core.engine import RefactoredEngine
from core.models import Request, ProcessingMode
from auth import get_current_user, get_optional_user, TokenData
from auth.jwt import encode_token, UserRole, ACCESS_TOKEN_EXPIRE_MINUTES
from api.schemas import (
    ChatRequest, ChatResponse,
    DocumentUploadResponse, DocumentStatusResponse,
    SearchRequest, SearchResponse,
    SandboxExecuteRequest, SandboxExecuteResponse,
    TokenRequest, TokenResponse,
)
from api.errors import APIError, register_error_handlers
from api.streaming import engine_event_generator

logger = logging.getLogger(__name__)

# In-memory stores (production would use DB/Redis)
_document_tasks: dict = {}

# Engine singleton - initialized in create_app lifespan
_engine: RefactoredEngine | None = None


def _get_engine() -> RefactoredEngine:
    if _engine is None:
        raise APIError(503, "ENGINE_NOT_READY", "Engine not initialized")
    return _engine


def create_app(engine: RefactoredEngine | None = None) -> FastAPI:
    """Create the FastAPI application with all routes."""
    global _engine

    # Engine injection (before lifespan so it's available)
    if engine is not None:
        _engine = engine

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global _engine
        # Auto-create engine from env if not injected (production path)
        if _engine is None:
            try:
                from services.llm import create_llm_client
                llm_client = create_llm_client()
                _engine = RefactoredEngine(llm_client=llm_client)
                logger.info("Engine auto-created with %s", llm_client.provider_name)
            except Exception as e:
                logger.warning("Could not auto-create engine: %s", e)
        if _engine is not None and not _engine.initialized:
            await _engine.initialize()
        yield

    app = FastAPI(
        title="OpenCode Platform API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    register_error_handlers(app)

    # ── Public endpoints ──

    @app.get("/")
    async def root():
        return {"message": "OpenCode Platform API", "version": "2.0.0", "status": "running"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/api/status")
    async def api_status():
        return {
            "api": "operational",
            "engine_ready": _engine is not None and _engine.initialized,
        }

    # ── Auth ──

    @app.post("/api/v1/auth/token", response_model=TokenResponse)
    async def create_token(req: TokenRequest):
        """Issue a JWT token.

        In production this would verify credentials against a user store.
        For now, accepts any username/password and issues a USER-role token.
        """
        # TODO: replace with real user store lookup
        demo_user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, req.username))
        token = encode_token(
            user_id=demo_user_id,
            username=req.username,
            role=UserRole.USER,
        )
        return TokenResponse(
            access_token=token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Chat ──

    @app.post("/api/v1/chat", response_model=ChatResponse)
    async def chat(
        req: ChatRequest,
        user: TokenData = Depends(get_current_user),
    ):
        """Synchronous chat endpoint supporting all ProcessingMode values."""
        eng = _get_engine()
        core_request = Request(
            query=req.query,
            mode=ProcessingMode(req.mode),
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            metadata=req.metadata,
        )
        response = await eng.process(core_request)
        return ChatResponse(
            result=response.result,
            mode=response.mode.value,
            trace_id=response.trace_id,
            tokens_used=response.tokens_used,
            time_ms=response.time_ms,
            events=response.events,
        )

    # ── Chat Stream (SSE) ──

    @app.post("/api/v1/chat/stream")
    async def chat_stream(
        req: ChatRequest,
        user: TokenData = Depends(get_current_user),
    ):
        """SSE streaming chat endpoint."""
        eng = _get_engine()
        core_request = Request(
            query=req.query,
            mode=ProcessingMode(req.mode),
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=True,
            metadata=req.metadata,
        )
        return EventSourceResponse(engine_event_generator(eng, core_request))

    # ── Documents ──

    @app.post("/api/v1/documents/upload", response_model=DocumentUploadResponse)
    async def upload_document(
        file: UploadFile = File(...),
        user: TokenData = Depends(get_current_user),
    ):
        """Upload a document for async knowledge-base indexing."""
        task_id = str(uuid.uuid4())
        _document_tasks[task_id] = {
            "status": "processing",
            "progress": 0.0,
            "filename": file.filename,
            "message": "Document queued for indexing",
        }

        # Read file content (store or pass to indexer in production)
        content = await file.read()
        _document_tasks[task_id]["size_bytes"] = len(content)

        # TODO: dispatch async indexing task via background worker
        # For now, mark as completed immediately
        _document_tasks[task_id].update(status="completed", progress=1.0, message="Indexed")

        return DocumentUploadResponse(
            task_id=task_id,
            filename=file.filename or "unknown",
            status=_document_tasks[task_id]["status"],
            message=_document_tasks[task_id]["message"],
        )

    @app.get("/api/v1/documents/status/{task_id}", response_model=DocumentStatusResponse)
    async def document_status(
        task_id: str,
        user: TokenData = Depends(get_current_user),
    ):
        """Check document processing status."""
        task = _document_tasks.get(task_id)
        if task is None:
            raise APIError(404, "TASK_NOT_FOUND", f"Task {task_id} not found")
        return DocumentStatusResponse(
            task_id=task_id,
            status=task["status"],
            progress=task.get("progress", 0.0),
            message=task.get("message", ""),
        )

    # ── Search ──

    @app.post("/api/v1/search", response_model=SearchResponse)
    async def search(
        req: SearchRequest,
        user: TokenData = Depends(get_current_user),
    ):
        """Semantic search endpoint using the engine's SEARCH mode."""
        eng = _get_engine()
        core_request = Request(query=req.query, mode=ProcessingMode.SEARCH)
        response = await eng.process(core_request)
        return SearchResponse(
            query=req.query,
            results=[{"content": response.result}],
            trace_id=response.trace_id,
            time_ms=response.time_ms,
        )

    # ── Sandbox ──

    @app.post("/api/v1/sandbox/execute", response_model=SandboxExecuteResponse)
    async def sandbox_execute(
        req: SandboxExecuteRequest,
        user: TokenData = Depends(get_current_user),
    ):
        """Execute code in a sandboxed environment."""
        try:
            from services.sandbox.service import SandboxService
            sandbox = SandboxService()

            if req.language == "python":
                result = await sandbox.execute_python(
                    code=req.code,
                    timeout=req.timeout,
                    context=req.context,
                )
            else:
                result = await sandbox.execute_bash(
                    command=req.code,
                    timeout=req.timeout,
                )

            return SandboxExecuteResponse(
                success=result.get("success", False),
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                return_value=result.get("return_value"),
                execution_time=result.get("execution_time", 0),
                error=result.get("error"),
            )
        except ImportError:
            raise APIError(503, "SANDBOX_UNAVAILABLE", "Sandbox service not available")
        except Exception as e:
            raise APIError(500, "SANDBOX_ERROR", str(e))

    # ── Metrics ──

    @app.get("/api/v1/metrics")
    async def get_metrics(user: TokenData = Depends(get_current_user)):
        """Cognitive metrics summary (requires auth)."""
        eng = _get_engine()
        return eng.metrics

    return app
