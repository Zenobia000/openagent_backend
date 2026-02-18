# 架構差距深度分析 (GAP Analysis)

## 文檔編號
`COGNITIVE-ARCH-GAP-002`

**版本**: 2.0.0 (Manus Context Engineering Revised)
**最後更新**: 2026-02-14
**狀態**: 分析完成 (第二版 - 融合 Manus 生產經驗)
**基礎版本**: OpenAgent Backend v3.0 (Linus Refactored)
**參考來源**: [Manus Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents)

---

## 修訂說明 (V2 vs V1)

| 項目 | V1 (原始) | V2 (Manus 修訂) | 理由 |
|------|----------|-----------------|------|
| **核心框架** | 神經科學理論驅動 | **KV-Cache 工程驅動** | Manus 生產驗證 |
| **MetacogGovernor** | 5 組件系統 (~500 行) | **todo.md 覆誦模式 (~50 行)** | 0 新組件，同等效果 |
| **GlobalWorkspace** | 可變字典 + TTL | **Append-Only 檔案上下文** | KV-Cache 友好 |
| **OODA Router** | 動態 Processor 切換 | **Logit Mask 約束** | 不破壞 KV-Cache |
| **錯誤處理** | 替換失敗結果 | **保留錯誤在上下文中** | 模型隱式學習 |
| **記憶系統** | Vector DB + 知識圖譜 | **檔案系統即上下文** | 無限、持久、可逆 |
| **預估代碼量** | <2,000 行 | **<500 行** | 極簡主義 |

---

## 執行摘要 (Executive Summary)

### 核心發現

**v3.0 架構優勢（已完成）**：
- Linus 風格重構：數據自包含，無字典映射，模組化
- 清晰的 System 1/2/Agent 分層
- Feature Flags 系統已就緒
- ProcessorFactory 可擴展架構

**Manus 關鍵教訓（新增）**：
1. **KV-Cache 命中率是最重要的指標** — 快取 token 比重新計算便宜 10 倍
2. **Context 必須 append-only** — 任何中途修改都會摧毀快取
3. **檔案系統是最佳 Context 擴展** — 無限、持久、Agent 可操控
4. **todo.md 覆誦 = 元認知** — 推入近期注意力窗口，對抗 "lost in the middle"
5. **保留錯誤轉次** — 永不隱藏失敗，模型從錯誤中隱式學習
6. **結構性雜訊防止少樣本鎖定** — 變化模板、措辭，避免模式固化

**原始設計 vs Manus 的 6 大矛盾**：

| # | 矛盾 | 嚴重度 | Manus 原則 | 原始設計 |
|---|------|--------|-----------|---------|
| 1 | KV-Cache 摧毀 | CRITICAL | append-only context | GlobalWorkspace 動態修改 |
| 2 | 工具集切換 | CRITICAL | mask, don't remove | OODA 動態 Processor 切換 |
| 3 | 元認知過度設計 | SEVERE | todo.md 覆誦 | 5 組件 Governor |
| 4 | 錯誤處理 | MODERATE | 保留錯誤在 context | 替換/覆寫失敗結果 |
| 5 | 記憶系統 | MODERATE | 檔案系統 | Vector DB + 知識圖譜 |
| 6 | 少樣本陷阱 | MODERATE | 結構性雜訊注入 | RL 探索-利用 |

**修訂後最小化建議**：
- **Phase 1 (P0)**：Context Engineering 基礎（append-only + todo.md + 錯誤保留）
- **Phase 2 (P1)**：Logit Masking + 結構性雜訊
- **暫不做 (P2-P3)**：Memory Systems, Neuromodulation, Event-Driven, 完整 OODA

---

## 1. 架構全景對比（三方比較）

### 1.1 當前架構 (v3.0)

```
RefactoredEngine
  +-- DefaultRouter (keyword-based)
  +-- ProcessorFactory
  |     +-- ChatProcessor
  |     +-- SearchProcessor
  |     +-- ThinkingProcessor
  |     +-- CodeProcessor
  |     +-- DeepResearchProcessor
  +-- ModelRuntime (System 1/2)
  +-- AgentRuntime (Agent)
  +-- FeatureFlags
  +-- CognitiveMetrics
```

