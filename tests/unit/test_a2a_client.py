"""
A2A Client Manager 單元測試
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.a2a_client import (
    A2AClientManager,
    A2AConfig,
    A2AAgentConfig,
    AgentCard,
    AgentSkill,
    A2ATaskState,
    load_a2a_config,
    _expand_env_vars,
)


# ============================================================
# Config loading tests
# ============================================================

class TestLoadA2AConfig:
    """load_a2a_config() 測試"""

    def test_load_nonexistent_file(self, tmp_path):
        """設定檔不存在時回傳空設定"""
        config = load_a2a_config(tmp_path / "nonexistent.yaml")
        assert config.agents == []

    def test_load_empty_file(self, tmp_path):
        """空設定檔回傳空設定"""
        config_file = tmp_path / "a2a.yaml"
        config_file.write_text("")
        config = load_a2a_config(config_file)
        assert config.agents == []

    def test_load_empty_agents(self, tmp_path):
        """agents: [] 回傳空 list"""
        config_file = tmp_path / "a2a.yaml"
        config_file.write_text("agents: []")
        config = load_a2a_config(config_file)
        assert config.agents == []

    def test_load_remote_agent(self, tmp_path):
        """正確解析 remote agent 設定"""
        config_file = tmp_path / "a2a.yaml"
        config_file.write_text("""
agents:
  - name: "legal-advisor"
    type: "remote"
    url: "https://agents.example.com/legal"
    auth_token: "secret-token"
""")
        config = load_a2a_config(config_file)
        assert len(config.agents) == 1
        a = config.agents[0]
        assert a.name == "legal-advisor"
        assert a.type == "remote"
        assert a.url == "https://agents.example.com/legal"
        assert a.auth_token == "secret-token"

    def test_load_local_agent(self, tmp_path):
        """正確解析 local agent 設定"""
        config_file = tmp_path / "a2a.yaml"
        config_file.write_text("""
agents:
  - name: "stock-analyst"
    type: "local"
    command: "python"
    args: ["server.py"]
    port: 9001
""")
        config = load_a2a_config(config_file)
        a = config.agents[0]
        assert a.type == "local"
        assert a.command == "python"
        assert a.port == 9001

    def test_env_var_expansion(self, tmp_path, monkeypatch):
        """環境變數 ${VAR} 正確展開"""
        monkeypatch.setenv("AGENT_TOKEN", "my-secret")
        config_file = tmp_path / "a2a.yaml"
        config_file.write_text("""
agents:
  - name: "test"
    type: "remote"
    url: "http://localhost:9000"
    auth_token: "${AGENT_TOKEN}"
