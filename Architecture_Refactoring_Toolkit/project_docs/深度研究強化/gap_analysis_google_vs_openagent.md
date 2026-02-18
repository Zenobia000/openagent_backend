# Deep Research Gap Analysis: Google Deep Research vs OpenAgent

**Date**: 2026-02-18
**Branch**: refactor/architecture-v2-linus-style
**Benchmark Query**: 「2026年藍領垂直領域平台服務轉型報告」

---

## 1. Executive Summary

以同一查詢分別送入 Google Deep Research 和 OpenAgent Deep Research，Google 產出了一份約 6,000 字、30+ 引用、5 張結構化表格、涵蓋技術架構 / 商業模式 / 勞動經濟 / 未來展望的完整報告。OpenAgent 目前的架構在搜尋基礎設施和骨架上具備合理設計（多引擎降級、SSE streaming、retry 機制），但在**研究深度、資訊保留率、跨領域合成能力**三個維度存在顯著差距。

核心問題不在於「缺少功能」，而在於**資訊流的瓶頸**：從搜尋結果到最終報告的過程中，資料被過度壓縮，LLM 只看到碎片化的摘要而非完整上下文，導致合成品質受限。

---

## 2. Google Deep Research 逆向工程

### 2.1 可觀察的行為特徵

Google Deep Research 在執行過程中展現以下可觀察特徵：

1. **Research Plan 展示**：執行前向使用者展示結構化研究計劃（章節大綱 + 每節預期內容）
2. **多波次漸進式搜尋**：非一次性搜尋，而是根據已有發現動態生成後續查詢（observable: 搜尋過程持續數分鐘，中間有 "thinking" 狀態更新）
3. **Thinking Chain 可見性**：每個階段都展示「正在思考什麼」，不是黑箱
4. **30+ 來源引用**：最終報告引用大量真實來源（`^^` 標記），顯示實際抓取了大量網頁內容
5. **跨領域合成**：報告不只回答「藍領平台」，還交叉分析了 AI 工具（Claude Cowork/Manus）、工作流框架（n8n）、經濟學（SaaS→SaaP）、勞動市場重構
6. **結構化比較表**：5 張 Markdown 表格，做了多維度交叉比較
7. **前瞻性分析**：不只描述現狀，還做了 2026-2030 趨勢預測
8. **可操作建議**：最後一張表是 5 步行動清單，每步有目標和工具推薦

### 2.2 推斷的架構設計（First Principles）

基於上述可觀察行為，逆向推斷其核心機制：

```
┌───────────────────────────────────────────────────────┐
│                  Google Deep Research                  │
│                                                       │
│  [1] Query → Research Plan Generation                 │
│       └─ 結構化大綱 + 每節研究目標                      │
│       └─ 展示給使用者確認                               │
│                                                       │
│  [2] Research Plan → Multi-wave Search                │
│       └─ Wave 1: 基礎查詢 (5-8 queries)               │
│       └─ Wave 2: Gap-filling queries (基於 Wave 1)     │
│       └─ Wave 3: Cross-domain queries (跨領域補充)      │
│       └─ 每波之間有 intermediate synthesis              │
│                                                       │
│  [3] Full-content Extraction                          │
│       └─ 不只讀 snippet，完整抓取頁面內容               │
│       └─ 保留原始數據、表格、數字                       │
│       └─ 可能使用 long-context model (1M+ tokens)      │
│                                                       │
│  [4] Progressive Synthesis                            │
│       └─ 每波搜尋後做 intermediate synthesis            │
│       └─ 識別知識缺口 → 生成補充查詢                    │
│       └─ 維護「已知/未知」知識圖                        │
│                                                       │
│  [5] Cross-domain Integration                         │
│       └─ 識別查詢涉及的所有領域                         │
│       └─ 為每個領域生成專門的搜尋策略                    │
│       └─ 最終合成時強制跨領域交叉分析                    │
│                                                       │
│  [6] Structured Report Generation                     │
│       └─ 遵循 research plan 的章節結構                  │
│       └─ 每節有深度約束 (≥500 words)                    │
│       └─ 強制包含：表格比較、具體數據、引用              │
│       └─ 自動生成前瞻性分析和行動建議                    │
│                                                       │
│  [7] Quality Gate                                     │
│       └─ 報告完成度檢查 (coverage rubric)               │
│       └─ 引用密度檢查                                   │
│       └─ 可能有 self-critique → revision cycle          │
└───────────────────────────────────────────────────────┘
```

