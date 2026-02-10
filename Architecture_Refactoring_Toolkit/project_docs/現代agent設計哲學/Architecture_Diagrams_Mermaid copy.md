# OpenCode Platform - 架構圖表集 (Mermaid)

**版本**: `v1.0`
**日期**: `2026-02-10`
**說明**: `所有架構流程的 Mermaid 視覺化`

---

## 1. 三層 Runtime 架構模型

```mermaid
graph TB
    subgraph "用戶交互層"
        UI[CLI / API / WebSocket]
    end

    subgraph "路由決策層"
        Router[Router Layer]
        ModeSelector[Mode Selector]
        ComplexityAnalyzer[Complexity Analyzer]
        RuntimeDispatcher[Runtime Dispatcher]

        Router --> ModeSelector
        Router --> ComplexityAnalyzer
        ComplexityAnalyzer --> RuntimeDispatcher
    end

    subgraph "執行層"
        subgraph "Model Runtime"
            QuickProcessor[Quick Processor]
            ThinkingProcessor[Thinking Processor]
            ChatProcessor[Chat Processor]
            SystemController[System Controller]

            QuickProcessor --> SystemController
            ThinkingProcessor --> SystemController
            ChatProcessor --> SystemController
        end

        subgraph "Agent Runtime"
            ResearchAgent[Research Agent]
            CodeAgent[Code Agent]
            AnalysisAgent[Analysis Agent]
            WorkflowOrchestrator[Workflow Orchestrator]

            ResearchAgent --> WorkflowOrchestrator
            CodeAgent --> WorkflowOrchestrator
            AnalysisAgent --> WorkflowOrchestrator
        end
    end

    subgraph "基礎設施層"
        LLMService[LLM Service]
        KnowledgeService[Knowledge Service]
        SandboxService[Sandbox Service]
        SearchService[Search Service]
        BrowserService[Browser Service]
        RepositoryService[Repository Service]
    end

    UI --> Router
    RuntimeDispatcher --> QuickProcessor
    RuntimeDispatcher --> ThinkingProcessor
    RuntimeDispatcher --> ChatProcessor
    RuntimeDispatcher --> ResearchAgent
    RuntimeDispatcher --> CodeAgent
    RuntimeDispatcher --> AnalysisAgent

    SystemController --> LLMService
    SystemController --> KnowledgeService
    WorkflowOrchestrator --> LLMService
    WorkflowOrchestrator --> SandboxService
    WorkflowOrchestrator --> SearchService
```

---

## 2. 請求處理管線 (Request Processing Pipeline)

```mermaid
flowchart LR
    subgraph "入口階段"
        A[請求接收] --> B[認證授權]
        B --> C[請求驗證]
    end

    subgraph "路由階段"
        C --> D[模式判斷]
        D --> E[複雜度分析]
        E --> F{Runtime 選擇}

        F -->|Score < 0.3| G[Model Runtime]
        F -->|Score >= 0.3| H[Agent Runtime]
    end

    subgraph "Model Runtime Pipeline"
        G --> I[Processor 選擇]
        I --> J[Context 建立]
        J --> K[執行控制]
        K --> L[結果返回]
    end

    subgraph "Agent Runtime Pipeline"
        H --> M[Workflow 規劃]
        M --> N[Step 執行]
        N --> O[狀態管理]
        O --> P[Checkpoint]
        P --> Q[結果聚合]
    end

    L --> R[響應返回]
    Q --> R
```

---

## 3. 架構演進路徑

```mermaid
graph LR
    subgraph "現有組件"
        RE[RefactoredEngine]
        PF[ProcessorFactory]
        BP[BaseProcessor]
        PC[ProcessingContext]
        SL[Services Layer]
    end

    subgraph "演進過程"
        RE --> RC[Router Component]
        RE --> RM[Runtime Manager]

        PF --> MRF[Model Runtime Factory]
        PF --> ARF[Agent Runtime Factory]

        BP --> MP[ModelProcessor]
        BP --> AP[AgentProcessor]

        PC --> EC[ExecutionContext]
        PC --> WS[WorkflowState]

        SL --> IL[Infrastructure Layer]
    end

    subgraph "目標架構"
        RC --> Router
        RM --> RuntimeManager

        MRF --> ModelRuntime
        ARF --> AgentRuntime

        MP --> QuickThinkingChat[Quick/Thinking/Chat]
        AP --> ResearchCodeAnalysis[Research/Code/Analysis]

        EC --> Stateless[無狀態執行]
        WS --> Stateful[有狀態工作流]

        IL --> SharedInfra[共享基礎設施]
    end
```

---

## 4. 控制權分配矩陣

