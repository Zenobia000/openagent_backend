# 與其他框架的比較

> **最後更新**：2026-02-24
> **比較框架**：LangChain、Haystack、AutoGPT、LlamaIndex

QuitCode Platform 與其他 AI 框架的比較。

---

## 🔍 快速比較矩陣

| 功能 | QuitCode | LangChain | Haystack | AutoGPT | LlamaIndex |
|------|----------|-----------|----------|---------|------------|
| **認知路由** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **多供應商備援** | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ |
| **生產 API** | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ |
| **回應快取** | ✅ | ⚠️ | ❌ | ❌ | ❌ |
| **程式碼執行** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **MCP/A2A 擴展** | ✅ | ❌ | ❌ | ❌ | ❌ |

圖例：✅ 內建 | ⚠️ 部分/手動 | ❌ 不支援

---

## vs. LangChain

### 功能比較

| 功能 | QuitCode Platform | LangChain |
|------|------------------|-----------|
| **認知路由** | ✅ 內建 System 1/2/Agent | ❌ 手動建構鏈 |
| **多供應商備援** | ✅ 自動重試 | ⚠️ 需手動重試邏輯 |
| **生產 API** | ✅ FastAPI + 認證 + 串流 | ⚠️ 需搭配 LangServe 部署 |
| **結構化例外** | ✅ 層級 + 可重試標記 | ⚠️ 改善中 |
| **Feature Flags** | ✅ YAML 驅動部署 | ❌ 需程式碼變更 |
| **回應快取** | ✅ 內建 System 1 | ⚠️ 有快取支援，需設定 |
| **MCP/A2A** | ✅ 標準化協定 | ❌ 自訂整合 |

### 何時使用 LangChain

**選擇 LangChain 如果：**
- ✅ 你需要大量預建鏈與模板
- ✅ 你想要龐大的整合生態系
- ✅ 你習慣自行建構生產基礎設施
- ✅ 你需要 LangServe 部署

**選擇 QuitCode 如果：**
- ✅ 你需要開箱即用的生產 API
- ✅ 你想要自動複雜度路由
- ✅ 你需要透過快取最佳化成本
- ✅ 你需要 MCP/A2A 標準化擴展

### 程式碼比較

**LangChain**：
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
prompt = ChatPromptTemplate.from_template("{query}")
chain = prompt | llm

# 無自動路由
result = chain.invoke({"query": query})
```

**QuitCode**（自動路由）：
```python
from core.engine import RefactoredEngine
from core.models_v2 import Request

engine = RefactoredEngine(llm_client=llm)

# 自動路由：簡單 → System 1，複雜 → System 2
result = engine.process(Request(query=query, mode="auto"))
# 自動多供應商備援 + 自動快取 + 自動指標追蹤
```

---

## vs. Haystack

### 功能比較

| 功能 | QuitCode Platform | Haystack |
|------|------------------|----------|
| **認知層級** | ✅ 三層（System 1/2/Agent） | ❌ 單一管線模型 |
| **執行時分派** | ✅ 雙（有狀態 + 無狀態） | ❌ 僅無狀態 |
| **程式碼執行** | ✅ Docker 沙箱 + 安全 | ❌ 不支援 |
| **RAG 焦點** | ⚠️ 多功能之一 | ✅ 主要焦點 |
| **搜尋整合** | ✅ 多引擎 | ✅ 廣泛 |

### 何時使用 Haystack

**選擇 Haystack 如果：**
- ✅ 你主要建構 RAG/搜尋應用程式
- ✅ 你需要廣泛的文件處理管線
- ✅ 你習慣管線式架構

**選擇 QuitCode 如果：**
- ✅ 你需要不僅是 RAG（程式碼執行、研究等）
- ✅ 你想要自動任務複雜度路由
- ✅ 你需要有狀態代理工作流程

---

## vs. AutoGPT

### 功能比較

| 功能 | QuitCode Platform | AutoGPT |
|------|------------------|---------|
| **智慧路由** | ✅ 複雜度分析器 | ❌ 永遠自主（慢） |
| **回應快取** | ✅ System 1 快取 | ❌ 無快取 |
| **生產 API** | ✅ FastAPI + JWT | ❌ 僅 CLI |
| **速度** | ✅ 快速（System 1） | ❌ 慢（永遠多步驟） |
| **自主性** | ⚠️ 僅 Agent 模式 | ✅ 完全自主 |

### 何時使用 AutoGPT

**選擇 AutoGPT 如果：**
- ✅ 你需要完全自主的代理處理*所有*任務
- ✅ 你不在意較慢的回應時間
- ✅ 成本不是主要考量

**選擇 QuitCode 如果：**
- ✅ 你想要最佳化成本
- ✅ 你需要簡單查詢的快速回應
- ✅ 你需要生產 API
- ✅ 你需要任務適當的處理（不是所有事都需要自主性）

---

## vs. LlamaIndex

### 功能比較

| 功能 | QuitCode Platform | LlamaIndex |
|------|------------------|------------|
| **資料索引** | ⚠️ 基本（Qdrant） | ✅ 廣泛 |
| **查詢引擎** | ✅ 多模式 | ⚠️ RAG 焦點 |
| **認知路由** | ✅ System 1/2/Agent | ❌ 無路由 |
| **程式碼執行** | ✅ 沙箱 | ❌ 否 |

### 何時使用 LlamaIndex

**選擇 LlamaIndex 如果：**
- ✅ 你建構資料為中心的應用程式
- ✅ 你需要進階索引策略
- ✅ RAG 是你的主要用途

**選擇 QuitCode 如果：**
- ✅ 你需要不僅是資料查詢
- ✅ 你想要自動任務路由
- ✅ 你需要生產基礎設施

---

## 架構哲學比較

### LangChain：鏈式

```
查詢 → 鏈 1 → 鏈 2 → 鏈 3 → 結果
```

**優點**：靈活、可組合
**缺點**：手動建構，無自動最佳化

### Haystack：管線式

```
查詢 → 管線 → [節點1 → 節點2 → 節點3] → 結果
```

**優點**：結構化、可重現
**缺點**：剛性，需前期設計

### AutoGPT：完全自主

```
查詢 → [代理迴圈：規劃 → 執行 → 反思] → 結果
```

**優點**：最少設定，自主
**缺點**：慢、昂貴、簡單任務過度使用

### QuitCode：認知路由

```
查詢 → Router → {
  System 1（快速、快取）或
  System 2（分析）或
  Agent（自主）
} → 結果
```

**優點**：自動最佳化、成本效益、生產就緒
**缺點**：比自訂建構鏈靈活度較低

---

## 使用情境決策矩陣

| 你的需求 | 推薦框架 |
|---------|---------|
| **僅 RAG 應用程式** | Haystack 或 LlamaIndex |
| **最大靈活性** | LangChain |
| **完全自主（成本不是考量）** | AutoGPT |
| **生產 API + 認證 + 串流** | **QuitCode** |
| **成本最佳化** | **QuitCode** |
| **多模態（聊天 + 程式碼 + 研究）** | **QuitCode** |
| **MCP/A2A 標準化擴展** | **QuitCode** |

---

## 問題？

- [GitHub Discussions](https://github.com/Zenobia000/openagent_backend/discussions)

---

**返回**：[README](../README.md) | [文件](../README.md#-文件)
