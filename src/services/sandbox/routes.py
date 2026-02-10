"""
Sandbox API 路由

提供代碼執行 API
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth import get_current_user, TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox", tags=["沙箱執行"])


class ExecuteRequest(BaseModel):
    """執行請求"""
    code: str
    language: str = "python"
    context: Optional[Dict[str, Any]] = None
    timeout: int = 60


class ExecuteResponse(BaseModel):
    """執行響應"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time: float = 0.0
    error: Optional[str] = None
    images: List[str] = []  # base64 images
    files: Dict[str, str] = {}  # filename -> base64


@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(
    request: ExecuteRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    執行代碼
    
    支援語言:
    - python: Python 3.11 (pandas, numpy, matplotlib, scikit-learn)
    - bash: Bash shell
    """
    try:
        from services.sandbox.service import SandboxService
        
        sandbox = SandboxService()
        
        if request.language == "python":
            result = await sandbox.execute_python(
                code=request.code,
                timeout=min(request.timeout, 120),  # 最多 2 分鐘
                context=request.context
            )
        elif request.language == "bash":
            result = await sandbox.execute_bash(
                command=request.code,
                timeout=min(request.timeout, 60)
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}"
            )
        
        return ExecuteResponse(
            success=result.get("success", False),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            return_value=result.get("return_value"),
            execution_time=result.get("execution_time", 0),
            error=result.get("error"),
            images=result.get("images", []),
            files=result.get("files", {})
        )
        
    except Exception as e:
        logger.error(f"Execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_sandbox_status(
    current_user: TokenData = Depends(get_current_user)
):
    """獲取沙箱狀態"""
    try:
        from services.sandbox.service import SandboxService
        
        sandbox = SandboxService()
        
        return {
            "available": True,
            "docker_enabled": sandbox._docker_available if hasattr(sandbox, '_docker_available') else False,
            "supported_languages": ["python", "bash"],
            "limits": {
                "timeout": 120,
                "memory": "512MB",
                "cpu": "1 core"
            }
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


@router.post("/validate")
async def validate_code(
    request: ExecuteRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    驗證代碼安全性（不執行）
    """
    try:
        from services.sandbox.service import CodeSecurityFilter
        
        filter = CodeSecurityFilter()
        is_safe, violations = filter.check_code(request.code)
        
        return {
            "is_safe": is_safe,
            "violations": violations
        }
    except Exception as e:
        return {
            "is_safe": False,
            "violations": [str(e)]
        }
