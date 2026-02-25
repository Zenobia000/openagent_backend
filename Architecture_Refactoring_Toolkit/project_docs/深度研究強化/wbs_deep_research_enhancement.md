# WBS: Deep Research Enhancement

**Date**: 2026-02-18
**Source**: gap_analysis_google_vs_openagent.md
**Branch**: refactor/architecture-v2-linus-style
**Target Files**: `src/core/processors/research/processor.py`, `src/core/prompts.py`

---

## Phase Overview

```
Phase 1 ── Tier 1: 高影響低成本 (4 tasks) ✅ COMPLETE
  ├─ 1.1 資訊保留率解鎖              ✅
  ├─ 1.2 報告 prompt 結構約束強化      ✅
  ├─ 1.3 查詢去重機制                ✅
  └─ 1.4 死代碼清理                  ✅

Phase 2 ── Tier 2: 漸進式合成 (3 tasks) ✅ COMPLETE
  ├─ 2.1 Intermediate Synthesis 方法  ✅
  ├─ 2.2 結構化 Completeness Review   ✅
  └─ 2.3 Critical Analysis 觸發統一    ✅

Phase 3 ── Tier 3: 架構級增強 (3 tasks) ✅ COMPLETE (3.3 deferred)
  ├─ 3.1 Full-content Extraction      ✅
  ├─ 3.2 Domain-aware Search Strategy  ✅
  └─ 3.3 Interactive Research Plan     ⏸️ DEFERRED (blocked by frontend)

驗證 ── 跨 Phase 驗證 (1 task) ✅ COMPLETE
  └─ V.1 端對端品質對比測試            ✅ 5/5 PASS

Phase 4 ── McKinsey-Grade 報告品質升級 (6 tasks) ✅ COMPLETE → ⚠️ PARTIALLY REVERSED (v3.3)
  ├─ P0-D Bug Fix (req_num + dead code)          ✅
  ├─ P0-A McKinsey-grade prompt (MECE/Pyramid)    ✅ → ⚠️ SIMPLIFIED (23→10 rules, v3.3)
  ├─ P1-D Chart Planning (always-on)              ✅ → ❌ REMOVED (v3.3)
  ├─ P1-E Per-Chart Code Generation               ✅ → ❌ REMOVED (v3.3)
  ├─ P1-F Inline Figure Embedding                 ✅ → ❌ REMOVED (v3.3)
  └─ P1-G Report Artifact Bundle                  ✅ (simplified, kept)

Phase 5 ── Pipeline Reengineering 去制式化 (6 tasks) ✅ COMPLETE
  ├─ 5.1 移除 Domain Identification               ✅
  ├─ 5.2 移除 Critical Analysis                   ✅
  ├─ 5.3 移除 Chart Planning + Execution          ✅
  ├─ 5.4 簡化 Report Prompt (23→10 rules)         ✅
  ├─ 5.5 簡化 Section Synthesis Prompt             ✅
  └─ 5.6 更新測試 mock side_effect 列表           ✅
```

---

## Phase 1: Tier 1 — 高影響低成本

> 目標：不改架構，只調參數和 prompt，立即提升報告品質。
> 預估：4 個獨立 task，無依賴關係，可平行開發。

---

### 1.1 資訊保留率解鎖

**Gap**: #1 — 資訊保留率 0.33% (200 chars × 5 results)
**File**: `src/core/processors/research/processor.py`
**Risk**: Low — 只改數值，不改邏輯

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | None |
| **Blocked by** | None |

**Tasks**:

- [x] **1.1.1** 修改 `_summarize_search_results()` (line 501-513)
  - 移除 `search_results[:5]` → 使用全部 results
  - 移除 `content[:200]` 截斷 → 保留完整 content
  ```python
  # Before
  for i, result in enumerate(search_results[:5], 1):
      content_preview = content[:200] + "..."
  # After
  for i, result in enumerate(search_results, 1):
      content_preview = content
  ```

- [x] **1.1.2** 修改 `_build_academic_report_prompt()` (line 1133-1136)
  - 移除 `references[:20]` → 使用全部 references
  ```python
  # Before
  ref_summary = "\n".join([
      f"[{ref['id']}] {ref['title']}"
      for ref in references[:20]
  ])
  # After
  ref_summary = "\n".join([
      f"[{ref['id']}] {ref['title']}"
      for ref in references
  ])
  ```

