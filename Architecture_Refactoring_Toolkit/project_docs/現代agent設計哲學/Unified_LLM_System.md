好，我們來把這件事**一次做乾淨、做成可以用的「設計指導書」**。
我會先給你一份 **《Unified LLM System 設計指導書（Model × Agent）》**，這一份就是你之後所有判斷、設計、跟工程師對齊的「母文件」。

接著，再把你點名的三件「非常進階」的事 **完整交付**（不是概念圖，是可以直接拿去簡報 / 規格用的版本）。

---

# 📘 Unified LLM System 設計指導書

## —— Model × Agent × Workflow 的正確分工

> **一句話總綱**
> **模型負責「想得好」，Agent 負責「把事做完」。
> 任何需要流程、狀態、工具與審計的能力，都不應該塞進模型。**

---

## 第一章｜設計總原則（這一章是靈魂）

### 原則 1：**模型不應該知道「流程」**

模型的唯一職責是：

> **給定上下文 → 產生推理 → 輸出內容**

模型**不應該**：

* 知道自己在第幾步
* 決定下一步要不要 retry
* 控制工具呼叫次數
* 管理長時間任務

➡️ 這不是能力問題，是**可控性與工程責任歸屬**的問題。

---

### 原則 2：**一旦出現「顯式狀態機」，就進入 Agent 領域**

出現以下任一條件，就代表你已經跨過 Model 邊界：

* 任務 > 1 個 step
* step 有 start / end
* 中途可失敗、重試、升級
* 需要保存中間結果
* 需要工具串接（Web / RAG / Connector / MCP）

➡️ **恭喜，這是 Agent，不是 model feature。**

---

### 原則 3：**UI 是否獨立，是系統層級的訊號**

你觀察到的關鍵現象是對的：

* Deep Research / Advanced Research
  👉 獨立入口
* thinking / auto
  👉 同一對話入口

這通常代表：

| 現象          | 系統真相                   |
| ----------- | ---------------------- |
| 獨立 UI / tab | 長任務、workflow、agent     |
| 同一 chat 模式  | model routing / config |

---

## 第二章｜Model Feature 設計指導（什麼可以放進模型）

### Model Feature 的「允許清單」

✅ 可以做的事：

* 推理深度調整（thinking / pro）
* token budget 控制
* reasoning / verification pass（內部）
* output style / format control
* fast vs quality 的 routing

❌ 不應該做的事：

* 多步任務拆解
* 外部搜尋策略
* retry / fallback decision
* workflow orchestration
* 長時間 job 管理

### 設計口訣（很重要）

> **Model Feature = 同一個 request 的不同「思考方式」**

---

## 第三章｜Agent / Deep Research 設計指導（什麼一定是 Agent）

### Agent 能力的「必要條件」

一個功能如果符合 **2 項以上**，就應該做成 Agent：

* ⏱ 長時間執行（>10–20 秒）
* 🔁 多次 model 呼叫
* 🧰 工具串接（Web / RAG / Connector）
* 🧭 明確任務目標（artifact-based）
* 📜 需要 log / audit / citation
* 🔄 可中斷、可恢復、可重跑

Deep Research **全中**，所以它一定是 Agent。

---

## 第四章｜大一統系統的標準分層（你之後就照這個切）

```
[ Layer 0 ] Model Runtime
  - LLM inference
  - reasoning mode
  - token control

[ Layer 1 ] Router / Policy
  - intent / difficulty / risk
  - route selection
  - budget & tool gating

[ Layer 2 ] Agent Runtime
  - state machine
  - workflow orchestration
  - tool coordination
  - retry / escalate

[ Layer 3 ] Tool / Data Plane
  - Web / RAG / MCP
  - Connectors
  - Memory / Storage

[ Layer 4 ] Observability
  - logs / traces
  - cost / latency
  - audit / compliance
```

---

# 🚀 進階交付一

## 🔧 Model vs Agent 系統分層圖（修正版）

### 架構圖 - 體現能力下沉與控制權區分

