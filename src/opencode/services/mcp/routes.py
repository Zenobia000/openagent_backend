"""
MCP 連接管理 API 路由
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from opencode.auth import get_current_user, require_admin, TokenData
from .manager import get_mcp_manager, MCPConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP 連接"])


class MCPConnectionCreate(BaseModel):
    """創建 MCP 連接"""
    name: str
    description: str = ""
    transport: str = "http"  # http, websocket, stdio
    endpoint: str = ""       # HTTP/WebSocket URL
    command: str = ""        # STDIO 命令
    args: List[str] = []     # STDIO 參數
    env: Dict[str, str] = {} # 環境變數


class MCPConnectionUpdate(BaseModel):
    """更新 MCP 連接"""
    name: Optional[str] = None
    description: Optional[str] = None
    transport: Optional[str] = None
    endpoint: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None


class MCPToolCall(BaseModel):
    """調用 MCP 工具"""
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.get("")
async def list_connections(
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """列出所有 MCP 連接"""
    connections = manager.list_connections()
    return {
        "connections": connections,
        "count": len(connections)
    }


@router.post("")
async def create_connection(
    conn: MCPConnectionCreate,
    current_user: TokenData = Depends(require_admin),
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """創建 MCP 連接（僅管理員）"""
    new_conn = manager.add_connection(
        name=conn.name,
        description=conn.description,
        transport=conn.transport,
        endpoint=conn.endpoint,
        command=conn.command,
        args=conn.args,
        env=conn.env
    )
    return new_conn.to_dict()


@router.get("/{conn_id}")
async def get_connection(
    conn_id: str,
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """取得 MCP 連接詳情"""
    conn = manager.get_connection(conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn.to_dict()


@router.put("/{conn_id}")
async def update_connection(
    conn_id: str,
    updates: MCPConnectionUpdate,
    current_user: TokenData = Depends(require_admin),
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """更新 MCP 連接（僅管理員）"""
    conn = manager.update_connection(conn_id, updates.dict(exclude_unset=True))
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn.to_dict()


@router.delete("/{conn_id}")
async def delete_connection(
    conn_id: str,
    current_user: TokenData = Depends(require_admin),
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """刪除 MCP 連接（僅管理員）"""
    success = manager.delete_connection(conn_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"message": f"Connection {conn_id} deleted"}


@router.post("/{conn_id}/test")
async def test_connection(
    conn_id: str,
    current_user: TokenData = Depends(get_current_user),
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """測試 MCP 連接"""
    result = await manager.test_connection(conn_id)
    return result


@router.post("/{conn_id}/enable")
async def enable_connection(
    conn_id: str,
    current_user: TokenData = Depends(require_admin),
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """啟用 MCP 連接"""
    conn = manager.update_connection(conn_id, {"enabled": True})
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"message": f"Connection {conn_id} enabled"}


@router.post("/{conn_id}/disable")
async def disable_connection(
    conn_id: str,
    current_user: TokenData = Depends(require_admin),
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """禁用 MCP 連接"""
    conn = manager.update_connection(conn_id, {"enabled": False})
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"message": f"Connection {conn_id} disabled"}


@router.post("/{conn_id}/call")
async def call_tool(
    conn_id: str,
    call: MCPToolCall,
    current_user: TokenData = Depends(get_current_user),
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """調用 MCP 工具"""
    result = await manager.call_tool(conn_id, call.tool_name, call.arguments)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
    return result


@router.get("/tools/all")
async def get_all_tools(
    manager: MCPConnectionManager = Depends(get_mcp_manager)
):
    """取得所有可用的 MCP 工具"""
    tools = manager.get_all_tools()
    return {
        "tools": tools,
        "count": len(tools)
    }
