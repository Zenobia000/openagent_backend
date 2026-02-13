"""
A2A Client Manager — 管理與外部 A2A Agent 的任務委派和協作

實作 Google A2A Protocol (2025)。
使用 httpx 進行 HTTP/SSE 通訊。

A2A Protocol 核心概念：
- Agent Card: Agent 的自我描述 (GET /.well-known/agent.json)
- Task: 任務生命週期 (submitted → working → input-required → completed/failed)
- Artifact: 任務產出的結果
"""

import asyncio
import json
import os
import re
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
import yaml
from pydantic import BaseModel

from .logger import structured_logger
from .protocols import A2AClientProtocol

logger = structured_logger


# ============================================================
# Data Models
# ============================================================

class A2ATaskState(str, Enum):
    """A2A Task 狀態機"""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AgentSkill(BaseModel):
    """Agent 技能描述"""
    id: str
    name: str
    description: str = ""
    input_modes: List[str] = ["text"]
    output_modes: List[str] = ["text"]


class AgentCard(BaseModel):
    """A2A Agent Card — Agent 的自我描述"""
    name: str
    description: str = ""
    url: str
    version: str = "1.0.0"
    capabilities: Dict[str, bool] = {}
    skills: List[AgentSkill] = []


class A2AAgentConfig(BaseModel):
    """單一 A2A Agent 的設定"""
    name: str
    type: str = "remote"  # "local" | "remote"
    # remote agent
    url: Optional[str] = None
    auth_token: Optional[str] = None
    # local agent (managed subprocess)
    command: Optional[str] = None
    args: Optional[List[str]] = None
    port: Optional[int] = None
    env: Optional[Dict[str, str]] = None


class A2AConfig(BaseModel):
    """A2A 整體設定"""
    agents: List[A2AAgentConfig] = []


# ============================================================
# Config Loading
# ============================================================

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


