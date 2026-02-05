"""
Repo Ops Service - Git/CI 操作服務
"""

from typing import List, Dict, Any, Optional
import asyncio
import os
import logging

from opencode.core.protocols import MCPServiceProtocol

logger = logging.getLogger(__name__)


class RepoOpsService(MCPServiceProtocol):
    """
    倉庫操作服務
    
    功能:
    - git_clone: Clone 倉庫
    - git_status: 查看狀態
    - git_commit: 提交變更
    - git_push: 推送
    - git_pull: 拉取
    - git_branch: 分支操作
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._service_id = "repo_ops"
        self._capabilities = [
            "git_clone",
            "git_status",
            "git_commit",
            "git_push",
            "git_pull",
            "git_branch",
            "git_log",
            "git_diff"
        ]
        
        self.working_dir = self.config.get("working_dir", "/tmp/repos")
        self._initialized = False
    
    @property
    def service_id(self) -> str:
        return self._service_id
    
    @property
    def capabilities(self) -> List[str]:
        return self._capabilities
    
    async def initialize(self) -> None:
        """初始化服務"""
        os.makedirs(self.working_dir, exist_ok=True)
        self._initialized = True
        logger.info(f"✅ {self.service_id} initialized")
    
    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """執行方法"""
        if not self._initialized:
            await self.initialize()
        
        if method == "git_clone":
            return await self._git_clone(
                url=params.get("url", ""),
                path=params.get("path"),
                branch=params.get("branch")
            )
        
        elif method == "git_status":
            return await self._git_status(params.get("path", "."))
        
        elif method == "git_commit":
            return await self._git_commit(
                path=params.get("path", "."),
                message=params.get("message", "Auto commit"),
                files=params.get("files")
            )
        
        elif method == "git_push":
            return await self._git_push(
                path=params.get("path", "."),
                remote=params.get("remote", "origin"),
                branch=params.get("branch")
            )
        
        elif method == "git_pull":
            return await self._git_pull(
                path=params.get("path", "."),
                remote=params.get("remote", "origin"),
                branch=params.get("branch")
            )
        
        elif method == "git_branch":
            return await self._git_branch(
                path=params.get("path", "."),
                action=params.get("action", "list"),
                name=params.get("name")
            )
        
        elif method == "git_log":
            return await self._git_log(
                path=params.get("path", "."),
                limit=params.get("limit", 10)
            )
        
        elif method == "git_diff":
            return await self._git_diff(
                path=params.get("path", "."),
                cached=params.get("cached", False)
            )
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    async def health_check(self) -> bool:
        """健康檢查"""
        # 檢查 git 是否可用
        result = await self._run_command(["git", "--version"])
        return result.get("exit_code") == 0
    
    async def shutdown(self) -> None:
        """關閉服務"""
        logger.info(f"{self.service_id} shutdown")
    
    # ========== 內部方法 ==========
    
    async def _run_command(
        self, 
        cmd: List[str], 
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """執行命令"""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or self.working_dir
            )
            
            stdout, stderr = await proc.communicate()
            
            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode,
                "success": proc.returncode == 0
            }
            
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }
    
    async def _git_clone(
        self, 
        url: str, 
        path: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clone 倉庫"""
        if not url:
            return {"error": "URL is required", "success": False}
        
        # 決定目標路徑
        if path is None:
            # 從 URL 提取倉庫名稱
            repo_name = url.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            path = os.path.join(self.working_dir, repo_name)
        
        cmd = ["git", "clone"]
        if branch:
            cmd.extend(["-b", branch])
        cmd.extend([url, path])
        
        result = await self._run_command(cmd)
        result["path"] = path
        
        return result
    
    async def _git_status(self, path: str) -> Dict[str, Any]:
        """查看狀態"""
        full_path = self._resolve_path(path)
        
        result = await self._run_command(
            ["git", "status", "--porcelain"],
            cwd=full_path
        )
        
        if result["success"]:
            # 解析狀態
            lines = result["stdout"].strip().split("\n") if result["stdout"].strip() else []
            files = []
            for line in lines:
                if line:
                    status = line[:2]
                    filename = line[3:]
                    files.append({"status": status, "file": filename})
            
            result["files"] = files
            result["clean"] = len(files) == 0
        
        return result
    
    async def _git_commit(
        self, 
        path: str, 
        message: str,
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """提交變更"""
        full_path = self._resolve_path(path)
        
        # 先 add
        if files:
            add_cmd = ["git", "add"] + files
        else:
            add_cmd = ["git", "add", "-A"]
        
        add_result = await self._run_command(add_cmd, cwd=full_path)
        if not add_result["success"]:
            return add_result
        
        # 然後 commit
        commit_result = await self._run_command(
            ["git", "commit", "-m", message],
            cwd=full_path
        )
        
        return commit_result
    
    async def _git_push(
        self, 
        path: str, 
        remote: str = "origin",
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """推送"""
        full_path = self._resolve_path(path)
        
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        
        return await self._run_command(cmd, cwd=full_path)
    
    async def _git_pull(
        self, 
        path: str, 
        remote: str = "origin",
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """拉取"""
        full_path = self._resolve_path(path)
        
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)
        
        return await self._run_command(cmd, cwd=full_path)
    
    async def _git_branch(
        self, 
        path: str, 
        action: str = "list",
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """分支操作"""
        full_path = self._resolve_path(path)
        
        if action == "list":
            result = await self._run_command(
                ["git", "branch", "-a"],
                cwd=full_path
            )
            if result["success"]:
                branches = []
                for line in result["stdout"].strip().split("\n"):
                    line = line.strip()
                    if line:
                        current = line.startswith("*")
                        name = line.lstrip("* ")
                        branches.append({"name": name, "current": current})
                result["branches"] = branches
            return result
        
        elif action == "create" and name:
            return await self._run_command(
                ["git", "checkout", "-b", name],
                cwd=full_path
            )
        
        elif action == "checkout" and name:
            return await self._run_command(
                ["git", "checkout", name],
                cwd=full_path
            )
        
        elif action == "delete" and name:
            return await self._run_command(
                ["git", "branch", "-d", name],
                cwd=full_path
            )
        
        return {"error": f"Unknown action: {action}", "success": False}
    
    async def _git_log(self, path: str, limit: int = 10) -> Dict[str, Any]:
        """查看日誌"""
        full_path = self._resolve_path(path)
        
        result = await self._run_command(
            ["git", "log", f"-{limit}", "--oneline"],
            cwd=full_path
        )
        
        if result["success"]:
            commits = []
            for line in result["stdout"].strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1]
                        })
            result["commits"] = commits
        
        return result
    
    async def _git_diff(self, path: str, cached: bool = False) -> Dict[str, Any]:
        """查看差異"""
        full_path = self._resolve_path(path)
        
        cmd = ["git", "diff"]
        if cached:
            cmd.append("--cached")
        
        return await self._run_command(cmd, cwd=full_path)
    
    def _resolve_path(self, path: str) -> str:
        """解析路徑"""
        if os.path.isabs(path):
            return path
        return os.path.join(self.working_dir, path)
