# Deep Research 迭代摘要策略修復方案 (已實作 + v3.3 更新)

## 問題診斷

### 資訊漏斗 (Information Funnel) — 三個致命瓶頸

Deep Research pipeline 的資料流呈現嚴重的單向壓縮：

```
原始搜尋結果 (~500K chars)
    │
    ▼ summarize_search_results()  [max 8K/result, 200K total]
波次摘要 (~70K chars)                     ← 瓶頸 1: ~65% 資訊損失
    │
    ▼ intermediate_synthesis()   [LLM 壓縮成 JSON]
accumulated_synthesis (~3.5K chars)       ← 瓶頸 2: ~95% 累計損失
    │
    ▼ reporter.py:82  [synthesis or prepare_report_context()]
最終報告輸入 (~3.5K chars)                ← 瓶頸 3: 原始資料完全不可達
```

### 瓶頸 1: `summarize_search_results()` (analyzer.py:17-47)

- 每筆結果截斷到 8000 chars，總量截斷到 200K chars
- 只保留 `full_content` / `processed` / `summary` 之一
- **丟失**: 來源 URL、metadata、多源交叉驗證資訊

### 瓶頸 2: `intermediate_synthesis()` (analyzer.py:57-101)

- 輸入 ~70K chars 的波次摘要 + 前次 synthesis
- LLM 輸出 JSON，其中 `synthesis` 欄位只有 ~3.5K chars
- **丟失**: 原始數據的細粒度資訊、具體數字、直接引用
- `section_coverage`, `evidence_quality`, `knowledge_gaps`, `cross_domain_links` 都有產出，但...

### 瓶頸 3: `write_final_report()` (reporter.py:82)

```python
research_context = synthesis or prepare_report_context(search_results)
```

- `synthesis` 永遠非 None（processor.py:274 保證），所以 `prepare_report_context()` **永遠不會執行**
- 最終報告 LLM 只收到 ~3.5K chars 的壓縮摘要
- `section_coverage`, `evidence_quality`, `knowledge_gaps`, `cross_domain_links` 全部被丟棄，從未傳遞到 reporter

### 影響

| 階段 | 輸入量 | 輸出量 | 累計保留率 |
|------|--------|--------|-----------|
| 原始搜尋 | ~500K | ~500K | 100% |
| summarize | ~500K | ~70K | ~14% |
| synthesis | ~70K | ~3.5K | ~0.7% |
| 最終報告 | ~3.5K | ~3.5K | ~0.7% |

最終報告的 LLM 只看到原始資料的 **0.7%**。

---

## 修復方案: Dual-Context + Structured Metadata

### 核心理念

> 不要二選一 — 給 LLM 「摘要骨架 + 原始細節」雙軌輸入。

```
最終報告 LLM 輸入:
  ├── synthesis (~3.5K)      ← 結構化骨架：整體理解、章節覆蓋、知識缺口
  ├── detailed_context (~50K) ← 原始細節：具體數字、引用、來源 URL
  └── metadata (structured)   ← section_coverage + evidence_quality + cross_domain_links
```

### 改動 1: `reporter.py` — Dual-Context 組合

**改動**: `write_final_report()` 不再 `synthesis or prepare_report_context()`，改為兩者合併。

```python
# reporter.py:82 — BEFORE
research_context = synthesis or prepare_report_context(search_results)

# reporter.py:82 — AFTER
detailed_context = prepare_report_context(search_results)
if synthesis:
    research_context = (
        f"## Research Synthesis (Structured Overview)\n\n{synthesis}"
        f"\n\n---\n\n"
        f"## Detailed Source Material\n\n{detailed_context}"
    )
else:
    research_context = detailed_context
```

**約束**: `research_context` 總量不超過 LLM context window 的 60%。
`prepare_report_context()` 的 `max_total` 參數依模型動態調整：
- GPT-4o / Claude Sonnet: `max_total=80000`
- GPT-4o-mini: `max_total=40000`

### 改動 2: `write_final_report()` — 接收 structured metadata

> **v3.3 更新**: `critical_analysis` 和 `computational_result` 參數已移除。當前簽名為：
> ```python
> async def write_final_report(self, context, search_results, report_plan,
>                              synthesis=None, language=None,
>                              evidence_index=None):
> ```

```python
# 原始提案（歷史記錄）:
async def write_final_report(self, context, search_results, report_plan,
                             critical_analysis=None, computational_result=None,
                             synthesis=None, language=None,
                             synthesis_metadata=None):  # NEW
```

`synthesis_metadata` 結構:
```python
{
    "section_coverage": {"section_name": {"status": "covered|partial|missing", ...}},
    "evidence_quality": {"section_name": {"tier1_2_count": 3, ...}},
    "knowledge_gaps": ["gap1", "gap2"],
    "cross_domain_links": ["link1", "link2"],
}
```

### 改動 3: `build_academic_report_prompt()` — 注入 metadata

在 prompt 中加入:

```
## Research Quality Metadata

### Section Coverage
{section_coverage formatted}

### Evidence Quality Assessment
{evidence_quality formatted}

### Known Knowledge Gaps
{knowledge_gaps formatted}

### Cross-Domain Connections
{cross_domain_links formatted}

INSTRUCTIONS:
- For sections marked "partial" or "missing", acknowledge limitations explicitly
- For sections with low Tier 1-2 source count, qualify claims appropriately
- Use cross-domain connections to strengthen the analysis
- Address knowledge gaps honestly in the report
```

### 改動 4: `processor.py` — 傳遞完整 synthesis_result

