# OpenCode Platform - 調整後架構圖表

**版本**: `v1.5`
**日期**: `2026-02-10`
**原則**: `微調優化、認知增強、向後兼容`

---

## 1. 調整後的三層架構（認知增強版）

```mermaid
graph TB
    subgraph "用戶交互層（不變）"
        UI[CLI / API / WebSocket]
    end

    subgraph "路由決策層（微調）"
        Router[Router Layer]
        ModeSelector[Mode Selector]
        CognitiveAnalyzer[認知分析器<br/>⭐ 新增可選]
        RuntimeDispatcher[Runtime Dispatcher]

        Router --> ModeSelector
        Router -.->|可選| CognitiveAnalyzer
        ModeSelector --> RuntimeDispatcher
        CognitiveAnalyzer -.-> RuntimeDispatcher
    end

    subgraph "執行層（標記優化）"
        subgraph "Model Runtime（認知分層）"
            subgraph "System 1 - 快速響應"
                QuickProcessor[Quick Processor]
                ChatProcessor[Chat Processor]
                KnowledgeProcessor[Knowledge Processor]
                Cache[響應緩存<br/>⭐ 新增]
            end

            subgraph "System 2 - 深度思考"
                ThinkingProcessor[Thinking Processor<br/>+ 思考鏈增強]
                CodeProcessor[Code Processor]
                Reflection[反思機制<br/>⭐ 可選]
            end

            SystemController[System Controller]
        end

        subgraph "Agent Runtime（Agent 層）"
            ResearchAgent[Research Agent]
            CodeAgent[Code Agent]
            AnalysisAgent[Analysis Agent]
            WorkflowOrchestrator[Workflow Orchestrator]
        end
    end

    subgraph "基礎設施層（不變）"
        LLM[LLM Service]
        Knowledge[Knowledge Service]
        Tools[Tools & Services]
    end

    UI --> Router
    RuntimeDispatcher --> QuickProcessor
    RuntimeDispatcher --> ThinkingProcessor
    RuntimeDispatcher --> ResearchAgent

    Cache -.->|緩存命中| QuickProcessor
    QuickProcessor --> SystemController
    ThinkingProcessor --> SystemController
    ResearchAgent --> WorkflowOrchestrator

    SystemController --> LLM
    WorkflowOrchestrator --> Tools

    style CognitiveAnalyzer fill:#FFE0B2,stroke-dasharray: 5 5
    style Cache fill:#E8F5E9,stroke-dasharray: 5 5
    style Reflection fill:#FFF3E0,stroke-dasharray: 5 5
    style QuickProcessor fill:#E8F5E9
    style ChatProcessor fill:#E8F5E9
    style ThinkingProcessor fill:#FFF3E0
    style ResearchAgent fill:#FCE4EC
```

---

## 2. 認知路由決策流程（增強版）

```mermaid
graph TD
    Start[請求到達] --> Check{認知路由<br/>是否啟用?}

    Check -->|禁用| Traditional[傳統路由]
    Check -->|啟用| Cognitive[認知分析]

    Traditional --> Mode[檢查 Mode 參數]
    Mode --> DirectSelect[直接選擇 Processor]

    Cognitive --> Extract[特徵提取]
    Extract --> Complexity[複雜度評分]
    Extract --> Pattern[模式匹配]

    Complexity --> Score{認知評分}
    Pattern --> Score

    Score -->|< 0.3<br/>簡單| System1[System 1<br/>快速通道]
    Score -->|0.3-0.7<br/>中等| System2[System 2<br/>思考通道]
    Score -->|> 0.7<br/>複雜| Agent[Agent<br/>工作流]

    System1 --> Cache{緩存檢查}
    Cache -->|命中| CacheResponse[< 0.5秒響應]
    Cache -->|未中| QuickProcess[快速處理<br/>< 3秒]

    System2 --> ThinkProcess[深度思考<br/>10-30秒]
    Agent --> WorkflowProcess[工作流執行<br/>2-10分鐘]

    DirectSelect --> Processor[執行 Processor]
    CacheResponse --> Output[返回結果]
    QuickProcess --> Output
    ThinkProcess --> Output
    WorkflowProcess --> Output
    Processor --> Output

    style Cognitive fill:#FFE0B2
    style System1 fill:#E8F5E9
    style System2 fill:#FFF3E0
    style Agent fill:#FCE4EC
    style CacheResponse fill:#90EE90
```

---

## 3. 執行流程對比（微調版）