### 2.3 Google 的核心優勢歸納

| 維度                 | Google 的做法                  | 為什麼有效                       |
| -------------------- | ------------------------------ | -------------------------------- |
| **資訊保留**   | 全文抓取 + long-context model  | LLM 能看到原始數據，不丟失細節   |
| **搜尋深度**   | 多波次漸進 + gap-based 補充    | 確保每個子主題都有足夠資料       |
| **跨領域**     | 自動識別 + 分域搜尋            | 報告不侷限於單一視角             |
| **合成品質**   | Progressive synthesis          | 每步都在更新理解，不是最後才合成 |
| **結構化輸出** | 強制表格/比較/前瞻             | 報告的實用性和可讀性極高         |
| **來源可信度** | 大量真實來源 + inline citation | 每個主張都有支撐                 |

---

## 3. OpenAgent 現狀分析

### 3.1 架構流程 (As-Is)

```
Query
  │
  ├─ [1] _should_clarify() ── 靜態關鍵詞判斷
  │     └─ _ask_clarifying_questions() ── 生成但從未發送給使用者
  │
  ├─ [2] _write_report_plan() ── LLM 生成章節大綱
  │
  ├─ [3] Loop (max 3 iterations):
  │     ├─ _generate_serp_queries() / _generate_followup_queries()
  │     ├─ _execute_search_tasks() ── 平行批次搜尋
  │     └─ _review_research_completeness() ── 二元 YES/NO 判斷
  │
  ├─ [4] _requires_critical_analysis() ── 靜態關鍵詞觸發
  │     └─ _critical_analysis_stage() ── 多角度批判
  │
  ├─ [5] _requires_computational_analysis() ── LLM 動態判斷
  │     └─ _computational_analysis_stage() ── Sandbox 執行
  │
  └─ [6] _write_final_report() ── 一次性合成
        ├─ _build_academic_report_prompt()
        ├─ _analyze_citations()
        └─ _format_report_with_categorized_references()
```

### 3.2 品質評分

| 維度       | 評分   | 說明                                              |
| ---------- | ------ | ------------------------------------------------- |
| 架構設計   | 8.5/10 | 模組化清晰、retry/fallback/SSE 完整               |
| 搜尋基礎   | 7.5/10 | 多引擎支持、平行搜尋、race mode                   |
| 資訊保留率 | 3/10   | **致命瓶頸** — 200 chars 截斷 × 5 results |
| 合成品質   | 5/10   | 一次性合成、無 intermediate synthesis             |
| 跨領域能力 | 4/10   | 無領域識別、無分域搜尋策略                        |
| 輸出結構   | 6/10   | 有學術格式但無強制表格/比較要求                   |
| 動態適應   | 5/10   | completeness review 過於粗糙                      |

---

## 4. Gap Analysis: 逐層對比

### Gap 1: 資訊保留率 (Critical — 最大瓶頸)

**問題根源**: `_summarize_search_results()` (processor.py:501-513)

```python
# 現狀：只取前 5 個結果，每個截斷 200 chars
for i, result in enumerate(search_results[:5], 1):
    content_preview = content[:200] + "..."
```

**影響**: 假設搜尋了 15 個查詢，每個返回 10 個來源，每個來源有 2000 chars 內容：

- 原始資訊量: 15 × 10 × 2000 = 300,000 chars
- 經過截斷後: 5 × 200 = 1,000 chars
- **資訊保留率: 0.33%**

Google 則可能保留 50-80% 的原始資訊（long-context model），這就是品質差距的數學根源。

**Google 的做法**: 全文抓取 + Gemini 的 1M token context window，LLM 直接看到完整原始內容。

**修復方向**:

1. 將 `_summarize_search_results` 的截斷閾值從 200 提高到 2000+
2. 使用 result 數量從 5 提高到全部（或至少 15）
3. 在 `_prepare_report_context` 中保留完整的 `processed` 和 `summary`
4. 考慮分段合成：先對每個子主題的搜尋結果做 intermediate synthesis，再合成最終報告

