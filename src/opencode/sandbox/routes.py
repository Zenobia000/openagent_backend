"""
Sandbox API 路由

提供代碼執行 API
"""

import logging
import base64
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field

from opencode.auth import get_current_user, TokenData
from . import get_sandbox, CodeSandbox, Language, ExecutionConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox", tags=["代碼執行"])


class ExecuteRequest(BaseModel):
    """執行請求"""
    code: str = Field(..., description="要執行的代碼")
    language: str = Field(default="python", description="程式語言: python, javascript, shell")
    timeout: int = Field(default=60, ge=1, le=300, description="超時秒數")
    network_enabled: bool = Field(default=True, description="是否允許網路")
    files: Optional[Dict[str, str]] = Field(default=None, description="輸入文件 {filename: base64_content}")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文變數")


class ExecuteResponse(BaseModel):
    """執行回應"""
    success: bool
    stdout: str
    stderr: str
    return_value: Any = None
    execution_time: float
    files: List[Dict[str, Any]] = []
    images: List[str] = []
    error: Optional[str] = None


@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(
    request: ExecuteRequest,
    current_user: TokenData = Depends(get_current_user),
    sandbox: CodeSandbox = Depends(get_sandbox)
):
    """
    執行代碼
    
    支援：
    - Python（含 pandas、matplotlib、numpy 等）
    - JavaScript (Node.js)
    - Shell
    
    會自動收集：
    - 標準輸出/錯誤
    - 生成的文件
    - matplotlib 圖表（自動轉 base64）
    """
    try:
        # 解析語言
        try:
            language = Language(request.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}. Supported: python, javascript, shell"
            )
        
        # 配置
        config = ExecutionConfig(
            timeout=request.timeout,
            network_enabled=request.network_enabled
        )
        
        # 解碼輸入文件
        input_files = {}
        if request.files:
            for filename, b64_content in request.files.items():
                try:
                    input_files[filename] = base64.b64decode(b64_content)
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid base64 for file {filename}: {e}"
                    )
        
        # 執行
        result = await sandbox.execute(
            code=request.code,
            language=language,
            config=config,
            input_files=input_files,
            context=request.context or {}
        )
        
        logger.info(
            f"🖥️ Code executed: user={current_user.username}, "
            f"lang={request.language}, success={result.success}, "
            f"time={result.execution_time:.2f}s"
        )
        
        return ExecuteResponse(**result.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-with-files")
async def execute_with_files(
    code: str,
    language: str = "python",
    timeout: int = 60,
    files: List[UploadFile] = File(default=[]),
    current_user: TokenData = Depends(get_current_user),
    sandbox: CodeSandbox = Depends(get_sandbox)
):
    """
    執行代碼（帶文件上傳）
    
    通過 multipart/form-data 上傳文件
    """
    try:
        lang = Language(language.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
    
    config = ExecutionConfig(timeout=timeout)
    
    # 讀取上傳的文件
    input_files = {}
    for f in files:
        content = await f.read()
        input_files[f.filename] = content
    
    result = await sandbox.execute(
        code=code,
        language=lang,
        config=config,
        input_files=input_files
    )
    
    return ExecuteResponse(**result.to_dict())


@router.get("/status")
async def get_sandbox_status(
    sandbox: CodeSandbox = Depends(get_sandbox)
):
    """取得沙箱狀態"""
    return {
        "docker_enabled": sandbox._use_docker,
        "supported_languages": [lang.value for lang in Language],
        "default_timeout": 60,
        "max_timeout": 300,
        "python_packages": sandbox.PYTHON_PACKAGES if hasattr(sandbox, 'PYTHON_PACKAGES') else []
    }


@router.post("/test")
async def test_sandbox(
    current_user: TokenData = Depends(get_current_user),
    sandbox: CodeSandbox = Depends(get_sandbox)
):
    """測試沙箱功能"""
    test_code = '''
import sys
import platform

print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")

# 測試常用庫
try:
    import pandas as pd
    print(f"pandas: {pd.__version__}")
except ImportError:
    print("pandas: not available")

try:
    import numpy as np
    print(f"numpy: {np.__version__}")
except ImportError:
    print("numpy: not available")

try:
    import matplotlib
    print(f"matplotlib: {matplotlib.__version__}")
except ImportError:
    print("matplotlib: not available")

# 測試圖表生成
try:
    import matplotlib.pyplot as plt
    import numpy as np
    
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    
    plt.figure(figsize=(8, 4))
    plt.plot(x, y)
    plt.title('Test Plot')
    plt.xlabel('X')
    plt.ylabel('sin(X)')
    plt.grid(True)
    plt.savefig('test_plot.png', dpi=100)
    print("Plot saved: test_plot.png")
except Exception as e:
    print(f"Plot error: {e}")

print("\\n✅ Sandbox test completed!")
'''
    
    result = await sandbox.execute(
        code=test_code,
        language=Language.PYTHON,
        config=ExecutionConfig(timeout=30)
    )
    
    return {
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "execution_time": result.execution_time,
        "images_count": len(result.images),
        "docker_enabled": sandbox._use_docker
    }