- [x] **1.1.3** 檢查 `_prepare_report_context()` (line 1084-1096)
  - 確認 `processed` 和 `summary` 欄位完整保留
  - 如果有截斷，移除

**Verification**:
- `python3 -c "import ast; ast.parse(open('src/core/processors/research/processor.py').read())"`
- grep 確認 `[:5]` 和 `[:200]` 在相關方法中已移除
- grep 確認 `[:20]` 在 `_build_academic_report_prompt` 中已移除

---

### 1.2 報告 Prompt 結構約束強化

**Gap**: #6 — 報告 prompt 缺乏結構化約束
**File**: `src/core/processors/research/processor.py`
**Risk**: Low — 只改 prompt 字串

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | None |
| **Blocked by** | None |

**Tasks**:

- [x] **1.2.1** 修改 `_build_academic_report_prompt()` 的 Requirements 區塊
  - 在現有 6 條 requirement 之後追加：
  ```
  7. Include at least 3 structured comparison tables where relevant
  8. Provide forward-looking analysis with trend predictions (2-5 year horizon)
  9. End with an actionable recommendation table (steps, goals, tools)
  10. Aim for 3000+ words with deep analysis, not surface-level summarization
  11. Include specific company names, product names, statistics, and real-world examples
  12. Perform cross-domain synthesis: connect findings from different fields
  ```

- [x] **1.2.2** 修改 IMPORTANT 區塊中的字數要求
  - `aim for 1000+ words` → `aim for 3000+ words`

**Verification**:
- AST syntax check
- grep 確認 "3000+" 和 "comparison tables" 出現在 prompt 中

---

### 1.3 查詢去重機制

**Gap**: #5 — follow-up queries 可能重複已搜尋的主題
**File**: `src/core/processors/research/processor.py`
**Risk**: Low — 新增狀態變數 + prompt 修改

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | None |
| **Blocked by** | None |

**Tasks**:

- [x] **1.3.1** 在 `_execute_research_workflow()` 的 loop 初始化前新增：
  ```python
  executed_queries: List[str] = []
  ```

- [x] **1.3.2** 在 search task 執行後收集已查詢列表：
  ```python
  # 在 _execute_search_tasks 呼叫後
  executed_queries.extend([t.get('query', '') for t in search_tasks])
  ```

- [x] **1.3.3** 修改 `_generate_followup_queries()` 簽名，加入 `executed_queries` 參數

- [x] **1.3.4** 在 `_generate_followup_queries()` 的 review_prompt 中加入去重提示：
  ```python
  # 在 prompt 尾部加入
  dedup_notice = ""
  if executed_queries:
      queries_list = "\n".join(f"- {q}" for q in executed_queries)
      dedup_notice = f"\n\nIMPORTANT: The following queries have already been executed. Do NOT generate similar or duplicate queries:\n{queries_list}"
  ```

- [x] **1.3.5** 更新 `_execute_research_workflow()` 中對 `_generate_followup_queries` 的呼叫，傳入 `executed_queries`

**Verification**:
- AST syntax check
- grep 確認 `executed_queries` 變數存在且在 loop 中被更新

---

### 1.4 死代碼清理

**Gap**: #7 — `_ask_clarifying_questions()` 生成問題但從未發送
**File**: `src/core/processors/research/processor.py`
**Risk**: Low — 移除未使用的呼叫，減少 LLM token 浪費

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | None |
| **Blocked by** | None |

**Tasks**:

- [x] **1.4.1** 在 `_execute_research_workflow()` 中跳過澄清呼叫
  - 註解掉 `_should_clarify` / `_ask_clarifying_questions` 的呼叫（保留方法定義供未來 SSE 互動使用）
  ```python
  # Before
  workflow_state["current_step"] = "clarification"
  if await self._should_clarify(context):
      await self._ask_clarifying_questions(context)

  # After
  # TODO: re-enable when interactive SSE clarification is implemented
  # workflow_state["current_step"] = "clarification"
  # if await self._should_clarify(context):
  #     await self._ask_clarifying_questions(context)
  ```

