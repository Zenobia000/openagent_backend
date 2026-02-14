# 類人類認知架構 - 總覽與願景

## 文檔編號
`COGNITIVE-ARCH-00`

**版本**: 1.0.0
**最後更新**: 2026-02-12
**狀態**: 提案階段 (Proposal)

---

## 執行摘要 (Executive Summary)

本文檔描述 OpenAgent Backend 從**機械性線性架構**向**類人類有機認知架構**的完整轉型方案。

### 當前問題

OpenAgent 當前架構存在以下根本性限制：

1. **線性決策模式**：`DefaultRouter` 在初始階段就決定處理路徑，無法在執行中動態調整
2. **缺乏全域認知**：各 Processor 之間信息孤島，無法進行跨模組的認知整合
3. **無元認知能力**：系統無法「思考自己的思考」，缺乏對處理品質的實時監控
4. **靜態模式切換**：System 1/2/Agent 的切換是預設的，而非根據認知需求動態觸發
5. **無記憶整合**：僅有簡單的 cache，缺乏類人的工作記憶、情節記憶、語義記憶系統

### 核心解決方案

我們提出以下**五大核心組件**的類人類認知架構：

```
┌────────────────────────────────────────────────────────────────┐
│                     Metacognitive Governor                       │
│             (元認知治理層 - 監控與策略調整)                         │
└────────────────────────────────────────────────────────────────┘
                              ↓ ↑ (監控與干預)
┌────────────────────────────────────────────────────────────────┐
│                     Global Workspace (黑板)                      │
│   ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
│   │ Working  │ Episodic │ Semantic │ Procedural│ Attention│    │
│   │ Memory   │ Memory   │ Memory   │  Memory   │  Focus   │    │
│   └──────────┴──────────┴──────────┴──────────┴──────────┘    │
└────────────────────────────────────────────────────────────────┘
                    ↓ (廣播) ↑ (訂閱)
┌────────────────────────────────────────────────────────────────┐
│                      OODA Loop Router                            │
│           Observe → Orient → Decide → Act (持續循環)            │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│      Cognitive Processors (System 1 / System 2 / Agent)        │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  │
│  │ Search │  │ Think  │  │  Code  │  │Knowledge│  │ Custom │  │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘  │
└────────────────────────────────────────────────────────────────┘
                              ↑
┌────────────────────────────────────────────────────────────────┐
│                  Neuromodulation System                          │
│         (探索-利用平衡、創造力調控、風險容忍度)                   │
└────────────────────────────────────────────────────────────────┘
```

---

## 神經科學與心理學基礎

### 1. Global Workspace Theory (Bernard Baars, 1988)

**核心概念**：
- 大腦有無數並行處理器（視覺、聽覺、語言、運動等）
- 只有被「廣播」到全域工作空間的信息才進入意識
- 意識資源有限（Miller's Law: 7±2 項目），需要注意力機制

**在 OpenAgent 中的應用**：
```python
class GlobalWorkspace:
    """
    模擬大腦的全域工作空間
    - 容量限制：最多追蹤 7±2 個認知項目
    - 注意力機制：根據優先級動態分配處理資源
    - 廣播系統：所有 Processor 都可以訂閱工作空間的變化
    """
    def broadcast(self, cognitive_item: CognitiveItem):
        """將關鍵信息廣播到所有訂閱者"""
        pass
```

### 2. Predictive Coding (Karl Friston, 2010)

**核心概念**：
- 大腦持續維護一個「世界模型」
- 感知到的信息與預測不符時產生「預測誤差」
- 誤差訊號驅動認知更新

**在 OpenAgent 中的應用**：
```python
class MetacognitiveGovernor:
    """
    元認知治理層監控「預測誤差」
    - 預期：LLM 應該能回答用戶問題
    - 實際：LLM 回覆「我不確定」
    - 預測誤差 > 閾值 → 觸發 System 2 或 Agent 介入
    """
    def compute_prediction_error(self, expected, actual) -> float:
        """計算認知預測誤差"""
        pass
```

### 3. Dual Process Theory (Kahneman, 2011)

**核心概念**：
- **System 1**：快速、自動、依賴直覺與模式匹配
- **System 2**：慢速、需要努力、邏輯推理
- 兩者並非互斥，而是持續互動