```python
# processor.py:243 — BEFORE
accumulated_synthesis = synthesis_result.get("synthesis", "")
section_coverage = synthesis_result.get("section_coverage", {})

# processor.py:243 — AFTER
accumulated_synthesis = synthesis_result.get("synthesis", "")
section_coverage = synthesis_result.get("section_coverage", {})
synthesis_metadata = {
    "section_coverage": section_coverage,
    "evidence_quality": synthesis_result.get("evidence_quality", {}),
    "knowledge_gaps": synthesis_result.get("knowledge_gaps", []),
    "cross_domain_links": synthesis_result.get("cross_domain_links", []),
}
```

```python
# processor.py:299 — BEFORE
final_report = await self.reporter.write_final_report(
    context, all_search_results, report_plan,
    critical_analysis, computational_result,
    synthesis=synthesis,
    language=user_language,
)

# processor.py:299 — AFTER
final_report = await self.reporter.write_final_report(
    context, all_search_results, report_plan,
    critical_analysis, computational_result,
    synthesis=synthesis,
    language=user_language,
    synthesis_metadata=synthesis_metadata,
)
```

### 改動 5: `prepare_report_context()` — 保留來源 URL

```python
# reporter.py:23 — BEFORE: 不包含 sources URL
entry = f"""
    搜索 {i}: {result['query']}
    目標: {result['goal']}
    ...
    來源數量: {len(result['result'].get('sources', []))}
    """

# reporter.py:23 — AFTER: 加入 top-3 來源 URL
sources = result['result'].get('sources', [])
source_urls = "\n".join(f"    - [{s.get('title','')}]({s.get('url','')})"
                        for s in sources[:3])
entry = f"""
    搜索 {i}: {result['query']}
    目標: {result['goal']}
    優先級: {result.get('priority', 1)}
    結果摘要: {summary}
    處理結果: {processed}
    關鍵來源:
{source_urls}
    """
```

---

## 改動影響分析

| 檔案 | 改動量 | 風險 |
|------|--------|------|
| `reporter.py` | ~30 行 | 低 — 只擴充輸入，不改輸出格式 |
| `processor.py` | ~10 行 | 低 — 只新增參數傳遞 |
| `prompts.py` (可選) | ~15 行 | 低 — prompt 內追加 metadata 區塊 |
| `analyzer.py` | 0 行 | 無 — 不需改動 |
| `planner.py` | 0 行 | 無 — 不需改動 |

### 向後相容性

- `synthesis_metadata` 預設 `None`，所有現有呼叫不受影響
- `prepare_report_context()` 已存在且可用，只是之前被 `or` 短路跳過
- Dual-context 在 `synthesis` 為 None 時退化為原始行為

### Token 預算估算

| 組件 | 估計 tokens |
|------|------------|
| synthesis | ~1,500 |
| detailed_context (80K chars) | ~25,000 |
| metadata | ~800 |
| report_plan | ~1,000 |
| critical_analysis | ~2,000 |
| prompt template | ~500 |
| **Total input** | **~30,800** |

對 128K context 的模型而言，30K input tokens 完全在安全範圍內（剩餘 ~97K 給 output）。

---

## 資訊保留率改善

| 階段 | 修復前保留率 | 修復後保留率 |
|------|-------------|-------------|
| summarize | 14% | 14% (不變) |
| synthesis | 0.7% | 0.7% (不變) |
| 最終報告輸入 | **0.7%** | **~16%** (synthesis + detailed_context) |

從 0.7% 提升到 ~16%，**提升 23 倍**。

---

## 進階優化 (已實作)

以下三項已在 `section_synthesizer.py` 中實作：

1. **Section-aware retrieval**: `classify_results_to_sections()` — 1 LLM call 將搜尋結果按章節分類
2. **Hierarchical synthesis**: `synthesize_section()` — 每個 section 獨立 LLM synthesis (parallel)
3. **Evidence citation index**: 每個 section synthesis 輸出 `evidence_index` (claim -> source_ids mapping)

新增檔案: `src/core/processors/research/section_synthesizer.py` (~230 lines)
新增 prompts: `get_section_classification_prompt()`, `get_section_synthesis_prompt()`

---

## 驗證方式

1. **對照測試**: 同一查詢，比較修復前後報告的具體數字、引用數量、章節完整度
2. **Token 監控**: 確認最終報告 prompt 的 input tokens 在模型限制內
3. **回歸測試**: 確認 `synthesis=None` 的退化路徑正常
4. **品質指標**: 報告中「具體數字」出現次數、引用來源數量

---

## v3.3 Pipeline Reengineering 更新 (2026-02-25)

本方案的核心改動（Dual-Context + Section-Aware Synthesis）已在 v3.3 中保留並強化。以下為 v3.3 對本方案的影響：

### 保留
- Dual-Context 組合（synthesis + detailed_context）
- Section-Aware Hierarchical Synthesis (`section_synthesizer.py`)
- Evidence Citation Index
- `prepare_report_context()` 來源 URL 保留

### 移除
- `critical_analysis` 參數 — 整個 Critical Analysis 階段已移除
- `computational_result` 參數 — 整個 Chart Pipeline 已移除
- `synthesis_metadata` 參數 — evidence_index 直接透過獨立參數傳遞

### 當前 `write_final_report()` 簽名
```python
async def write_final_report(
    self, context: ProcessingContext,
    search_results: List[Dict],
    report_plan: str,
    synthesis: str = None,
    language: str = None,
    evidence_index: Optional[List[Dict]] = None,
) -> str:
```
