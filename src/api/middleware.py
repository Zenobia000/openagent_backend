"""
API middleware - request logging and error handling.
Replaces the legacy AuditMiddleware that depended on non-existent modules.
"""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from auth.jwt import decode_token

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, and duration for every API call."""

    EXCLUDE_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in self.EXCLUDE_PATHS):
            return await call_next(request)

        start = time.time()
        response: Response | None = None
        error_msg: str | None = None

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            duration_ms = round((time.time() - start) * 1000, 2)
            status_code = response.status_code if response else 500

            # Extract username from token (best-effort, never fail)
            username = self._extract_username(request)

            level = logging.WARNING if status_code >= 400 else logging.INFO
            logger.log(
                level,
                "%s %s %d %.1fms user=%s%s",
                request.method,
                path,
                status_code,
                duration_ms,
                username or "anonymous",
                f" error={error_msg}" if error_msg else "",
            )

    @staticmethod
    def _extract_username(request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token_data = decode_token(auth_header[7:])
        return token_data.username if token_data else None