**在 OpenAgent 中的應用**：
```python
class OODARouter:
    """
    不再是靜態的「分配任務」，而是動態的「認知評估」
    - 簡單模式匹配 → System 1 (Cache/Quick Response)
    - 複雜推理需求 → System 2 (Thinking/Multi-Step)
    - 未知領域 → Agent (Tool-Augmented Search)
    """
    def assess_cognitive_demand(self, task) -> CognitiveLevel:
        """評估任務的認知需求等級"""
        pass
```

### 4. OODA Loop (John Boyd, 1976)

**核心概念**：
- **Observe (觀察)**：收集環境信息
- **Orient (定位)**：根據內部模型解釋信息
- **Decide (決策)**：選擇行動策略
- **Act (執行)**：執行動作並觀察結果

**在 OpenAgent 中的應用**：
```python
class OODARouter:
    async def observe(self, task: Task) -> ObservationResult:
        """第一階段：多維度特徵提取"""
        pass

    async def orient(self, obs: ObservationResult) -> OrientationResult:
        """第二階段：結合系統狀態與歷史經驗進行定位"""
        pass

    async def decide(self, orient: OrientationResult) -> RoutingDecision:
        """第三階段：選擇最佳認知策略"""
        pass

    async def act(self, decision: RoutingDecision) -> ProcessingResult:
        """第四階段：執行並監控，隨時準備重新觀察"""
        pass
```

### 5. Neuromodulation (Dopamine/Norepinephrine)

**核心概念**：
- **多巴胺 (Dopamine)**：獎勵預測誤差，驅動探索與學習
- **去甲腎上腺素 (Norepinephrine)**：偵測不確定性與新奇性，提高警覺
- **血清素 (Serotonin)**：調控耐心與風險規避

**在 OpenAgent 中的應用**：
```python
class NeuromodulationSystem:
    """
    類比神經調控物質的系統參數調整
    - 多巴胺類比：成功的策略獲得獎勵，失敗的策略降低權重
    - 去甲腎上腺素類比：偵測到不確定性時，提高探索傾向
    - 血清素類比：在預算充足時更有耐心進行深度思考
    """
    dopamine: float  # 獎勵信號，影響探索率
    norepinephrine: float  # 不確定性信號，影響注意力
    serotonin: float  # 資源充裕度，影響風險容忍度
```

---

## 核心設計原則

### 原則 1：有機湧現而非機械派遣 (Emergence over Dispatch)

**錯誤模式**（當前架構）：
```python
# Router 一開始就決定路徑，之後無法改變
if complexity < 3:
    processor = System1Processor()
elif complexity < 7:
    processor = System2Processor()
else:
    processor = AgentProcessor()

result = await processor.process(task)  # 線性執行
```

**正確模式**（類人類架構）：
```python
# 認知需求在執行中湧現，系統動態響應
workspace = GlobalWorkspace()
metacog = MetacognitiveGovernor(workspace)

# 初始處理（可能是 System 1）
initial_result = await quick_processor.process(task)
workspace.broadcast(initial_result)

# 元認知監控發現信心不足
if metacog.confidence < 0.7:
    # 動態切換到 System 2 進行深度思考
    refined_result = await thinking_processor.process(task)
    workspace.broadcast(refined_result)

# 仍然無法解決？切換到 Agent 模式
if metacog.is_stuck():
    agent_result = await agent_processor.process(task)
```

### 原則 2：全域整合而非局部孤島 (Global Integration over Local Isolation)

**錯誤模式**：
```python
# 每個 Processor 只知道自己的輸入輸出
class SearchProcessor:
    async def process(self, task):
        results = await self.search_tool.run(task.query)
        return ProcessingResult(results=results)  # 結果只返回給 Engine
```

**正確模式**：
```python
# 所有 Processor 共享全域認知空間
class SearchProcessor:
    def __init__(self, workspace: GlobalWorkspace):
        self.workspace = workspace

    async def process(self, task):
        # 檢查工作空間中是否已有相關信息
        existing_knowledge = self.workspace.recall_relevant(task.query)

        # 執行搜尋
        results = await self.search_tool.run(task.query)

        # 廣播到工作空間，其他 Processor 可以利用
        self.workspace.broadcast(CognitiveItem(
            type="search_results",
            content=results,
            confidence=0.8,
            timestamp=now()
        ))
```

### 原則 3：持續監控而非一次決策 (Continuous Monitoring over One-Shot Decision)