```mermaid
graph LR
    subgraph "現有流程（基礎路徑）"
        A1[Request] --> B1[Mode Check]
        B1 --> C1[Get Processor]
        C1 --> D1[Process]
        D1 --> E1[Response]
    end

    subgraph "增強流程（可選路徑）"
        A2[Request] --> B2[Mode Check]
        B2 -.-> CA[認知分析<br/>可選]
        CA -.-> CS{認知決策}

        CS -->|System 1| C2[Cache Check]
        C2 -->|Hit| E2[Fast Response]
        C2 -->|Miss| D2[Quick Process]

        CS -->|System 2| TC[思考鏈構建]
        TC --> D3[Deep Process]

        CS -->|Agent| WF[工作流規劃]
        WF --> D4[Workflow Execute]

        B2 --> C3[Get Processor<br/>傳統路徑]
        C3 --> D5[Process]

        D2 --> E3[Response]
        D3 --> E3
        D4 --> E3
        D5 --> E3
    end

    style CA fill:#FFE0B2,stroke-dasharray: 5 5
    style C2 fill:#E8F5E9,stroke-dasharray: 5 5
    style TC fill:#FFF3E0,stroke-dasharray: 5 5
```

---

## 4. Processor 認知分類映射

```mermaid
graph TB
    subgraph "System 1 類別"
        S1_1[ChatProcessor<br/>對話處理]
        S1_2[QuickProcessor<br/>快速響應]
        S1_3[KnowledgeProcessor<br/>知識檢索]
        S1_Cache[⭐ ResponseCache<br/>結果緩存]
    end

    subgraph "System 2 類別"
        S2_1[ThinkingProcessor<br/>深度推理]
        S2_2[CodeProcessor<br/>代碼生成]
        S2_Chain[⭐ ThinkingChain<br/>思考鏈增強]
    end

    subgraph "Agent 類別"
        A1[ResearchAgent<br/>研究任務]
        A2[CodeAgent<br/>編程任務]
        A3[AnalysisAgent<br/>分析任務]
    end

    subgraph "性能特徵"
        P1[System 1<br/>< 3秒<br/>70% 請求]
        P2[System 2<br/>10-30秒<br/>25% 請求]
        P3[Agent<br/>2-10分鐘<br/>5% 請求]
    end

    S1_1 --> P1
    S2_1 --> P2
    A1 --> P3

    style S1_Cache fill:#E8F5E9,stroke-dasharray: 5 5
    style S2_Chain fill:#FFF3E0,stroke-dasharray: 5 5
    style S1_1 fill:#E8F5E9
    style S2_1 fill:#FFF3E0
    style A1 fill:#FCE4EC
```

---

## 5. 配置驅動的特性開關

```mermaid
graph LR
    subgraph "配置中心"
        Config[配置文件<br/>cognitive_features.yaml]
    end

    subgraph "可選特性"
        F1[認知路由<br/>默認: 關]
        F2[響應緩存<br/>默認: 關]
        F3[思考鏈<br/>默認: 關]
        F4[智能重試<br/>默認: 關]
        F5[認知監控<br/>默認: 關]
    end

    subgraph "運行時行為"
        B1[傳統模式]
        B2[增強模式]
    end

    Config --> F1
    Config --> F2
    Config --> F3

    F1 -->|關| B1
    F1 -->|開| B2
    F2 -->|開| B2

    B1 --> Legacy[現有邏輯<br/>100% 兼容]
    B2 --> Enhanced[認知增強<br/>性能優化]

    style F1 fill:#FFE0B2,stroke-dasharray: 5 5
    style F2 fill:#E8F5E9,stroke-dasharray: 5 5
    style F3 fill:#FFF3E0,stroke-dasharray: 5 5
```

---

## 6. 監控指標體系（增量式）

```mermaid
graph TB
    subgraph "現有監控（保持）"
        M1[請求量]
        M2[響應時間]
        M3[錯誤率]
        M4[資源使用率]
    end

    subgraph "認知監控（新增可選）"
        C1[System 1 指標]
        C2[System 2 指標]
        C3[Agent 指標]

        subgraph "System 1 詳細"
            S1M1[緩存命中率]
            S1M2[P95 < 3秒]
            S1M3[快速響應率]
        end

        subgraph "System 2 詳細"
            S2M1[思考深度]
            S2M2[P95 < 30秒]
            S2M3[推理質量]
        end

        subgraph "Agent 詳細"
            AM1[任務成功率]
            AM2[平均步驟數]
            AM3[執行效率]
        end

        C1 --> S1M1
        C2 --> S2M1
        C3 --> AM1
    end

    M1 --> Dashboard[統一面板]
    M2 --> Dashboard
    C1 -.->|可選| Dashboard
    C2 -.->|可選| Dashboard

    style C1 fill:#E8F5E9,stroke-dasharray: 5 5
    style C2 fill:#FFF3E0,stroke-dasharray: 5 5
    style C3 fill:#FCE4EC,stroke-dasharray: 5 5
```

---

## 7. 實施階段與風險控制

