# Gap Analysis V2: Report Quality — McKinsey-grade vs Current Output

**Date**: 2026-02-18
**Context**: V.1 Benchmark 5/5 PASS, but output quality is "passing the bar" not "setting the bar"
**Benchmark Report**: `tests/benchmark/output/benchmark_report.md`

---

> **⚠️ v3.3 更新 (2026-02-25)**: 本文件的建議在 Phase 4 (McKinsey-Grade) 中全部實作，但隨後在 Phase 5 (Pipeline Reengineering) 中部分被反轉。
>
> **已反轉/移除的建議:**
> - Gap A (Report Structure: MECE + Pyramid + So-What) → **簡化** — 保留自然分析式寫作指引，移除 MECE/Pyramid/CEI/So-What 制式框架
> - Gap B (Table Quality: analytical table spec) → **簡化** — 保留 pipe-table syntax，移除表格類型強制
> - Gap C (Data Visualization: Computational Pipeline) → **完全移除** — Chart Planning、Per-Chart Code Gen、Inline Embedding 全部移除
> - Layer 2b (Sandbox-free Fallback) → **不再需要** — chart pipeline 已移除
> - Layer 3 (Report Artifact Bundle) → **保留但簡化** — 移除 figure/artifacts 子目錄
>
> **仍然有效的建議:**
> - Gap D (Analytical Depth) → 透過簡化 prompt 讓 LLM 自然發揮，而非強制 So-What chain
> - Layer 1 Gap C (Quantification Standard) → 保留為待實作
> - 上游搜尋品質導向 → 保留為待實作

---

## 1. Problem Statement

V.1 benchmark 達標（字數、引用、表格數量都超標），但**報告品質的本質**距離 McKinsey / top-tier consulting 報告仍有明顯差距。

核心問題不是「有沒有表格」，而是「表格是否在做分析」。

---

## 2. Current Output 診斷

### 2.1 現有 6 張表格的分類

| # | Table | Type | Analytical Value |
|---|---|---|---|
| 1 | MVP 功能優先矩陣 | Listing (feature catalog) | Low — 純列舉，無交叉比較 |
| 2 | 品質管控與投訴處理流程 | Process flow | Low — SOP 描述，非分析 |
| 3 | 收費模型比較 | Comparison matrix | **Medium** — 有優劣對比，但無數據支撐 |
| 4 | 三階段實施時程 | Timeline listing | Low — 里程碑列表，非 Gantt 邏輯 |
| 5 | 行動建議 (Steps/Goals) | Action plan | Medium — 有 KPI 但無量化依據 |
| 6 | 優先行動表 | Duplicate of #5 | Low — 與 Table 5 重複 |

**診斷**: 6 張表格中 0 張是真正的分析型表格（pivot、cross-tab、sensitivity matrix、waterfall decomposition）。

### 2.2 現有報告結構問題

| Dimension | McKinsey Standard | Current Output | Gap |
|---|---|---|---|
| **MECE 結構** | 每層分解互斥且窮盡 | 有 sections 但存在重複（Table 5 ≈ Table 6, 執行摘要 ≈ 結論） | High |
| **Pyramid Principle** | 結論先行 → 支撐論據 → 細節 | 混合式（描述 + 分析混雜） | Medium |
| **So What** | 每段結尾有明確的 "so what" | 大量描述段落缺少推論 | High |
| **Quantified Claims** | 每個主張都有數字支撐 | 大量定性描述（"高"、"快速"、"顯著"） | High |
| **Analytical Tables** | Pivot / Cross-tab / Sensitivity | 純 listing tables | **Critical** |
| **Data Visualization** | Charts embedded (bar, waterfall, scatter) | 0 charts | **Critical** |
| **Framework Application** | Porter's 5 Forces, Value Chain, 2x2 matrix | 無框架，自由論述 | High |

### 2.3 為什麼 Computational Analysis 沒有觸發？

