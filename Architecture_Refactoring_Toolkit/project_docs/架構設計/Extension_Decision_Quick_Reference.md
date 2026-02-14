# Extension Decision Quick Reference

---

**Document Version:** `v1.0`
**Last Updated:** `2026-02-13`
**Parent Document:** `Extension_Architecture_MCP_A2A_Plugin.md`

---

## One-Line Summary

> **Service** = 核心能力（心臟），**MCP** = 使用工具（手），**A2A** = 與人合作（對話），**Plugin** = 包裝盒（不是協議）

---

## Decision Tree (Quick)

```
新功能？
  │
  ├─ 移除它核心會壞嗎？ → YES → Internal Service
  │                      → NO  ↓
  ├─ 確定性操作？        → YES → MCP Server
  │  (輸入→輸出)         → NO  ↓
  ├─ 需要推理/多輪？     → YES → A2A Agent
  │                      → NO  ↓
  └─ 平台事件反應？      → YES → Internal Hook
                         → NO  → 可能不需要
```

---

## Scenario → Solution Map

| 我要... | 用什麼 | 範例 |
|:---|:---|:---|
| 加一個 LLM provider | Internal Service | `services/llm/deepseek_client.py` |
| 換向量 DB 後端 | Service + MCP Protocol | Qdrant → Pinecone |
| 接資料庫查詢 | MCP Server | `@modelcontextprotocol/server-postgres` |
| 接 Slack/Discord | MCP Server | `mcp-server-slack` |
| 做翻譯 | MCP Server | 確定性 tool |
| 查天氣 | MCP Server | 確定性 tool |
| 做股票分析 | A2A Agent | 需要推理、多步驟 |
| 做 Code Review | A2A Agent | 需要理解上下文 |
| 記 audit log | Internal Hook | 不需要外部協議 |
| 讓使用者安裝擴展 | Package Manager | 裝的是 MCP/A2A |

---

## MCP vs A2A — The Key Distinction

```
MCP:  你的 Agent 是「老闆」，MCP Server 是「工具」
      Agent 說「查天氣」，Server 回「25°C」
      → 確定性、無狀態、主從關係

A2A:  你的 Agent 是「同事」，A2A Agent 也是「同事」
      Agent 說「幫我分析這支股票」
      對方可能說「你要看哪個時間範圍？」（反問）
      → 非確定性、有狀態、對等關係
```

---

## Current Code Mapping

| 現有元件 | 現在是 | 應該演進成 |
|:---|:---|:---|
| `services/llm/` | Internal Service | 不變 |
| `services/knowledge/` | Service + MCPServiceProtocol | 不變（已正確） |
| `services/search/` | Internal Service | 不變 |
| `services/sandbox/` | Internal Service | 不變 |
| `plugins/weather-tool/` | 自訂 ToolPlugin | MCP Server (package) |
| `plugins/example-translator/` | 自訂 ToolPlugin | MCP Server (package) |
| `plugins/stock-analyst/` | 自訂 AgentPlugin | A2A Agent (package) |

---

## Industry Trends (2024-2026)

```
2023: ChatGPT Plugins（自訂格式）       → 失敗，已廢棄
2024: Anthropic MCP（開放標準）          → 被 Claude/Cursor/Windsurf 採用
2025: Google A2A（開放標準）             → Agent 互通的標準
2025: ChatGPT 支援 MCP                  → 標準勝過自訂

結論：自訂 Plugin 格式是死路，擁抱 MCP + A2A 標準
```