- [x] **1.4.2** 在 `_should_clarify()` 和 `_ask_clarifying_questions()` 方法上加 docstring 標記
  ```python
  """...(現有 docstring)...
  NOTE: Currently disabled in workflow — awaiting SSE interactive implementation.
  """
  ```

**Verification**:
- AST syntax check
- grep 確認 workflow 中的 clarification 呼叫已被註解

---

## Phase 2: Tier 2 — 漸進式合成

> 目標：在搜尋 loop 中加入理解和整合層，從「堆積碎片」變成「漸進理解」。
> 預估：3 個 task，2.2 依賴 2.1（synthesis 結果驅動 completeness review）。

---

### 2.1 Intermediate Synthesis

**Gap**: #2 — 一次性合成 vs 漸進式合成
**File**: `src/core/processors/research/processor.py`, `src/core/prompts.py`
**Risk**: Medium — 修改核心 search loop 邏輯

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | Phase 1 完成（1.1 資訊保留率解鎖是前置條件：synthesis 需要看完整資料） |
| **Blocked by** | 1.1 |

**Tasks**:

- [x] **2.1.1** 在 `prompts.py` 新增 `get_intermediate_synthesis_prompt()` 靜態方法
  - 輸入：query, report_plan, wave_results (本波搜尋結果), previous_synthesis (前波合成)
  - 輸出指示：
    - 整合本波新發現與前波理解
    - 識別每個 plan section 的覆蓋狀態（covered / partially / missing）
    - 列出尚未解答的關鍵問題
    - 標記需要跨領域交叉驗證的點
  - 輸出格式要求：JSON 結構
    ```json
    {
      "synthesis": "整合後的理解...",
      "section_coverage": {
        "section_name": {"status": "covered|partial|missing", "notes": "..."}
      },
      "knowledge_gaps": ["gap1", "gap2"],
      "cross_domain_links": ["link1"]
    }
    ```

- [x] **2.1.2** 新增 `_intermediate_synthesis()` 方法在 processor.py
  ```python
  async def _intermediate_synthesis(
      self,
      context: ProcessingContext,
      report_plan: str,
      wave_results: List[Dict],
      previous_synthesis: Optional[str] = None
  ) -> Dict[str, Any]:
  ```
  - 呼叫 `PromptTemplates.get_intermediate_synthesis_prompt()`
  - 解析 JSON 回應
  - 發射 SSE progress event: `intermediate-synthesis`
  - 記錄到 `context.response.metadata["synthesis_history"]`
  - 返回 synthesis dict

- [x] **2.1.3** 修改 `_execute_research_workflow()` 的 search loop
  - 在每輪 `_execute_search_tasks()` 之後、`_review_research_completeness()` 之前插入 synthesis 呼叫
  - 維護 `accumulated_synthesis` 變數
  ```python
  # 在 loop 初始化處
  accumulated_synthesis = None

  # 在每輪 search 之後
  synthesis_result = await self._intermediate_synthesis(
      context, report_plan, search_results, accumulated_synthesis
  )
  accumulated_synthesis = synthesis_result.get("synthesis", "")
  ```

- [x] **2.1.4** 將 `accumulated_synthesis` 傳入 `_generate_followup_queries()` 和 `_write_final_report()`
  - follow-up queries 基於 synthesis 中的 `knowledge_gaps` 生成
  - final report 使用 accumulated synthesis 作為輸入，而非原始搜尋碎片

**Verification**:
- AST syntax check (both files)
- grep 確認 `_intermediate_synthesis` 方法存在
- grep 確認 `accumulated_synthesis` 在 loop 中被更新和傳遞

---

### 2.2 結構化 Completeness Review

**Gap**: #3 — 二元 YES/NO 判斷 → 章節級評估
**File**: `src/core/processors/research/processor.py`, `src/core/prompts.py`
**Risk**: Medium — 重寫現有方法

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | 2.1（需要 synthesis 結果中的 `section_coverage` 資料） |
| **Blocked by** | 2.1 |

**Tasks**:

