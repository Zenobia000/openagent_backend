"""Unified error response format and exception handlers."""

import logging
import traceback
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response body."""
    error_code: str
    message: str
    trace_id: Optional[str] = None
    detail: Optional[str] = None


class APIError(Exception):
    """Application-level API error with structured response."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        detail: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.detail = detail
        self.trace_id = trace_id
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                trace_id=exc.trace_id,
                detail=exc.detail,
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            ).model_dump(exclude_none=True),
        )