Current flow:
```
_requires_computational_analysis()
  → Hard gate: self.services.get("sandbox") → sandbox exists?
  → LLM triage: "Does this data warrant computation?"
```

**Root cause chain**:
1. **Sandbox service 可能未初始化**（Docker 不在、或初始化失敗被 silent catch）
2. **即使 sandbox 存在，LLM triage 太保守** — triage prompt 問的是 "do findings contain numerical data that can be computed"，而不是 "would analytical charts improve this report"
3. **即使 triage 通過，code generation prompt 是 generic** — 沒有指定要產出什麼類型的圖表（不知道要做 market sizing waterfall 還是 sensitivity tornado chart）
4. **圖表與報告分離** — figures 被 append 到報告最後（`## Computational Analysis Figures`），不是 inline 嵌入各 section

---

## 3. Gap Decomposition（MECE）

### Gap A: Report Structure — 缺乏諮詢級框架思維

**現狀**: Prompt 只說 "write in academic style with clear sections" + "3000+ words"

**問題**: LLM 不知道什麼是好的分析結構。沒有人告訴它：
- 用 MECE 確保每層不重疊不遺漏
- 用 Pyramid Principle 確保結論先行
- 每段最後要有 "so what" / "implications"
- 段落要 claim → evidence → implication 三段式

**目標**: Report prompt 應內建結構框架指令

### Gap B: Table Quality — 為了表格而表格 vs 分析驅動

**現狀**: Prompt 說 "Include at least 3 structured comparison tables"

**問題**:
- "at least 3" 鼓勵數量，不鼓勵質量
- "structured comparison" 太模糊，LLM 傾向產出 feature listing
- 沒有指定分析型表格的類型（pivot、cross-tab、sensitivity、decomposition）

**目標**: Prompt 應指定表格必須是「分析型」，並提供具體模式：

| Table Type | Purpose | Example |
|---|---|---|
| Pivot / Cross-tab | 雙維度交叉分析 | 產業 × 職位類型 → 缺口人數 |
| Sensitivity Matrix | 參數敏感度 | Take-rate × Churn → NPV |
| Waterfall Decomposition | 數值拆解 | TAM → SAM → SOM breakdown |
| Scoring Matrix | 多準則評估 | 方案 × 評估維度 → 加權得分 |
| Comparison (有量化) | 量化對比 | 競爭者 × 維度 → 具體數字 |

### Gap C: Data Visualization — Computational 管道斷裂

**現狀**: Computational analysis phase 存在但形同虛設

**問題鏈**:

```
Sandbox 不在 ──────→ 直接 return False（最常見）
                         ↓
Sandbox 在但 triage 說 NO ──→ 搜尋結果大多是文字，triage 認為 "no numerical data"
                         ↓
Triage 說 YES 但 code 品質差 ──→ generic prompt，不知道該畫什麼圖
                         ↓
Code 成功但圖表放尾巴 ──→ "Computational Analysis Figures" section，與正文脫節
```

**Root cause**: 把「是否需要圖表」交給 triage LLM 判斷是錯誤的抽象。

**正確模型**: 諮詢報告**永遠需要**數據視覺化。問題不是 "should we compute?" 而是 "what specific charts would make this report more convincing?"

### Gap D: Analytical Depth — 缺乏 "So What" 推論鏈

**現狀**: 報告大量段落是「事實陳述」而非「分析推論」

**例子**（從 benchmark 報告截取）:
```
❌ 描述型:
"台灣進入超高齡社會與低生育週期，短期內年輕勞動力補充不足"

✅ 分析型:
"台灣進入超高齡社會（2026 年 65+ 人口佔比預估 21.3%），
 年輕勞動力（15-29 歲）年減 1.8%，意味著每流失 1 名藍領工
 需要平台將匹配效率提升 15-20% 才能維持相同填充率。
 → So what: 平台的核心 KPI 不是增加供給而是提升 fill-rate per worker"
```

---