```mermaid
graph TB
    subgraph "控制權決策流程"
        Request[請求] --> Analysis{分析類型}

        Analysis -->|簡單查詢| MR[Model Runtime]
        Analysis -->|複雜任務| AR[Agent Runtime]

        subgraph "Model Runtime 控制"
            MR --> SystemDecision[系統決定]
            SystemDecision --> ToolCall1[工具調用<30s]
            SystemDecision --> NoRetry[無/簡單重試]
            SystemDecision --> Stateless1[無狀態]
            SystemDecision --> NonInterruptible[不可中斷]
            SystemDecision --> StrictLimit[嚴格限制]
        end

        subgraph "Agent Runtime 控制"
            AR --> WorkflowDecision[工作流決定]
            WorkflowDecision --> ToolCall2[工具調用>分鐘]
            WorkflowDecision --> SmartRetry[智能重試]
            WorkflowDecision --> Stateful[有狀態持久化]
            WorkflowDecision --> Interruptible[可中斷/恢復]
            WorkflowDecision --> FlexibleQuota[彈性配額]
        end
    end
```

---

## 5. Runtime 執行流程對比

```mermaid
flowchart TB
    subgraph "Model Runtime 執行流程"
        MR1[接收請求] --> MR2[選擇Processor]
        MR2 --> MR3[建立Context]
        MR3 --> MR4[系統控制執行]
        MR4 --> MR5{需要工具?}
        MR5 -->|Yes| MR6[系統批准]
        MR6 --> MR7[執行工具]
        MR7 --> MR8[返回結果]
        MR5 -->|No| MR8
    end

    subgraph "Agent Runtime 執行流程"
        AR1[接收目標] --> AR2[規劃Workflow]
        AR2 --> AR3[初始化State]
        AR3 --> AR4{執行循環}
        AR4 --> AR5[執行Step]
        AR5 --> AR6[更新State]
        AR6 --> AR7{完成?}
        AR7 -->|No| AR8[Checkpoint]
        AR8 --> AR4
        AR7 -->|Yes| AR9[聚合結果]
        AR9 --> AR10[返回報告]
    end
```

---

## 6. 基礎設施共享模型

```mermaid
graph TB
    subgraph "Runtime 層"
        MR[Model Runtime]
        AR[Agent Runtime]
    end

    subgraph "Infrastructure Layer"
        subgraph "LLM Services"
            OpenAI[OpenAI API]
            Anthropic[Anthropic API]
            Fallback[Fallback Logic]
        end

        subgraph "Knowledge Services"
            VectorDB[Vector Database]
            DocumentStore[Document Store]
            RAG[RAG Pipeline]
        end

        subgraph "Execution Services"
            Sandbox[Code Sandbox]
            Browser[Browser Automation]
            FileSystem[File System]
        end

        subgraph "Search Services"
            WebSearch[Web Search]
            CodeSearch[Code Search]
            RepoSearch[Repository Search]
        end
    end

    MR --> |受限訪問| OpenAI
    MR --> |只讀| VectorDB
    MR --> |禁用| Sandbox
    MR --> |受限| WebSearch

    AR --> |完全訪問| OpenAI
    AR --> |讀寫| VectorDB
    AR --> |完全| Sandbox
    AR --> |完全| WebSearch

    OpenAI --> Fallback
    Fallback --> Anthropic
```

---

## 7. 實施路線圖時間線

```mermaid
gantt
    title 架構演進實施計劃
    dateFormat YYYY-MM-DD
    section Phase 1 基礎準備
    抽象 Runtime Interface        :a1, 2026-02-10, 3d
    創建 Router Component         :a2, after a1, 4d
    重構 Services 層              :a3, after a1, 5d
    建立 Runtime 選擇機制          :a4, after a2, 2d

    section Phase 2 Runtime 分離
    實現 ModelRuntime             :b1, after a4, 7d
    整合現有 Processors           :b2, after b1, 3d
    實現 AgentRuntime 基礎         :b3, after b1, 7d
    Workflow Engine 開發          :b4, after b3, 5d

    section Phase 3 Pipeline 優化
    優化 Router 邏輯              :c1, after b4, 3d
    實現複雜度分析器               :c2, after c1, 3d
    Pipeline 中間件支持           :c3, after c2, 4d
    執行監控實現                  :c4, after c3, 4d

    section Phase 4 生產就緒
    性能優化                      :d1, after c4, 4d
    錯誤處理完善                  :d2, after d1, 3d
    監控和告警                    :d3, after d2, 3d
    文檔更新                      :d4, after d3, 4d
```

---

## 8. 複雜度分析決策樹