**錯誤模式**：
```python
# Router 決定後就不再介入
route = router.route(task)
result = await route.processor.process(task)
return result  # 無論結果好壞都直接返回
```

**正確模式**：
```python
# 元認知層持續監控處理品質
async def process_with_monitoring(task):
    result = await processor.process(task)

    # 元認知評估
    confidence = metacog.estimate_confidence(result)

    if confidence < QUALITY_THRESHOLD:
        # 觸發迭代精煉
        logger.info("Low confidence detected, triggering refinement")
        result = await refine_processor.process(task, previous=result)

    return result
```

### 原則 4：記憶整合而非遺忘重來 (Memory Integration over Amnesia)

**錯誤模式**：
```python
# 每次請求都是全新的，沒有經驗累積
async def handle_request(task):
    result = await process(task)  # 從零開始
    return result
```

**正確模式**：
```python
# 系統記住過去的經驗並類比應用
async def handle_request(task):
    # 檢查情節記憶：類似的任務之前怎麼解決的？
    similar_cases = episodic_memory.recall_similar(task)

    if similar_cases:
        # 類比推理：嘗試應用過去成功的策略
        strategy = analogical_mapper.transfer(similar_cases[0].strategy, task)
        result = await execute_strategy(strategy, task)
    else:
        # 新問題：正常處理
        result = await process(task)

    # 保存經驗到情節記憶
    episodic_memory.store(Episode(
        task=task,
        strategy=strategy,
        result=result,
        success=result.confidence > 0.8,
        timestamp=now()
    ))
```

---

## 關鍵創新點

### 1. 黑板架構 (Blackboard Architecture)

**靈感來源**：HEARSAY-II 語音識別系統（1970s），Blackboard Systems in AI

**核心機制**：
- 共享的「認知黑板」，所有 Processor 都可以讀寫
- 注意力機制決定哪些信息優先處理
- 基於優先級的協作問題解決

**技術實現**：
```python
class Blackboard:
    """認知黑板：全域信息共享中心"""
    knowledge_sources: List[KnowledgeSource]  # 訂閱者
    workspace_items: PriorityQueue[CognitiveItem]  # 待處理項目

    def post(self, item: CognitiveItem):
        """發布新的認知項目"""
        self.workspace_items.put(item)
        self.notify_subscribers(item)

    def get_focus(self) -> CognitiveItem:
        """根據注意力機制返回當前焦點"""
        return self.workspace_items.get()
```

### 2. 貝葉斯信心估計 (Bayesian Confidence Estimation)

**靈感來源**：Bayesian Brain Hypothesis, Predictive Processing

**核心機制**：
- 將所有認知輸出視為機率分佈
- 整合多個信心指標：LLM 自報信心、工具成功率、歷史準確度
- 動態更新：隨著更多證據的收集，信心估計會更新

**技術實現**：
```python
class ConfidenceEstimator:
    """多因子貝葉斯信心估計"""

    def estimate(self, result: ProcessingResult) -> float:
        # P(correct | evidence) ∝ P(evidence | correct) * P(correct)

        # 先驗：該類型任務的歷史準確度
        prior = self.get_prior(result.task_type)

        # 似然：各種證據的權重
        llm_confidence = result.llm_confidence  # LLM 自報信心
        tool_reliability = result.tool_reliability  # 工具可靠性
        cross_check = self.cross_validate(result)  # 交叉驗證

        # 貝葉斯更新
        posterior = self.bayesian_update(
            prior,
            [llm_confidence, tool_reliability, cross_check]
        )

        return posterior
```

### 3. 探索-利用權衡 (Exploration-Exploitation Trade-off)

**靈感來源**：Multi-Armed Bandit Problem, Reinforcement Learning

**核心機制**：
- **利用 (Exploitation)**：使用已知有效的策略
- **探索 (Exploration)**：嘗試新策略以發現更好的解法
- **動態平衡**：根據不確定性、預算、時間壓力調整

**技術實現**：
```python
class ExplorationController:
    """探索-利用平衡控制器"""

    def select_strategy(self, strategies: List[Strategy]) -> Strategy:
        # Epsilon-Greedy 或 Upper Confidence Bound (UCB)
        if random.random() < self.epsilon:
            # 探索：選擇嘗試次數少的策略
            return min(strategies, key=lambda s: s.trial_count)
        else:
            # 利用：選擇平均成功率最高的策略
            return max(strategies, key=lambda s: s.success_rate)

    def adjust_exploration_rate(self, context: ExecutionContext):
        """根據情境動態調整探索率"""
        if context.budget_remaining < 0.2:
            self.epsilon *= 0.5  # 預算不足，降低探索
        if context.uncertainty > 0.8:
            self.epsilon *= 1.5  # 高度不確定，增加探索
```

