# 外部 MCP Server 整合說明書

> 適用對象：需要在 QuitCode 後端平台接入外部工具的開發者
> 版本：v1.0 (2026-02-24)

---

## 1. MCP 協議概覽

**Model Context Protocol (MCP)** 是由 Anthropic 主導的開放協議，用於讓 AI 應用程式存取外部工具（Tools）和資源（Resources）。

### 核心概念

| 概念 | 說明 |
|:---|:---|
| **Server** | 提供工具和資源的服務端（如天氣 API、資料庫查詢） |
| **Client** | 消費工具的客戶端（如我們的 QuitCode 後端） |
| **Tool** | 一個可被呼叫的函式（名稱 + 描述 + JSON Schema 輸入） |
| **Resource** | 一個可被讀取的資料來源（URI + MIME type） |
| **Session** | Client 與 Server 之間的有狀態連線 |

### Transport 機制

| Transport | 通訊方式 | 適用場景 | 延遲 |
|:---|:---|:---|:---|
| **stdio** | 標準輸入/輸出 | 本機子進程，開發用 | 低（無網路） |
| **SSE** | HTTP + Server-Sent Events | 遠端服務，生產環境 | 中（需網路） |

```
stdio 模式：
  Client ──stdin──> Server Process
  Client <──stdout── Server Process

SSE 模式：
  Client ──HTTP POST──> Remote Server
  Client <──SSE stream── Remote Server
```

---

## 2. 專案現有架構

### 2.1 MCPClientManager

**檔案**：`src/core/mcp_client.py`

`MCPClientManager` 實作 `MCPClientProtocol`（定義於 `src/core/protocols.py`），負責管理所有外部 MCP Server 連線。

```
MCPClientManager
├── initialize()           → 啟動所有設定的 Server 連線
├── list_tools()           → 聚合所有 Server 的 Tools（含 server_name 標記）
├── call_tool(server, tool, args) → 呼叫指定 Server 的指定 Tool
├── list_resources()       → 聚合所有 Server 的 Resources
├── read_resource(server, uri)    → 讀取指定 Resource
├── add_server(config)     → 動態新增 Server（Runtime）
├── remove_server(name)    → 動態移除 Server
└── shutdown()             → 關閉所有連線
```

**內部連線管理**：

- 每個 Server 封裝為 `_MCPServerConnection`（session + tools + resources）
- 使用 MCP Python SDK 的 `ClientSession` 進行通訊
- `AsyncExitStack` 管理所有連線的生命週期

### 2.2 設定檔格式

**檔案**：`config/mcp_servers.yaml`

```yaml
servers:
  # stdio 模式 — 本機子進程
  - name: "weather"
    transport: "stdio"
    command: "python"
    args: ["packages/weather/server.py"]
    env:
      OPENWEATHERMAP_API_KEY: "${OPENWEATHERMAP_API_KEY}"

  # SSE 模式 — 遠端服務
  - name: "remote-db"
    transport: "sse"
    url: "https://mcp.example.com/database"
    headers:
      Authorization: "Bearer ${MCP_DB_TOKEN}"
```

**環境變數展開**：設定值中的 `${VAR_NAME}` 會自動替換為對應環境變數（由 `_expand_env_vars()` 處理）。

### 2.3 PackageManager 自動掃描

**檔案**：`src/core/package_manager.py`

`PackageManager` 掃描 `packages/` 目錄下的 `package.yaml`，將 `type: mcp-server` 的套件自動轉換為 `MCPServerConfig` 並透過 `MCPClientManager.add_server()` 動態註冊。

```
packages/
├── weather/
│   ├── package.yaml    ← type: mcp-server
│   └── server.py
├── translator/
│   ├── package.yaml    ← type: mcp-server
│   └── server.py
└── stock-analyst/
    ├── package.yaml    ← type: a2a-agent（非 MCP）
    └── server.py
```

### 2.4 初始化流程

**檔案**：`src/core/service_initializer.py` → `src/core/engine.py`