## 4. Root Cause Analysis

```
                    為什麼報告品質不夠？
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    Report Prompt    Computational    Analysis
    太弱太通用       Pipeline 斷裂    Framework 缺失
         │               │               │
   「academic style」  Sandbox 常不在   沒有 MECE/Pyramid
   不等於分析品質    Triage 太保守    沒有 So What 指令
         │               │               │
   只規定字數/表格數  圖表放尾巴      LLM 預設描述模式
   不規定分析深度    不 inline        不主動做推論
```

---

## 5. Solution Design

### 5.1 Approach: 分兩層解決

**Layer 1 — Prompt Engineering（低成本、高 ROI）**
不改架構、不改 pipeline，只升級 prompt 指令，讓 LLM 產出更接近諮詢品質的報告。

**Layer 2 — Computational Pipeline 修復（中成本、高 ROI）**
修復 sandbox 觸發邏輯、改用 "chart planning" 取代 "blind triage"、圖表 inline 嵌入。

### 5.2 Layer 1: Prompt-level Upgrades

#### 5.2.1 Report Structure Framework

在 `_build_academic_report_prompt()` 的 Requirements 區塊，**替換**現有的通用指令為結構化框架：

```
Report Structure Rules:
1. MECE: Each section must be mutually exclusive — no content duplication across sections.
   If two sections naturally overlap, merge them or create a clear boundary.

2. Pyramid Principle: State conclusions FIRST, then supporting evidence.
   Bad:  "Data shows X, Y, Z... therefore we conclude A"
   Good: "A is the key finding. This is supported by X (evidence), Y (evidence), Z (evidence)"

3. So-What Chain: Every paragraph of facts must end with an explicit implication.
   Pattern: [Fact] + [Fact] → [So what does this mean for the reader?]
   Mark implications clearly: "→ Implication:" or "This means..."

4. Claim-Evidence-Implication: Each analytical paragraph follows:
   - Claim: One clear statement
   - Evidence: Specific numbers, sources, citations
   - Implication: What the reader should do about it
```

#### 5.2.2 Analytical Table Specification

**替換** `"Include at least 3 structured comparison tables"` 為：

```
Tables must be ANALYTICAL, not descriptive. Each table should reveal an insight
that is not obvious from the text alone. Required table types (use where appropriate):

- Cross-tabulation: Compare 2+ dimensions with quantified cells
  (e.g., industry × job-type → shortage count, not just a feature list)
- Scoring/Decision matrix: Rate options against weighted criteria with numeric scores
- Decomposition: Break a total into components (TAM → SAM → SOM, or cost structure)
- Sensitivity: Show how output changes when key assumptions vary (±20%)

Do NOT create tables that are merely lists with columns. If a table has no numbers
or no cross-dimensional analysis, convert it to bullet points instead.
```

#### 5.2.3 Quantification Standard

追加 prompt 指令：

```
Quantification Rule:
- Replace vague words with numbers: "significant growth" → "23% CAGR (2022-2026)"
- Every market claim needs a source and a number
- If exact data is unavailable, provide order-of-magnitude estimates with assumptions stated
  (e.g., "Estimated TAM: ~NT$15B, assuming 2.1M blue-collar workers × NT$7,200 avg monthly platform spend")
- Use "approximately", "estimated", "our analysis suggests" for derived numbers
```

### 5.3 Layer 2: Computational Pipeline Fix

#### 5.3.1 Replace Blind Triage with Chart Planning

**問題**: `_requires_computational_analysis()` 問 "is there data?" — 太被動。
**解決**: 改為 `_plan_report_charts()` — 主動規劃每個 section 需要什麼圖表。

