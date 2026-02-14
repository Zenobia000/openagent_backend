"""
MCP Client Manager 單元測試
"""

import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.mcp_client import (
    MCPClientManager,
    MCPConfig,
    MCPServerConfig,
    load_mcp_config,
    _expand_env_vars,
)


# ============================================================
# Config loading tests
# ============================================================

class TestLoadMCPConfig:
    """load_mcp_config() 測試"""

    def test_load_nonexistent_file(self, tmp_path):
        """設定檔不存在時回傳空設定"""
        config = load_mcp_config(tmp_path / "nonexistent.yaml")
        assert config.servers == []

    def test_load_empty_file(self, tmp_path):
        """空設定檔回傳空設定"""
        config_file = tmp_path / "mcp.yaml"
        config_file.write_text("")
        config = load_mcp_config(config_file)
        assert config.servers == []

    def test_load_empty_servers(self, tmp_path):
        """servers: [] 回傳空 list"""
        config_file = tmp_path / "mcp.yaml"
        config_file.write_text("servers: []")
        config = load_mcp_config(config_file)
        assert config.servers == []

    def test_load_stdio_server(self, tmp_path):
        """正確解析 stdio server 設定"""
        config_file = tmp_path / "mcp.yaml"
        config_file.write_text("""
servers:
  - name: "weather"
    transport: "stdio"
    command: "python"
    args: ["server.py"]
    env:
      API_KEY: "test-key"
""")
        config = load_mcp_config(config_file)
        assert len(config.servers) == 1
        s = config.servers[0]
        assert s.name == "weather"
        assert s.transport == "stdio"
        assert s.command == "python"
        assert s.args == ["server.py"]
        assert s.env == {"API_KEY": "test-key"}

    def test_load_sse_server(self, tmp_path):
        """正確解析 sse server 設定"""
        config_file = tmp_path / "mcp.yaml"
        config_file.write_text("""
servers:
  - name: "remote"
    transport: "sse"
    url: "https://example.com/mcp"
    headers:
      Authorization: "Bearer token123"
""")
        config = load_mcp_config(config_file)
        s = config.servers[0]
        assert s.transport == "sse"
        assert s.url == "https://example.com/mcp"
        assert s.headers["Authorization"] == "Bearer token123"

    def test_env_var_expansion(self, tmp_path, monkeypatch):
        """環境變數 ${VAR} 正確展開"""
        monkeypatch.setenv("MY_API_KEY", "secret-123")
        config_file = tmp_path / "mcp.yaml"
        config_file.write_text("""
servers:
  - name: "test"
    transport: "stdio"
    command: "python"
    args: ["server.py"]
    env:
      API_KEY: "${MY_API_KEY}"
""")
        config = load_mcp_config(config_file)
        assert config.servers[0].env["API_KEY"] == "secret-123"

    def test_env_var_not_set_keeps_placeholder(self, tmp_path):
        """未設定的環境變數保留原始 ${VAR} 字串"""
        config_file = tmp_path / "mcp.yaml"
        config_file.write_text("""
servers:
  - name: "test"
    transport: "stdio"
    command: "python"
    args: ["server.py"]
    env:
      MISSING: "${DEFINITELY_NOT_SET_XYZ}"
""")
        config = load_mcp_config(config_file)
        assert config.servers[0].env["MISSING"] == "${DEFINITELY_NOT_SET_XYZ}"

    def test_invalid_yaml(self, tmp_path):
        """格式錯誤的 YAML 回傳空設定（不拋例外）"""
        config_file = tmp_path / "mcp.yaml"
        config_file.write_text("servers:\n  - {invalid yaml here [")
        config = load_mcp_config(config_file)
        assert config.servers == []


class TestExpandEnvVars:
    """_expand_env_vars() 測試"""

    def test_simple_expansion(self, monkeypatch):
        monkeypatch.setenv("FOO", "bar")
        assert _expand_env_vars("${FOO}") == "bar"

    def test_no_vars(self):
        assert _expand_env_vars("hello world") == "hello world"

    def test_multiple_vars(self, monkeypatch):
        monkeypatch.setenv("A", "1")
        monkeypatch.setenv("B", "2")
        assert _expand_env_vars("${A}-${B}") == "1-2"


# ============================================================
# MCPClientManager tests
# ============================================================

class TestMCPClientManager:
    """MCPClientManager 測試"""

    def test_init_empty_config(self):
        """空設定建立 manager 不報錯"""
        manager = MCPClientManager(MCPConfig())
        assert manager.connected_servers == []
        assert manager.total_tools == 0

    @pytest.mark.asyncio
    async def test_initialize_no_servers(self):
        """無 server 設定時 initialize 成功"""
        manager = MCPClientManager(MCPConfig())
        await manager.initialize()
        assert manager._initialized is True
        assert manager.connected_servers == []

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """多次 initialize 只執行一次"""
        manager = MCPClientManager(MCPConfig())
        await manager.initialize()
        await manager.initialize()  # should not error
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_list_tools_empty(self):
        """無連線時 list_tools 回傳空 list"""
        manager = MCPClientManager(MCPConfig())
        await manager.initialize()
        tools = await manager.list_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_list_resources_empty(self):
        """無連線時 list_resources 回傳空 list"""
        manager = MCPClientManager(MCPConfig())
        await manager.initialize()
        resources = await manager.list_resources()
        assert resources == []

    @pytest.mark.asyncio
    async def test_call_tool_unknown_server(self):
        """呼叫不存在的 server 拋出 KeyError"""
        manager = MCPClientManager(MCPConfig())
        await manager.initialize()
        with pytest.raises(KeyError, match="not connected"):
            await manager.call_tool("nonexistent", "tool", {})

    @pytest.mark.asyncio
    async def test_read_resource_unknown_server(self):
        """讀取不存在 server 的 resource 拋出 KeyError"""
        manager = MCPClientManager(MCPConfig())
        await manager.initialize()
        with pytest.raises(KeyError, match="not connected"):
            await manager.read_resource("nonexistent", "file:///test")

    @pytest.mark.asyncio
    async def test_shutdown_empty(self):
        """無連線時 shutdown 不報錯"""
        manager = MCPClientManager(MCPConfig())
        await manager.initialize()
        await manager.shutdown()
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_server_connection_failure_graceful(self):
        """單一 server 連線失敗不影響初始化"""
        config = MCPConfig(servers=[
            MCPServerConfig(
                name="bad-server",
                transport="stdio",
                command="nonexistent_command_xyz",
                args=[],
            )
        ])
        manager = MCPClientManager(config)
        await manager.initialize()  # should not raise
        assert manager._initialized is True
        assert manager.connected_servers == []

    @pytest.mark.asyncio
    async def test_invalid_transport(self):
        """不支持的 transport 不影響初始化"""
        config = MCPConfig(servers=[
            MCPServerConfig(
                name="bad",
                transport="websocket",  # unsupported
                command="python",
                args=[],
            )
        ])
        manager = MCPClientManager(config)
        await manager.initialize()  # graceful degradation
        assert manager.connected_servers == []


# ============================================================
# MCPServerConfig model tests
# ============================================================

class TestMCPServerConfig:
    """MCPServerConfig 模型測試"""

    def test_minimal_stdio(self):
        """最小 stdio 設定"""
        config = MCPServerConfig(name="test", command="python", args=["server.py"])
        assert config.transport == "stdio"
        assert config.env is None

    def test_minimal_sse(self):
        """最小 sse 設定"""
        config = MCPServerConfig(name="test", transport="sse", url="http://localhost:8080")
        assert config.transport == "sse"
        assert config.command is None