```
Engine.initialize()
  │
  ├── ServiceInitializer.initialize_all()
  │     └── search / knowledge / sandbox 服務
  │
  ├── ServiceInitializer.initialize_mcp_client()
  │     ├── load_mcp_config("config/mcp_servers.yaml")
  │     ├── MCPClientManager(config)
  │     └── mcp_client.initialize()  ← 逐一連線所有 Server
  │
  └── ServiceInitializer.initialize_package_manager(packages_dir, mcp_client, ...)
        ├── PackageManager.scan_packages()
        └── PackageManager.start_all()  ← auto_start=true 的套件自動啟動並註冊
```

初始化採 **graceful degradation**：任何 Server 連線失敗只記錄 warning，不影響其他服務。

---

## 3. 如何新增外部 MCP Server

### 方式 A：YAML 設定檔（推薦）

編輯 `config/mcp_servers.yaml`，新增 Server 項目：

```yaml
servers:
  # 範例：連接 Filesystem MCP Server（npm 套件）
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/safe"]

  # 範例：連接遠端 Database MCP Server
  - name: "remote-db"
    transport: "sse"
    url: "https://mcp.example.com/database"
    headers:
      Authorization: "Bearer ${MCP_DB_TOKEN}"
```

重啟應用後自動生效。

### 方式 B：packages/ 目錄（自訂套件）

在 `packages/` 建立目錄，包含 `package.yaml` 和 `server.py`：

```yaml
# packages/my-tool/package.yaml
id: my-tool
name: "我的工具"
version: "1.0.0"
description: "自訂 MCP Server"
type: mcp-server          # ← 關鍵欄位
transport: stdio
command: python
args: ["server.py"]
env:
  MY_API_KEY: "${MY_API_KEY}"
auto_start: true           # ← 應用啟動時自動連線
dependencies:
  - httpx
  - mcp
```

`PackageManager` 會在啟動時自動掃描並註冊。

### 方式 C：Runtime 動態新增

透過程式碼在執行期新增 Server：

```python
from src.core.mcp_client import MCPServerConfig

config = MCPServerConfig(
    name="dynamic-server",
    transport="stdio",
    command="python",
    args=["path/to/server.py"],
)
success = await mcp_client.add_server(config)
```

也可透過 API 端點操作（`src/api/routes.py` 提供 `/mcp/servers` 和 `/mcp/tools` 端點）。

---

## 4. 如何開發自訂 MCP Server

### 4.1 以 Weather Server 為範例

**檔案**：`packages/weather/server.py`

核心結構只有三步：

```python
from mcp.server import Server
from mcp.server.stdio import run_server
from mcp.types import TextContent, Tool

# Step 1: 建立 Server 實例
server = Server("weather")

# Step 2: 註冊 Tool 清單
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="weather_current",
            description="查詢城市目前天氣",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名稱"}
                },
                "required": ["city"],
            },
        ),
    ]

# Step 3: 實作 Tool 呼叫邏輯
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "weather_current":
        result = await _get_current_weather(arguments["city"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

# 啟動
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server(server))
```

### 4.2 MCP Server 開發要點

| 要點 | 說明 |
|:---|:---|
| SDK 版本 | `mcp>=1.0.0`（Anthropic 官方 Python SDK） |
| Tool inputSchema | 使用標準 JSON Schema 定義參數 |
| 回傳格式 | `list[TextContent]`，每項含 `type="text"` 和 `text` |
| 錯誤處理 | 在 `call_tool` 內部 try/except，回傳 error JSON |
| 環境變數 | 透過 `os.environ.get()` 取得，在 `package.yaml` 的 `env` 中宣告 |
| 測試方式 | 直接 `python server.py` 後用 MCP Inspector 測試 |

### 4.3 完整 package.yaml 欄位

```yaml
id: my-tool              # 唯一識別碼
name: "顯示名稱"          # 人類可讀名稱
version: "1.0.0"         # 語意版本號
description: "描述"       # 功能說明
type: mcp-server         # 套件類型（mcp-server | a2a-agent）
transport: stdio         # Transport（stdio | sse）
command: python          # 啟動指令
args: ["server.py"]      # 指令參數
env:                     # 環境變數
  KEY: "${ENV_VAR}"
auto_start: false        # 是否隨平台自動啟動
dependencies:            # Python 套件依賴
  - httpx
  - mcp
tags:                    # 分類標籤
  - utility
```