**新 flow**:
```
_plan_report_charts(report_plan, synthesis)
  → LLM 輸出: [
      {section: "市場分析", chart_type: "stacked_bar",
       data_source: "搜尋結果中的產業缺口數據",
       description: "各產業藍領缺口人數對比 (2022-2026)"},
      {section: "商業模式", chart_type: "waterfall",
       data_source: "unit economics 參數",
       description: "單位經濟拆解: GMV → Revenue → Gross Margin"},
      ...
    ]
  → 如果 sandbox 不在：將 chart plan 作為 text description 嵌入 report prompt
     （LLM 會用 markdown 近似表達）
  → 如果 sandbox 在：為每張圖產生 targeted Python code → execute → inline embed
```

**關鍵改變**: Chart planning 永遠執行（不需要 sandbox），只有 execution 依賴 sandbox。

#### 5.3.2 Targeted Code Generation

**替換** generic `get_computational_analysis_prompt()` 為 per-chart code generation：

```python
# Instead of one big "analyze everything" prompt:
for chart_spec in chart_plan:
    code = await self._generate_chart_code(chart_spec, search_data)
    result = await self._execute_analysis_code(code)
    if result:
        chart_results[chart_spec["section"]] = result
```

每張圖有明確的 spec（type、data source、target section），code quality 會遠高於 "write a Python script that analyzes everything"。

#### 5.3.3 Inline Chart Embedding

**替換** 尾部 `## Computational Analysis Figures` section，改為在 report prompt 中 per-section 提供 chart:

```python
# In _build_academic_report_prompt():
if chart_results.get(section_name):
    prompt += f"""
For section "{section_name}", a chart has been generated:
[Figure {fig_num}: {chart_spec['description']}]
Reference this figure inline and explain what it shows."""
```

Final report assembly 時，將 base64 image 插入對應 section（不是全部堆在最後）。

### 5.4 Layer 2b: Sandbox-free Fallback（重要）

如果 sandbox 不可用（Docker 不在），chart plan 仍然有價值：

1. **Text-based chart descriptions** — LLM 用 ASCII / markdown 近似表達（如 bar chart 用 `█████` 表示）
2. **Structured data tables** — 把 chart 的底層數據直接用 markdown table 呈現，但標注 "Figure X (data)"
3. **Mermaid diagrams** — flowchart、gantt、pie 用 mermaid 語法（許多 markdown renderer 支援）

這確保即使沒有 sandbox，報告仍然有 "visual thinking" 的痕跡。

### 5.5 Layer 3: Report Artifact Bundle（持久化與可追溯性）

#### 5.5.1 問題

**現狀**:
```
logs/reports/
  e675fcb8_20260218_122538.md    ← flat file, YAML frontmatter + markdown body
                                    figures 是 base64 inline（臃腫、不可單獨取用）
                                    metadata 混在 frontmatter 裡
                                    chart code / raw data 完全遺失
```

**問題**:
- **不可追溯**: base64 inline 圖片嵌在 .md 中，無法單獨檢視、比較、或在其他報告中複用
- **不可重現**: 產生圖表的 Python code 和 sandbox stdout 在 pipeline 結束後消失
- **不可管理**: 所有報告平鋪在同一目錄，隨時間增長變成垃圾堆
- **不可查詢**: metadata 藏在 frontmatter 裡，無法快速搜尋「哪些報告涵蓋了某個 domain」

#### 5.5.2 設計: Report Artifact Bundle

每份報告產出一個自包含的資料夾（bundle），結構如下：

```
logs/reports/
  {trace_id[:8]}_{timestamp}/           ← bundle directory
    report.md                           ← clean markdown (no base64, figures by relative path)
    metadata.json                       ← structured metadata (trace_id, query, mode, domains, duration, metrics)
    figures/                            ← chart images as standalone files
      fig_01_market_sizing.png
      fig_02_unit_economics_waterfall.png
      fig_03_sensitivity_tornado.png
    artifacts/                          ← computational analysis artifacts
      chart_plan.json                   ← LLM-generated chart specs
      fig_01_code.py                    ← source code that generated fig_01
      fig_01_stdout.txt                 ← sandbox stdout for fig_01
      fig_02_code.py
      fig_02_stdout.txt
    sources/                            ← research provenance
      search_results.json               ← raw search results (url, snippet, full_content)
      synthesis_history.json            ← per-iteration synthesis snapshots
```