- [x] **2.2.1** 在 `prompts.py` 新增 `get_completeness_review_prompt()` 靜態方法
  - 輸入：report_plan, section_coverage (from synthesis), iteration, max_iterations
  - 要求 LLM 做章節級判斷：
    - 每個 section 的 coverage (0-100%)、depth (low/medium/high)
    - 整體是否足夠（基於所有 section 的最低覆蓋率）
    - 如果不足，具體指出哪些 section 需要什麼補充
  - 輸出 JSON：
    ```json
    {
      "is_sufficient": true/false,
      "overall_coverage": 85,
      "sections": [
        {"name": "...", "coverage": 90, "depth": "high", "gaps": []},
        {"name": "...", "coverage": 40, "depth": "low", "gaps": ["缺少具體案例", "需要數據"]}
      ],
      "priority_gaps": ["最急需補充的查詢方向1", "方向2"]
    }
    ```

- [x] **2.2.2** 重寫 `_review_research_completeness()` 方法
  - 接收 synthesis 結果中的 section_coverage
  - 使用新 prompt 取代原始的二元判斷
  - 解析 JSON 回應
  - 返回 `(is_sufficient: bool, gap_report: Dict)` 元組
  - gap_report 的 `priority_gaps` 用於驅動 follow-up queries

- [x] **2.2.3** 修改 `_generate_followup_queries()` 以使用 gap_report
  - 將 `priority_gaps` 直接作為查詢方向，而非讓 LLM 從零生成

**Verification**:
- AST syntax check
- grep 確認 `section_coverage` 和 `priority_gaps` 在程式碼中流通

---

### 2.3 Critical Analysis 觸發統一

**Gap**: #8 — 靜態關鍵詞觸發 → LLM 動態判斷 or always-on
**File**: `src/core/processors/research/processor.py`
**Risk**: Low — 簡化現有方法

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | None |
| **Blocked by** | None |

**Tasks**:

- [x] **2.3.1** 決策：always-on 或 LLM triage（建議 always-on）
  - Deep research 本質上永遠需要批判性分析
  - 移除 `_requires_critical_analysis()` 方法
  - 在 workflow 中直接呼叫 `_critical_analysis_stage()`（不經過 gate）

- [x] **2.3.2** 修改 `_execute_research_workflow()`:
  ```python
  # Before
  critical_analysis = None
  if await self._requires_critical_analysis(context.request.query):
      ...
  # After
  workflow_state["current_step"] = "critical_analysis"
  critical_analysis = await self._critical_analysis_stage(
      context, all_search_results, report_plan
  )
  ```

- [x] **2.3.3** 移除 `_requires_critical_analysis()` 方法定義（line 245-283）

**Verification**:
- AST syntax check
- grep 確認 `_requires_critical_analysis` 方法不再被呼叫
- grep 確認 `_critical_analysis_stage` 在 workflow 中無條件呼叫

---

## Phase 3: Tier 3 — 架構級增強

> 目標：搜尋服務和使用者互動層面的架構調整。
> 預估：3 個獨立 task，可平行開發，但每個涉及多個模組。

---

### 3.1 Full-content Extraction

**Gap**: #1 延伸 — 搜尋結果只有 snippet，缺少完整頁面內容
**Files**: `src/core/processors/research/processor.py`
**Risk**: Low — search service 已有 `fetch_url()`/`fetch_multiple()`，只需在 processor 中接線

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | Phase 1 & 2 完成 |
| **Blocked by** | 1.1, 2.1 |

**Tasks**:

- [x] **3.1.1** 調研搜尋服務現狀
  - 確認 search service 返回的欄位（url, title, snippet）
  - 確認是否已有 web fetch / scraping 能力
  - 確認 MCP server 是否提供 web_fetch tool

- [x] **3.1.2** 新增 `_fetch_full_content()` 方法
  - 對搜尋結果的 top-N URL 做全文抓取
  - 使用 MCP web_fetch 或 httpx + readability 提取正文
  - HTML → plain text / markdown 轉換
  - 超時和錯誤靜默處理

- [x] **3.1.3** 整合到搜尋流程
  - 在 `_execute_single_search_task()` 返回結果後
  - 對 top 3-5 sources 做 full-content extraction
  - 將全文存入 search_result dict 的 `full_content` 欄位

