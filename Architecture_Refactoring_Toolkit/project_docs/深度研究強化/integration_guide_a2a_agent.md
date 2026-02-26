# Sub Agent（A2A）整合說明書

> 適用對象：需要在 QuitCode 後端平台接入外部 Agent 或與 Claude Code 整合 Agent 能力的開發者
> 版本：v1.0 (2026-02-24)

---

## 1. A2A 協議概覽

**Agent-to-Agent Protocol (A2A)** 是 Google 於 2025 年發布的開放協議，用於 AI Agent 之間的任務委派與協作。

### 核心概念

| 概念 | 說明 |
|:---|:---|
| **Agent Card** | Agent 的自我描述，透過 `GET /.well-known/agent.json` 暴露 |
| **Skill** | Agent 提供的具體能力（如「股票查詢」、「技術分析」） |
| **Task** | 一次任務執行，有完整的生命週期狀態機 |
| **Artifact** | 任務產出的結果（文字、圖片等） |

### Task 狀態機

```
submitted → working → completed
                   → failed
                   → canceled
              ↓
        input-required → working（收到補充資訊後）
```

### 通訊協議

- **JSON-RPC 2.0** 格式的 HTTP 請求
- **SSE（Server-Sent Events）** 用於串流任務結果
- 可選的 **Bearer Token** 認證

### A2A vs MCP 差異

| 面向 | MCP | A2A |
|:---|:---|:---|
| 定位 | 工具提供者（被動） | 自主代理人（主動） |
| 通訊 | Tool call → Result | Task 委派 → 自主執行 |
| 狀態 | 無狀態（每次呼叫獨立） | 有狀態（Task 生命週期） |
| 能力描述 | Tool + JSON Schema | Agent Card + Skills |
| 串流 | 無原生支援 | SSE 原生支援 |
| 適用場景 | 資料查詢、API 呼叫 | 複雜分析、多步驟任務 |

---

## 2. 專案現有架構

### 2.1 A2AClientManager

**檔案**：`src/core/a2a_client.py`

`A2AClientManager` 實作 `A2AClientProtocol`（定義於 `src/core/protocols.py`），管理所有外部 A2A Agent 連線。

```
A2AClientManager
├── initialize()                    → 啟動所有設定的 Agent 連線
├── list_agents()                   → 列出所有 Agent 及其 Skills
├── send_task(agent, message, meta) → 同步發送任務，等待完成
├── send_task_streaming(agent, msg) → SSE 串流接收任務結果
├── get_task_status(agent, task_id) → 查詢任務狀態
├── cancel_task(agent, task_id)     → 取消進行中的任務
├── add_agent(config)               → 動態新增 Agent
├── remove_agent(name)              → 動態移除 Agent
└── shutdown()                      → 關閉所有連線與子進程
```

### 2.2 連線類型

| 類型 | 說明 | 管理責任 |
|:---|:---|:---|
| **local** | 由平台啟動子進程 | 平台管理進程生命週期 |
| **remote** | 連接已在運行的外部 HTTP 端點 | 外部自行管理 |

**連線建立流程**：

```
_connect_agent(config)
  │
  ├── local: asyncio.create_subprocess_exec(command, args)
  │          → await sleep(1.0)  ← 等待 Server 啟動
  │          → url = http://localhost:{port}
  │
  └── remote: url = config.url
  │
  └── _fetch_agent_card(url)  ← GET /.well-known/agent.json
      → 儲存為 _A2AAgentConnection(name, url, card, process, auth_token)
```

### 2.3 設定檔格式

**檔案**：`config/a2a_agents.yaml`

```yaml
agents:
  # local — 平台管理子進程
  - name: "stock-analyst"
    type: "local"
    command: "python"
    args: ["packages/stock-analyst/server.py"]
    port: 9001
    env:
      PORT: "9001"

  # remote — 外部已運行的 Agent
  - name: "legal-advisor"
    type: "remote"
    url: "https://agents.example.com/legal"
    auth_token: "${LEGAL_AGENT_TOKEN}"
```

### 2.4 Engine 中的路由委派

**檔案**：`src/core/engine.py`

當 Router 判斷請求應委派給外部 Agent 時：

```python
# engine.py 中的處理邏輯（簡化）
if decision.delegate_to_agent and self._a2a_client:
    try:
        result = await self._a2a_client.send_task(
            agent_name=decision.delegate_to_agent,
            message=context.request.query,
        )
        return result["text"]
    except Exception:
        # Fallback: 改用本地 Processor 處理
        ...
```