```mermaid
graph TD
    Start[收到請求] --> Q1{是否有多步驟?}

    Q1 -->|No| Q2{需要工具調用?}
    Q1 -->|Yes| ComplexTask[複雜任務]

    Q2 -->|No| Q3{查詢長度?}
    Q2 -->|Yes| Q4{工具數量?}

    Q3 -->|< 100字| SimpleQuery[簡單查詢]
    Q3 -->|> 100字| Q5{包含代碼?}

    Q4 -->|1個| ModerateTask[中等任務]
    Q4 -->|多個| ComplexTask

    Q5 -->|No| ModerateTask
    Q5 -->|Yes| ComplexTask

    SimpleQuery --> Score1[Score: 0.1-0.2]
    ModerateTask --> Score2[Score: 0.3-0.6]
    ComplexTask --> Score3[Score: 0.7-1.0]

    Score1 --> QuickMode[Quick Mode]
    Score2 --> ThinkingMode[Thinking Mode]
    Score3 --> AgentMode[Agent Mode]

    style SimpleQuery fill:#90EE90
    style ModerateTask fill:#FFD700
    style ComplexTask fill:#FFA07A
```

---

## 9. 狀態管理流程

```mermaid
stateDiagram-v2
    [*] --> Idle: 系統啟動

    Idle --> Routing: 接收請求

    Routing --> ModelExecution: Model Runtime
    Routing --> AgentExecution: Agent Runtime

    state ModelExecution {
        [*] --> Processing
        Processing --> Completed
        Processing --> Failed
        Completed --> [*]
        Failed --> [*]
    }

    state AgentExecution {
        [*] --> Planning
        Planning --> Executing
        Executing --> Checkpointing
        Checkpointing --> Executing: 繼續
        Executing --> Completed: 完成
        Executing --> Paused: 中斷
        Paused --> Resuming: 恢復
        Resuming --> Executing
        Executing --> Failed: 錯誤
        Failed --> Recovering: 恢復策略
        Recovering --> Executing: 重試
        Recovering --> Terminated: 無法恢復
        Completed --> [*]
        Terminated --> [*]
    }

    ModelExecution --> Idle: 完成
    AgentExecution --> Idle: 完成
```

---

## 10. 錯誤處理策略

```mermaid
flowchart TB
    Error[發生錯誤] --> Classify{錯誤分類}

    Classify -->|網絡錯誤| Network[網絡重試]
    Classify -->|LLM錯誤| LLM[LLM Fallback]
    Classify -->|資源限制| Resource[資源等待]
    Classify -->|業務錯誤| Business[業務處理]

    Network --> Retry1{重試次數}
    Retry1 -->|< 3| Wait1[等待 2^n 秒]
    Wait1 --> NetworkCall[重新請求]
    NetworkCall --> Success1{成功?}
    Success1 -->|Yes| Continue[繼續執行]
    Success1 -->|No| Retry1
    Retry1 -->|>= 3| Fail[失敗返回]

    LLM --> Switch{切換模型}
    Switch -->|Primary| Secondary[使用備用模型]
    Switch -->|Secondary| Degrade[降級處理]
    Secondary --> Success2{成功?}
    Success2 -->|Yes| Continue
    Success2 -->|No| Degrade

    Resource --> Queue[進入等待隊列]
    Queue --> Monitor[監控資源]
    Monitor --> Available{資源可用?}
    Available -->|Yes| Allocate[分配資源]
    Available -->|No| Timeout{超時?}
    Timeout -->|No| Monitor
    Timeout -->|Yes| Cancel[取消任務]
    Allocate --> Continue

    Business --> Log[記錄日誌]
    Log --> UserError[返回用戶錯誤]

    style Continue fill:#90EE90
    style Fail fill:#FF6B6B
    style Cancel fill:#FF6B6B
    style UserError fill:#FFD700
```

---

## 11. 性能優化決策流程

```mermaid
flowchart LR
    Monitor[性能監控] --> Metrics{關鍵指標}

    Metrics --> Latency[延遲分析]
    Metrics --> Throughput[吞吐量分析]
    Metrics --> Resource[資源使用分析]

    Latency --> L1{P95 > 2s?}
    L1 -->|Yes| OptimizeRoute[優化路由]
    L1 -->|No| L2{P99 > 5s?}
    L2 -->|Yes| CacheStrategy[緩存策略]
    L2 -->|No| OK1[延遲正常]

    Throughput --> T1{QPS < 目標?}
    T1 -->|Yes| T2{CPU < 80%?}
    T2 -->|Yes| CodeOptimize[代碼優化]
    T2 -->|No| ScaleOut[水平擴展]
    T1 -->|No| OK2[吞吐量正常]

    Resource --> R1{內存 > 80%?}
    R1 -->|Yes| MemoryLeak[檢查內存洩漏]
    R1 -->|No| R2{CPU > 80%?}
    R2 -->|Yes| ProfileCode[性能分析]
    R2 -->|No| OK3[資源正常]

    OptimizeRoute --> Deploy[部署優化]
    CacheStrategy --> Deploy
    CodeOptimize --> Deploy
    ScaleOut --> Deploy
    MemoryLeak --> Fix[修復問題]
    ProfileCode --> Fix
    Fix --> Deploy

    style OK1 fill:#90EE90
    style OK2 fill:#90EE90
    style OK3 fill:#90EE90
    style Deploy fill:#87CEEB
```