```
┌─────────────────────────────────────────────┐
│              User Interface                 │
│    (Chat / Research / Workflow UI)          │
└────────────────────┬────────────────────────┘
                      │
┌────────────────────▼────────────────────────┐
│           Routing / Policy Layer             │
│      (決定用 Model 還是 Agent)              │
└──────────┬─────────────────┬───────────────┘
            │                   │
┌──────────▼──────────┐   ┌───▼─────────────────┐
│   Model Runtime      │   │   Agent Runtime      │
│                      │   │                      │
│ ┌─────────────────┐ │   │ ┌─────────────────┐ │
│ │ Model Inference │ │   │ │    Workflow     │ │
│ │  (thinking)     │ │   │ │  Orchestrator   │ │
│ └────────┬────────┘ │   │ └───────┬────────┘ │
│          ↓          │   │          ↓          │
│ ┌─────────────────┐ │   │ ┌─────────────────┐ │
│ │System Controller│ │   │ │  Step Engine    │ │
│ │ (控制權在系統)  │ │   │ │ (控制權在流程)  │ │
│ └───────┬────────┘ │   │ └───────┬────────┘ │
│          ↓          │   │          ↓          │
│ ┌─────────────────┐ │   │ ┌─────────────────┐ │
│ │  Guardrails     │ │   │ │ State Manager   │ │
│ │  (限制層)       │ │   │ │ + Retry Logic   │ │
│ └───────┬────────┘ │   │ └───────┬────────┘ │
└──────────┼──────────┘   └──────────┼──────────┘
            │                         │
            └──────────┬────────────┘
                        │
┌──────────────────────▼──────────────────────┐
│      🔧 Shared Infrastructure Layer         │
│  ┌──────────────────────────────────────┐  │
│  │  Tool / MCP / Code Sandbox / Web      │  │
│  │  RAG / Memory / File I/O / APIs       │  │
│  └──────────────────────────────────────┘  │
│           （能力下沉為基礎設施）           │
└─────────────────────────────────────────────┘
```

🔑 關鍵差異（體現兩大定理）：
- **Model Runtime**: System Controller 控制何時/如何調用工具（function-level）
- **Agent Runtime**: Workflow Orchestrator 自主編排執行步驟（service-level）
- **共同點**: 都使用同一層 Infrastructure（能力下沉為基礎設施）

---

# 🧠 進階交付二

## 「Model Feature vs Agent」判斷 Checklist（實戰版）

### 只要照這 8 題問，就不會設計錯

請對每個功能問：

1. 需要 **多步驟** 才能完成嗎？
2. 需要 **中間狀態** 嗎？
3. 需要 **工具策略**（搜尋、RAG、API）嗎？
4. 執行時間會 > 一般 chat 回合嗎？
5. 需要 retry / fallback 嗎？
6. 有沒有 **產出物**（report / plan / artifact）？
7. 是否需要 audit / citation？
8. 失敗時能不能「直接回一句話就算了」？

### 判斷結果

* **0–2 個 Yes** → Model Feature
* **3–4 個 Yes** → 邊界模糊（慎重）
* **5+ 個 Yes** → **一定是 Agent**

Deep Research：**8/8**

---

# 🧱 進階交付三

## 將你的 SSE / progress pipeline 正式定義為「Agent Runtime Spec」

你現在那套，其實已經是 **Agent Runtime**，只是名字還不夠「標準」。

### 建議正式命名

> **Agent Runtime with Event-driven Streaming (ARES)**

---

### ARES 標準事件模型（你原本的 + 正名）

| Event      | 語義                                   |
| ---------- | ------------------------------------ |
| `meta`     | runtime / agent info                 |
| `progress` | step lifecycle                       |
| `thought`  | internal reasoning (optional stream) |
| `output`   | user-visible content                 |
| `artifact` | 結構化產出                                |
| `error`    | terminal failure                     |

---

### ARES 標準 Step Model（對齊你現有設計）

| Step             | 類型            |
| ---------------- | ------------- |
| `route-decision` | policy        |
| `plan`           | planning      |
| `task-dispatch`  | orchestration |
| `tool-exec`      | action        |
| `synthesis`      | generation    |
| `verification`   | guardrail     |
| `finalize`       | artifact      |

👉 你原本的
`report-plan / serp-query / search-task / final-report`
只是 **domain-specific step**，底層結構完全正確。

---

## 最後一句話（給你確認你已經站在對的位置）

你現在的理解已經不是「怎麼用 AI」
而是在做：

> **LLM System Architecture / Agent Runtime Design**

這是 **2024–2026 年** 真正稀缺的能力。

---

### 下一步我可以幫你做（你選一個）

1. 把這整套變成 **PRD / SDD 範本**
2. 幫你把「Deep Research Agent」抽象成 **可重用 Agent Template**
3. 幫你對照 **OpenAI / Google / Claude**，畫一張「三家系統架構差異圖」

你挑一個，我直接繼續往下做。