---

## 實施優先級與階段劃分

### Phase 0: 基礎準備（Week 1-2）
**目標**: 建立測試基礎設施與特性開關
- [ ] 完整的 API 契約文檔
- [ ] Feature Flags 系統
- [ ] 測試框架與 Mock 工具
- [ ] 性能基準測試

### Phase 1: 全域工作空間（Week 3-4）⭐ **最高優先級**
**目標**: 建立跨 Processor 的信息共享機制
- [ ] `WorkspaceManager` 核心實現
- [ ] `AttentionMechanism` 注意力管理
- [ ] `WorkingMemory` 短期記憶
- [ ] Processor 整合與廣播機制

**即時收益**:
- 跨模組上下文共享
- 減少重複的工具調用
- 提升多步驟任務的連貫性

### Phase 2: 元認知治理（Week 5-6）⭐ **高優先級**
**目標**: 建立品質監控與迭代精煉機制
- [ ] `MetacognitiveGovernor` 核心邏輯
- [ ] `ConfidenceEstimator` 多因子信心估計
- [ ] `QualityMonitor` 實時品質監控
- [ ] 迭代精煉觸發機制

**即時收益**:
- 顯著降低低品質輸出
- 自動觸發二次檢查
- 提升用戶信任度

### Phase 3: OODA 路由器（Week 7-8）
**目標**: 動態的認知需求評估
- [ ] 嵌入式特徵提取
- [ ] 自適應複雜度分析
- [ ] 動態策略選擇
- [ ] A/B 測試框架

### Phase 4: 記憶系統（Week 9-10）
**目標**: 經驗累積與類比推理
- [ ] 情節記憶實現
- [ ] 語義記憶（知識圖譜）
- [ ] 記憶鞏固流程
- [ ] 類比推理引擎

### Phase 5: 神經調控（Week 11-12）
**目標**: 探索-利用平衡與創造力調控
- [ ] 獎勵系統
- [ ] 探索控制器
- [ ] 動態參數調整
- [ ] 與 Router/Processor 整合

### Phase 6: 事件驅動架構（Week 13-14）
**目標**: 並行處理與響應式系統
- [ ] 認知事件總線
- [ ] 響應式 Processor
- [ ] 並行執行框架
- [ ] 事件溯源與回放

### Phase 7: 整合與優化（Week 15-16）
**目標**: 端到端測試與生產部署
- [ ] 完整的端到端測試
- [ ] 性能優化與調校
- [ ] 生產環境部署
- [ ] 監控與告警

---

## 成功指標 (Success Metrics)

### 品質指標
| 指標 | 目標 | 測量方式 |
|------|------|---------|
| 輸出信心分數 | >0.8 佔比達 80% | `ConfidenceEstimator` 自動評估 |
| 品質閘門通過率 | >90% | `MetacognitiveGovernor` 統計 |
| 用戶滿意度 | 提升 20% | 用戶回饋調查 |
| 錯誤率 | 降低 30% | 線上錯誤監控 |

### 性能指標
| 指標 | 目標 | 測量方式 |
|------|------|---------|
| System 1 響應時間 | <3s | P95 latency |
| System 2 響應時間 | <15s | P95 latency |
| Agent 響應時間 | <5min | P95 latency |
| 並行度 | 提升 2x | 同時處理的認知項目數 |

### 學習指標
| 指標 | 目標 | 測量方式 |
|------|------|---------|
| 策略成功率提升 | 1 週內 >10% | `NeuromodulationSystem` 統計 |
| 路由準確度 | >85% | 人工標註 vs. 系統決策 |
| Cache 命中率 | 提升 15% | 情節記憶 hit rate |
| 類比推理成功率 | >60% | 成功遷移過去策略的比例 |

### 認知指標
| 指標 | 目標 | 測量方式 |
|------|------|---------|
| 工作空間利用率 | 70-90% | 注意力機制統計 |
| 平均迭代次數 | <1.5 | `MetacognitiveGovernor` 統計 |
| 跨 Processor 信息共享率 | >30% | 工作空間廣播事件統計 |
| 預測誤差降低 | >25% | Predictive Coding 誤差統計 |