**特點**：
- 簡潔、可預測、易調試
- 每個 Processor 孤立運行
- 無元認知、無共享狀態

### 1.2 原始目標架構（類人類認知 - 已過時）

```
MetacognitiveGovernor         <-- 過度設計
  +-- ConfidenceEstimator
  +-- QualityMonitor
  +-- StrategyController
  +-- BudgetManager
GlobalWorkspace               <-- 破壞 KV-Cache
  +-- WorkingMemory
  +-- AttentionMechanism
  +-- Blackboard
  +-- BroadcastChannel
OODARouter                    <-- 破壞 KV-Cache
  +-- Observe -> Orient -> Decide -> Act
MemorySystems                 <-- 過早優化
  +-- EpisodicMemory
  +-- SemanticMemory
  +-- ProceduralMemory
NeuromodulationSystem         <-- 炫耀理論
  +-- Dopamine/Norepinephrine/Serotonin
```

**Linus 批判 + Manus 驗證**：
> 6 層架構、16 週、10,000+ 行代碼 — 這不是在解決問題，是在建造大教堂。
> Manus 在生產環境中用 todo.md 一個檔案達到了同等的「元認知」效果。

### 1.3 修訂目標架構（Context Engineering - 推薦）

```
RefactoredEngine (v3.0 保持不變)
  +-- DefaultRouter (保持 keyword-based)
  |     +-- ToolAvailabilityMask (新增：logit mask)
  +-- ProcessorFactory (保持不變)
  |     +-- 所有工具始終定義，用前綴分組
  +-- ContextManager (新增，<200 行)
  |     +-- append_only_history (只增不刪)
  |     +-- todo_recitation (todo.md 覆誦)
  |     +-- error_preservation (錯誤保留)
  +-- TemplateRandomizer (新增，<100 行)
  |     +-- 結構性雜訊注入
  +-- ModelRuntime / AgentRuntime (保持不變)
  +-- FeatureFlags (保持不變)
  +-- CognitiveMetrics (保持不變)
```

**核心差異**：
- 0 個新的「認知組件」 — 只有 Context 管理
- <500 行新代碼
- 完全 KV-Cache 友好
- 向後兼容 v3.0

---

## 2. 逐矛盾深度分析

### 矛盾 1: KV-Cache 摧毀 (CRITICAL)

#### 問題

**原始設計**：GlobalWorkspace 使用可變字典 + TTL 過期清理 + 廣播/衰減
```python
# 原始 GlobalWorkspace - 違反 append-only
class GlobalWorkspace:
    def post(self, item):
        self.items[item.type].append(item)
        self._cleanup_expired(item.type)  # <-- 中途刪除！

    def _cleanup_expired(self, item_type):
        self.items[item_type] = [       # <-- 重寫列表！
            i for i in self.items[item_type] if not i.is_expired()
        ]
```

**為何致命**：
- 每次 `_cleanup_expired()` 都修改了歷史 context
- LLM 的 KV-Cache 基於前綴匹配：context 中任何位置的改動都會使後續所有 cache 失效
- Manus 數據：快取 token $0.30/MTok vs 非快取 $3.00/MTok — **10 倍成本差異**

#### Manus 原則
> "KV-Cache 的運作方式很簡單：只要你的 prompt 與之前的 prompt 共享相同的前綴，
> 那個前綴的計算就可以被複用。因此，保持 context 前綴的穩定是最重要的。"

#### 修正方案