---

## 5. Claude Code 端整合

### 5.1 Claude Code 的 MCP 設定

Claude Code 自身也支援 MCP Server，設定檔為專案根目錄的 `.mcp.json`：

```json
{
  "mcpServers": {
    "server-name": {
      "command": "/path/to/executable",
      "args": ["arg1", "arg2"],
      "env": {
        "API_KEY": "${API_KEY}"
      }
    },
    "remote-server": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${TOKEN}"
      }
    }
  }
}
```

也可透過 CLI 新增：

```bash
# stdio Server
claude mcp add --transport stdio --scope project weather \
  -- python packages/weather/server.py

# HTTP Server
claude mcp add --transport http --scope project remote-api \
  https://api.example.com/mcp
```

### 5.2 讓專案 MCP Server 同時服務兩端

專案 `packages/` 下的 MCP Server 可以同時被 QuitCode 後端和 Claude Code 使用：

```
                    ┌─────────────────────┐
                    │  packages/weather/   │
                    │    server.py         │
                    │  (MCP Server)        │
                    └──────┬──────────────┘
                           │ stdio
              ┌────────────┼────────────┐
              │                         │
    ┌─────────▼──────────┐   ┌─────────▼──────────┐
    │  QuitCode Backend  │   │    Claude Code      │
    │  MCPClientManager  │   │   .mcp.json 設定    │
    │  (config/mcp_      │   │                     │
    │   servers.yaml)    │   │                     │
    └────────────────────┘   └─────────────────────┘
```

**注意**：stdio 模式下每個 Client 會啟動獨立的 Server 子進程，兩端不共享狀態。如需共享，應改用 SSE 模式讓 Server 作為獨立服務運行。

### 5.3 實際設定範例

**QuitCode 端**（`config/mcp_servers.yaml`）：

```yaml
servers:
  - name: "weather"
    transport: "stdio"
    command: "python"
    args: ["packages/weather/server.py"]
    env:
      OPENWEATHERMAP_API_KEY: "${OPENWEATHERMAP_API_KEY}"
```

**Claude Code 端**（`.mcp.json`）：

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["packages/weather/server.py"],
      "env": {
        "OPENWEATHERMAP_API_KEY": "${OPENWEATHERMAP_API_KEY}"
      }
    }
  }
}
```

設定完成後，Claude Code 在對話中即可呼叫 `weather_current` 和 `weather_forecast` 工具。

### 5.4 Claude Code MCP 設定層級

| 層級 | 檔案位置 | 適用範圍 |
|:---|:---|:---|
| 專案 | `.mcp.json`（專案根目錄） | 此專案，可提交至版控 |
| 使用者 | `~/.claude.json` | 所有專案 |
| 系統管理 | `/etc/claude-code/managed-mcp.json` | 組織強制設定 |

---

## 6. 常見整合模式

### 模式一：本機開發工具

```yaml
# 為 Claude Code 提供專案特定的查詢工具
# .mcp.json
{
  "mcpServers": {
    "project-db": {
      "command": "python",
      "args": ["tools/db_query_server.py"],
      "env": { "DATABASE_URL": "${DATABASE_URL}" }
    }
  }
}
```

### 模式二：共用基礎設施

```yaml
# QuitCode + Claude Code 共用同一遠端 MCP Server
# config/mcp_servers.yaml
servers:
  - name: "shared-tools"
    transport: "sse"
    url: "https://internal-mcp.company.com"
    headers:
      Authorization: "Bearer ${MCP_TOKEN}"
```

### 模式三：開發階段專用

```json
// .mcp.json — 只在開發時讓 Claude Code 存取
{
  "mcpServers": {
    "test-fixtures": {
      "command": "python",
      "args": ["tests/fixtures/mcp_server.py"]
    }
  }
}
```