---

### Gap 2: 漸進式合成 vs 一次性合成

**問題根源**: 整個 workflow 的 search loop 只做「搜尋 → 判斷夠不夠 → 繼續搜」，沒有 intermediate synthesis 步驟。

**現狀流程**:

```
Search Wave 1 → 結果堆積
Search Wave 2 → 結果繼續堆積
Search Wave 3 → 結果繼續堆積
──── 全部丟給 LLM 一次合成 ────
```

**Google 推斷流程**:

```
Search Wave 1 → Intermediate Synthesis 1 → 識別知識缺口
Search Wave 2 → Intermediate Synthesis 2 → 更新理解，再識別缺口
Search Wave 3 → Intermediate Synthesis 3 → 完善理解
──── 基於已合成的理解寫最終報告 ────
```

**關鍵差異**: Progressive synthesis 的好處：

1. 每波搜尋的方向是基於**已理解的內容**，不是基於原始 plan
2. 知識缺口識別更精確（因為已經合成過，知道缺什麼）
3. 最終報告品質更高（LLM 看到的是多層精煉的理解，不是原始碎片）

**修復方向**:

- 在 `_review_research_completeness` 中加入 synthesis 步驟
- 維護 `accumulated_synthesis` 變數，每輪迭代更新
- 用 synthesis 結果（而非原始搜尋結果）驅動後續查詢生成

---

### Gap 3: 完整性評估粒度

**問題根源**: `_review_research_completeness()` (processor.py:566-609)

```python
# 現狀：粗糙的二元判斷
review_prompt = f"""...Answer with YES if research is sufficient, NO if more research is needed..."""
response = await self._call_llm(review_prompt, context)
is_sufficient = "YES" in response.upper()[:10]
```

**問題**:

1. 沒有結構化的評估維度（coverage、depth、diversity、recency）
2. LLM 只看到統計數字（source count、topic count），看不到實際內容品質
3. 二元判斷無法表達「哪個部分不夠深」

**Google 推斷做法**: 基於 research plan 的章節級評估

```
Plan Section 1: "SaaS to SaaP" → Coverage: 80%, Depth: Medium → 需要補充具體案例
Plan Section 2: "AI Tools"      → Coverage: 90%, Depth: High  → 足夠
Plan Section 3: "n8n"           → Coverage: 40%, Depth: Low   → 需要大量補充
```

**修復方向**:

- 將 research plan 拆解為章節列表
- 對每個章節獨立評估 coverage 和 depth
- 返回結構化的 gap report，驅動精確的補充搜尋

---

### Gap 4: 搜尋策略的領域感知

**問題根源**: `_generate_serp_queries()` 和 `_generate_followup_queries()` 都是通用搜尋，沒有領域感知。

**現狀**: LLM 從 research plan 中提取查詢，但不會識別「這個 topic 涉及多個領域，需要針對每個領域設計不同的搜尋策略」。

**Google 推斷做法**:

1. 從使用者查詢識別涉及的領域（技術、商業、經濟、社會）
2. 為每個領域生成專門的搜尋查詢（e.g., "AI agent computer use 2026" vs "SaaS pricing model evolution" vs "blue-collar labor market automation impact"）
3. 確保每個領域都有足夠的搜尋覆蓋

**修復方向**:

- 在 `_write_report_plan` 階段加入 domain identification
- 每個 domain 分配搜尋配額
- Follow-up queries 優先填補 coverage 最低的 domain

---

### Gap 5: 查詢去重與演化

**問題根源**: `_generate_followup_queries()` 沒有去重機制，可能重複搜尋已覆蓋的主題。

```python
# 現狀：直接讓 LLM 生成 follow-up，沒有傳入「已搜尋過的查詢列表」
# 只傳了 learnings，但 LLM 不一定能從 learnings 推斷哪些主題已搜過
```

**修復方向**:

- 維護 `searched_queries: List[str]`
- 傳入 LLM prompt：「以下查詢已執行過，不要重複：[list]」
- 或在生成後用 embedding similarity 去重

---

### Gap 6: 報告生成 prompt 的深度約束