委派是 **可選且有 fallback** 的 — A2A Agent 不可用時退回本地處理。

### 2.5 初始化流程

```
Engine.initialize()
  │
  ├── ServiceInitializer.initialize_a2a_client()
  │     ├── load_a2a_config("config/a2a_agents.yaml")
  │     ├── A2AClientManager(config)
  │     └── a2a_client.initialize()  ← 逐一連線（fetch Agent Card）
  │
  └── ServiceInitializer.initialize_package_manager(packages_dir, mcp_client, a2a_client)
        └── 掃描 type: a2a-agent 的套件 → add_agent() 動態註冊
```

---

## 3. 如何新增外部 A2A Agent

### 方式 A：YAML 設定檔

編輯 `config/a2a_agents.yaml`：

```yaml
agents:
  # 本機 Agent
  - name: "data-analyst"
    type: "local"
    command: "python"
    args: ["agents/data_analyst/server.py"]
    port: 9002
    env:
      PORT: "9002"
      DB_URL: "${DATABASE_URL}"

  # 遠端 Agent
  - name: "translation-agent"
    type: "remote"
    url: "https://translate.example.com"
    auth_token: "${TRANSLATE_TOKEN}"
```

### 方式 B：packages/ 目錄

```yaml
# packages/data-analyst/package.yaml
id: data-analyst
name: "數據分析師"
version: "1.0.0"
description: "分析數據集並生成洞察報告"
type: a2a-agent            # ← 關鍵欄位
command: python
args: ["server.py"]
port: 9002
env:
  PORT: "9002"
auto_start: true
dependencies:
  - pandas
  - starlette
  - sse-starlette
  - uvicorn
```

### 方式 C：Runtime 動態新增

```python
from src.core.a2a_client import A2AAgentConfig

config = A2AAgentConfig(
    name="dynamic-agent",
    type="remote",
    url="https://agents.example.com/agent",
    auth_token="Bearer xxx",
)
success = await a2a_client.add_agent(config)
```

---

## 4. 如何開發自訂 A2A Agent

### 4.1 以 Stock Analyst 為範例

**檔案**：`packages/stock-analyst/server.py`

A2A Agent 本質上是一個 HTTP Server，需實作以下端點：

| 端點 | 方法 | 用途 |
|:---|:---|:---|
| `/.well-known/agent.json` | GET | 回傳 Agent Card |
| `/tasks/send` | POST | 同步任務執行 |
| `/tasks/sendSubscribe` | POST | SSE 串流任務 |
| `/tasks/get` | POST | 查詢任務狀態 |
| `/tasks/cancel` | POST | 取消任務 |

### 4.2 Agent Card 定義

```python
AGENT_CARD = {
    "name": "stock-analyst",
    "description": "專業股票分析師，可查詢股價、進行技術分析",
    "url": f"http://localhost:{os.environ.get('PORT', '9001')}",
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False},
    "skills": [
        {
            "id": "stock-query",
            "name": "股票查詢",
            "description": "查詢股票即時價格和基本資訊",
            "input_modes": ["text"],
            "output_modes": ["text"],
        },
        # ... 更多 skills
    ],
}
```

### 4.3 同步任務端點

```python
async def tasks_send(request: Request) -> JSONResponse:
    body = await request.json()
    params = body.get("params", body)
    task_id = params.get("id", str(uuid.uuid4()))

    # 從 message.parts 取出文字
    message_parts = params.get("message", {}).get("parts", [])
    text = next(
        (p.get("text", "") for p in message_parts if p.get("type") == "text"),
        ""
    )

    # 處理任務
    try:
        output = await _process_task(text)
        result = {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [{"parts": [{"type": "text", "text": output}]}],
        }
    except Exception as e:
        result = {
            "id": task_id,
            "status": {"state": "failed"},
            "error": str(e),
        }

    return JSONResponse({"jsonrpc": "2.0", "id": body.get("id"), "result": result})
```

### 4.4 SSE 串流端點

```python
async def tasks_send_subscribe(request: Request) -> EventSourceResponse:
    # ... 解析 request ...

    async def event_generator():
        # 1. 發送 working 狀態
        yield {"event": "status", "data": json.dumps({
            "id": task_id, "status": {"state": "working"},
        })}

        # 2. 執行任務並發送結果
        output = await _process_task(text)
        yield {"event": "artifact", "data": json.dumps({
            "id": task_id,
            "artifact": {"parts": [{"type": "text", "text": output}]},
        })}

        # 3. 發送完成狀態
        yield {"event": "status", "data": json.dumps({
            "id": task_id, "status": {"state": "completed"},
        })}

    return EventSourceResponse(event_generator())
```

