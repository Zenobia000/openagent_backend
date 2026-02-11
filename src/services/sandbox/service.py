"""
Sandbox Service - 安全沙箱執行服務（Docker 隔離版）

功能:
- execute_python: 安全執行 Python 程式碼
- execute_bash: 執行 Bash 命令
- 支援 pandas, numpy, matplotlib 等常用套件
- 支援圖表輸出（base64）
- Docker 容器隔離，資源限制
- 代碼安全過濾（防止危險操作）
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
import json
import os
import logging
import tempfile
import time
import uuid
import re

from core.protocols import MCPServiceProtocol

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 代碼安全過濾器
# ═══════════════════════════════════════════════════════════════

class CodeSecurityFilter:
    """
    代碼安全過濾器
    
    檢測並阻止危險的 Python 操作，如：
    - 文件系統操作 (刪除、修改系統文件)
    - 系統命令執行 (os.system, subprocess)
    - 網路操作 (socket, requests)
    - 動態代碼執行 (eval, exec, compile)
    """
    
    # 危險模式 (黑名單)
    DANGEROUS_PATTERNS = [
        # 文件系統危險操作
        (r'\bos\s*\.\s*(remove|unlink|rmdir|removedirs|rename|renames|replace)\s*\(', 
         "禁止刪除或重命名文件: os.remove/unlink/rmdir"),
        (r'\bshutil\s*\.\s*(rmtree|move|copy|copy2|copytree)\s*\(', 
         "禁止 shutil 文件操作: rmtree/move/copy"),
        (r'\bpathlib\s*\.\s*Path\s*\([^)]*\)\s*\.\s*(unlink|rmdir|rename)\s*\(', 
         "禁止 pathlib 刪除操作"),
        
        # 系統命令執行
        (r'\bos\s*\.\s*(system|popen|spawn|exec[lvpe]*)\s*\(', 
         "禁止執行系統命令: os.system/popen/exec"),
        (r'\bsubprocess\s*\.', 
         "禁止使用 subprocess 模組"),
        (r'\bcommands\s*\.', 
         "禁止使用 commands 模組"),
        
        # 動態代碼執行
        (r'(?<!["\'])\beval\s*\(', 
         "禁止使用 eval()"),
        (r'(?<!["\'])\bexec\s*\((?!\s*code\s*,)', 
         "禁止使用 exec() 執行動態代碼"),
        (r'(?<!["\'])\bcompile\s*\(', 
         "禁止使用 compile()"),
        (r'\b__import__\s*\(', 
         "禁止使用 __import__()"),
        
        # 網路操作
        (r'\bsocket\s*\.', 
         "禁止使用 socket 模組"),
        (r'\burllib\s*\.', 
         "禁止使用 urllib 模組"),
        (r'\brequests\s*\.', 
         "禁止使用 requests 模組"),
        (r'\bhttpx\s*\.', 
         "禁止使用 httpx 模組"),
        (r'\baiohttp\s*\.', 
         "禁止使用 aiohttp 模組"),
        
        # 危險的內建操作
        (r'\bopen\s*\([^)]*["\'][wa]\+?["\']', 
         "禁止以寫入模式開啟文件"),
        (r'\bglobals\s*\(\s*\)\s*\[', 
         "禁止修改 globals"),
        (r'\bsetattr\s*\(\s*__builtins__', 
         "禁止修改 builtins"),
        (r'\bdelattr\s*\(', 
         "禁止使用 delattr"),
        
        # 危險模組導入
        (r'\bimport\s+(ctypes|cffi|multiprocessing|threading)\b', 
         "禁止導入危險模組: ctypes/cffi/multiprocessing/threading"),
        (r'\bfrom\s+(ctypes|cffi|multiprocessing|threading)\s+import', 
         "禁止從危險模組導入"),
        
        # 環境變數和系統資訊
        (r'\bos\s*\.\s*environ\s*\[', 
         "禁止修改環境變數"),
        (r'\bos\s*\.\s*putenv\s*\(', 
         "禁止設置環境變數"),
    ]
    
    # 允許的模組 (白名單)
    ALLOWED_MODULES = {
        # 數學和科學計算
        'math', 'cmath', 'decimal', 'fractions', 'random', 'statistics',
        'numpy', 'np', 'scipy', 'sympy',
        
        # 數據處理
        'pandas', 'pd', 'csv', 'json',
        
        # 視覺化
        'matplotlib', 'matplotlib.pyplot', 'plt', 'seaborn', 'sns', 'plotly',
        
        # 機器學習
        'sklearn', 'scikit-learn',
        
        # 字串和正則
        're', 'string', 'textwrap',
        
        # 日期時間
        'datetime', 'time', 'calendar',
        
        # 集合和迭代
        'collections', 'itertools', 'functools', 'operator',
        
        # 類型
        'typing', 'dataclasses', 'enum',
        
        # 其他安全模組
        'copy', 'pprint', 'io', 'base64', 'hashlib', 'hmac',
    }
    
    @classmethod
    def check_code_safety(cls, code: str) -> Tuple[bool, str, List[str]]:
        """
        檢查代碼安全性
        
        Args:
            code: 要檢查的 Python 代碼
            
        Returns:
            (is_safe, error_message, warnings)
        """
        warnings = []
        
        # 檢查危險模式
        for pattern, message in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"🚫 安全檢查失敗: {message}", warnings
        
        # 檢查可疑但不一定危險的模式
        suspicious_patterns = [
            (r'\bpickle\s*\.', "使用 pickle 可能有安全風險"),
            (r'\bshelve\s*\.', "使用 shelve 可能有安全風險"),
            (r'\b__\w+__', "使用雙下劃線屬性需謹慎"),
        ]
        
        for pattern, message in suspicious_patterns:
            if re.search(pattern, code):
                warnings.append(f"⚠️ 警告: {message}")
        
        return True, "", warnings
    
    @classmethod
    def sanitize_code(cls, code: str) -> str:
        """
        清理代碼（移除危險部分）
        
        目前只做基本清理，主要依賴 check_code_safety 來阻擋
        """
        # 移除可能的 shell 注入
        code = re.sub(r'`[^`]*`', '', code)
        
        # 移除可能的註釋中的危險指令
        # (有些攻擊會在註釋中隱藏代碼)
        
        return code


class SandboxService(MCPServiceProtocol):
    """
    Docker 隔離的程式碼執行沙箱
    
    安全特性:
    - 網路隔離 (network_mode="none")
    - 記憶體限制 (預設 512MB)
    - CPU 限制 (50% 單核)
    - 執行時間限制 (預設 30 秒)
    - 非 root 用戶執行
    """
    
    # Docker image 名稱
    SANDBOX_IMAGE = "opencode-sandbox:latest"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._service_id = "sandbox"
        self._capabilities = [
            "execute_python",
            "execute_bash",
            "file_read",
            "file_write"
        ]
        
        # 配置
        self.docker_enabled = self.config.get("docker_enabled", True)
        self.timeout = self.config.get("timeout", 30)
        self.memory_limit = self.config.get("memory_limit", "512m")
        self.cpu_quota = self.config.get("cpu_quota", 50000)  # 50% CPU
        self.working_dir = self.config.get("working_dir", "/tmp/sandbox")
        
        # Docker 客戶端
        self.docker_client = None
        self._image_ready = False
        self._initialized = False
    
    @property
    def service_id(self) -> str:
        return self._service_id
    
    @property
    def capabilities(self) -> List[str]:
        return self._capabilities
    
    async def initialize(self) -> None:
        """初始化服務"""
        import platform
        
        # 建立工作目錄
        os.makedirs(self.working_dir, exist_ok=True)
        
        # Windows 上 Docker 有問題，默認禁用
        if platform.system() == "Windows":
            logger.info("⚠️ Windows detected, using local execution (Docker has issues on Windows)")
            self.docker_enabled = False
            self._initialized = True
            return
        
        # 初始化 Docker
        if self.docker_enabled:
            try:
                import docker
                self.docker_client = docker.from_env()
                
                # 檢查 image 是否存在
                try:
                    self.docker_client.images.get(self.SANDBOX_IMAGE)
                    self._image_ready = True
                    logger.info(f"✅ Sandbox image '{self.SANDBOX_IMAGE}' ready")
                except docker.errors.ImageNotFound:
                    logger.warning(f"⚠️ Sandbox image '{self.SANDBOX_IMAGE}' not found")
                    logger.warning("   Run: cd services/sandbox/docker && ./build.sh")
                    self._image_ready = False
                
                logger.info("✅ Docker client initialized")
                
            except ImportError:
                logger.warning("⚠️ docker package not installed: pip install docker")
                self.docker_enabled = False
            except Exception as e:
                logger.warning(f"⚠️ Docker not available: {e}")
                self.docker_enabled = False
        
        self._initialized = True
        logger.info(f"✅ {self.service_id} initialized (Docker: {self.docker_enabled})")
    
    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """執行方法"""
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"🔧 [Sandbox] 執行方法: {method}")
        logger.debug(f"🔧 [Sandbox] 參數: {params}")
        
        if method == "execute_python":
            return await self._execute_python(
                code=params.get("code", ""),
                timeout=params.get("timeout", self.timeout)
            )
        
        elif method == "execute_bash":
            return await self._execute_bash(
                command=params.get("command", ""),
                timeout=params.get("timeout", self.timeout)
            )
        
        elif method == "file_read":
            return await self._file_read(params.get("path", ""))
        
        elif method == "file_write":
            return await self._file_write(
                path=params.get("path", ""),
                content=params.get("content", "")
            )
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    async def health_check(self) -> bool:
        """健康檢查"""
        if not self._initialized:
            return False
        
        if self.docker_enabled:
            try:
                self.docker_client.ping()
                return True
            except:
                return False
        
        return True
    
    async def shutdown(self) -> None:
        """關閉服務"""
        logger.info(f"{self.service_id} shutdown")
    
    # ========== 核心執行方法 ==========
    
    async def _execute_python(
        self,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        執行 Python 程式碼
        
        Args:
            code: Python 程式碼
            timeout: 超時時間（秒）
            
        Returns:
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "error": str | None,
                "error_type": str | None,
                "figures": [base64_string, ...],
                "return_value": any,
                "execution_time": float
            }
        """
        if not code or not code.strip():
            return {
                "success": False,
                "error": "No code provided",
                "error_type": "ValueError",
                "stdout": "",
                "stderr": "",
                "figures": [],
                "return_value": None,
                "execution_time": 0
            }
        
        # ═══ 安全檢查 ═══
        is_safe, error_msg, warnings = CodeSecurityFilter.check_code_safety(code)
        
        if not is_safe:
            logger.warning(f"🚫 [Sandbox] 代碼安全檢查失敗: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "SecurityError",
                "stdout": "",
                "stderr": error_msg,
                "figures": [],
                "return_value": None,
                "execution_time": 0,
                "security_blocked": True
            }
        
        # 記錄警告
        for warning in warnings:
            logger.warning(f"⚠️ [Sandbox] {warning}")
        
        start_time = time.time()
        
        # 優先使用 Docker
        if self.docker_enabled and self._image_ready:
            result = await self._execute_python_docker(code, timeout)
        else:
            # Fallback: 本地執行（開發用，不安全）
            logger.warning("⚠️ Docker not available, using local execution (UNSAFE)")
            result = await self._execute_python_local(code, timeout)
        
        result["execution_time"] = round(time.time() - start_time, 3)
        
        logger.info(f"🔧 [Sandbox] 執行完成: success={result['success']}, "
                   f"time={result['execution_time']}s, "
                   f"figures={len(result.get('figures', []))}")
        
        return result
    
    async def _execute_python_docker(
        self,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """在 Docker 容器中執行 Python 代碼"""
        import docker
        
        # 準備輸入
        input_data = json.dumps({"code": code}, ensure_ascii=False)
        
        container = None
        try:
            # 創建容器
            container = self.docker_client.containers.run(
                self.SANDBOX_IMAGE,
                detach=True,
                stdin_open=True,
                mem_limit=self.memory_limit,
                cpu_quota=self.cpu_quota,
                network_mode="none",  # 禁止網路
                read_only=True,  # 唯讀文件系統
                remove=False,
                tmpfs={'/tmp': 'size=100M'},  # 可寫的臨時目錄
                user="sandbox",  # 非 root 用戶
            )
            
            # 發送輸入
            socket = container.attach_socket(params={'stdin': 1, 'stream': 1})
            socket._sock.sendall(input_data.encode('utf-8'))
            socket._sock.shutdown(1)  # 關閉寫入端
            socket.close()
            
            # 等待完成
            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get("StatusCode", -1)
            except Exception as e:
                # 超時
                container.kill()
                return {
                    "success": False,
                    "error": f"Execution timed out after {timeout}s",
                    "error_type": "TimeoutError",
                    "stdout": "",
                    "stderr": "",
                    "figures": [],
                    "return_value": None
                }
            
            # 獲取輸出
            logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
            
            # 解析 JSON 結果
            try:
                result = json.loads(logs)
                return result
            except json.JSONDecodeError:
                # 如果不是 JSON，直接返回
                return {
                    "success": exit_code == 0,
                    "stdout": logs,
                    "stderr": "",
                    "error": None if exit_code == 0 else "Execution failed",
                    "figures": [],
                    "return_value": None
                }
                
        except docker.errors.ImageNotFound:
            return {
                "success": False,
                "error": f"Sandbox image '{self.SANDBOX_IMAGE}' not found. Run build.sh first.",
                "error_type": "ImageNotFound",
                "stdout": "",
                "stderr": "",
                "figures": [],
                "return_value": None
            }
            
        except Exception as e:
            logger.error(f"Docker execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "stdout": "",
                "stderr": "",
                "figures": [],
                "return_value": None
            }
            
        finally:
            # 清理容器
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
    
    async def _execute_python_local(
        self,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """本地執行 Python（開發用，不安全）"""
        import io
        import sys
        import base64
        import traceback
        
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        figures = []
        return_value = None
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # 設置 matplotlib 為非交互式後端（必須在 import 之前）
            import matplotlib
            matplotlib.use('Agg')  # 非交互式後端，不會彈出窗口
            import matplotlib.pyplot as plt
            
            # 清除之前的圖表
            plt.close('all')
            
            # 創建一個假的 show() 函數，攔截彈窗
            original_show = plt.show
            def fake_show(*args, **kwargs):
                pass  # 不做任何事，防止彈窗
            plt.show = fake_show
            
            sys.stdout = stdout_buffer
            sys.stderr = stderr_buffer
            
            # 準備執行環境
            local_vars = {}
            
            # 預載入常用模組
            exec_globals = {
                '__builtins__': __builtins__,
                'plt': plt,
                'matplotlib': matplotlib,
            }
            
            # 預載入 numpy（如果可用）
            try:
                import numpy as np
                exec_globals['np'] = np
            except ImportError:
                pass
            
            # 執行代碼
            exec(code, exec_globals, local_vars)
            
            # 捕獲所有 matplotlib 圖表
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                figures.append(img_base64)
                logger.info(f"📊 [Sandbox] 捕獲圖表 {fig_num}，大小: {len(img_base64)} 字符")
            
            # 關閉所有圖表
            plt.close('all')
            
            # 恢復原始 show
            plt.show = original_show
            
            # 獲取返回值
            return_value = local_vars.get('result', local_vars.get('output', None))
            
            logger.info(f"📊 [Sandbox] 執行成功，捕獲 {len(figures)} 張圖表")
            
            return {
                "success": True,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": None,
                "error_type": None,
                "figures": figures,
                "return_value": return_value
            }
            
        except Exception as e:
            logger.error(f"❌ [Sandbox] 執行失敗: {e}")
            return {
                "success": False,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "figures": figures,
                "return_value": None
            }
            
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    async def _execute_bash(
        self,
        command: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """執行 Bash 命令"""
        if self.docker_enabled:
            return await self._execute_bash_docker(command, timeout)
        
        # 本地執行
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode,
                "error": None if proc.returncode == 0 else "Command failed"
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1,
                "error": "TimeoutError"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "error": str(e)
            }
    
    async def _execute_bash_docker(
        self,
        command: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """在 Docker 中執行 Bash"""
        try:
            container = self.docker_client.containers.run(
                "alpine:latest",
                ["/bin/sh", "-c", command],
                detach=True,
                mem_limit=self.memory_limit,
                network_mode="none",
                remove=False
            )
            
            try:
                result = container.wait(timeout=timeout)
                logs = container.logs().decode("utf-8", errors="replace")
                exit_code = result.get("StatusCode", -1)
                
                return {
                    "success": exit_code == 0,
                    "stdout": logs,
                    "stderr": "",
                    "exit_code": exit_code,
                    "error": None if exit_code == 0 else "Command failed"
                }
            finally:
                container.remove(force=True)
                
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "error": str(e)
            }
    
    async def _file_read(self, path: str) -> Dict[str, Any]:
        """讀取檔案"""
        try:
            full_path = os.path.join(self.working_dir, path)
            if not os.path.abspath(full_path).startswith(os.path.abspath(self.working_dir)):
                return {"success": False, "error": "Access denied"}
            
            with open(full_path, 'r') as f:
                content = f.read()
            
            return {"success": True, "content": content, "path": path}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _file_write(self, path: str, content: str) -> Dict[str, Any]:
        """寫入檔案"""
        try:
            full_path = os.path.join(self.working_dir, path)
            if not os.path.abspath(full_path).startswith(os.path.abspath(self.working_dir)):
                return {"success": False, "error": "Access denied"}
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            return {"success": True, "path": path, "bytes_written": len(content)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== 工具定義 ==========
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """返回工具定義，供 Planner 使用"""
        return [
            {
                "name": "sandbox_execute_python",
                "description": """執行 Python 程式碼。支援 numpy, pandas, matplotlib, scipy, sklearn 等套件。
                
適用場景：
- 數學計算
- 數據分析和統計
- 生成圖表和視覺化
- 處理 CSV/Excel 數據
- 機器學習模型訓練

特殊變數：
- 將結果存入 `result` 變數會自動返回
- matplotlib 圖表會自動捕獲為 base64""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "要執行的 Python 程式碼"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "超時時間（秒），預設 30",
                            "default": 30
                        }
                    },
                    "required": ["code"]
                }
            }
        ]