```python
# Manus-aligned: AppendOnlyContext
class ContextManager:
    """
    Context 管理 - append-only, KV-Cache friendly

    Rule 1: Never modify history
    Rule 2: Never delete entries
    Rule 3: All compression must be reversible (write to file)
    """

    def __init__(self):
        self._entries: list[ContextEntry] = []  # Append-only list

    def append(self, entry: ContextEntry):
        """Append to context. Never modify existing entries."""
        self._entries.append(entry)

    def get_context(self) -> list[ContextEntry]:
        """Return full context. Read-only view."""
        return self._entries  # No filtering, no expiry, no mutation

    def compress_to_file(self, filepath: str):
        """
        When context is too large, compress OLD entries to file.
        This is reversible: agent can read the file to recover.
        """
        old_entries = self._entries[:-10]  # Keep last 10 in memory
        with open(filepath, 'w') as f:
            json.dump([e.to_dict() for e in old_entries], f)
        # Keep reference in context (not deletion!)
        self._entries = [
            ContextEntry(type="compressed", content=f"Previous context saved to {filepath}"),
            *self._entries[-10:]
        ]
```

**效果**：
- KV-Cache 命中率接近 100%（前綴永遠穩定）
- 成本降低最高 10 倍
- 0 個新的「認知組件」

---

### 矛盾 2: 工具集切換 (CRITICAL)

#### 問題

**原始設計**：OODA Router 在執行中動態切換 Processor
```python
# OODA Router - 動態切換破壞 KV-Cache
class OODARouter:
    async def re_route(self, context):
        # Act 階段發現需要不同的 Processor
        new_mode = self._decide(context)
        processor = self.factory.get_processor(new_mode)  # <-- 切換！
        return await processor.process(context)            # <-- Cache 失效！
```

**為何致命**：
- 不同 Processor 有不同的 system prompt 和工具定義
- 切換 Processor = 改變 context 前綴 = KV-Cache 完全失效
- Manus 發現：頻繁切換工具集造成的性能損失遠超其帶來的準確度提升

#### Manus 原則
> "永遠不要在運行中動態增減工具。改用 logit mask。
> 通過一致的工具名稱前綴（browser_*、shell_*），可以在不改變 context 的前提下
> 約束工具選擇。"

#### 修正方案

```python
# Manus-aligned: All tools always defined, mask unused
class ToolAvailabilityMask:
    """
    Logit masking - constrain tool selection without changing context.

    All tools are ALWAYS in the prompt (stable prefix).
    Mode determines which tools are allowed via mask.
    """

    # Tool prefix groups
    TOOL_GROUPS = {
        "chat": ["chat_*"],
        "search": ["chat_*", "search_*", "web_*"],
        "code": ["chat_*", "code_*", "shell_*"],
        "thinking": ["chat_*", "search_*", "code_*"],
        "knowledge": ["chat_*", "search_*"],
    }

    def get_allowed_tools(self, mode_name: str) -> list[str]:
        """Return allowed tool prefixes for this mode."""
        return self.TOOL_GROUPS.get(mode_name, ["chat_*"])

    def mask_tool_call(self, mode_name: str, tool_name: str) -> bool:
        """Check if a tool call is allowed for this mode."""
        allowed = self.get_allowed_tools(mode_name)
        return any(
            tool_name.startswith(prefix.rstrip("*"))
            for prefix in allowed
        )
```

**效果**：
- System prompt 永不改變（所有工具始終定義）
- KV-Cache 前綴完全穩定
- DefaultRouter 保持不變，只加一層 mask

**與 DefaultRouter 的整合**：
```python
# router.py - 無需替換，只需擴展
class DefaultRouter(RouterProtocol):
    def __init__(self, feature_flags=None):
        self._flags = feature_flags or default_flags
        self._complexity_analyzer = ComplexityAnalyzer()
        self._tool_mask = ToolAvailabilityMask()  # 新增

    async def route(self, request: Request) -> RoutingDecision:
        decision = ...  # existing logic unchanged

        # Attach tool mask to decision (non-breaking addition)
        decision.allowed_tools = self._tool_mask.get_allowed_tools(
            decision.mode.name
        )
        return decision
```

---

### 矛盾 3: 元認知過度設計 (SEVERE)

#### 問題

**原始設計**：5 組件的 MetacognitiveGovernor
```
MetacognitiveGovernor (~500 行)
  +-- ConfidenceEstimator (多因子加權)
  +-- QualityMonitor (閾值檢查)
  +-- StrategyController (策略選擇)
  +-- BudgetManager (預算控制)
  +-- PredictiveCoding (預測誤差)
```