### 4.5 建議使用的技術棧

```
Starlette      — 輕量 ASGI 框架（路由 + 請求處理）
sse-starlette  — SSE 支援（EventSourceResponse）
uvicorn        — ASGI Server
pydantic       — 資料模型驗證（可選）
```

### 4.6 完整 package.yaml 欄位

```yaml
id: my-agent
name: "我的 Agent"
version: "1.0.0"
description: "Agent 功能描述"
type: a2a-agent          # 套件類型
command: python           # 啟動指令
args: ["server.py"]       # 指令參數
port: 9002                # HTTP 監聽埠
env:
  PORT: "9002"
  API_KEY: "${MY_API_KEY}"
auto_start: false         # 是否隨平台自動啟動
dependencies:
  - starlette
  - sse-starlette
  - uvicorn
tags:
  - analysis
```

---

## 5. Claude Code Agent/Skill 整合可行性分析

### 5.1 Claude Code 的 Sub-agent 機制

Claude Code 內建 **Task tool**，可啟動專門的子代理人（Sub-agent）處理子任務。

**內建 Sub-agent 類型**：

| 類型 | 用途 | 工具存取 |
|:---|:---|:---|
| Explore | 快速探索程式碼庫 | 唯讀（Read, Glob, Grep） |
| Plan | 設計實作方案 | 唯讀 |
| Bash | 執行終端指令 | Bash |
| general-purpose | 複雜多步驟任務 | 全部工具 |

**自訂 Sub-agent**：

可在 `.claude/agents/` 目錄建立自訂 Sub-agent：

```
.claude/agents/
└── research-helper/
    └── SKILL.md
```

```yaml
# .claude/agents/research-helper/SKILL.md
---
name: research-helper
description: 協助進行深度研究，分析搜尋結果並生成報告
model: sonnet
tools: Read, Glob, Grep, Bash, WebSearch, WebFetch
maxTurns: 15
---

你是一個研究助手。當收到研究任務時：
1. 使用 WebSearch 搜尋相關資料
2. 使用 WebFetch 取得完整內容
3. 分析並整理結果
4. 生成結構化報告
```

### 5.2 Claude Code 的 Skill 機制

**Skills** 是可重複使用的指令模板，透過 `/skill-name` 或 Claude 自動觸發。

```
.claude/skills/
└── analyze-code/
    └── SKILL.md
```

```yaml
# .claude/skills/analyze-code/SKILL.md
---
name: analyze-code
description: 分析程式碼品質和安全性。當使用者要求 code review 時使用。
user-invocable: true
allowed-tools: Read, Grep, Glob
---

分析以下程式碼的品質：
1. 安全性問題（OWASP Top 10）
2. 程式碼風格
3. 測試覆蓋率
4. 效能瓶頸
```

**Skills 與 MCP 的關係**：Skills 可以在指令中呼叫 MCP 工具，但兩者是獨立的概念。Skills 是「行為指令」，MCP 是「工具提供者」。

### 5.3 整合路徑分析

#### 路徑一：MCP Server 橋接（推薦）

將專案的工具同時暴露給 QuitCode 後端和 Claude Code：

```
┌─────────────────┐
│ packages/weather │  ← 同一個 MCP Server
│   server.py      │
└────┬────────┬────┘
     │ stdio  │ stdio
     │        │
     ▼        ▼
 QuitCode   Claude Code
 Backend    (.mcp.json)
```

**設定**（`.mcp.json`）：

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["packages/weather/server.py"],
      "env": { "OPENWEATHERMAP_API_KEY": "${OPENWEATHERMAP_API_KEY}" }
    },
    "translator": {
      "command": "python",
      "args": ["packages/translator/server.py"],
      "env": { "OPENAI_API_KEY": "${OPENAI_API_KEY}" }
    }
  }
}
```

#### 路徑二：A2A Agent 包裝為 MCP Server

Claude Code **不直接支援 A2A 協議**。若要讓 Claude Code 使用 A2A Agent 的能力，需要建立一個 MCP Server wrapper：

```python
# packages/stock-analyst-mcp-bridge/server.py
"""將 A2A Agent 包裝為 MCP Server，供 Claude Code 使用"""