- [x] **3.1.4** 更新 `_prepare_report_context()` 使用 `full_content`

**Verification**:
- 單元測試（mock HTTP）驗證全文抓取邏輯
- 端對端測試確認 full_content 欄位出現在搜尋結果中

---

### 3.2 Domain-aware Search Strategy

**Gap**: #4 — 搜尋策略無領域感知
**Files**: `src/core/processors/research/processor.py`, `src/core/prompts.py`
**Risk**: Medium — 新增 domain 識別邏輯

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) |
| **Depends** | Phase 2 完成（synthesis 提供 cross_domain_links） |
| **Blocked by** | 2.1 |

**Tasks**:

- [x] **3.2.1** 新增 `get_domain_identification_prompt()` in prompts.py
  - 輸入：query, report_plan
  - 要求 LLM 識別涉及的領域和每個領域的搜尋策略
  - 輸出 JSON:
    ```json
    {
      "domains": [
        {"name": "technology", "weight": 0.3, "search_angles": ["...", "..."]},
        {"name": "business", "weight": 0.4, "search_angles": ["...", "..."]},
        {"name": "economics", "weight": 0.3, "search_angles": ["...", "..."]}
      ]
    }
    ```

- [x] **3.2.2** 新增 `_identify_research_domains()` 方法
  - 在 `_write_report_plan()` 之後呼叫
  - 返回 domain 列表和每個 domain 的搜尋配額

- [x] **3.2.3** 修改 `_generate_serp_queries()` 以使用 domain 配額
  - 確保每個 domain 都有最少 N 個查詢
  - 在 prompt 中告知 LLM 每個 domain 的搜尋角度

- [x] **3.2.4** 修改 follow-up queries 優先填補 coverage 最低的 domain

**Verification**:
- AST syntax check
- grep 確認 `domain` 相關邏輯在 workflow 中流通

---

### 3.3 Interactive Research Plan

**Gap**: #7 延伸 — 使用者無法在研究前確認/修改計劃
**Files**: `src/core/processors/research/processor.py`, SSE 相關模組
**Risk**: High — 涉及 SSE 協議修改和前端配合

| Item | Detail |
|------|--------|
| **Status** | [ ] Deferred (blocked by frontend) |
| **Depends** | Phase 1 (1.4 死代碼清理確定了方向) |
| **Blocked by** | 前端配合 |

**Tasks**:

- [ ] **3.3.1** 設計 SSE 互動協議
  - 定義新的 event type: `research_plan_review`
  - 定義 payload: `{plan, sections, suggested_modifications}`
  - 定義使用者回應格式: `{approved: bool, modifications: [...]}`

- [ ] **3.3.2** 修改 `_write_report_plan()` 加入 SSE 互動點
  - 生成計劃後，發射 `research_plan_review` event
  - 等待使用者回應（或超時自動繼續）
  - 如使用者有修改，更新 plan

- [ ] **3.3.3** 重新啟用 `_ask_clarifying_questions()` 整合到互動流程
  - 澄清問題作為 plan review 的一部分發送
  - 使用者可以同時確認 plan 和回答問題

- [ ] **3.3.4** 前端適配（跨團隊協作項目）

**Verification**:
- SSE event 格式測試
- 端對端測試：plan review → user approval → research continues

---

## Verification Phase

### V.1 端對端品質對比測試

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-18) — **5/5 PASS** |
| **Depends** | Phase 1 完成（最低要求）或 Phase 2 完成（理想） |

**Tasks**:

- [x] **V.1.1** 使用 benchmark query 跑 deep research ✅
  - Query: 「2026年藍領垂直領域平台服務轉型報告」
  - 結果：4996 words, 43 unique citations, 6 tables, 63 sections, 5 domains
  - Duration: 1899.1s (~31.6 min), 3 iterations, 3 synthesis rounds

- [x] **V.1.2** 與 Google Deep Research 結果做逐項對比 ✅ ALL PASS
  - 字數：4996 ≥ 3000 ✅ (167% of target)
  - 引用：43 ≥ 15 ✅ (287% of target)
  - 表格：6 ≥ 3 ✅ (200% of target)
  - 領域：5 ≥ 3 ✅ (5/5 domains covered)
  - Sections: 63 ≥ 5 ✅ (18 major sections + subsections)