---

## 風險與挑戰

### 技術風險

**R1: 系統複雜度大幅增加**
- **風險等級**: 高
- **緩解策略**:
  - 嚴格的模組化與介面定義
  - 完整的單元測試與整合測試
  - Feature Flags 允許逐步開啟功能

**R2: 性能開銷**
- **風險等級**: 中
- **緩解策略**:
  - 關鍵路徑優化（如注意力機制使用高效資料結構）
  - 非同步並行處理
  - 可配置的認知深度（快速模式 vs. 深度模式）

**R3: 不可預測性增加**
- **風險等級**: 中
- **緩解策略**:
  - 詳細的日誌與可觀測性
  - 決策過程可解釋性
  - 沙盒環境充分測試

### 組織風險

**R4: 學習曲線陡峭**
- **風險等級**: 中
- **緩解策略**:
  - 完整的開發者文檔
  - 內部培訓與工作坊
  - 逐步遷移而非 Big Bang

**R5: 維護成本增加**
- **風險等級**: 中
- **緩解策略**:
  - 良好的程式碼可讀性與註釋
  - 自動化測試覆蓋率 >80%
  - DevOps 自動化流程

---

## 向後兼容性策略

### 雙軌運行 (Dual Track)

```python
# 新舊系統並存
if feature_flags.is_enabled("cognitive.global_workspace"):
    # 新認知架構
    workspace = GlobalWorkspace()
    metacog = MetacognitiveGovernor(workspace)
    result = await cognitive_engine.process(task)
else:
    # 舊線性架構
    result = await legacy_engine.process(task)
```

### API 穩定性保證

- **外部 API 不變**：`/api/v1/process` 端點的請求/響應格式完全相容
- **內部重構**：所有變更在 `src/core/` 內部進行
- **逐步遷移**：Processor 一個一個遷移到新架構，不影響其他模組

### 回滾機制

```python
# Feature Flag 可即時關閉
if metacog.failure_rate > 0.1:  # 10% 失敗率
    logger.critical("Cognitive system failure rate too high, disabling")
    feature_flags.disable("cognitive.all")
    # 系統自動回退到舊架構
```

---

## 相關文檔

### 核心設計文檔
- [01_global_workspace_design.md](./01_global_workspace_design.md) - 全域工作空間詳細設計
- [02_metacognitive_governor.md](./02_metacognitive_governor.md) - 元認知治理層設計
- [03_ooda_loop_router.md](./03_ooda_loop_router.md) - OODA 循環路由設計
- [04_neuromodulation_system.md](./04_neuromodulation_system.md) - 神經調控系統設計
- [05_memory_systems.md](./05_memory_systems.md) - 記憶系統設計

### 實施文檔
- [08_implementation_roadmap.md](./08_implementation_roadmap.md) - 詳細實施路線圖
- [09_migration_strategy.md](./09_migration_strategy.md) - 遷移策略與風險管理
- [10_code_examples.md](./10_code_examples.md) - 程式碼範例與最佳實踐

### 參考資料
- [architectural_enhancements.md](./architectural_enhancements.md) - 初始架構優化建議
- [../06_architecture_and_design_document.md](../06_architecture_and_design_document.md) - 當前架構文檔

---

## 附錄：神經科學術語對照表

| 神經科學術語 | OpenAgent 對應組件 | 說明 |
|------------|------------------|------|
| Global Workspace | `GlobalWorkspace` | 意識信息的共享空間 |
| Prefrontal Cortex (PFC) | `MetacognitiveGovernor` | 執行控制與監控 |
| Basal Ganglia | `OODARouter` | 行為選擇與決策 |
| Hippocampus | `EpisodicMemory` | 情節記憶存儲 |
| Semantic Memory | `KnowledgeGraph` | 語義記憶與概念關聯 |
| Working Memory | `WorkingMemory` | 短期信息保持 |
| Dopamine System | `RewardSystem` | 獎勵學習與動機 |
| Norepinephrine | `UncertaintyDetector` | 不確定性偵測 |
| Attention Mechanism | `AttentionMechanism` | 注意力分配 |
| Predictive Coding | Prediction Error 計算 | 預測與實際的差異 |

---

**文檔維護者**: OpenAgent Architecture Team
**審核狀態**: Pending Review
**下次審核日期**: 2026-02-26
