"""
文件操作工具

提供文件讀寫、創建等功能
"""

import os
import json
import logging
from typing import Dict, List, Any
from pathlib import Path

from .base import BaseTool, ToolDefinition, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class FileReadTool(BaseTool):
    """文件讀取工具"""
    
    def __init__(self, base_path: str = None):
        super().__init__()
        self._base_path = Path(base_path or os.getenv("DATA_DIR", "data"))
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_read",
            description="讀取文件內容。支援文字文件、JSON、CSV 等格式。",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="文件路徑（相對於 data 目錄）",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="文件編碼",
                    required=False,
                    default="utf-8"
                )
            ],
            returns="文件內容",
            examples=[
                {"file_path": "documents/report.txt"}
            ]
        )
    
    async def execute(
        self,
        file_path: str,
        encoding: str = "utf-8",
        **kwargs
    ) -> Dict[str, Any]:
        """讀取文件"""
        try:
            full_path = self._base_path / file_path
            
            # 安全檢查：防止路徑穿越
            if ".." in str(file_path):
                return {"error": "Invalid path"}
            
            if not full_path.exists():
                return {"error": f"File not found: {file_path}"}
            
            content = full_path.read_text(encoding=encoding)
            
            # 如果是 JSON，嘗試解析
            if full_path.suffix == ".json":
                try:
                    content = json.loads(content)
                except:
                    pass
            
            return {
                "success": True,
                "file_path": str(file_path),
                "content": content,
                "size": full_path.stat().st_size
            }
        except Exception as e:
            logger.error(f"File read error: {e}")
            return {"error": str(e)}


class FileWriteTool(BaseTool):
    """文件寫入工具"""
    
    def __init__(self, base_path: str = None):
        super().__init__()
        self._base_path = Path(base_path or os.getenv("DATA_DIR", "data"))
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_write",
            description="寫入內容到文件。可以創建新文件或覆蓋現有文件。",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="文件路徑（相對於 data 目錄）",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="要寫入的內容",
                    required=True
                ),
                ToolParameter(
                    name="append",
                    type="boolean",
                    description="是否追加模式",
                    required=False,
                    default=False
                )
            ],
            returns="寫入結果",
            examples=[
                {
                    "file_path": "output/report.txt",
                    "content": "# Report\n\nContent here..."
                }
            ]
        )
    
    async def execute(
        self,
        file_path: str,
        content: str,
        append: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """寫入文件"""
        try:
            full_path = self._base_path / file_path
            
            # 安全檢查
            if ".." in str(file_path):
                return {"error": "Invalid path"}
            
            # 確保目錄存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = "a" if append else "w"
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)
            
            return {
                "success": True,
                "file_path": str(file_path),
                "bytes_written": len(content.encode("utf-8")),
                "mode": "append" if append else "write"
            }
        except Exception as e:
            logger.error(f"File write error: {e}")
            return {"error": str(e)}


class FileListTool(BaseTool):
    """文件列表工具"""
    
    def __init__(self, base_path: str = None):
        super().__init__()
        self._base_path = Path(base_path or os.getenv("DATA_DIR", "data"))
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_list",
            description="列出目錄中的文件和子目錄。",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="directory",
                    type="string",
                    description="目錄路徑（相對於 data 目錄）",
                    required=False,
                    default=""
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="文件名匹配模式（如 *.pdf）",
                    required=False,
                    default="*"
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="是否遞迴搜尋",
                    required=False,
                    default=False
                )
            ],
            returns="文件列表",
            examples=[
                {"directory": "documents", "pattern": "*.pdf"}
            ]
        )
    
    async def execute(
        self,
        directory: str = "",
        pattern: str = "*",
        recursive: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """列出文件"""
        try:
            full_path = self._base_path / directory
            
            if ".." in str(directory):
                return {"error": "Invalid path"}
            
            if not full_path.exists():
                return {"error": f"Directory not found: {directory}"}
            
            if recursive:
                files = list(full_path.rglob(pattern))
            else:
                files = list(full_path.glob(pattern))
            
            file_list = []
            for f in files:
                rel_path = f.relative_to(self._base_path)
                file_list.append({
                    "name": f.name,
                    "path": str(rel_path),
                    "is_dir": f.is_dir(),
                    "size": f.stat().st_size if f.is_file() else 0
                })
            
            return {
                "success": True,
                "directory": directory,
                "files": file_list,
                "count": len(file_list)
            }
        except Exception as e:
            logger.error(f"File list error: {e}")
            return {"error": str(e)}