---

## 12. 架構決策流程

```mermaid
flowchart TD
    Requirement[新需求] --> Analysis{需求分析}

    Analysis --> Impact{影響評估}

    Impact -->|核心變更| Major[重大架構決策]
    Impact -->|模組變更| Minor[局部架構調整]
    Impact -->|配置變更| Config[配置調整]

    Major --> ADR[撰寫 ADR]
    ADR --> Review[架構評審]
    Review --> Approve{批准?}
    Approve -->|Yes| Implementation[實施計劃]
    Approve -->|No| Revise[修訂方案]
    Revise --> ADR

    Minor --> TechLead[Tech Lead 決策]
    TechLead --> QuickReview[快速評審]
    QuickReview --> Implement[直接實施]

    Config --> DirectChange[直接修改]

    Implementation --> Pilot[試點實施]
    Pilot --> Validate{驗證結果}
    Validate -->|成功| Rollout[全面推廣]
    Validate -->|失敗| Rollback[回滾]

    Implement --> Test[測試驗證]
    Test --> Deploy[部署]

    DirectChange --> Deploy

    style Rollout fill:#90EE90
    style Deploy fill:#90EE90
    style Rollback fill:#FF6B6B
```

---

## 13. 監控體系架構

```mermaid
graph TB
    subgraph "數據採集層"
        App[應用程序]
        Runtime[Runtime 指標]
        Infra[基礎設施]
        Business[業務指標]
    end

    subgraph "數據處理層"
        Collector[指標收集器]
        Aggregator[聚合器]
        Analyzer[分析器]
    end

    subgraph "存儲層"
        TimeSeries[(時序數據庫)]
        LogStore[(日誌存儲)]
        TraceStore[(追蹤存儲)]
    end

    subgraph "展示層"
        Dashboard[監控面板]
        Alert[告警系統]
        Report[報表系統]
    end

    App --> Collector
    Runtime --> Collector
    Infra --> Collector
    Business --> Collector

    Collector --> Aggregator
    Aggregator --> Analyzer

    Analyzer --> TimeSeries
    Analyzer --> LogStore
    Analyzer --> TraceStore

    TimeSeries --> Dashboard
    LogStore --> Dashboard
    TraceStore --> Dashboard

    Analyzer --> Alert
    TimeSeries --> Report

    Alert --> Notification[通知]
    Notification --> SMS[短信]
    Notification --> Email[郵件]
    Notification --> Slack[Slack]
```

---

## 14. 部署流程

```mermaid
flowchart LR
    subgraph "開發環境"
        Dev[開發] --> Test[測試]
        Test --> PR[Pull Request]
    end

    subgraph "CI/CD Pipeline"
        PR --> CI{CI 檢查}
        CI -->|通過| Merge[合併]
        CI -->|失敗| Fix[修復]
        Fix --> PR

        Merge --> Build[構建]
        Build --> UnitTest[單元測試]
        UnitTest --> IntegrationTest[集成測試]
        IntegrationTest --> Package[打包]
    end

    subgraph "部署階段"
        Package --> Staging[預發環境]
        Staging --> SmokeTest[冒煙測試]
        SmokeTest --> Approval{審批}
        Approval -->|通過| Production[生產環境]
        Approval -->|拒絕| Investigate[調查問題]

        Production --> HealthCheck[健康檢查]
        HealthCheck --> Monitor[監控驗證]
        Monitor --> Success{成功?}
        Success -->|Yes| Complete[部署完成]
        Success -->|No| Rollback[回滾]
    end

    style Complete fill:#90EE90
    style Rollback fill:#FF6B6B
```

---

## 總結

這份 Mermaid 圖表集涵蓋了 OpenCode Platform 的所有核心架構和流程：

1. **架構層次**：三層 Runtime 模型、基礎設施共享
2. **處理流程**：請求管線、執行流程、狀態管理
3. **決策邏輯**：複雜度分析、路由決策、控制權分配
4. **運維流程**：錯誤處理、性能優化、部署流程
5. **管理流程**：架構決策、監控體系

每個圖表都可以直接在支持 Mermaid 的環境中渲染，提供清晰的視覺化理解。