**為何過度**：
- Manus 用 `todo.md` 一個檔案達到了相同效果
- 自信心估計本身就是一個 LLM 任務 — 讓 LLM 自己判斷更準確
- 5 個組件的複雜度遠超收益

#### Manus 原則
> "我們發現 Agent 經常在長 context 中迷失方向。
> 解決方法出奇地簡單：讓 Agent 在每一步都更新 todo.md。
> 這將目標推入 context 的最近位置，維持注意力聚焦。"

#### 修正方案：todo.md 覆誦模式

```python
# Replaces entire MetacognitiveGovernor with ~50 lines
class TodoRecitation:
    """
    todo.md recitation pattern - push goals into recent attention window.

    This is NOT a file on disk. It's a context management technique:
    1. Before each LLM call, prepend current objectives
    2. After each LLM call, let the model update its plan
    3. The updated plan appears at the END of context (most attended)

    Achieves same effect as MetacognitiveGovernor:
    - Self-monitoring (agent sees its own progress)
    - Quality gate (agent checks off completed items)
    - Strategy adjustment (agent reprioritizes remaining items)
    """

    def __init__(self):
        self.current_plan: str = ""

    def create_initial_plan(self, query: str) -> str:
        """Generate initial plan from user query."""
        return f"""## Current Task
{query}

## Plan
- [ ] Understand the question
- [ ] Gather relevant information
- [ ] Formulate response
- [ ] Verify answer quality

## Status: Starting
"""

    def build_recitation_prefix(self) -> str:
        """Prefix to add before each LLM call."""
        if not self.current_plan:
            return ""
        return f"""[CURRENT PROGRESS]
{self.current_plan}
[END PROGRESS]

Continue working on the above plan. Update the plan as you make progress.
"""

    def update_plan(self, llm_output: str):
        """Extract updated plan from LLM output (if present)."""
        # Simple: look for markdown checklist in output
        if "## Plan" in llm_output or "- [" in llm_output:
            # Extract plan section
            lines = llm_output.split("\n")
            plan_lines = [l for l in lines if l.startswith("- [")]
            if plan_lines:
                self.current_plan = "\n".join(plan_lines)
```

**效果**：
- 0 個新組件
- ~50 行代碼（vs 原始 ~500 行）
- 利用 LLM 自身能力做品質判斷
- Context 位置最優（最近位置 = 最高注意力）

---

### 矛盾 4: 錯誤處理 (MODERATE)

#### 問題

**原始設計**：精煉時替換上下文
```python
# 原始 MetacogGovernor - 替換歷史
async def process_with_monitoring(self, processor, context):
    result = await processor.process(context)
    if confidence.is_low:
        # 替換原始請求！
        context.request = refine_request   # <-- 歷史被修改
        result = await processor.process(context)
        context.request = old_request      # <-- 偷偷恢復
```

**為何有害**：
- 模型看不到自己之前的失敗嘗試
- 失去了「隱式學習」的機會
- 違反 append-only 原則

#### Manus 原則
> "永遠不要從 context 中移除失敗的行動。保留完整的嘗試記錄。
> 模型從看到自己的錯誤中隱式地學到避免重複同樣的錯誤。"

#### 修正方案

```python
# Manus-aligned: Append failed attempt, never replace
class ErrorPreservation:
    """
    Keep all attempts (including failures) in context.

    The model learns implicitly from seeing its own mistakes.
    """

    def build_retry_context(
        self,
        original_query: str,
        failed_result: str,
        error_info: str = "",
    ) -> str:
        """Build retry prompt that INCLUDES the failed attempt."""
        return f"""Previous attempt to answer "{original_query}":

{failed_result}

{f"Error: {error_info}" if error_info else "The previous answer was incomplete or low quality."}

Please provide an improved answer. Learn from the issues in the previous attempt.
"""
```

**效果**：
- Context 只增不刪
- 模型隱式學習避免重複錯誤
- 0 個新組件（只是改變 prompt 組裝方式）

---

### 矛盾 5: 記憶系統 (MODERATE)

#### 問題

