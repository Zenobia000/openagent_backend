"""
代碼沙箱執行服務

為 Coder Agent 提供安全的代碼執行環境：
- Docker 容器隔離
- 資源限制（CPU、記憶體、時間）
- 支援 Python、JavaScript、Shell
- 圖表生成（matplotlib、plotly）
- 文件讀寫（限定目錄）
"""

import os
import sys
import json
import asyncio
import logging
import tempfile
import subprocess
import base64
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """支援的程式語言"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    SHELL = "shell"


@dataclass
class ExecutionConfig:
    """執行配置"""
    timeout: int = 60                    # 超時秒數
    memory_limit: str = "512m"           # 記憶體限制
    cpu_limit: float = 1.0               # CPU 限制
    network_enabled: bool = True         # 是否允許網路
    max_output_size: int = 1024 * 1024   # 最大輸出 1MB
    working_dir: Optional[str] = None    # 工作目錄


@dataclass
class ExecutionResult:
    """執行結果"""
    success: bool
    stdout: str
    stderr: str
    return_value: Any = None
    execution_time: float = 0.0
    files: List[Dict[str, str]] = field(default_factory=list)  # 生成的文件
    images: List[str] = field(default_factory=list)            # base64 圖片
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_value": self.return_value,
            "execution_time": self.execution_time,
            "files": self.files,
            "images": self.images,
            "error": self.error
        }


class CodeSandbox:
    """
    代碼沙箱執行器
    
    支援：
    1. Docker 模式（生產環境，完全隔離）
    2. 本地模式（開發環境，subprocess 執行）
    """
    
    # Docker 映像
    DOCKER_IMAGES = {
        Language.PYTHON: "python:3.11-slim",
        Language.JAVASCRIPT: "node:18-slim",
        Language.SHELL: "alpine:latest"
    }
    
    # 預安裝的 Python 包
    PYTHON_PACKAGES = [
        "pandas", "numpy", "matplotlib", "seaborn",
        "requests", "httpx", "aiohttp",
        "openpyxl", "xlrd", "python-docx",
        "Pillow", "plotly", "scikit-learn"
    ]
    
    def __init__(self, use_docker: bool = None):
        """
        初始化沙箱
        
        Args:
            use_docker: 是否使用 Docker，None 表示自動檢測
        """
        if use_docker is None:
            self._use_docker = self._check_docker()
        else:
            self._use_docker = use_docker
            
        # 創建工作目錄
        self._base_dir = Path(tempfile.gettempdir()) / "opencode_sandbox"
        self._base_dir.mkdir(exist_ok=True)
        
        if self._use_docker:
            logger.info("🐳 CodeSandbox: Docker mode enabled")
            self._ensure_docker_image()
        else:
            logger.warning("⚠️ CodeSandbox: Local mode (less secure)")
    
    def _check_docker(self) -> bool:
        """檢查 Docker 是否可用"""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _ensure_docker_image(self) -> None:
        """確保 Docker 映像存在"""
        try:
            # 構建自訂 Python 映像（包含常用包）
            dockerfile = '''
FROM python:3.11-slim

RUN pip install --no-cache-dir \\
    pandas numpy matplotlib seaborn \\
    requests httpx openpyxl xlrd \\
    Pillow plotly scikit-learn

WORKDIR /app
'''
            # 檢查是否已有映像
            result = subprocess.run(
                ["docker", "images", "-q", "opencode-sandbox-python"],
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                logger.info("📦 Building Docker image for sandbox...")
                # 創建臨時 Dockerfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    dockerfile_path = Path(tmpdir) / "Dockerfile"
                    dockerfile_path.write_text(dockerfile)
                    
                    subprocess.run(
                        ["docker", "build", "-t", "opencode-sandbox-python", tmpdir],
                        capture_output=True,
                        timeout=300
                    )
                logger.info("✅ Docker image built")
                
        except Exception as e:
            logger.warning(f"Failed to build Docker image: {e}")
    
    async def execute(
        self,
        code: str,
        language: Language = Language.PYTHON,
        config: ExecutionConfig = None,
        input_files: Dict[str, bytes] = None,
        context: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        執行代碼
        
        Args:
            code: 要執行的代碼
            language: 程式語言
            config: 執行配置
            input_files: 輸入文件 {filename: content}
            context: 上下文變數
            
        Returns:
            ExecutionResult
        """
        config = config or ExecutionConfig()
        input_files = input_files or {}
        context = context or {}
        
        # 創建執行目錄
        exec_id = str(uuid.uuid4())[:8]
        exec_dir = self._base_dir / exec_id
        exec_dir.mkdir(exist_ok=True)
        
        try:
            # 寫入輸入文件
            for filename, content in input_files.items():
                file_path = exec_dir / filename
                if isinstance(content, bytes):
                    file_path.write_bytes(content)
                else:
                    file_path.write_text(content)
            
            # 執行
            if self._use_docker:
                result = await self._execute_docker(
                    code, language, config, exec_dir, context
                )
            else:
                result = await self._execute_local(
                    code, language, config, exec_dir, context
                )
            
            # 收集生成的文件和圖片
            result.files, result.images = self._collect_outputs(exec_dir)
            
            return result
            
        finally:
            # 清理（延遲刪除以便調試）
            asyncio.get_event_loop().call_later(
                300,  # 5分鐘後清理
                lambda: shutil.rmtree(exec_dir, ignore_errors=True)
            )
    
    async def _execute_docker(
        self,
        code: str,
        language: Language,
        config: ExecutionConfig,
        exec_dir: Path,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """Docker 模式執行"""
        import time
        start_time = time.time()
        
        try:
            # 準備代碼文件
            if language == Language.PYTHON:
                code_file = exec_dir / "main.py"
                wrapper_code = self._wrap_python_code(code, context)
                code_file.write_text(wrapper_code, encoding='utf-8')
                cmd = ["python", "/app/main.py"]
                image = "opencode-sandbox-python"
            elif language == Language.JAVASCRIPT:
                code_file = exec_dir / "main.js"
                code_file.write_text(code, encoding='utf-8')
                cmd = ["node", "/app/main.js"]
                image = self.DOCKER_IMAGES[language]
            else:
                code_file = exec_dir / "main.sh"
                code_file.write_text(code, encoding='utf-8')
                cmd = ["sh", "/app/main.sh"]
                image = self.DOCKER_IMAGES[language]
            
            # Docker 命令
            docker_cmd = [
                "docker", "run", "--rm",
                f"--memory={config.memory_limit}",
                f"--cpus={config.cpu_limit}",
                f"--name=sandbox-{exec_dir.name}",
                "-v", f"{exec_dir}:/app",
                "-w", "/app",
            ]
            
            # 網路配置
            if not config.network_enabled:
                docker_cmd.append("--network=none")
            
            docker_cmd.extend([image] + cmd)
            
            # 執行
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=config.timeout
                )
                
                execution_time = time.time() - start_time
                
                stdout_str = stdout.decode('utf-8', errors='replace')[:config.max_output_size]
                stderr_str = stderr.decode('utf-8', errors='replace')[:config.max_output_size]
                
                # 嘗試解析返回值
                return_value = None
                if language == Language.PYTHON:
                    result_file = exec_dir / "_result.json"
                    if result_file.exists():
                        try:
                            return_value = json.loads(result_file.read_text())
                        except:
                            pass
                
                return ExecutionResult(
                    success=process.returncode == 0,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    return_value=return_value,
                    execution_time=execution_time,
                    error=None if process.returncode == 0 else f"Exit code: {process.returncode}"
                )
                
            except asyncio.TimeoutError:
                # 強制停止容器
                subprocess.run(
                    ["docker", "kill", f"sandbox-{exec_dir.name}"],
                    capture_output=True
                )
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    execution_time=config.timeout,
                    error=f"Execution timeout ({config.timeout}s)"
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _execute_local(
        self,
        code: str,
        language: Language,
        config: ExecutionConfig,
        exec_dir: Path,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """本地模式執行（subprocess）"""
        import time
        start_time = time.time()
        
        try:
            if language == Language.PYTHON:
                code_file = exec_dir / "main.py"
                wrapper_code = self._wrap_python_code(code, context)
                code_file.write_text(wrapper_code, encoding='utf-8')
                cmd = [sys.executable, str(code_file)]
            elif language == Language.JAVASCRIPT:
                code_file = exec_dir / "main.js"
                code_file.write_text(code, encoding='utf-8')
                cmd = ["node", str(code_file)]
            else:
                code_file = exec_dir / "main.sh"
                code_file.write_text(code, encoding='utf-8')
                cmd = ["sh", str(code_file)]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(exec_dir)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=config.timeout
                )
                
                execution_time = time.time() - start_time
                
                stdout_str = stdout.decode('utf-8', errors='replace')[:config.max_output_size]
                stderr_str = stderr.decode('utf-8', errors='replace')[:config.max_output_size]
                
                # 嘗試解析返回值
                return_value = None
                result_file = exec_dir / "_result.json"
                if result_file.exists():
                    try:
                        return_value = json.loads(result_file.read_text())
                    except:
                        pass
                
                return ExecutionResult(
                    success=process.returncode == 0,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    return_value=return_value,
                    execution_time=execution_time,
                    error=None if process.returncode == 0 else f"Exit code: {process.returncode}"
                )
                
            except asyncio.TimeoutError:
                process.kill()
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    execution_time=config.timeout,
                    error=f"Execution timeout ({config.timeout}s)"
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    def _wrap_python_code(self, code: str, context: Dict[str, Any]) -> str:
        """包裝 Python 代碼，添加輔助功能"""
        wrapper = '''
import sys
import json
import os

# 設置 matplotlib 為非互動模式
import matplotlib
matplotlib.use('Agg')

# 上下文變數
_context = {context}

# 保存圖表的輔助函數
def save_figure(fig=None, name=None):
    """保存 matplotlib 圖表"""
    import matplotlib.pyplot as plt
    if fig is None:
        fig = plt.gcf()
    if name is None:
        name = f"figure_{{len(os.listdir('.'))}}".replace('.', '_')
    filename = f"{{name}}.png"
    fig.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename

# 自動保存所有圖表
import atexit
def _save_all_figures():
    import matplotlib.pyplot as plt
    for i, fig_num in enumerate(plt.get_fignums()):
        fig = plt.figure(fig_num)
        fig.savefig(f"figure_{{i}}.png", dpi=150, bbox_inches='tight')
atexit.register(_save_all_figures)

# 用戶代碼
_result = None
try:
{indented_code}
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 保存結果
if _result is not None:
    with open("_result.json", "w") as f:
        json.dump(_result, f)
'''
        # 縮排用戶代碼
        indented_code = '\n'.join('    ' + line for line in code.split('\n'))
        
        return wrapper.format(
            context=json.dumps(context),
            indented_code=indented_code
        )
    
    def _collect_outputs(self, exec_dir: Path) -> tuple:
        """收集執行產生的文件和圖片"""
        files = []
        images = []
        
        for item in exec_dir.iterdir():
            if item.name.startswith('_') or item.name.startswith('main.'):
                continue
            
            if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                # 圖片轉 base64
                try:
                    content = item.read_bytes()
                    b64 = base64.b64encode(content).decode('utf-8')
                    mime = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.svg': 'image/svg+xml'
                    }.get(item.suffix.lower(), 'image/png')
                    images.append(f"data:{mime};base64,{b64}")
                except Exception as e:
                    logger.warning(f"Failed to read image {item}: {e}")
            else:
                # 其他文件
                try:
                    if item.stat().st_size < 1024 * 1024:  # < 1MB
                        content = item.read_text(errors='replace')
                        files.append({
                            "name": item.name,
                            "content": content,
                            "size": item.stat().st_size
                        })
                except Exception as e:
                    logger.warning(f"Failed to read file {item}: {e}")
        
        return files, images


# 全域實例
_sandbox: Optional[CodeSandbox] = None


def get_sandbox() -> CodeSandbox:
    """取得沙箱實例"""
    global _sandbox
    if _sandbox is None:
        _sandbox = CodeSandbox()
    return _sandbox