def load_a2a_config(config_path: Optional[Path] = None) -> A2AConfig:
    """從 YAML 載入 A2A Agent 設定

    Args:
        config_path: 設定檔路徑，預設為 config/a2a_agents.yaml

    Returns:
        A2AConfig 實例（無設定檔時回傳空設定）
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "a2a_agents.yaml"

    if not config_path.exists():
        return A2AConfig()

    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        expanded = _expand_config_env(raw)
        return A2AConfig(**expanded)
    except Exception as e:
        logger.warning(f"Failed to load A2A config from {config_path}: {e}")
        return A2AConfig()


# ============================================================
# A2A Client Manager
# ============================================================

class _A2AAgentConnection:
    """封裝單一 A2A Agent 的連線狀態"""

    def __init__(self, name: str, url: str, card: Optional[AgentCard],
                 process: Optional[asyncio.subprocess.Process] = None,
                 auth_token: Optional[str] = None):
        self.name = name
        self.url = url
        self.card = card
        self.process = process
        self.auth_token = auth_token


class A2AClientManager(A2AClientProtocol):
    """管理多個外部 A2A Agent 的統一入口

    Usage:
        config = load_a2a_config()
        manager = A2AClientManager(config)
        await manager.initialize()
        agents = await manager.list_agents()
        result = await manager.send_task("stock-analyst", "分析台積電股票")
        await manager.shutdown()
    """

    def __init__(self, config: A2AConfig):
        self._config = config
        self._connections: Dict[str, _A2AAgentConnection] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """啟動所有設定的 A2A Agents 連線"""
        if self._initialized:
            return

        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

        for agent_config in self._config.agents:
            try:
                await self._connect_agent(agent_config)
                logger.info(
                    f"A2A agent '{agent_config.name}' connected",
                    agent_name=agent_config.name,
                    agent_type=agent_config.type,
                )
            except Exception as e:
                logger.warning(
                    f"A2A agent '{agent_config.name}' unavailable: {e}",
                    agent_name=agent_config.name,
                )

        self._initialized = True

    async def _connect_agent(self, config: A2AAgentConfig) -> None:
        """建立與單一 A2A Agent 的連線"""
        process = None
        url = config.url

        if config.type == "local":
            # Launch local subprocess
            if not config.command:
                raise ValueError(f"A2A agent '{config.name}': local type requires 'command'")
            if not config.port:
                raise ValueError(f"A2A agent '{config.name}': local type requires 'port'")

            env = {**os.environ}
            if config.env:
                env.update(config.env)

            process = await asyncio.create_subprocess_exec(
                config.command, *(config.args or []),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            url = f"http://localhost:{config.port}"

            # Wait briefly for server to start
            await asyncio.sleep(1.0)

        elif config.type == "remote":
            if not config.url:
                raise ValueError(f"A2A agent '{config.name}': remote type requires 'url'")
            url = config.url

        else:
            raise ValueError(f"A2A agent '{config.name}': unsupported type '{config.type}'")

        # Fetch Agent Card
        card = await self._fetch_agent_card(url, config.auth_token)

        self._connections[config.name] = _A2AAgentConnection(
            name=config.name,
            url=url.rstrip("/"),
            card=card,
            process=process,
            auth_token=config.auth_token,
        )

    async def _fetch_agent_card(self, base_url: str, auth_token: Optional[str] = None) -> Optional[AgentCard]:
        """從 /.well-known/agent.json 取得 Agent Card"""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            resp = await self._http_client.get(
                f"{base_url.rstrip('/')}/.well-known/agent.json",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return AgentCard(**data)
        except Exception as e:
            logger.warning(f"Failed to fetch Agent Card from {base_url}: {e}")
            return None

    def _build_headers(self, conn: _A2AAgentConnection) -> Dict[str, str]:
        """建構請求 headers"""
        headers = {"Content-Type": "application/json"}
        if conn.auth_token:
            headers["Authorization"] = f"Bearer {conn.auth_token}"
        return headers

    # --------------------------------------------------------
    # Protocol Methods
    # --------------------------------------------------------

    async def add_agent(self, config: A2AAgentConfig) -> bool:
        """動態新增一個 A2A Agent 連線"""
        if config.name in self._connections:
            logger.warning(f"A2A agent '{config.name}' already connected")
            return False
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        try:
            await self._connect_agent(config)
            logger.info(f"A2A agent '{config.name}' dynamically added", agent_name=config.name)
            return True
        except Exception as e:
            logger.warning(f"Failed to add A2A agent '{config.name}': {e}", agent_name=config.name)
            raise

    async def remove_agent(self, name: str) -> bool:
        """動態移除一個 A2A Agent 連線"""
        if name not in self._connections:
            return False
        conn = self._connections[name]
        if conn.process and conn.process.returncode is None:
            try:
                conn.process.terminate()
                await asyncio.wait_for(conn.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                conn.process.kill()
            except Exception as e:
                logger.warning(f"Error stopping A2A agent '{name}': {e}")
        del self._connections[name]
        logger.info(f"A2A agent '{name}' removed", agent_name=name)
        return True

    async def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有已連線的 Agent 及其能力"""
        agents = []
        for name, conn in self._connections.items():
            agent_info = {
                "name": name,
                "url": conn.url,
                "connected": True,
            }
            if conn.card:
                agent_info["description"] = conn.card.description
                agent_info["version"] = conn.card.version
                agent_info["capabilities"] = conn.card.capabilities
                agent_info["skills"] = [
                    {"id": s.id, "name": s.name, "description": s.description}
                    for s in conn.card.skills
                ]
            agents.append(agent_info)
        return agents

    async def send_task(
        self, agent_name: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """向外部 Agent 發送任務，等待完成

        Args:
            agent_name: Agent 名稱
            message: 任務訊息
            metadata: 附加元資料

        Returns:
            Dict with 'id', 'state', 'artifacts', 'error'

        Raises:
            KeyError: agent_name 不存在
            RuntimeError: 任務失敗
        """
        if agent_name not in self._connections:
            raise KeyError(f"A2A agent '{agent_name}' not connected")

        conn = self._connections[agent_name]
        task_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "id": task_id,
            "params": {
                "id": task_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
            },
        }
        if metadata:
            payload["params"]["metadata"] = metadata

        resp = await self._http_client.post(
            f"{conn.url}/tasks/send",
            json=payload,
            headers=self._build_headers(conn),
        )
        resp.raise_for_status()
        result = resp.json()

        # Extract task from JSON-RPC response
        task_data = result.get("result", result)
        return self._normalize_task(task_data)

    async def send_task_streaming(
        self, agent_name: str, message: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """串流接收任務結果 (SSE)

        Yields:
            Dict events with 'type' and 'data'
        """
        if agent_name not in self._connections:
            raise KeyError(f"A2A agent '{agent_name}' not connected")

        conn = self._connections[agent_name]
        task_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/sendSubscribe",
            "id": task_id,
            "params": {
                "id": task_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
            },
        }

        async with self._http_client.stream(
            "POST",
            f"{conn.url}/tasks/sendSubscribe",
            json=payload,
            headers={**self._build_headers(conn), "Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            event_type = None
            data_lines = []

            async for line in response.aiter_lines():
                line = line.strip()
                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:"):].strip())
                elif line == "" and data_lines:
                    # End of SSE event
                    raw_data = "\n".join(data_lines)
                    try:
                        parsed = json.loads(raw_data)
                    except json.JSONDecodeError:
                        parsed = {"text": raw_data}

                    yield {
                        "type": event_type or "message",
                        "data": parsed,
                    }
                    event_type = None
                    data_lines = []

    async def get_task_status(self, agent_name: str, task_id: str) -> Dict[str, Any]:
        """查詢任務狀態"""
        if agent_name not in self._connections:
            raise KeyError(f"A2A agent '{agent_name}' not connected")

        conn = self._connections[agent_name]

        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "id": str(uuid.uuid4()),
            "params": {"id": task_id},
        }

        resp = await self._http_client.post(
            f"{conn.url}/tasks/get",
            json=payload,
            headers=self._build_headers(conn),
        )
        resp.raise_for_status()
        result = resp.json()
        task_data = result.get("result", result)
        return self._normalize_task(task_data)

    async def cancel_task(self, agent_name: str, task_id: str) -> bool:
        """取消進行中的任務"""
        if agent_name not in self._connections:
            raise KeyError(f"A2A agent '{agent_name}' not connected")

        conn = self._connections[agent_name]

        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "id": str(uuid.uuid4()),
            "params": {"id": task_id},
        }

        try:
            resp = await self._http_client.post(
                f"{conn.url}/tasks/cancel",
                json=payload,
                headers=self._build_headers(conn),
            )
            resp.raise_for_status()
            return True
        except Exception:
            return False

    async def shutdown(self) -> None:
        """關閉所有連線和子進程"""
        # Terminate local agent subprocesses
        for conn in self._connections.values():
            if conn.process and conn.process.returncode is None:
                try:
                    conn.process.terminate()
                    await asyncio.wait_for(conn.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    conn.process.kill()
                except Exception as e:
                    logger.warning(f"Error stopping A2A agent '{conn.name}': {e}")

        # Close HTTP client
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        self._connections.clear()
        self._initialized = False

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def _normalize_task(data: Dict[str, Any]) -> Dict[str, Any]:
        """正規化 Task 回應格式"""
        # Extract text from artifacts
        artifacts = data.get("artifacts", [])
        text_parts = []
        for artifact in artifacts:
            for part in artifact.get("parts", []):
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_parts.append(part)

        return {
            "id": data.get("id"),
            "state": data.get("status", {}).get("state", data.get("state", "unknown")),
            "artifacts": artifacts,
            "text": "\n".join(text_parts) if text_parts else None,
            "error": data.get("error"),
        }

    @property
    def connected_agents(self) -> List[str]:
        """已連線的 agent 名稱"""
        return list(self._connections.keys())

    @property
    def total_skills(self) -> int:
        """所有已連線 agent 的 skill 總數"""
        return sum(
            len(conn.card.skills) if conn.card else 0
            for conn in self._connections.values()
        )