**原始設計**：Vector DB + 知識圖譜
```
MemorySystems
  +-- EpisodicMemory (向量數據庫)
  +-- SemanticMemory (知識圖譜)
  +-- ProceduralMemory (策略庫)
```

**為何過度**：
- 引入外部依賴（Vector DB 部署、維護）
- 知識圖譜構建需要大量人工
- 當前 LLM context window 已經足夠大（128k+ tokens）

#### Manus 原則
> "檔案系統是我們發現的最被低估的 context 形式。
> 它是無限的、持久的、Agent 可自由操控的。
> 所有壓縮必須可逆 — Agent 隨時可以回讀。"

#### 修正方案

```python
# File system as memory - zero new infrastructure
class FileBasedMemory:
    """
    Use file system as memory. No Vector DB needed.

    - context/*.md = reversible compression
    - history/*.jsonl = episodic memory
    - patterns/*.md = procedural memory (agent-written)
    """

    def __init__(self, workspace_dir: str = ".agent_workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)

    def save_context(self, filename: str, content: str):
        """Save context to file (reversible compression)."""
        filepath = self.workspace_dir / filename
        filepath.write_text(content)
        return str(filepath)

    def load_context(self, filename: str) -> str:
        """Load previously saved context."""
        filepath = self.workspace_dir / filename
        if filepath.exists():
            return filepath.read_text()
        return ""

    def append_history(self, entry: dict):
        """Append to history (append-only JSONL)."""
        filepath = self.workspace_dir / "history.jsonl"
        with open(filepath, 'a') as f:
            f.write(json.dumps(entry) + "\n")
```

**效果**：
- 0 個新外部依賴
- 檔案系統天然持久
- Agent 可以讀/寫自己的記憶
- 所有壓縮可逆

---

### 矛盾 6: 少樣本陷阱 (MODERATE)

#### 問題

**原始設計**：Neuromodulation RL 探索-利用
```
NeuromodulationSystem
  +-- UCB / epsilon-greedy
  +-- Reward Learning
```

**為何過度**：
- RL 需要大量數據
- 探索-利用問題在 Agent 場景中幾乎不存在

#### Manus 原則
> "如果你在 prompt 中放了 2-3 個相似的例子，
> LLM 會『鎖定』到那個格式，即使你不希望它。
> 引入結構性雜訊：變化的模板、不同的措辭、多種格式。"

#### 修正方案

```python
# Structural noise injection - prevent few-shot lock-in
class TemplateRandomizer:
    """
    Prevent few-shot pattern lock-in by introducing structural variation.

    Instead of RL exploration-exploitation:
    - Randomize prompt templates
    - Vary example formatting
    - Use different phrasings for same instruction
    """

    _SYSTEM_TEMPLATES = [
        "You are a helpful assistant. {instruction}",
        "As an AI assistant, please {instruction}",
        "{instruction} Be thorough and accurate.",
        "Task: {instruction}. Provide a clear response.",
    ]

    _QUALITY_REMINDERS = [
        "Ensure your answer is accurate and well-structured.",
        "Double-check your response for completeness.",
        "Provide a thorough and reliable answer.",
        "Be precise and comprehensive in your response.",
    ]

    def randomize_template(self, instruction: str) -> str:
        """Select a random template to prevent pattern lock-in."""
        import random
        template = random.choice(self._SYSTEM_TEMPLATES)
        reminder = random.choice(self._QUALITY_REMINDERS)
        return f"{template.format(instruction=instruction)}\n\n{reminder}"
```

**效果**：
- ~30 行代碼（vs RL 系統 1500+ 行）
- 防止模式固化
- 0 外部依賴

---

## 3. 修訂優先級矩陣

### 3.1 投入產出分析（Manus 修訂版）

