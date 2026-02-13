"""
MCP Client Manager — 管理與外部 MCP Server 的連線和工具呼叫

使用 Anthropic 官方 MCP Python SDK (mcp>=1.0.0) 實作。
支援 stdio 和 sse 兩種 transport。
"""

import os
import re
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel

from .logger import structured_logger
from .protocols import MCPClientProtocol

logger = structured_logger


# ============================================================
# Configuration Models
# ============================================================

class MCPServerConfig(BaseModel):
    """單一 MCP Server 的設定"""
    name: str
    transport: str = "stdio"  # "stdio" | "sse"
    # stdio transport
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    # sse transport
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class MCPConfig(BaseModel):
    """MCP 整體設定"""
    servers: List[MCPServerConfig] = []


def _expand_env_vars(value: str) -> str:
    """展開 ${VAR_NAME} 格式的環境變數"""
    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return re.sub(r'\$\{(\w+)\}', replacer, value)


def _expand_config_env(data: Any) -> Any:
    """遞迴展開設定中的環境變數"""
    if isinstance(data, str):
        return _expand_env_vars(data)
    if isinstance(data, dict):
        return {k: _expand_config_env(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_config_env(item) for item in data]
    return data


def load_mcp_config(config_path: Optional[Path] = None) -> MCPConfig:
    """從 YAML 載入 MCP Server 設定

    Args:
        config_path: 設定檔路徑，預設為 config/mcp_servers.yaml

    Returns:
        MCPConfig 實例（無設定檔時回傳空設定）
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "mcp_servers.yaml"

    if not config_path.exists():
        return MCPConfig()

    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        expanded = _expand_config_env(raw)
        return MCPConfig(**expanded)
    except Exception as e:
        logger.warning(f"Failed to load MCP config from {config_path}: {e}")
        return MCPConfig()


# ============================================================
# MCP Client Manager
# ============================================================

class _MCPServerConnection:
    """封裝單一 MCP Server 的連線狀態"""

    def __init__(self, name: str, session, tools: list, resources: list):
        self.name = name
        self.session = session
        self.tools = tools
        self.resources = resources


class MCPClientManager(MCPClientProtocol):
    """管理多個 MCP Server 連線的統一入口

    使用 MCP Python SDK 的 stdio_client / sse_client 建立連線，
    透過 ClientSession 與 Server 互動。

    Usage:
        config = load_mcp_config()
        manager = MCPClientManager(config)
        await manager.initialize()
        tools = await manager.list_tools()
        result = await manager.call_tool("weather", "get_weather", {"city": "Taipei"})
        await manager.shutdown()
    """

    def __init__(self, config: MCPConfig):
        self._config = config
        self._connections: Dict[str, _MCPServerConnection] = {}
        self._exit_stack = AsyncExitStack()
        self._initialized = False

    async def initialize(self) -> None:
        """啟動所有設定的 MCP Server 連線"""
        if self._initialized:
            return

        for server_config in self._config.servers:
            try:
                await self._connect_server(server_config)
                logger.info(
                    f"MCP server '{server_config.name}' connected",
                    server_name=server_config.name,
                    transport=server_config.transport,
                )
            except Exception as e:
                logger.warning(
                    f"MCP server '{server_config.name}' unavailable: {e}",
                    server_name=server_config.name,
                )

        self._initialized = True

    async def _connect_server(self, config: MCPServerConfig) -> None:
        """建立與單一 MCP Server 的連線"""
        from mcp import ClientSession

        if config.transport == "stdio":
            from mcp.client.stdio import stdio_client, StdioServerParameters

            if not config.command:
                raise ValueError(f"MCP server '{config.name}': stdio transport requires 'command'")

            server_params = StdioServerParameters(
                command=config.command,
                args=config.args or [],
                env=config.env,
                cwd=config.cwd,
            )
            transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )

        elif config.transport == "sse":
            from mcp.client.sse import sse_client

            if not config.url:
                raise ValueError(f"MCP server '{config.name}': sse transport requires 'url'")

            transport = await self._exit_stack.enter_async_context(
                sse_client(config.url, headers=config.headers)
            )

        else:
            raise ValueError(f"MCP server '{config.name}': unsupported transport '{config.transport}'")

        # Create and initialize session
        read_stream, write_stream = transport
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        # Fetch available tools and resources
        tools_result = await session.list_tools()
        tools = tools_result.tools if tools_result.tools else []

        try:
            resources_result = await session.list_resources()
            resources = resources_result.resources if resources_result.resources else []
        except Exception:
            resources = []

        self._connections[config.name] = _MCPServerConnection(
            name=config.name,
            session=session,
            tools=tools,
            resources=resources,
        )

    async def add_server(self, config: MCPServerConfig) -> bool:
        """動態新增一個 MCP Server 連線"""
        if config.name in self._connections:
            logger.warning(f"MCP server '{config.name}' already connected")
            return False
        try:
            await self._connect_server(config)
            logger.info(f"MCP server '{config.name}' dynamically added", server_name=config.name)
            return True
        except Exception as e:
            logger.warning(f"Failed to add MCP server '{config.name}': {e}", server_name=config.name)
            raise

    async def remove_server(self, name: str) -> bool:
        """動態移除一個 MCP Server 連線"""
        if name not in self._connections:
            return False
        del self._connections[name]
        logger.info(f"MCP server '{name}' removed", server_name=name)
        return True

    async def list_tools(self) -> List[Dict[str, Any]]:
        """聚合所有已連線 server 的 tools

        Returns:
            List of tool descriptions, each with server_name, name, description, inputSchema
        """
        all_tools = []
        for name, conn in self._connections.items():
            for tool in conn.tools:
                all_tools.append({
                    "server_name": name,
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                })
        return all_tools

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """呼叫指定 server 的指定 tool

        Args:
            server_name: MCP server 名稱
            tool_name: Tool 名稱
            arguments: Tool 參數

        Returns:
            Dict with 'content' (list of content items) and 'is_error' flag

        Raises:
            KeyError: server_name 不存在
            RuntimeError: tool 呼叫失敗
        """
        if server_name not in self._connections:
            raise KeyError(f"MCP server '{server_name}' not connected")

        conn = self._connections[server_name]
        result = await conn.session.call_tool(tool_name, arguments)

        # Convert MCP result to plain dict
        content_items = []
        for item in (result.content or []):
            content_items.append({
                "type": getattr(item, 'type', 'text'),
                "text": getattr(item, 'text', str(item)),
            })

        return {
            "content": content_items,
            "is_error": bool(result.isError) if hasattr(result, 'isError') else False,
        }

    async def list_resources(self) -> List[Dict[str, Any]]:
        """聚合所有已連線 server 的 resources"""
        all_resources = []
        for name, conn in self._connections.items():
            for resource in conn.resources:
                all_resources.append({
                    "server_name": name,
                    "uri": str(resource.uri),
                    "name": resource.name,
                    "description": getattr(resource, 'description', None),
                    "mime_type": getattr(resource, 'mimeType', None),
                })
        return all_resources

    async def read_resource(self, server_name: str, uri: str) -> Any:
        """讀取指定 server 的 resource"""
        if server_name not in self._connections:
            raise KeyError(f"MCP server '{server_name}' not connected")

        conn = self._connections[server_name]
        result = await conn.session.read_resource(uri)
        return result

    async def shutdown(self) -> None:
        """關閉所有連線和子進程"""
        try:
            await self._exit_stack.aclose()
        except Exception as e:
            logger.warning(f"Error during MCP client shutdown: {e}")
        self._connections.clear()
        self._initialized = False

    @property
    def connected_servers(self) -> List[str]:
        """已連線的 server 名稱"""
        return list(self._connections.keys())

    @property
    def total_tools(self) -> int:
        """所有已連線 server 的 tool 總數"""
        return sum(len(conn.tools) for conn in self._connections.values())