""")
        config = load_a2a_config(config_file)
        assert config.agents[0].auth_token == "my-secret"

    def test_invalid_yaml(self, tmp_path):
        """格式錯誤的 YAML 回傳空設定"""
        config_file = tmp_path / "a2a.yaml"
        config_file.write_text("agents:\n  - {invalid [yaml")
        config = load_a2a_config(config_file)
        assert config.agents == []


# ============================================================
# Data model tests
# ============================================================

class TestA2AModels:
    """資料模型測試"""

    def test_task_state_values(self):
        assert A2ATaskState.SUBMITTED == "submitted"
        assert A2ATaskState.WORKING == "working"
        assert A2ATaskState.INPUT_REQUIRED == "input-required"
        assert A2ATaskState.COMPLETED == "completed"
        assert A2ATaskState.FAILED == "failed"
        assert A2ATaskState.CANCELED == "canceled"

    def test_agent_card(self):
        card = AgentCard(
            name="Test Agent",
            url="http://localhost:9000",
            skills=[AgentSkill(id="s1", name="Skill 1")],
        )
        assert card.name == "Test Agent"
        assert len(card.skills) == 1
        assert card.skills[0].id == "s1"

    def test_agent_config_defaults(self):
        config = A2AAgentConfig(name="test", url="http://localhost")
        assert config.type == "remote"
        assert config.command is None
        assert config.port is None


# ============================================================
# A2AClientManager tests
# ============================================================

class TestA2AClientManager:
    """A2AClientManager 測試"""

    def test_init_empty_config(self):
        """空設定建立 manager 不報錯"""
        manager = A2AClientManager(A2AConfig())
        assert manager.connected_agents == []
        assert manager.total_skills == 0

    @pytest.mark.asyncio
    async def test_initialize_no_agents(self):
        """無 agent 設定時 initialize 成功"""
        manager = A2AClientManager(A2AConfig())
        await manager.initialize()
        assert manager._initialized is True
        assert manager.connected_agents == []
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """多次 initialize 只執行一次"""
        manager = A2AClientManager(A2AConfig())
        await manager.initialize()
        await manager.initialize()
        assert manager._initialized is True
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_list_agents_empty(self):
        """無連線時 list_agents 回傳空 list"""
        manager = A2AClientManager(A2AConfig())
        await manager.initialize()
        agents = await manager.list_agents()
        assert agents == []
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_send_task_unknown_agent(self):
        """呼叫不存在的 agent 拋出 KeyError"""
        manager = A2AClientManager(A2AConfig())
        await manager.initialize()
        with pytest.raises(KeyError, match="not connected"):
            await manager.send_task("nonexistent", "hello")
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_get_task_status_unknown_agent(self):
        """查詢不存在 agent 的 task 拋出 KeyError"""
        manager = A2AClientManager(A2AConfig())
        await manager.initialize()
        with pytest.raises(KeyError, match="not connected"):
            await manager.get_task_status("nonexistent", "task-123")
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_cancel_task_unknown_agent(self):
        """取消不存在 agent 的 task 拋出 KeyError"""
        manager = A2AClientManager(A2AConfig())
        await manager.initialize()
        with pytest.raises(KeyError, match="not connected"):
            await manager.cancel_task("nonexistent", "task-123")
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_empty(self):
        """無連線時 shutdown 不報錯"""
        manager = A2AClientManager(A2AConfig())
        await manager.initialize()
        await manager.shutdown()
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_remote_agent_connection_failure_graceful(self):
        """remote agent 連線失敗不影響初始化（agent 仍註冊，card 為 None）"""
        config = A2AConfig(agents=[
            A2AAgentConfig(
                name="bad-agent",
                type="remote",
                url="http://localhost:99999",  # unreachable
            )
        ])
        manager = A2AClientManager(config)
        await manager.initialize()
        assert manager._initialized is True
        # Agent is registered (connection created) but card fetch failed gracefully
        assert "bad-agent" in manager.connected_agents
        assert manager.total_skills == 0  # no card = no skills
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_invalid_agent_type(self):
        """不支持的 type 不影響初始化"""
        config = A2AConfig(agents=[
            A2AAgentConfig(
                name="bad",
                type="grpc",  # unsupported
                url="http://localhost:9000",
            )
        ])
        manager = A2AClientManager(config)
        await manager.initialize()
        assert manager.connected_agents == []
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_local_agent_missing_command(self):
        """local agent 缺少 command 不影響初始化"""
        config = A2AConfig(agents=[
            A2AAgentConfig(
                name="bad",
                type="local",
                port=9001,
                # command missing
            )
        ])
        manager = A2AClientManager(config)
        await manager.initialize()
        assert manager.connected_agents == []
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_local_agent_missing_port(self):
        """local agent 缺少 port 不影響初始化"""
        config = A2AConfig(agents=[
            A2AAgentConfig(
                name="bad",
                type="local",
                command="python",
                args=["server.py"],
                # port missing
            )
        ])
        manager = A2AClientManager(config)
        await manager.initialize()
        assert manager.connected_agents == []
        await manager.shutdown()


# ============================================================
# Task normalization tests
# ============================================================

class TestNormalizeTask:
    """_normalize_task() 測試"""

    def test_completed_task_with_text_artifact(self):
        data = {
            "id": "task-1",
            "status": {"state": "completed"},
            "artifacts": [
                {"parts": [{"type": "text", "text": "Analysis result here"}]}
            ],
        }
        result = A2AClientManager._normalize_task(data)
        assert result["id"] == "task-1"
        assert result["state"] == "completed"
        assert result["text"] == "Analysis result here"

    def test_failed_task(self):
        data = {
            "id": "task-2",
            "status": {"state": "failed"},
            "error": "Agent crashed",
            "artifacts": [],
        }
        result = A2AClientManager._normalize_task(data)
        assert result["state"] == "failed"
        assert result["error"] == "Agent crashed"
        assert result["text"] is None

    def test_no_artifacts(self):
        data = {"id": "task-3", "status": {"state": "working"}}
        result = A2AClientManager._normalize_task(data)
        assert result["state"] == "working"
        assert result["text"] is None

    def test_multiple_text_parts(self):
        data = {
            "id": "task-4",
            "status": {"state": "completed"},
            "artifacts": [
                {"parts": [
                    {"type": "text", "text": "Part 1"},
                    {"type": "text", "text": "Part 2"},
                ]}
            ],
        }
        result = A2AClientManager._normalize_task(data)
        assert result["text"] == "Part 1\nPart 2"

    def test_legacy_state_field(self):
        """支持直接 state 欄位（非 status.state 嵌套）"""
        data = {"id": "task-5", "state": "completed", "artifacts": []}
        result = A2AClientManager._normalize_task(data)
        assert result["state"] == "completed"