**問題根源**: `_build_academic_report_prompt()` (processor.py:1127-1223)

```python
# 現狀的 requirements
prompt += """
Requirements:
1. Write in academic style with clear sections
2. Use inline citations...
3. Each claim should be supported...
4. DO NOT include a references section...
5. Focus on synthesis and analysis...
6. Ensure logical flow..."""
```

**缺失**:

1. 沒有要求生成**比較表格**（Google 報告有 5 張）
2. 沒有要求**前瞻性分析**（趨勢預測、未來展望）
3. 沒有要求**可操作建議**（行動清單）
4. 沒有**字數下限約束**（"aim for 1000+ words" 太低，Google 產出 6000+）
5. 沒有要求**跨領域交叉分析**
6. 沒有要求**具體數據和案例**（Google 報告充滿具體公司名、產品名、數字）

**修復方向**:

- 增加報告品質約束：最少 3 張比較表、最少 3000 字、必須包含前瞻分析
- 增加跨領域交叉分析要求
- 增加具體案例和數據引用要求

---

### Gap 7: 澄清問題的死代碼

**問題根源**: `_ask_clarifying_questions()` (processor.py:226-243)

```python
# 這裡可以實際發送給用戶並獲取回應
# 目前先記錄供參考
context.response.metadata["clarifying_questions"] = questions
```

**影響**: Google Deep Research 會先展示 research plan 給使用者確認/修改。OpenAgent 生成了澄清問題但從未使用，等同浪費一次 LLM 調用。

**修復方向**:

- 要嘛實現真正的互動式澄清（通過 SSE 推送問題，等待使用者回應）
- 要嘛移除這段死代碼，減少不必要的 LLM 調用成本

---

### Gap 8: 批判性分析的觸發機制

**問題根源**: `_requires_critical_analysis()` (processor.py:245-283) 使用靜態關鍵詞。

```python
critical_keywords = ['分析', '評估', '批判', ...]
is_complex_query = len(query) > 50  # 超過 50 字就觸發
```

**問題**: 幾乎所有 deep research 查詢都超過 50 字符，所以批判性分析**幾乎永遠觸發**。這不是動態判斷，而是偽裝的 always-on。

對比：`_requires_computational_analysis()` 已正確使用 LLM 動態判斷（上輪修改）。

**修復方向**:

- 統一為 LLM 動態判斷（與 computational analysis 的 triage 模式一致）
- 或者承認「deep research 永遠需要批判性分析」，直接移除條件判斷，always-on

---

## 5. 根因分析：為什麼差距存在

### 5.1 架構層面

OpenAgent 的 deep research 是從**一般 chat processor 演化**而來的，不是從零設計的研究系統。這導致：

1. **Context window 意識不足**: 沒有針對 long-context 場景優化資訊管理策略
2. **單一合成點**: 所有合成都發生在最後一步，沒有漸進式知識構建
3. **搜尋即完成心態**: 搜尋完就算「研究完成」，缺少「理解」和「整合」的中間層

### 5.2 資料流層面

```
Google:  [Raw Content] ──→ [Synthesis] ──→ [Report]
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         資訊保留率高     漸進式精煉     高品質輸出

OpenAgent: [Raw Content] ──→ [200 char truncation] ──→ [Report]
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
           資訊損失 99.7%   無中間步驟    品質受限
```

**核心洞察**: 問題不在 LLM 的能力（都是 frontier model），而在**LLM 看到的資訊量**。給同一個 LLM 完整資料 vs 200 chars 摘要，輸出品質天壤之別。

### 5.3 Prompt Engineering 層面

Google 的 prompt（推斷）強制要求了具體的輸出結構元素（表格、案例、數據、前瞻），而 OpenAgent 的 prompt 只給了泛化的「academic style」要求。

---

## 6. 優先級排序的修復路線圖

按 **影響 / 成本比** 排序：

### Tier 1: 高影響、低成本 (立即可做)

| # | 改動                                                      | 影響範圍         | 預估工作量       |
| - | --------------------------------------------------------- | ---------------- | ---------------- |
| 1 | **提高 `_summarize_search_results` 的資訊保留率** | 所有報告品質提升 | 改 2 個數字      |
| 2 | **強化報告 prompt 的結構約束** (表格/數據/前瞻)     | 輸出品質         | 修改 1 個 prompt |
| 3 | **查詢去重** (傳入已搜尋列表)                       | 搜尋效率         | 改 1 個方法      |
| 4 | **移除或修正死代碼** (clarifying_questions)         | 減少浪費         | 刪幾行           |