```mermaid
graph TB
    subgraph "Phase 0 - 準備（無風險）"
        P0_1[代碼審查]
        P0_2[添加認知標記]
        P0_3[準備配置文件]
    end

    subgraph "Phase 1 - 監控（極低風險）"
        P1_1[部署認知指標]
        P1_2[收集基準數據]
        P1_3[分析使用模式]
    end

    subgraph "Phase 2 - 優化（低風險）"
        P2_1[啟用緩存<br/>5% 用戶]
        P2_2[觀察效果]
        P2_3[逐步推廣]
    end

    subgraph "Phase 3 - 增強（中風險）"
        P3_1[認知路由<br/>測試環境]
        P3_2[思考鏈<br/>小範圍]
        P3_3[全面推廣]
    end

    P0_1 --> P0_2 --> P0_3
    P0_3 --> P1_1
    P1_1 --> P1_2 --> P1_3
    P1_3 --> Decision1{評估}

    Decision1 -->|正常| P2_1
    Decision1 -->|異常| Stop1[保持現狀]

    P2_1 --> P2_2 --> P2_3
    P2_3 --> Decision2{評估}

    Decision2 -->|良好| P3_1
    Decision2 -->|問題| Rollback[回滾]

    P3_1 --> P3_2 --> P3_3

    style P0_1 fill:#90EE90
    style P1_1 fill:#E8F5E9
    style P2_1 fill:#FFF3E0
    style P3_1 fill:#FFE0B2
```

---

## 8. 性能優化效果預期

```mermaid
graph LR
    subgraph "優化前（基準）"
        B1[平均響應: 5秒]
        B2[P95: 15秒]
        B3[緩存率: 0%]
    end

    subgraph "Phase 1 優化"
        O1_1[啟用標記]
        O1_2[響應: 5秒<br/>無變化]
    end

    subgraph "Phase 2 優化"
        O2_1[啟用緩存]
        O2_2[響應: 3.5秒<br/>-30%]
        O2_3[緩存率: 40%]
    end

    subgraph "Phase 3 優化"
        O3_1[認知路由]
        O3_2[響應: 3秒<br/>-40%]
        O3_3[緩存率: 60%]
    end

    B1 --> O1_1 --> O2_1 --> O3_1
    B2 --> O1_2 --> O2_2 --> O3_2

    style O2_2 fill:#90EE90
    style O3_2 fill:#90EE90
```

---

## 9. 灰度發布流程

```mermaid
graph TB
    Start[開始發布] --> Config[配置準備]

    Config --> Enable{啟用特性}

    Enable -->|1%| Canary[金絲雀用戶]
    Enable -->|99%| Stable[穩定版本]

    Canary --> Monitor1[監控24小時]
    Monitor1 --> Check1{檢查指標}

    Check1 -->|正常| Expand5[擴展到 5%]
    Check1 -->|異常| Rollback1[回滾]

    Expand5 --> Monitor2[監控48小時]
    Monitor2 --> Check2{檢查指標}

    Check2 -->|正常| Expand20[擴展到 20%]
    Check2 -->|異常| Rollback2[回滾]

    Expand20 --> Monitor3[監控72小時]
    Monitor3 --> Check3{檢查指標}

    Check3 -->|正常| Expand50[擴展到 50%]
    Check3 -->|異常| Rollback3[回滾]

    Expand50 --> FinalCheck{最終評估}
    FinalCheck -->|成功| FullDeploy[全量發布]
    FinalCheck -->|問題| PartialKeep[保持 50%]

    style Canary fill:#FFE0B2
    style FullDeploy fill:#90EE90
    style Rollback1 fill:#FF6B6B
```

---

## 10. API 兼容性保證

```mermaid
graph TB
    subgraph "API 層（完全兼容）"
        API1["API: /v1/chat<br/>現有 API"]
        API2["API: /v1/thinking<br/>現有 API"]
        API3["API: /v1/research<br/>現有 API"]
        API4["API: /v1/chat/cognitive<br/>⭐ 新增可選"]
    end

    subgraph "路由層"
        Router[統一路由器]
        Legacy[傳統處理]
        Cognitive[認知處理]
    end

    subgraph "處理層"
        Processors[所有 Processors<br/>保持不變]
    end

    API1 --> Router
    API2 --> Router
    API3 --> Router
    API4 --> Router

    Router --> Legacy
    Router -.->|可選| Cognitive

    Legacy --> Processors
    Cognitive --> Processors

    style API4 fill:#FFE0B2,stroke-dasharray: 5 5
    style Cognitive fill:#FFE0B2,stroke-dasharray: 5 5
```

---

## 總結

調整後的架構保持了原有結構的 90% 不變，通過以下方式實現認知增強：

1. **最小侵入**：所有改動都是可選的，通過配置開關控制
2. **向後兼容**：現有 API 和功能完全不受影響
3. **漸進優化**：分階段實施，每步都可獨立評估和回滾
4. **性能提升**：緩存和智能路由帶來顯著性能改善
5. **易於維護**：代碼改動小，理解成本低

關鍵特點：
- 🟢 **綠色部分**：性能優化區域
- 🟡 **黃色部分**：智能增強區域
- 🔴 **紅色部分**：需要謹慎的區域
- ⭐ **虛線部分**：可選特性

這個調整方案確保了系統能夠平滑演進到認知架構，同時保持穩定性和可控性。