#### 5.5.3 報告中的圖表引用

**現狀** (base64 inline — 臃腫):
```markdown
![Figure 1](data:image/png;base64,iVBORw0KGgoAAAANSUhE... <200KB>)
```

**目標** (relative path — 乾淨、可獨立管理):
```markdown
![Figure 1: 各產業藍領缺口對比 2022-2026](figures/fig_01_market_sizing.png)
```

前端 / markdown renderer 直接看到圖片路徑。API response 可選擇：
- 返回 bundle path，client 自行 fetch 圖片
- 返回 report.md + 自動將 relative path 替換為 base64（向下相容）

#### 5.5.4 metadata.json 結構

```json
{
  "trace_id": "e675fcb8-...",
  "query": "2026年藍領垂直領域平台服務轉型報告",
  "mode": "deep_research",
  "created_at": "2026-02-18T12:25:38+08:00",
  "duration_seconds": 1899.1,
  "iterations": 3,
  "research_domains": ["勞動市場與經濟趨勢", "法規與政策", ...],
  "content_domains": ["technology", "business", "labor/workforce", "regulation", "economics"],
  "metrics": {
    "word_count": 4996,
    "citation_count": 43,
    "table_count": 6,
    "figure_count": 3,
    "section_count": 63
  },
  "figures": [
    {"id": "fig_01", "filename": "fig_01_market_sizing.png", "section": "市場分析", "chart_type": "stacked_bar"},
    {"id": "fig_02", "filename": "fig_02_unit_economics_waterfall.png", "section": "商業模式", "chart_type": "waterfall"}
  ],
  "sources_count": 47,
  "model": "gpt-5-mini",
  "search_engines_used": ["tavily", "serper", "model"]
}
```

#### 5.5.5 Implementation: `_save_report_bundle()`

取代現有的 `self.logger.save_response_as_markdown()`，在 processor 中新增：

```python
def _save_report_bundle(self, report: str, context: ProcessingContext,
                         computational_result: Optional[Dict] = None,
                         chart_plan: Optional[List[Dict]] = None,
                         search_results: Optional[List[Dict]] = None) -> Path:
    """Save report + all artifacts as a self-contained bundle."""
    trace_id = context.request.trace_id
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = self.logger.log_dir / "reports" / f"{trace_id[:8]}_{timestamp}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extract figures from computational_result → save as PNG files
    figure_manifest = []
    if computational_result and computational_result.get("figures"):
        figures_dir = bundle_dir / "figures"
        figures_dir.mkdir(exist_ok=True)
        for i, fig_b64 in enumerate(computational_result["figures"], 1):
            spec = chart_plan[i-1] if chart_plan and i <= len(chart_plan) else {}
            filename = f"fig_{i:02d}_{spec.get('slug', 'chart')}.png"
            (figures_dir / filename).write_bytes(base64.b64decode(fig_b64))
            figure_manifest.append({
                "id": f"fig_{i:02d}", "filename": filename,
                "section": spec.get("section", ""), "chart_type": spec.get("chart_type", "")
            })

    # 2. Replace base64 in report with relative paths
    clean_report = report
    for fig in figure_manifest:
        # Replace data:image/png;base64,... with figures/filename
        clean_report = re.sub(
            rf'!\[Figure {fig["id"][-2:]}\]\(data:image/png;base64,[A-Za-z0-9+/=]+\)',
            f'![Figure {fig["id"][-2:]}](figures/{fig["filename"]})',
            clean_report
        )

    # 3. Save clean report.md
    (bundle_dir / "report.md").write_text(clean_report, encoding="utf-8")

    # 4. Save metadata.json
    metadata = { ... }  # structured from context.response.metadata
    (bundle_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 5. Save artifacts (chart code + stdout)
    if chart_plan or computational_result:
        artifacts_dir = bundle_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        if chart_plan:
            (artifacts_dir / "chart_plan.json").write_text(
                json.dumps(chart_plan, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        # per-chart code + stdout saved during execution

    # 6. Save research provenance
    if search_results:
        sources_dir = bundle_dir / "sources"
        sources_dir.mkdir(exist_ok=True)
        (sources_dir / "search_results.json").write_text(
            json.dumps(search_results, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return bundle_dir
```