import httpx
from mcp.server import Server
from mcp.server.stdio import run_server
from mcp.types import TextContent, Tool

server = Server("stock-analyst-bridge")
A2A_URL = "http://localhost:9001"

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_stock",
            description="分析股票（透過 A2A Agent）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "股票查詢，如：分析 2330"}
                },
                "required": ["query"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # 呼叫 A2A Agent
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{A2A_URL}/tasks/send", json={
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "id": "bridge-call",
            "params": {
                "id": "bridge-call",
                "message": {"role": "user", "parts": [
                    {"type": "text", "text": arguments["query"]}
                ]},
            },
        })
        result = resp.json().get("result", {})
        text = ""
        for artifact in result.get("artifacts", []):
            for part in artifact.get("parts", []):
                if part.get("type") == "text":
                    text += part["text"]

    return [TextContent(type="text", text=text or "No result")]
```

**Claude Code 設定**：

```json
{
  "mcpServers": {
    "stock-analyst": {
      "command": "python",
      "args": ["packages/stock-analyst-mcp-bridge/server.py"]
    }
  }
}
```

#### 路徑三：Claude Code Custom Sub-agent + MCP

建立自訂 Sub-agent，讓它使用 MCP 工具來完成任務：

```yaml
# .claude/agents/stock-researcher/SKILL.md
---
name: stock-researcher
description: 股票研究助手，使用 MCP 工具查詢股票資料並分析
model: sonnet
tools: Read, Bash
maxTurns: 10
---

你是股票研究助手。使用可用的 MCP 工具來：
1. 查詢股票即時價格（analyze_stock 工具）
2. 分析技術指標
3. 提供投資建議（附免責聲明）

每次分析都應包含：
- 基本面資料
- 技術面指標（MA、RSI）
- 風險提示
```

### 5.4 整合方案對比

| 方案 | 複雜度 | 即時性 | Claude Code 支援 | 適用場景 |
|:---|:---:|:---:|:---:|:---|
| MCP Server 直接共用 | 低 | 高 | 原生 | 簡單工具（查詢、翻譯） |
| A2A → MCP Bridge | 中 | 中 | 需 wrapper | 已有 A2A Agent，需給 Claude Code 用 |
| Custom Sub-agent + MCP | 低 | 高 | 原生 | 需要 Claude Code 自主決策 |
| Custom Skill | 最低 | 高 | 原生 | 固定工作流程（如 code review） |

### 5.5 限制與不可行之處

| 限制 | 說明 |
|:---|:---|
| Claude Code 不支援 A2A | 無法直接在 `.claude/` 設定 A2A Agent，必須透過 MCP Bridge |
| Sub-agent 不可外部化 | Claude Code 的 Sub-agent 是內部機制，無法被外部系統呼叫 |
| Skill 不是服務 | Skill 只是提示模板，不是獨立運行的服務 |
| stdio 不共享狀態 | 每個 Client 啟動獨立進程，跨 Client 狀態不共享 |
| 無雙向通訊 | Claude Code 只能呼叫 MCP Tool，不能被 MCP Server 主動推送 |

### 5.6 建議整合策略

```
                        ┌──────────────────────────────┐
                        │       packages/ 目錄          │
                        │                              │
                        │  weather/     ← MCP Server   │
                        │  translator/  ← MCP Server   │
                        │  stock-analyst/ ← A2A Agent  │
                        │  stock-mcp-bridge/ ← Bridge  │◄─ 新增
                        └──────┬───────────┬───────────┘
                               │           │
                    ┌──────────▼──┐  ┌─────▼──────────┐
                    │  QuitCode   │  │  Claude Code    │
                    │  Backend    │  │                 │
                    │             │  │  .mcp.json:     │
                    │  mcp_client │  │   weather ✓     │
                    │  a2a_client │  │   translator ✓  │
                    │             │  │   stock-bridge ✓│
                    │             │  │                 │
                    │             │  │  .claude/agents/ │
                    │             │  │   研究助手 ✓     │
                    │             │  │                 │
                    │             │  │  .claude/skills/ │
                    │             │  │   分析指令 ✓     │
                    └─────────────┘  └─────────────────┘
```

**總結**：
- **MCP Server** → 直接共用，零額外成本
- **A2A Agent** → 需建立 MCP Bridge wrapper 才能給 Claude Code 用
- **Claude Code Sub-agent** → 可搭配 MCP 工具使用，但無法被外部系統調用
- **Claude Code Skill** → 適合定義固定工作流程，可引用 MCP 工具
