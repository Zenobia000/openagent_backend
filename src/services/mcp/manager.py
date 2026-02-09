"""
MCP 連接管理服務

讓用戶可以:
- 添加外部 MCP 服務端點
- 管理 MCP 連接
- 動態調用 MCP 工具
"""

import os
import json
import logging
import asyncio
import httpx
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

from opencode.core.utils import get_project_root

logger = logging.getLogger(__name__)


class MCPConnectionStatus(str, Enum):
    """MCP 連接狀態"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class MCPTransportType(str, Enum):
    """MCP 傳輸類型"""
    HTTP = "http"
    WEBSOCKET = "websocket"
    STDIO = "stdio"


@dataclass
class MCPConnection:
    """MCP 連接配置"""
    id: str
    name: str
    description: str = ""
    transport: MCPTransportType = MCPTransportType.HTTP
    endpoint: str = ""  # HTTP/WebSocket URL
    command: str = ""   # STDIO 命令
    args: List[str] = field(default_factory=list)  # STDIO 參數
    env: Dict[str, str] = field(default_factory=dict)  # 環境變數
    enabled: bool = True
    status: MCPConnectionStatus = MCPConnectionStatus.UNKNOWN
    tools: List[Dict[str, Any]] = field(default_factory=list)  # 可用工具
    last_connected: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["transport"] = self.transport.value
        data["status"] = self.status.value
        return data


class MCPConnectionManager:
    """
    MCP 連接管理器
    
    管理外部 MCP 服務的連接
    """
    
    def __init__(self):
        self.data_dir = get_project_root() / "data" / "mcp"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.data_dir / "connections.json"
        
        self._connections: Dict[str, MCPConnection] = {}
        self._http_clients: Dict[str, httpx.AsyncClient] = {}
        
        self._load_connections()
        logger.info(f"✅ MCPConnectionManager initialized, {len(self._connections)} connections")
    
    def _load_connections(self) -> None:
        """載入連接配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for conn_data in data.get("connections", []):
                    conn = MCPConnection(
                        id=conn_data["id"],
                        name=conn_data["name"],
                        description=conn_data.get("description", ""),
                        transport=MCPTransportType(conn_data.get("transport", "http")),
                        endpoint=conn_data.get("endpoint", ""),
                        command=conn_data.get("command", ""),
                        args=conn_data.get("args", []),
                        env=conn_data.get("env", {}),
                        enabled=conn_data.get("enabled", True),
                        tools=conn_data.get("tools", []),
                        created_at=conn_data.get("created_at", datetime.utcnow().isoformat())
                    )
                    self._connections[conn.id] = conn
                    
            except Exception as e:
                logger.error(f"Failed to load MCP connections: {e}")
    
    def _save_connections(self) -> None:
        """保存連接配置"""
        try:
            data = {
                "connections": [conn.to_dict() for conn in self._connections.values()]
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save MCP connections: {e}")
    
    def add_connection(
        self,
        name: str,
        transport: str,
        endpoint: str = "",
        command: str = "",
        args: List[str] = None,
        env: Dict[str, str] = None,
        description: str = ""
    ) -> MCPConnection:
        """添加 MCP 連接"""
        import hashlib
        conn_id = hashlib.md5(f"{name}-{datetime.utcnow().timestamp()}".encode()).hexdigest()[:12]
        
        conn = MCPConnection(
            id=conn_id,
            name=name,
            description=description,
            transport=MCPTransportType(transport),
            endpoint=endpoint,
            command=command,
            args=args or [],
            env=env or {}
        )
        
        self._connections[conn_id] = conn
        self._save_connections()
        
        logger.info(f"✅ Added MCP connection: {name} ({conn_id})")
        return conn
    
    def update_connection(self, conn_id: str, updates: Dict[str, Any]) -> Optional[MCPConnection]:
        """更新連接配置"""
        conn = self._connections.get(conn_id)
        if not conn:
            return None
        
        for key, value in updates.items():
            if hasattr(conn, key) and key not in ['id', 'created_at']:
                if key == 'transport':
                    value = MCPTransportType(value)
                setattr(conn, key, value)
        
        self._save_connections()
        return conn
    
    def delete_connection(self, conn_id: str) -> bool:
        """刪除連接"""
        if conn_id not in self._connections:
            return False
        
        # 關閉 HTTP client
        if conn_id in self._http_clients:
            asyncio.create_task(self._http_clients[conn_id].aclose())
            del self._http_clients[conn_id]
        
        del self._connections[conn_id]
        self._save_connections()
        
        logger.info(f"🗑️ Deleted MCP connection: {conn_id}")
        return True
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """列出所有連接"""
        return [conn.to_dict() for conn in self._connections.values()]
    
    def get_connection(self, conn_id: str) -> Optional[MCPConnection]:
        """取得連接"""
        return self._connections.get(conn_id)
    
    async def test_connection(self, conn_id: str) -> Dict[str, Any]:
        """測試連接"""
        conn = self._connections.get(conn_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        try:
            if conn.transport == MCPTransportType.HTTP:
                return await self._test_http_connection(conn)
            elif conn.transport == MCPTransportType.STDIO:
                return await self._test_stdio_connection(conn)
            else:
                return {"success": False, "error": f"Unsupported transport: {conn.transport}"}
        except Exception as e:
            conn.status = MCPConnectionStatus.ERROR
            self._save_connections()
            return {"success": False, "error": str(e)}
    
    async def _test_http_connection(self, conn: MCPConnection) -> Dict[str, Any]:
        """測試 HTTP 連接"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 嘗試調用 tools/list
                response = await client.post(
                    f"{conn.endpoint}/tools/list",
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tools = data.get("result", {}).get("tools", [])
                    
                    conn.status = MCPConnectionStatus.CONNECTED
                    conn.tools = tools
                    conn.last_connected = datetime.utcnow().isoformat()
                    self._save_connections()
                    
                    return {
                        "success": True,
                        "tools_count": len(tools),
                        "tools": tools
                    }
                else:
                    conn.status = MCPConnectionStatus.ERROR
                    self._save_connections()
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            conn.status = MCPConnectionStatus.ERROR
            self._save_connections()
            return {"success": False, "error": str(e)}
    
    async def _test_stdio_connection(self, conn: MCPConnection) -> Dict[str, Any]:
        """測試 STDIO 連接"""
        try:
            # 創建子進程
            env = {**os.environ, **conn.env}
            process = await asyncio.create_subprocess_exec(
                conn.command,
                *conn.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # 發送 initialize 請求
            init_request = json.dumps({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "OpenCode", "version": "1.0.0"}
                },
                "id": 1
            }) + "\n"
            
            process.stdin.write(init_request.encode())
            await process.stdin.drain()
            
            # 讀取回應
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=5
                )
                response = json.loads(response_line.decode())
                
                # 發送 tools/list 請求
                tools_request = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 2
                }) + "\n"
                
                process.stdin.write(tools_request.encode())
                await process.stdin.drain()
                
                tools_response_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=5
                )
                tools_response = json.loads(tools_response_line.decode())
                tools = tools_response.get("result", {}).get("tools", [])
                
                conn.status = MCPConnectionStatus.CONNECTED
                conn.tools = tools
                conn.last_connected = datetime.utcnow().isoformat()
                self._save_connections()
                
                return {
                    "success": True,
                    "tools_count": len(tools),
                    "tools": tools
                }
                
            finally:
                process.terminate()
                
        except Exception as e:
            conn.status = MCPConnectionStatus.ERROR
            self._save_connections()
            return {"success": False, "error": str(e)}
    
    async def call_tool(
        self,
        conn_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """調用 MCP 工具"""
        conn = self._connections.get(conn_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        if not conn.enabled:
            return {"success": False, "error": "Connection is disabled"}
        
        try:
            if conn.transport == MCPTransportType.HTTP:
                return await self._call_http_tool(conn, tool_name, arguments)
            else:
                return {"success": False, "error": f"Tool call not implemented for {conn.transport}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_http_tool(
        self,
        conn: MCPConnection,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """通過 HTTP 調用工具"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{conn.endpoint}/tools/call",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    return {"success": False, "error": data["error"]}
                return {"success": True, "result": data.get("result")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """取得所有已連接服務的工具"""
        all_tools = []
        for conn in self._connections.values():
            if conn.enabled and conn.status == MCPConnectionStatus.CONNECTED:
                for tool in conn.tools:
                    all_tools.append({
                        **tool,
                        "mcp_connection_id": conn.id,
                        "mcp_connection_name": conn.name
                    })
        return all_tools


# 全域實例
_mcp_manager: Optional[MCPConnectionManager] = None


def get_mcp_manager() -> MCPConnectionManager:
    """取得 MCP 連接管理器實例"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPConnectionManager()
    return _mcp_manager
