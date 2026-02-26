# QuitCode Platform v2.0 高階架構藍圖

**版本**: `v1.0`
**日期**: `2026-02-10`
**核心理念**: `Process Pipeline + Runtime 分層 + 控制權明確化`

---

## 一、架構設計核心問題

### 1.1 當前架構的核心優勢與挑戰

**✅ 現有優勢**：
- **策略模式成熟**：ProcessorFactory + BaseProcessor 提供良好的擴展性
- **服務解耦完整**：Services 層已經實現良好的邊界隔離
- **無狀態設計**：Engine-Processor 無狀態，易於水平擴展

**⚠️ 核心挑戰**：
- **控制權不明確**：所有 Processor 都在同一層級，無法區分系統控制 vs 工作流控制
- **缺乏 Runtime 概念**：沒有區分 Function-level vs Service-level 執行
- **Pipeline 過於簡單**：Request → Engine → Processor → Service 缺乏中間層次

### 1.2 兩大定理的架構啟示

基於 LLM System Design Principles：

```
第一定理：能力下沉 ≠ 控制權轉移
→ 架構啟示：Services 層應成為 Infrastructure Layer，而非被某個 Processor 獨佔

第二定理：Runtime 決定架構
→ 架構啟示：需要區分 Model Runtime（系統控制）和 Agent Runtime（工作流控制）
```

---

## 二、高階架構設計方案

### 2.1 三層 Runtime 架構模型

```
┌─────────────────────────────────────────────────────────┐
│                    用戶交互層                            │
│              CLI / API / WebSocket                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 路由決策層 (Router Layer)                │
├─────────────────────────────────────────────────────────┤
│  • Mode Selector：用戶選擇或 Auto 模式                   │
│  • Complexity Analyzer：分析請求複雜度                   │
│  • Runtime Dispatcher：分發到合適的 Runtime              │
└────────────────┬──────────────────┬────────────────────┘
                 │                  │
                 ▼                  ▼
┌────────────────────────┐ ┌────────────────────────┐
│    Model Runtime       │ │    Agent Runtime       │
├────────────────────────┤ ├────────────────────────┤
│ • Quick Processor      │ │ • Research Agent       │
│ • Thinking Processor   │ │ • Code Agent          │
│ • Chat Processor       │ │ • Analysis Agent      │
├────────────────────────┤ ├────────────────────────┤
│ System Controller      │ │ Workflow Orchestrator  │
│ (系統控制執行)          │ │ (工作流控制執行)        │
└────────────┬───────────┘ └────────────┬───────────┘
             │                           │
             └─────────┬─────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│           Infrastructure Layer (共享基礎設施)             │
├─────────────────────────────────────────────────────────┤
│ • LLM Service      • Knowledge Service                  │
│ • Sandbox Service  • Search Service                     │
│ • Browser Service  • Repository Service                 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Process Pipeline 設計

基於現有的 Engine-Processor 模式，演進為更精細的 Pipeline：

```
                    請求處理管線 (Request Processing Pipeline)
                    ═══════════════════════════════════════

入口階段 (Entry Phase)
│
├─→ [請求接收] → [認證授權] → [請求驗證]
│
▼
路由階段 (Routing Phase)
│
├─→ [模式判斷] → [複雜度分析] → [Runtime 選擇]
│                    │
│                    ├─ Score < 0.3 → Model Runtime
│                    └─ Score >= 0.3 → Agent Runtime
▼
執行階段 (Execution Phase)
│
├─ Model Runtime Pipeline:
│  └─→ [Processor 選擇] → [Context 建立] → [執行控制] → [結果返回]
│
└─ Agent Runtime Pipeline:
   └─→ [Workflow 規劃] → [Step 執行] → [狀態管理] → [Checkpoint] → [結果聚合]
```

---

## 三、架構演進策略

### 3.1 基於現有架構的漸進式演進

```
現有組件 → 演進路徑 → 目標組件
═════════════════════════════════

RefactoredEngine
    ↓ 擴展
    ├─ Router Component (新增)
    └─ Runtime Manager (新增)

ProcessorFactory
    ↓ 分化
    ├─ Model Runtime Factory
    └─ Agent Runtime Factory

BaseProcessor
    ↓ 繼承樹調整
    ├─ ModelProcessor (Quick, Thinking, Chat)
    └─ AgentProcessor (Research, Code, Analysis)

ProcessingContext
    ↓ 分層
    ├─ ExecutionContext (無狀態，Model Runtime 用)
    └─ WorkflowState (有狀態，Agent Runtime 用)

Services 層
    ↓ 統一化
    Infrastructure Layer (所有 Runtime 共享)
```

### 3.2 控制權分配設計

```
控制權矩陣 (Control Matrix)
═══════════════════════════

              Model Runtime    Agent Runtime
              ────────────    ──────────────
工具調用權      系統決定         工作流決定
執行時長       < 30秒          分鐘級
重試策略       無/簡單          智能重試
狀態管理       無狀態           有狀態持久化
中斷控制       不可中斷         可中斷/恢復
資源限制       嚴格限制         彈性配額
```

---

## 四、關鍵設計決策

### 4.1 為什麼保留 ProcessorFactory 模式？

```
理由：
1. 現有代碼資產保護
   - 已實現的 Processor 可以平滑遷移
   - 團隊熟悉這個模式