| 組件 | 投入 | 收益 | ROI | 優先級 | 來源 |
|------|------|------|-----|--------|------|
| **ContextManager (append-only)** | 0.5 週 | KV-Cache 10x 省成本 | 極高 | P0 | Manus 原則 1 |
| **TodoRecitation** | 0.5 週 | 等同 MetacogGovernor | 極高 | P0 | Manus 原則 4 |
| **ErrorPreservation** | 0.5 週 | 隱式學習提升品質 | 高 | P0 | Manus 原則 5 |
| **ToolAvailabilityMask** | 1 週 | 保護 KV-Cache | 高 | P1 | Manus 原則 2 |
| **TemplateRandomizer** | 0.5 週 | 防止模式鎖定 | 中 | P1 | Manus 原則 6 |
| **FileBasedMemory** | 1 週 | 替代 Vector DB | 中 | P1 | Manus 原則 3 |
| ~~MetacogGovernor~~ | ~~2 週~~ | ~~同 TodoRecitation~~ | ~~低~~ | ~~已廢止~~ | Manus 矛盾 3 |
| ~~GlobalWorkspace~~ | ~~2 週~~ | ~~破壞 KV-Cache~~ | ~~負~~ | ~~已廢止~~ | Manus 矛盾 1 |
| ~~OODA Router~~ | ~~2-8 週~~ | ~~破壞 KV-Cache~~ | ~~負~~ | ~~已廢止~~ | Manus 矛盾 2 |
| Memory Systems | 8 週 | 2% | 極低 | P3 不做 | - |
| Neuromodulation | 6 週 | 0% | 0 | P3 不做 | - |
| Event-Driven | 4 週 | 0% | 0 | P3 不做 | - |

### 3.2 V1 vs V2 對比

| 指標 | V1 計劃 | V2 計劃 (Manus) | 改善 |
|------|---------|-----------------|------|
| 實施時長 | 6 週 | **4 週** | -33% |
| 代碼量 | <2,000 行 | **<500 行** | -75% |
| 新組件數 | 3 個 | **0 個** (只有工具類) | -100% |
| 投入人天 | 35 人天 | **15 人天** | -57% |
| KV-Cache 影響 | 負面（破壞快取） | **正面（保護快取）** | 質變 |
| 風險 | 低 | **極低** | 更安全 |
| 回滾難度 | 中（新組件需移除） | **極易（Feature Flag）** | 更簡單 |

### 3.3 風險評估

| 組件 | 複雜度 | 破壞性 | KV-Cache 影響 | 總風險 |
|------|--------|--------|--------------|-------|
| ContextManager | 極低 | 無 | 正面 | 極低 |
| TodoRecitation | 極低 | 無 | 正面 | 極低 |
| ErrorPreservation | 極低 | 無 | 正面 | 極低 |
| ToolAvailabilityMask | 低 | 無 | 正面 | 低 |
| TemplateRandomizer | 極低 | 無 | 中性 | 極低 |
| FileBasedMemory | 低 | 無 | 正面 | 低 |
| ~~GlobalWorkspace~~ | ~~中~~ | ~~低~~ | ~~負面~~ | ~~中~~ |
| ~~MetacogGovernor~~ | ~~中~~ | ~~低~~ | ~~負面~~ | ~~中~~ |

---

## 4. 修訂架構演進路徑

### 4.1 Phase 0: 當前狀態（v3.0 - 不變）

```
RefactoredEngine
  +-- DefaultRouter (keyword-based)
  +-- ProcessorFactory
  +-- ModelRuntime / AgentRuntime
  +-- FeatureFlags
  +-- CognitiveMetrics
```

### 4.2 Phase 1: Context Engineering 基礎（v3.1）

```
RefactoredEngine
  +-- DefaultRouter (不變)
  +-- ProcessorFactory (不變)
  +-- ContextManager (新增)           <-- append-only
  |     +-- append_only_history
  |     +-- compress_to_file
  +-- TodoRecitation (新增)            <-- 替代 MetacogGovernor
  |     +-- create_initial_plan
  |     +-- build_recitation_prefix
  |     +-- update_plan
  +-- ErrorPreservation (新增)         <-- 保留錯誤
  |     +-- build_retry_context
  +-- ModelRuntime / AgentRuntime (不變)
```

**新增能力**：
- KV-Cache 友好的 context 管理
- 自我監控（todo.md 覆誦）
- 從錯誤中學習
- ~150 行新代碼