- [x] **V.1.3** 品質觀察 ✅
  - 資訊密度：每 section 含具體數據、合約條款範本、KPI 定義
  - 跨領域交叉分析：technology, business, labor/workforce, regulation, economics
  - 前瞻性分析：包含 3-5 年財務模型框架、pilot KPI targets
  - 可操作性：18 個 major sections + action tables + 分階段 roadmap

---

## Dependency Graph

```
Phase 1 (全部可平行)
  1.1 ──┐
  1.2 ──┤
  1.3 ──┼──→ Phase 2
  1.4 ──┘
           2.1 (intermediate synthesis) ──→ 2.2 (completeness review)
           2.3 (critical analysis) ── 獨立，可平行

Phase 2 ──→ Phase 3
           3.1 (full-content) ── 獨立
           3.2 (domain-aware) ── 依賴 2.1
           3.3 (interactive plan) ── 依賴前端

All Phases ──→ V.1 (驗證)
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context window overflow (Phase 1.1 移除截斷) | LLM 拒絕或截斷 | 監控 token count；如超限，fallback 為 top-N 排序後截斷 |
| Intermediate synthesis 增加延遲 (Phase 2.1) | 使用者等待時間增加 | SSE streaming 即時顯示 synthesis 進度 |
| Full-content extraction 被目標網站封鎖 (Phase 3.1) | 部分 URL 無法抓取 | 靜默降級：使用 snippet 作為 fallback |
| Phase 3.3 需要前端配合 | 無法獨立完成 | 先實現 backend API，前端可後續接入 |

---

## Phase 4: McKinsey-Grade 報告品質升級

> 目標：報告結構從流水帳升級為顧問級（MECE + Pyramid + So-What），表格從 listing 升級為 analytical，新增圖表 pipeline + artifact bundle。
> 來源：`gap_analysis_report_quality_v2.md`
> 修改檔案：`processor.py`, `prompts.py`（僅 2 個檔案）

---

### P0-D: Bug Fix

- [x] **修復 `req_num = 7` → `req_num = 17`**（base requirements 有 16 項）
- [x] **刪除 dead code**（lines 1356-1358，`return prompt` 後的不可達程式碼）

### P0-A: McKinsey-Grade Report Prompt

- [x] **替換 Requirements block**（12 項通用 → 16 項 McKinsey-grade）
  - MECE + Pyramid Principle 結構要求
  - CEI (Claim-Evidence-Implication) 段落模式
  - Analytical table 類型約束（BANNED listing tables）
  - So-What chain（每個事實必須有推論）
  - BANNED vague phrases（"重要的是", "值得注意的是", "眾所周知"）

### P1-D: Chart Planning (Always-On)

- [x] **新增 `get_chart_planning_prompt()`** in prompts.py
  - LLM 規劃 2-4 張圖表（title, chart_type, data_description, target_section, insight）
- [x] **新增 `_plan_report_charts()`** in processor.py
  - Always-on（不需 sandbox gate），解析 JSON chart specs
- [x] **修改 workflow**：chart specs → sandbox execution（取代 blind triage）

### P1-E: Per-Chart Code Generation

- [x] **新增 `get_single_chart_code_prompt()`** in prompts.py
  - 單一圖表 matplotlib 程式碼生成（<40 行）
- [x] **新增 `_execute_chart_plan()`** in processor.py
  - 逐一生成 + 執行，獨立失敗處理
  - 回傳 `{figures, figure_specs, stdout, code, execution_time}`

### P1-F: Inline Figure Embedding

- [x] **修改 `_format_report_with_categorized_references()`**
  - 圖表內嵌到 target_section 之後（取代底部集中 append）
  - Fallback：找不到 target section 時 append 到底部

### P1-G: Report Artifact Bundle

- [x] **新增 `_save_report_bundle()`** in processor.py
  - Bundle 結構：`{trace_id}_{timestamp}/report.md + metadata.json + figures/`
  - report.md 中 base64 替換為相對路徑 `figures/figure_N.png`
  - Fallback：bundle 失敗時退回 flat file
- [x] **替換 persistence 邏輯**（`save_response_as_markdown` → `_save_report_bundle`）

---

## Summary Metrics

| Metric | Phase 1 後 | Phase 2 後 | Phase 3 後 | Phase 4 後 |
|--------|-----------|-----------|-----------|-----------|
| 資訊保留率 | 30%+ (from 0.33%) | 40%+ | 60%+ | 60%+ |
| 合成策略 | 一次性 | 漸進式 | 漸進式 + 跨域 | 漸進式 + 跨域 |
| 報告字數 | 2000-3000 | 3000-5000 | 5000+ | 5000+ |
| 表格數 | 3+ | 3+ | 5+ | 3-5 analytical |
| 表格類型 | listing | listing | listing | analytical (MECE) |
| 圖表數 | 0 | 0 | 0 | 2-4 per report |
| Artifact | flat .md | flat .md | flat .md | bundle (dir) |
| 預估品質分 | 6.5/10 | 8/10 | 9/10 | 9.5/10 |

---

## Phase 5: Pipeline Reengineering — 去制式化

> 目標：移除制式化框架（MECE/Pyramid/CEI/強制表格），信任 LLM 推理能力，簡化 pipeline，讓報告像人寫的研究報告而非模板填充。
> 核心理念：模型思維能力已足夠強，不需要強 prompt 約束。保持靈活性，讓 LLM 自行發揮。
> 來源：實際報告品質審計 — 發現 23 條制式規則導致機械化輸出（如 "這意味著" 52 次重複）

---

### 5.1 移除 Domain Identification

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-25) |

**改動**:
- `processor.py`: 移除 `identify_research_domains()` 呼叫和 `domains=research_domains` 參數
- `planner.py`: `generate_serp_queries()` 移除 `domains` 參數和 `domain_supplement` 邏輯
- SERP prompt 已有 "Cover different aspects/domains proportionally"，足夠引導多角度

**理由**: Domain Identification 是獨立 LLM call，但其輸出只是在 SERP prompt 中追加 domain 列表。這個功能可以直接合併到 SERP prompt 中。

---

### 5.2 移除 Critical Analysis

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-25) |

**改動**:
- `processor.py`: 移除 `critical_analysis_stage()` 呼叫和 `critical_analysis` 變數
- `reporter.py`: `write_final_report()` 移除 `critical_analysis` 參數
- `reporter.py`: `build_academic_report_prompt()` 移除 critical analysis 注入區塊

**理由**: Critical Analysis 的輸出（limitation analysis、contradiction identification）在實際報告中表現為機械化的公式段落。LLM 在報告生成時本身就有能力做批判性分析，不需要額外的 LLM call 強制注入。

---

### 5.3 移除 Chart Planning + Execution

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-25) |

**改動**:
- `processor.py`: 移除 `plan_report_charts()` 和 `chart_specs` / `computational_result` 邏輯
- `processor.py`: 移除 `ComputationEngine` import 和初始化
- `reporter.py`: 移除 `computational_result` 參數、figure 內嵌邏輯、figure 儲存邏輯
- `reporter.py`: `save_report_bundle()` 簡化（移除 figure 處理）

**理由**: 圖表為了呈現而呈現（強制 3-5 張表、指定表格類型）。在沙箱環境不穩定的情況下，chart pipeline 經常失敗或產出品質低的圖表。LLM 可以在報告中自然地使用 Markdown 表格和文字描述來傳達數據分析。

---

### 5.4 簡化 Report Prompt (23→10 rules)

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-25) |

**移除的規則 (13 條)**:

| 規則 | 移除原因 |
|------|---------|
| Executive Summary 固定格式 | 讓 LLM 自行組織開頭 |
| MECE sub-sections | MBA 框架，非自然寫作 |
| Pyramid Principle | 同上 |
| So-What 強制（含固定句式） | 制式化根源（"這意味著" 52 次） |
| CEI 段落結構 | 制式化根源 |
| 3-5 張分析表格強制 | 為呈現而呈現 |
| 強制表格類型 | 同上 |
| 表格完整性 | 過度控制 |
| 表達多樣性控制 | 微觀管理寫作風格 |
| 強制競爭分析章節 | 不是每個主題都需要 |
| Bull/Base/Bear 情境分析 | 不是每個主題都適用 |
| Figure 排序規則 | charts 已移除 |
| Critical analysis 整合 | critical analysis 已移除 |

**保留的規則 (10 條)**: Inline citations, no references section, heading structure, 3000+ words, specific data, pipe-table syntax, cross-reference, Tier 1-2 source priority, methodology section, natural writing.

---

### 5.5 簡化 Section Synthesis Prompt

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-25) |

**改動**:
- `prompts.py`: `get_section_synthesis_prompt()` 移除 "2000-3000 characters minimum" 硬性要求
- 改為 "Be thorough — cover all substantive findings"
- 簡化 JSON 輸出結構指引

---

### 5.6 更新測試 mock side_effect 列表

| Item | Detail |
|------|--------|
| **Status** | [x] **Complete** (2026-02-25) |

**改動**:
- `test_deep_research_enhancement.py`: 所有 mock `side_effect` 從 11 項縮減到 8 項
- `test_processors.py`: 所有 mock `side_effect` 從 11 項縮減到 8 項
- 移除 `TestCriticalAnalysisAlwaysOn` 測試類
- `TestReportPromptConstraints` 重寫為測試新的 10 條規則

**最終測試結果**: 323 passed, 1 failed (pre-existing)

---

### Phase 5 影響分析

| File | 改動類型 | 淨行數 |
|------|---------|--------|
| `processor.py` | 移除 3 階段 + 清理 imports | -30 |
| `reporter.py` | 簡化 prompt, 移除 2 參數 | -50 |
| `prompts.py` | 簡化 section synthesis prompt | -5 |
| `planner.py` | 移除 domains 參數 | -15 |
| `test_deep_research_enhancement.py` | 更新 mock lists | ~10 處 |
| `test_processors.py` | 更新 mock lists | ~5 處 |

**淨刪除約 100 行產品程式碼。**

### LLM Call 變化

| 階段 | v3.2 | v3.3 |
|------|------|------|
| Report Plan | 1 | 1 |
| Domain Identification | 1 | **0** |
| SERP Queries | 1 | 1 |
| Search (model mode) | N | N |
| Intermediate Synthesis | 1 | 1 |
| Completeness Review | 1 | 1 |
| Critical Analysis | 1 | **0** |
| Chart Planning | 1 | **0** |
| Chart Code Gen | 0-5 | **0** |
| Section Classification | 1 | 1 |
| Section Synthesis | N | N |
| Final Report | 1 | 1 |
| **Total (min-max)** | **~12-22** | **~9-16** |

---

## Summary Metrics (Updated)

| Metric | Phase 1 後 | Phase 2 後 | Phase 3 後 | Phase 4 後 | Phase 5 後 |
|--------|-----------|-----------|-----------|-----------|-----------|
| 資訊保留率 | 30%+ (from 0.33%) | 40%+ | 60%+ | 60%+ | ~16% (section-aware) |
| 合成策略 | 一次性 | 漸進式 | 漸進式 + 跨域 | 漸進式 + 跨域 | 漸進式 + 階層式 |
| 報告字數 | 2000-3000 | 3000-5000 | 5000+ | 5000+ | 3000+ (flexible) |
| 表格數 | 3+ | 3+ | 5+ | 3-5 analytical | flexible (LLM decides) |
| 表格類型 | listing | listing | listing | analytical (MECE) | natural (LLM decides) |
| 圖表數 | 0 | 0 | 0 | 2-4 per report | 0 (removed) |
| Artifact | flat .md | flat .md | flat .md | bundle (dir) | bundle (simplified) |
| LLM calls | ~9 | ~10 | ~11 | ~12-22 | ~9-16 |
| Prompt 規則 | 6 | 6 | 6 | 23 | 10 |
| 預估品質分 | 6.5/10 | 8/10 | 9/10 | 9.5/10 (理論) | 8/10 (實際, 去制式化) |

---

*WBS generated: 2026-02-18*
*Phase 4 added: 2026-02-18*
*Phase 5 added: 2026-02-25*
*Source: gap_analysis_google_vs_openagent.md, gap_analysis_report_quality_v2.md, pipeline reengineering plan*