2. 符合 SOLID 原則
   - 開閉原則：新增 Processor 不修改現有代碼
   - 單一職責：每個 Processor 專注一個處理模式

演進方案：
ProcessorFactory
    → ModelProcessorFactory + AgentProcessorFactory
    → 各自管理不同 Runtime 的 Processor
```

### 4.2 如何實現 Runtime 分離？

```
步驟：
1. 抽象 Runtime Interface
   - define process()
   - define control_policy()

2. 實現兩個 Runtime
   - ModelRuntime: 封裝現有 Quick/Thinking/Chat Processor
   - AgentRuntime: 新增 Workflow Engine + State Manager

3. Router 層判斷
   - 基於請求特徵選擇 Runtime
   - 用戶可覆蓋自動選擇
```

### 4.3 Infrastructure Layer 如何設計？

```
設計原則：
1. 統一接口
   - 所有 Service 實現相同的基礎接口
   - 支持不同的權限和配額

2. 共享但隔離
   - Runtime 共享 Service 實例
   - 但通過 Context 隔離執行環境

3. 可觀測性
   - 統一的監控和日誌
   - 追蹤不同 Runtime 的使用情況
```

---

## 五、技術實施路線圖

### Phase 1：基礎準備（2週）

```
目標：在不破壞現有功能的前提下，準備架構演進

任務清單：
□ 抽象 Runtime Interface
□ 創建 Router Component（初版）
□ 重構 Services 為 Infrastructure Layer
□ 建立 Runtime 選擇機制
```

### Phase 2：Runtime 分離（3週）

```
目標：實現 Model Runtime 和 Agent Runtime

任務清單：
□ 實現 ModelRuntime
  - 整合 Quick/Thinking/Chat Processor
  - 實現 System Controller

□ 實現 AgentRuntime（基礎版）
  - Workflow Engine
  - State Manager
  - Step Executor
```

### Phase 3：Pipeline 優化（2週）

```
目標：完善處理管線

任務清單：
□ 優化 Router 邏輯
□ 實現複雜度分析器
□ 添加 Pipeline 中間件支持
□ 實現執行監控
```

### Phase 4：生產就緒（2週）

```
目標：確保系統穩定性

任務清單：
□ 性能優化
□ 錯誤處理完善
□ 監控和告警
□ 文檔更新
```

---

## 六、架構評估指標

### 6.1 技術指標

| 指標 | 當前值 | 目標值 | 衡量方法 |
|------|--------|--------|----------|
| 請求處理延遲 | 2-5s | < 2s (Model) / < 5min (Agent) | P95 延遲 |
| 系統吞吐量 | 100 req/s | 500 req/s | 壓測結果 |
| 代碼複雜度 | 中等 | 低 | 圈複雜度 |
| 測試覆蓋率 | 60% | > 80% | 單元測試 |

### 6.2 架構質量指標

| 維度 | 評估標準 | 目標狀態 |
|------|----------|----------|
| 可擴展性 | 新增功能的代碼改動量 | 最小化核心改動 |
| 可維護性 | 問題定位時間 | < 30分鐘 |
| 可測試性 | 模組獨立測試能力 | 100% 模組可獨立測試 |
| 解耦程度 | 模組間依賴 | 單向依賴，無循環 |

---

## 七、風險分析與緩解

### 7.1 技術風險

| 風險項 | 可能性 | 影響 | 緩解策略 |
|--------|--------|------|----------|
| Runtime 分離增加複雜度 | 高 | 中 | 漸進式實施，保留回退方案 |
| 性能下降 | 中 | 高 | 提前性能測試，優化關鍵路徑 |
| 向後兼容性問題 | 低 | 高 | 保持 API 穩定，版本化接口 |

### 7.2 組織風險

| 風險項 | 可能性 | 影響 | 緩解策略 |
|--------|--------|------|----------|
| 團隊學習成本 | 中 | 中 | 充分的文檔和培訓 |
| 開發週期延長 | 中 | 中 | 明確的里程碑和檢查點 |

---

## 八、總結與下一步

### 8.1 架構演進的核心價值

```
1. 控制權明確化
   - Model Runtime：系統控制
   - Agent Runtime：工作流控制

2. 能力下沉
   - Services → Infrastructure Layer
   - 所有 Runtime 共享基礎能力

3. Pipeline 精細化
   - 更清晰的處理階段
   - 更好的可觀測性

4. 漸進式演進
   - 保護現有投資
   - 降低遷移風險
```

### 8.2 立即行動項

```
Week 1-2:
1. 召開架構評審會議
2. 確定技術選型
3. 建立原型驗證
4. 制定詳細計劃

關鍵決策點：
□ 是否採用這個架構方案？
□ 優先實現哪個 Runtime？
□ 如何分配團隊資源？
```

---

## 附錄：架構決策記錄 (ADR)

### ADR-001：採用 Runtime 分層架構

**狀態**：提議

**背景**：當前所有 Processor 在同一層級，無法區分控制權

**決策**：引入 Model Runtime 和 Agent Runtime 概念

**後果**：
- ✅ 控制權明確
- ✅ 更好的資源管理
- ⚠️ 增加架構複雜度

### ADR-002：Services 層演進為 Infrastructure Layer

**狀態**：提議

**背景**：Services 被不同 Processor 重複使用

**決策**：統一為共享的 Infrastructure Layer

**後果**：
- ✅ 減少重複代碼
- ✅ 統一的服務管理
- ⚠️ 需要更細緻的權限控制