### 4.3 Phase 2: 工具約束與雜訊注入（v3.2）

```
RefactoredEngine
  +-- DefaultRouter
  |     +-- ToolAvailabilityMask (新增)  <-- logit mask
  +-- ContextManager
  +-- TodoRecitation
  +-- ErrorPreservation
  +-- TemplateRandomizer (新增)          <-- 防止鎖定
  +-- FileBasedMemory (新增)             <-- 替代 Vector DB
```

**新增能力**：
- 模式約束不破壞 KV-Cache
- 防止少樣本鎖定
- 檔案系統記憶
- ~300 行新代碼（累計 ~450 行）

### 4.4 Phase 3: 未來擴展（v4.0+ - 條件觸發）

```
RefactoredEngine
  +-- EnhancedRouter (條件觸發：DefaultRouter 準確度 <70%)
  +-- ContextManager
  +-- TodoRecitation
  +-- ErrorPreservation
  +-- TemplateRandomizer
  +-- FileBasedMemory
  +-- [可選] 輕量級 ConfidenceEstimator (條件觸發：todo.md 不足以判斷品質)
```

**觸發條件**：
- DefaultRouter 準確度 <70% → 考慮增強路由
- 用戶明確要求跨 session 記憶 → FileBasedMemory 持久化
- 生產數據顯示品質問題 → 輕量級信心估計

---

## 5. Linus 風格檢查清單（Manus 增強版）

### 5.1 真實性檢查
- [ ] **這是真問題嗎？** 有用戶抱怨？有數據證明？
- [ ] **問題嚴重嗎？** 影響 >10% 的用戶？
- [ ] **有更簡單的方法嗎？** 能用 50 行解決的不要寫 500 行

### 5.2 Context Engineering 檢查（新增）
- [ ] **Context 是 append-only 嗎？** 沒有中途刪除或修改？
- [ ] **KV-Cache 前綴穩定嗎？** System prompt + 工具定義不變？
- [ ] **壓縮可逆嗎？** Agent 能恢復被壓縮的 context？
- [ ] **錯誤被保留嗎？** 失敗的嘗試仍在 context 中？

### 5.3 設計檢查
- [ ] **數據自包含？** 沒有字典映射？沒有特殊情況？
- [ ] **消除了特殊情況？** 所有路徑用同樣邏輯處理？
- [ ] **函數 <50 行？** 文件 <500 行？

### 5.4 實施檢查
- [ ] **可以回滾嗎？** Feature Flag 保護？
- [ ] **會破壞什麼嗎？** API 相容？測試通過？
- [ ] **性能開銷 <10%？** 性能測試通過？

### 5.5 價值檢查
- [ ] **ROI > 3:1？** 投入 1 週，收益 >3 週？
- [ ] **用戶可感知？** 用戶會注意到改進嗎？
- [ ] **可量化？** 有明確的成功指標？

---

## 6. 成功指標定義

### 6.1 Phase 1 成功標準（Context Engineering 基礎）

| 指標 | 基線 (v3.0) | 目標 (v3.1) | 測量方式 |
|------|------------|------------|---------|
| KV-Cache 命中率 | 未知 | >80% | API 計費分析 |
| Token 成本 | 基線 | -30% | 月度帳單對比 |
| 品質保持率 | 基線 | >=基線 | 人工評估 |
| 性能開銷 | 0ms | <50ms | P95 延遲 |
| 新增代碼量 | - | <200 行 | git diff --stat |

### 6.2 Phase 2 成功標準

| 指標 | 基線 | 目標 | 測量方式 |
|------|------|------|---------|
| 工具選擇正確率 | 基線 | >=基線 | 日誌分析 |
| 模式多樣性 | 基線 | +20% | 回覆模板分布 |
| KV-Cache 命中率 | >80% | >90% | API 分析 |
| 新增代碼量（累計） | <200 | <500 行 | git diff --stat |

---

## 7. 結論與建議

### 7.1 核心發現