#### 5.5.6 Backward Compatibility

- 現有的 `save_response_as_markdown()` 保留不動（其他 mode 仍使用）
- 只有 `deep_research` mode 使用新的 bundle 機制
- API response 預設仍返回 full report string（含 base64），bundle 是額外的持久化層
- 未來可加 API endpoint: `GET /reports/{trace_id}/figures/{filename}` 直接取圖

---

## 6. Priority & Effort Matrix

| # | Action | Impact | Effort | Priority |
|---|---|---|---|---|
| A | Report prompt: MECE + Pyramid + So-What 指令 | High | Low (prompt only) | **P0** |
| B | Table prompt: 分析型表格 spec 替換 listing | High | Low (prompt only) | **P0** |
| C | Quantification standard 追加 | Medium | Low (prompt only) | **P0** |
| D | Chart planning phase (always-on, no sandbox needed) | High | Medium (new method + prompt) | **P1** |
| E | Targeted per-chart code gen (replaces generic) | High | Medium (refactor existing) | **P1** |
| F | Inline chart embedding (replaces tail section) | Medium | Low (template change) | **P1** |
| G | Report artifact bundle (`_save_report_bundle`) | High | Medium (new method, replaces save logic) | **P1** |
| H | Sandbox-free fallback (mermaid/ASCII/data tables) | Medium | Medium (new logic) | **P2** |
| I | Report index API (`GET /reports/`) | Low | Low (route + glob) | **P2** |

**建議**: P0 三項純 prompt 改動，零風險、零架構變更、立即生效。P1 改 processor — chart planning + artifact bundle 同步實作（圖表產出自然需要 bundle 承接）。

---

## 7. Expected Outcome

### Before (Current V.1)
```
報告品質:  "通過考試" — 字數夠、引用多、有表格
表格類型:  100% listing / descriptive
圖表:     0
分析深度:  描述 > 分析，缺 So-What
結構:     有 sections 但有重複，非 MECE
持久化:   flat .md file, base64 inline, metadata in frontmatter
可追溯性: 無（code/data/provenance 消失）
```

### After (P0 Prompt Upgrades Only)
```
報告品質:  "top 20%" — 結構清晰、每段有推論
表格類型:  60%+ analytical (cross-tab, scoring matrix)
圖表:     0（prompt only，sandbox 問題未解）
分析深度:  Claim-Evidence-Implication chain
結構:     MECE、Pyramid、So-What
持久化:   同上（P0 不改存儲）
```

### After (P0 + P1)
```
報告品質:  "McKinsey junior analyst level"
表格類型:  80%+ analytical
圖表:     3-5 per report (inline in correct section)
分析深度:  量化推論 + 視覺化佐證
結構:     MECE + 圖表驅動敘事
持久化:   bundle directory — report.md + figures/ + artifacts/ + sources/
可追溯性: chart code 可重現、search results 可查、metadata 可查詢
```

---

## 8. Files to Modify

| File | Changes |
|---|---|
| `src/core/prompts.py` | Replace report requirements, add chart planning prompt, add quantification rules |
| `src/core/processors/research/processor.py` | Add `_plan_report_charts()`, `_save_report_bundle()`, refactor computational phase, inline embedding |
| `src/core/logger.py` | No change (existing `save_response_as_markdown` kept for non-deep-research modes) |

---

*Analysis generated: 2026-02-18*
*Perspective: McKinsey-grade report quality standard + artifact management*
