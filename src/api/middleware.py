"""
審計中間件 - 自動記錄所有 API 請求
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from control_plane.audit import get_audit_service, AuditAction, AuditLevel
from auth.jwt import decode_token

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    審計中間件
    
    自動記錄所有 API 請求到審計日誌
    """
    
    # 不需要記錄的路徑
    EXCLUDE_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    }
    
    # 路徑到動作的映射
    PATH_ACTION_MAP = {
        "/auth/login": AuditAction.LOGIN,
        "/auth/register": AuditAction.REGISTER,
        "/upload": AuditAction.UPLOAD_FILE,
        "/chat": AuditAction.CHAT_QUERY,
        "/chat/stream": AuditAction.CHAT_QUERY,
        "/search": AuditAction.SEARCH_QUERY,
        "/research": AuditAction.RESEARCH_START,
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳過不需要記錄的路徑
        path = request.url.path
        if any(path.startswith(p) for p in self.EXCLUDE_PATHS):
            return await call_next(request)
        
        # 開始計時
        start_time = time.time()
        
        # 提取用戶資訊
        user_id = None
        username = None
        user_role = None
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            token_data = decode_token(token)
            if token_data:
                user_id = token_data.user_id
                username = token_data.username
                user_role = token_data.role.value if token_data.role else None
        
        # 執行請求
        response = None
        error_message = None
        success = True
        
        try:
            response = await call_next(request)
            success = response.status_code < 400
            if not success:
                error_message = f"HTTP {response.status_code}"
        except Exception as e:
            error_message = str(e)
            success = False
            raise
        finally:
            # 計算耗時
            duration = time.time() - start_time
            
            # 決定動作類型
            action = self._get_action(path, request.method)
            
            # 決定級別
            level = AuditLevel.INFO
            if not success:
                level = AuditLevel.ERROR
            elif duration > 5:
                level = AuditLevel.WARNING
            
            # 記錄審計日誌
            try:
                audit_service = get_audit_service()
                audit_service.log(
                    action=action,
                    user_id=user_id,
                    username=username,
                    user_role=user_role,
                    resource=path,
                    success=success,
                    error_message=error_message,
                    level=level,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("User-Agent"),
                    endpoint=path,
                    method=request.method,
                    details={
                        "duration_ms": round(duration * 1000, 2),
                        "status_code": response.status_code if response else 500
                    }
                )
            except Exception as e:
                logger.error(f"Failed to log audit: {e}")
        
        return response
    
    def _get_action(self, path: str, method: str) -> AuditAction:
        """根據路徑和方法決定動作類型"""
        # 精確匹配
        for pattern, action in self.PATH_ACTION_MAP.items():
            if path.startswith(pattern):
                return action
        
        # 根據方法推斷
        if "document" in path.lower():
            if method == "DELETE":
                return AuditAction.DELETE_FILE
            elif method == "GET":
                return AuditAction.VIEW_FILE
            elif method == "POST":
                return AuditAction.UPLOAD_FILE
        
        if "user" in path.lower():
            if method == "POST":
                return AuditAction.USER_CREATE
            elif method == "PUT":
                return AuditAction.USER_UPDATE
            elif method == "DELETE":
                return AuditAction.USER_DELETE
        
        # 預設為工具執行
        return AuditAction.TOOL_EXECUTE
    
    def _get_client_ip(self, request: Request) -> str:
        """獲取客戶端 IP"""
        # 檢查代理標頭
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 直接連接
        if request.client:
            return request.client.host
        
        return "unknown"