**Manus 的生產經驗顛覆了原始設計**：
- 原始設計基於**神經科學理論**（全域工作空間理論、元認知理論）
- Manus 基於**KV-Cache 工程現實**（append-only、成本優化）
- **理論與實踐衝突時，實踐勝出。每一次。**

**真正需要的不是「認知組件」，而是「Context Engineering」**：
- 不需要 MetacognitiveGovernor → 需要 todo.md 覆誦
- 不需要 GlobalWorkspace → 需要 append-only context
- 不需要 OODA Router → 需要 logit masking
- 不需要 MemorySystems → 需要 file system
- 不需要 Neuromodulation → 需要 structural noise

### 7.2 最終建議

**推薦路徑：Context Engineering First**

```yaml
Phase 1 (2 週): Context Engineering 基礎
  ContextManager (append-only context)
  TodoRecitation (todo.md 覆誦)
  ErrorPreservation (錯誤保留)
  - 預估：<200 行，2 週

Phase 2 (2 週): 工具約束與雜訊
  ToolAvailabilityMask (logit masking)
  TemplateRandomizer (結構性雜訊)
  FileBasedMemory (檔案系統記憶)
  - 預估：<300 行，2 週

Phase 3 (未來): 條件觸發
  [條件] EnhancedRouter (如果準確度 <70%)
  [條件] ConfidenceEstimator (如果 todo.md 不夠)
```

**不推薦**：
```yaml
- 一次性實施 16 週完整認知架構
- 實施 GlobalWorkspace（破壞 KV-Cache）
- 實施 MetacognitiveGovernor（todo.md 更簡單）
- 實施 OODA Router（Logit mask 更安全）
- 實施 Memory Systems（過早優化）
- 實施 Neuromodulation（炫耀理論）
```

### 7.3 下一步行動

1. **Phase 1 立即開始**：
   - 實現 ContextManager（append-only）
   - 實現 TodoRecitation（todo.md 覆誦）
   - 實現 ErrorPreservation（錯誤保留）

2. **測量效果**：
   - KV-Cache 命中率
   - Token 成本變化
   - 品質變化（人工評估）

3. **數據驅動 Phase 2**：
   - 基於 Phase 1 數據決定是否需要 Phase 2
   - 如果 Phase 1 已經足夠，不做 Phase 2

---

**文檔維護者**: OpenAgent Architecture Team
**審核狀態**: Revised (V2 - Manus Aligned)
**下次審核日期**: 2026-02-28

---

## 附錄 A: 術語對照表（修訂版）

| 原始設計術語 | Manus 對應 | v3.0 對應 | 修訂後方案 |
|-------------|-----------|----------|-----------|
| MetacognitiveGovernor | todo.md recitation | 不存在 | TodoRecitation (~50 行) |
| GlobalWorkspace | Append-only context | 不存在 | ContextManager (~100 行) |
| OODA Router | Logit masking | DefaultRouter | ToolAvailabilityMask (~50 行) |
| MemorySystems | File system | 不存在 | FileBasedMemory (~50 行) |
| Neuromodulation | Structural noise | 不存在 | TemplateRandomizer (~30 行) |
| BroadcastChannel | 不需要 | 不存在 | 不實施 |
| AttentionMechanism | KV-Cache attention | 不存在 | Context 位置管理 |

## 附錄 B: 代碼行數估算（修訂版）

| 組件 | V1 估算 | V2 估算 (Manus) | 減少 |
|------|---------|-----------------|------|
| ContextManager | 300 (Workspace) | **100** | -67% |
| TodoRecitation | 500 (Governor) | **50** | -90% |
| ErrorPreservation | 含在 Governor | **30** | - |
| ToolAvailabilityMask | 500 (Router) | **50** | -90% |
| TemplateRandomizer | 1500 (Neuro) | **30** | -98% |
| FileBasedMemory | 3000 (Memory) | **50** | -98% |
| **總計** | **5,800** | **310** | **-95%** |

## 附錄 C: 參考資料

- OpenAgent v3.0 架構代碼
- [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents)
- 類人類思維架構設計文檔（00-11）— 作為理論參考
- Linus Torvalds 技術哲學
- 80/20 原則（Pareto Principle）
