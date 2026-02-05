"""
插件沙箱執行器

提供安全的插件代碼執行環境：
- Docker 容器隔離
- 資源限制
- 網路限制
- 超時控制
"""

import os
import sys
import json
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """沙箱配置"""
    timeout: int = 60
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network_enabled: bool = False
    allowed_imports: list = None
    
    def __post_init__(self):
        if self.allowed_imports is None:
            self.allowed_imports = [
                "json", "re", "math", "datetime", "collections",
                "itertools", "functools", "typing", "dataclasses",
                "pandas", "numpy", "requests", "httpx", "aiohttp",
                "openai", "anthropic", "cohere"
            ]


class PluginSandbox:
    """
    插件沙箱執行器
    
    提供兩種模式：
    1. Docker 模式（推薦，完全隔離）
    2. 本地模式（開發用，有安全風險）
    """
    
    def __init__(self, config: SandboxConfig = None):
        self.config = config or SandboxConfig()
        self._docker_available = self._check_docker()
        
        if self._docker_available:
            logger.info("🐳 Docker sandbox enabled")
        else:
            logger.warning("⚠️ Docker not available, using local execution (UNSAFE)")
    
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
    
    async def execute_plugin_code(
        self,
        plugin_id: str,
        code: str,
        function_name: str,
        args: Dict[str, Any],
        plugin_dir: Path = None
    ) -> Dict[str, Any]:
        """
        在沙箱中執行插件代碼
        
        Args:
            plugin_id: 插件 ID
            code: 要執行的代碼
            function_name: 要調用的函數名
            args: 函數參數
            plugin_dir: 插件目錄（用於掛載）
            
        Returns:
            {
                "success": bool,
                "result": Any,
                "stdout": str,
                "stderr": str,
                "execution_time": float,
                "error": Optional[str]
            }
        """
        if self._docker_available:
            return await self._execute_in_docker(
                plugin_id, code, function_name, args, plugin_dir
            )
        else:
            return await self._execute_local(
                plugin_id, code, function_name, args, plugin_dir
            )
    
    async def _execute_in_docker(
        self,
        plugin_id: str,
        code: str,
        function_name: str,
        args: Dict[str, Any],
        plugin_dir: Path = None
    ) -> Dict[str, Any]:
        """在 Docker 容器中執行"""
        import time
        start_time = time.time()
        
        try:
            # 創建執行腳本
            wrapper_code = f'''
import json
import sys

# 插件代碼
{code}

# 執行函數
if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    try:
        result = {function_name}(**args)
        # 處理異步函數
        import asyncio
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        print(json.dumps({{"success": True, "result": result}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
'''
            
            # 寫入臨時文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(wrapper_code)
                script_path = f.name
            
            # Docker 命令
            docker_cmd = [
                "docker", "run", "--rm",
                f"--memory={self.config.memory_limit}",
                f"--cpus={self.config.cpu_limit}",
                f"--name=plugin-{plugin_id}-{int(time.time())}",
            ]
            
            # 網路配置
            if not self.config.network_enabled:
                docker_cmd.append("--network=none")
            
            # 掛載腳本
            docker_cmd.extend(["-v", f"{script_path}:/app/script.py:ro"])
            
            # 掛載插件目錄
            if plugin_dir and plugin_dir.exists():
                docker_cmd.extend(["-v", f"{plugin_dir}:/app/plugin:ro"])
            
            # 執行
            docker_cmd.extend([
                "python:3.11-slim",
                "python", "/app/script.py",
                json.dumps(args)
            ])
            
            # 運行
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "result": None,
                    "stdout": "",
                    "stderr": "",
                    "execution_time": self.config.timeout,
                    "error": f"Execution timeout ({self.config.timeout}s)"
                }
            
            # 清理
            Path(script_path).unlink()
            
            # 解析結果
            execution_time = time.time() - start_time
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            try:
                result = json.loads(stdout_str.strip().split('\n')[-1])
                return {
                    "success": result.get("success", False),
                    "result": result.get("result"),
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "execution_time": execution_time,
                    "error": result.get("error")
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "result": None,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "execution_time": execution_time,
                    "error": "Failed to parse output"
                }
                
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "stdout": "",
                "stderr": "",
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def _execute_local(
        self,
        plugin_id: str,
        code: str,
        function_name: str,
        args: Dict[str, Any],
        plugin_dir: Path = None
    ) -> Dict[str, Any]:
        """本地執行（不安全，僅用於開發）"""
        import time
        start_time = time.time()
        
        stdout_capture = []
        stderr_capture = []
        
        try:
            # 創建隔離的命名空間
            namespace = {
                '__builtins__': __builtins__,
                'print': lambda *args: stdout_capture.append(' '.join(map(str, args))),
            }
            
            # 添加常用模組
            safe_modules = [
                'json', 're', 'math', 'datetime', 'collections',
                'itertools', 'functools', 'typing', 'dataclasses'
            ]
            
            for mod_name in safe_modules:
                try:
                    namespace[mod_name] = __import__(mod_name)
                except ImportError:
                    pass
            
            # 執行代碼
            exec(code, namespace)
            
            # 獲取函數
            func = namespace.get(function_name)
            if not func or not callable(func):
                raise ValueError(f"Function {function_name} not found or not callable")
            
            # 執行函數
            result = func(**args)
            
            # 處理異步
            if asyncio.iscoroutine(result):
                result = await result
            
            return {
                "success": True,
                "result": result,
                "stdout": '\n'.join(stdout_capture),
                "stderr": '\n'.join(stderr_capture),
                "execution_time": time.time() - start_time,
                "error": None
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "result": None,
                "stdout": '\n'.join(stdout_capture),
                "stderr": traceback.format_exc(),
                "execution_time": time.time() - start_time,
                "error": str(e)
            }


# 全域實例
_sandbox: Optional[PluginSandbox] = None


def get_sandbox() -> PluginSandbox:
    """取得沙箱實例"""
    global _sandbox
    if _sandbox is None:
        _sandbox = PluginSandbox()
    return _sandbox