### Tier 2: 高影響、中等成本

| # | 改動                                              | 影響範圍   | 預估工作量                |
| - | ------------------------------------------------- | ---------- | ------------------------- |
| 5 | **加入 intermediate synthesis**             | 研究深度   | 新增 1 個方法 + 修改 loop |
| 6 | **結構化 completeness review** (章節級評估) | 搜尋精確度 | 重寫 1 個方法             |
| 7 | **統一 critical analysis 為 LLM 動態判斷**  | 一致性     | 改 1 個方法               |

### Tier 3: 高影響、高成本 (需架構調整)

| #  | 改動                                             | 影響範圍   | 預估工作量           |
| -- | ------------------------------------------------ | ---------- | -------------------- |
| 8  | **Full-content extraction** (完整頁面抓取) | 資訊品質   | 搜尋服務改造         |
| 9  | **Domain-aware search strategy**           | 跨領域能力 | 新增 domain 識別模組 |
| 10 | **Interactive research plan** (使用者確認) | 使用者體驗 | SSE 協議修改         |

---

## 7. Tier 1 具體修改規格

### 7.1 提高資訊保留率

**File**: `src/core/processors/research/processor.py`
**Method**: `_summarize_search_results` (line 501-513)

```python
# Before:
for i, result in enumerate(search_results[:5], 1):
    content_preview = content[:200] + "..."

# After:
for i, result in enumerate(search_results[:15], 1):
    content_preview = content
```

同時修改 `_build_academic_report_prompt` 中的 `references[:20]` → `references`。

### 7.2 強化報告 prompt

**File**: `src/core/processors/research/processor.py`
**Method**: `_build_academic_report_prompt` (line 1127)

在 Requirements 區塊中增加：

```
- Include at least 3 structured comparison tables where relevant
- Provide forward-looking analysis with trend predictions (2-5 year horizon)
- End with an actionable recommendation table (steps, goals, tools)
- Aim for 3000+ words with deep analysis, not surface-level summarization
- Include specific company names, product names, statistics, and real-world examples
- Perform cross-domain synthesis: connect findings from different fields
```

### 7.3 查詢去重

**File**: `src/core/processors/research/processor.py`
**Method**: `_execute_research_workflow` (line 142)

在 loop 中維護 `executed_queries` 集合，傳入 `_generate_followup_queries`。

### 7.4 清理死代碼

**File**: `src/core/processors/research/processor.py`
**Methods**: `_should_clarify` + `_ask_clarifying_questions` (line 219-243)

兩個選項：

- Option A: 移除（如果短期不打算實現互動式澄清）
- Option B: 保留但加 `# TODO: implement interactive clarification via SSE` 標記，並在 workflow 中跳過調用（避免浪費 LLM 調用）

---

## 8. 核心結論

### What Google Does Right (First Principles)

1. **資料是王道**: 輸出品質 = f(輸入資料量 × 合成策略)。Google 兩個都做對了。
2. **漸進式理解**: 研究不是「搜→寫」，而是「搜→理解→搜→理解→寫」。
3. **結構化約束**: 不是讓 LLM 自由發揮，而是強制要求特定的輸出元素（表格、數據、案例）。

### What OpenAgent Needs

不需要重寫架構。骨架（多引擎、retry、SSE、event-driven）是健全的。需要的是：

1. **打開資訊保留的閥門**: 從 0.33% 提升到 30%+（改兩個數字就能做到）
2. **在搜尋 loop 中加入 synthesis 步驟**: 從「堆積碎片」變成「漸進理解」
3. **強化報告 prompt 的結構要求**: 從泛化的 "academic style" 變成具體的品質門檻

這三個改動覆蓋了 80% 的品質差距，且不破壞現有架構。

---

*Document generated: 2026-02-18*
*Reference: google_deepresearch_result.md (benchmark output)*
*Reference: src/core/processors/research/processor.py (current implementation)*
