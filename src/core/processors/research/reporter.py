"""
Report Generator - Final report generation, formatting, and persistence

Contains report writing, citation analysis, reference categorization,
academic prompt construction, and report bundle saving.
Extracted from DeepResearchProcessor (~500 lines).
"""

import re
import json
import base64
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Any, Callable, Awaitable

from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger
from .analyzer import summarize_search_results


def prepare_report_context(search_results: List[Dict],
                           max_per_result: int = 6000,
                           max_total: int = 200000) -> str:
    """Prepare report context from search results (with truncation protection).

    Standalone function — used by both ReportGenerator and ResearchPlanner.
    """
    context_parts = []
    total_chars = 0
    for i, result in enumerate(search_results, 1):
        summary = result['result'].get('summary', '')
        processed = result['result'].get('processed', '')
        if isinstance(processed, str) and len(processed) > max_per_result:
            processed = processed[:max_per_result] + "... [truncated]"
        entry = f"""
            搜索 {i}: {result['query']}
            目標: {result['goal']}
            優先級: {result.get('priority', 1)}
            結果摘要: {summary}
            處理結果: {processed}
            來源數量: {len(result['result'].get('sources', []))}
            """
        total_chars += len(entry)
        if total_chars > max_total:
            context_parts.append(f"... [{len(search_results) - i} more results truncated]")
            break
        context_parts.append(entry)
    return "\n\n".join(context_parts)


class ReportGenerator:
    """Final report generation, citation analysis, and persistence."""

    def __init__(self, call_llm: Callable[..., Awaitable[str]],
                 log_dir: str = None,
                 model_name: str = 'unknown'):
        self._call_llm = call_llm
        self.log_dir = log_dir
        self.model_name = model_name
        self.logger = structured_logger

    async def write_final_report(self, context: ProcessingContext,
                                 search_results: List[Dict],
                                 report_plan: str,
                                 critical_analysis: Optional[str] = None,
                                 computational_result: Optional[Dict[str, Any]] = None,
                                 synthesis: str = None) -> str:
        """Generate final academic-style report with categorized references."""
        self.logger.progress("final-report", "start")

        self.logger.info(
            f"Final Report: Synthesizing {len(search_results)} search results",
            "deep_research", "final_report",
            phase="final-report",
            results_count=len(search_results),
            plan_length=len(report_plan)
        )

        research_context = synthesis or prepare_report_context(search_results)
        references_list = self.extract_references(search_results)

        self.logger.info(
            "Memory: Research context for report",
            "memory", "store",
            context_size=len(research_context),
            chunks=len(search_results),
            type="research_report"
        )

        enhanced_prompt = self.build_academic_report_prompt(
            report_plan, research_context, references_list,
            context.request.query,
            critical_analysis, computational_result
        )

        self.logger.reasoning("綜合所有研究結果，生成最終報告...", streaming=True)
        report_body = await self._call_llm(enhanced_prompt, context)

        cited_refs, uncited_refs, citation_stats = self.analyze_citations(
            report_body, references_list
        )

        final_report = self.format_report_with_categorized_references(
            report_body, cited_refs, uncited_refs, context,
            critical_analysis is not None, citation_stats, computational_result
        )

        self.logger.info(
            "Memory: Retrieved research synthesis",
            "memory", "retrieve",
            report_length=len(final_report),
            citations_included=True
        )

        self.logger.message(final_report, streaming=False)

        report_metadata = {
            "title": f"Research Report: {context.request.query[:50]}",
            "sections": self.extract_report_sections(final_report),
            "sources_used": sum(
                len(r['result'].get('sources', [])) for r in search_results
            ),
            "word_count": len(final_report.split()),
            "timestamp": datetime.now().isoformat()
        }

        self.logger.info(
            f"Report Completed: {report_metadata['word_count']} words, "
            f"{report_metadata['sources_used']} sources",
            "deep_research", "complete",
            metadata=report_metadata
        )

        self.logger.progress("final-report", "end", {"data": report_metadata})
        return final_report

    def extract_report_sections(self, report: str) -> List[str]:
        """Extract markdown headings from report."""
        headers = re.findall(r'^#{1,3}\s+(.+)$', report, re.MULTILINE)
        return headers[:10]

    def extract_references(self, search_results: List[Dict]) -> List[Dict]:
        """Extract references from search results."""
        references = []
        ref_id = 1

        for result in search_results:
            sources = result.get('result', {}).get('sources', [])
            for source in sources:
                if source.get('url'):
                    references.append({
                        'id': ref_id,
                        'title': source.get('title', 'Untitled'),
                        'url': source.get('url'),
                        'query': result.get('query', ''),
                        'relevance': source.get('relevance', 0)
                    })
                    ref_id += 1

        references.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return references

    def build_academic_report_prompt(self, plan: str, context: str,
                                     references: List[Dict], requirement: str,
                                     critical_analysis: Optional[str] = None,
                                     computational_result: Optional[Dict[str, Any]] = None) -> str:
        """Build academic-format report prompt with critical analysis and computation."""
        ref_summary = "\n".join([
            f"[{ref['id']}] {ref['title']}"
            for ref in references
        ])

        prompt = f"""Generate a comprehensive research report based on the following information.

Research Plan:
{plan}

Research Context and Findings:
{context}

Available References:
{ref_summary}"""

        if critical_analysis:
            prompt += f"""

Critical Analysis (Multi-Perspective Thinking):
{critical_analysis}

IMPORTANT: Integrate the insights from the critical analysis throughout your report.
Use the multi-perspective thinking to enrich your conclusions and provide more nuanced views."""

        prompt += f"""

Requirements:

=== STRUCTURE (MECE + Pyramid Principle) ===
1. Open with Executive Summary (3-5 bullet conclusions FIRST, then supporting evidence below)
2. Structure every section using MECE: sub-sections must be mutually exclusive and collectively exhaustive — no overlaps, no gaps
3. Each section follows the Pyramid Principle: state the conclusion/claim as the section heading, then provide supporting evidence underneath
4. Every factual claim ends with a So-What: "This means..." or "The implication is..." — never leave raw data without interpretation

=== ANALYTICAL DEPTH (Claim-Evidence-Implication) ===
5. Every analytical paragraph follows CEI: Claim (one sentence) → Evidence (data, citations) → Implication (so-what for the reader)
6. Cross-domain synthesis is mandatory: connect findings from different fields (e.g., regulatory changes → business model impact → technology response)
7. Include forward-looking analysis with specific trend predictions (2-5 year horizon with quantified estimates)

=== TABLES (Analytical, Not Listing) ===
8. Include 3-5 ANALYTICAL tables. Each table MUST have a "So-What" interpretation paragraph immediately after it. BANNED table types: simple feature lists, timeline-only tables, raw data dumps
9. Required analytical table types (use at least 2): Cross-tabulation matrix (rows vs columns with scores/ratings), Comparative scoring matrix (weighted criteria evaluation), Decomposition waterfall (breaking totals into components), Risk-impact quadrant (2x2 or 3x3 matrix with strategic implications)
10-TABLE. MANDATORY: All tables MUST use standard Markdown pipe syntax. Example:
| Criterion | Option A | Option B | Score |
|-----------|----------|----------|-------|
| data      | data     | data     | data  |
Do NOT describe tables in prose. Do NOT use bullet lists as table substitutes. Render every table as a proper Markdown pipe table with header row and separator row.

=== QUANTIFICATION ===
10. Every market claim must include specific numbers: market size ($B), growth rate (CAGR%), adoption rate (%), company names with revenue/headcount
11. Use inline citations [1], [2], [3] for every factual claim — minimum 15 unique citations across the report
12. DO NOT include a references section in your output (it will be added separately)

=== OUTPUT STANDARDS ===
13. Aim for 3000+ words with deep analysis, not surface-level summarization
14. Structure with ## for main sections, ### for sub-sections
15. Write in professional analytical tone — BANNED vague phrases: "重要的是", "值得注意的是", "眾所周知" — replace with specific analytical claims
16. Include specific company names, product names, statistics, and real-world examples"""

        req_num = 17
        if critical_analysis:
            prompt += f"""
{req_num}. Incorporate critical analysis insights to provide balanced, multi-perspective conclusions
{req_num + 1}. Address potential limitations, counterarguments, or alternative interpretations
{req_num + 2}. Demonstrate analytical depth beyond surface-level findings"""
            req_num += 3

        if computational_result:
            stdout = computational_result.get('stdout', '')
            figure_count = len(computational_result.get('figures', []))
            prompt += f"""

Computational Analysis Results:
The following quantitative analysis was performed programmatically:

Output:
{stdout}

Number of charts/figures generated: {figure_count}

IMPORTANT: Integrate these computational findings into your report:
- Reference specific numbers, calculations, and statistical results from the output
- If charts were generated, reference them as "Figure 1", "Figure 2", etc. INLINE within the relevant analysis section's paragraph (e.g., "As shown in Figure 1, the market share distribution reveals...")
- Do NOT create a separate section for figures/charts — embed each figure reference naturally in the section where its data is discussed
- Explain what the computational analysis reveals in plain language"""

            prompt += f"""
{req_num}. Integrate computational analysis results with specific numbers and findings
{req_num + 1}. Reference generated figures as "Figure 1", "Figure 2" etc. where relevant"""

        prompt += f"""

User's Research Question:
{requirement}"""

        prompt += f"""

IMPORTANT:
- Use citations [1] to [{len(references)}] naturally throughout the text
- Make the report comprehensive and detailed (aim for 3000+ words)
- Structure with clear headings using ## for main sections
- Write in professional, academic tone

Generate the report body (without references section):
"""

        return prompt

    def analyze_citations(self, report_body: str, references: List[Dict]) -> tuple:
        """Analyze which references are actually cited in the report.

        Returns: (cited_refs, uncited_refs, citation_stats)
        """
        citation_pattern = r'\[(\d+)\]'
        citation_counts = Counter()
        invalid_citations = set()

        valid_ref_ids = {ref['id'] for ref in references}

        for match in re.finditer(citation_pattern, report_body):
            try:
                ref_num = int(match.group(1))
                citation_counts[ref_num] += 1
                if ref_num not in valid_ref_ids:
                    invalid_citations.add(ref_num)
            except ValueError:
                continue

        cited_refs = []
        uncited_refs = []

        for ref in references:
            if ref['id'] in citation_counts:
                ref_with_count = ref.copy()
                ref_with_count['citation_count'] = citation_counts[ref['id']]
                cited_refs.append(ref_with_count)
            else:
                uncited_refs.append(ref)

        cited_refs.sort(key=lambda x: x.get('citation_count', 0), reverse=True)

        citation_stats = {
            'total_citations': sum(citation_counts.values()),
            'unique_citations': len(citation_counts),
            'invalid_citations': list(invalid_citations),
            'most_cited': citation_counts.most_common(5),
            'avg_citations_per_source': (
                sum(citation_counts.values()) / max(1, len(citation_counts))
            ),
            'citation_distribution': dict(citation_counts)
        }

        return cited_refs, uncited_refs, citation_stats

    def format_report_with_categorized_references(self, report_body: str,
                                                  cited_refs: List[Dict],
                                                  uncited_refs: List[Dict],
                                                  context: ProcessingContext = None,
                                                  has_critical_analysis: bool = False,
                                                  citation_stats: Dict = None,
                                                  computational_result: Optional[Dict[str, Any]] = None) -> str:
        """Format report with categorized references and citation statistics."""
        references_section = "\n\n---\n\n"

        if cited_refs:
            references_section += "## 參考文獻 (Cited References)\n\n"
            references_section += "*以下為報告中實際引用的文獻（按引用次數排序）：*\n\n"

            for ref in cited_refs[:30]:
                citation_count = ref.get('citation_count', 0)
                citation_indicator = f" `×{citation_count}`" if citation_count > 1 else ""

                ref_entry = f"[{ref['id']}] **{ref['title']}**{citation_indicator}\n"
                if ref.get('url'):
                    ref_entry += f"   URL: {ref['url']}\n"
                if ref.get('query'):
                    ref_entry += f"   Search context: {ref['query'][:50]}...\n"
                references_section += f"{ref_entry}\n"

        if uncited_refs:
            references_section += "\n## 相關文獻 (Related Sources - Not Cited)\n\n"
            references_section += "*以下為研究過程中查閱但未直接引用的相關資料：*\n\n"

            for ref in uncited_refs[:20]:
                ref_entry = f"- {ref['title']}\n"
                if ref.get('url'):
                    ref_entry += f"  URL: {ref['url']}\n"
                references_section += f"{ref_entry}\n"

        references_section += f"\n---\n\n## 引用統計 (Citation Statistics)\n\n"

        references_section += f"### 基本指標\n"
        references_section += f"- **實際引用文獻**: {len(cited_refs)} 篇\n"
        references_section += f"- **相關未引用文獻**: {len(uncited_refs)} 篇\n"
        references_section += f"- **總查閱文獻**: {len(cited_refs) + len(uncited_refs)} 篇\n"
        references_section += (
            f"- **引用率**: "
            f"{len(cited_refs) / max(1, len(cited_refs) + len(uncited_refs)) * 100:.1f}%\n"
        )

        if citation_stats:
            references_section += f"\n### 引用深度分析\n"
            references_section += f"- **總引用次數**: {citation_stats['total_citations']} 次\n"
            references_section += (
                f"- **平均每篇文獻被引用**: "
                f"{citation_stats['avg_citations_per_source']:.1f} 次\n"
            )

            if citation_stats['most_cited']:
                references_section += f"- **最常引用**: "
                most_cited_strs = [
                    f"[{ref_id}] ({count}次)"
                    for ref_id, count in citation_stats['most_cited'][:3]
                ]
                references_section += ", ".join(most_cited_strs) + "\n"

            if citation_stats['invalid_citations']:
                references_section += (
                    f"\n**警告**: 檢測到 {len(citation_stats['invalid_citations'])} "
                    f"個無效引用編號: {citation_stats['invalid_citations']}\n"
                )

        references_section += f"\n### 分析模式\n"
        modes = ["深度研究"]
        if has_critical_analysis:
            modes.append("批判性思考")
        if computational_result:
            fig_count = len(computational_result.get("figures", []))
            modes.append(f"計算分析 ({fig_count} figures)")
        references_section += f"- **研究模式**: {' + '.join(modes)}\n"

        references_section += f"\n---\n"
        references_section += f"*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        references_section += f"*Powered by OpenCode Deep Research Engine"

        if has_critical_analysis:
            references_section += f" with Critical Analysis*"
        else:
            references_section += f"*"

        # Embed figures inline where "Figure N" is referenced in text
        overflow_figures = ""
        if computational_result and computational_result.get("figures"):
            figure_specs = computational_result.get("figure_specs", [])
            for i, fig_base64 in enumerate(computational_result["figures"], 1):
                spec = figure_specs[i - 1] if i - 1 < len(figure_specs) else {}
                title = spec.get("title", f"Figure {i}")
                insight = spec.get("insight", "")

                figure_md = f"\n\n**Figure {i}: {title}**\n\n"
                figure_md += f"![Figure {i}: {title}](data:image/png;base64,{fig_base64})\n\n"
                if insight:
                    figure_md += f"*{insight}*\n\n"

                inserted = False
                fig_ref_pattern = re.compile(
                    rf'Figure\s+{i}\b', re.IGNORECASE
                )
                match = fig_ref_pattern.search(report_body)
                if match:
                    para_end = report_body.find('\n\n', match.end())
                    if para_end == -1:
                        para_end = len(report_body)
                    else:
                        para_end += 1
                    report_body = (
                        report_body[:para_end] + figure_md + report_body[para_end:]
                    )
                    inserted = True

                if not inserted:
                    overflow_figures += figure_md

        full_report = f"{report_body}{overflow_figures}{references_section}"

        # Save report as structured bundle
        if context:
            try:
                save_path = self.save_report_bundle(
                    full_report, context, computational_result, cited_refs
                )
                if save_path:
                    self.logger.info(
                        f"Report saved to: {save_path}",
                        "deep_research", "report_saved"
                    )
            except Exception as e:
                self.logger.warning(
                    f"Failed to save report: {e}",
                    "deep_research", "save_error"
                )

        return full_report

    def save_report_bundle(self, full_report: str, context: ProcessingContext,
                           computational_result: Optional[Dict[str, Any]] = None,
                           cited_refs: List[Dict] = None) -> Optional[str]:
        """Save report as a structured bundle: report.md + metadata.json + figures/."""
        log_dir = self.log_dir or getattr(self.logger, 'log_dir', 'logs')
        trace_id = context.request.trace_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"{trace_id[:8]}_{timestamp}"

        reports_dir = Path(log_dir) / "reports"
        bundle_dir = reports_dir / bundle_name
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save figures as individual PNG files + replace base64 inline
        report_for_bundle = full_report
        if computational_result and computational_result.get("figures"):
            figures_dir = bundle_dir / "figures"
            figures_dir.mkdir(exist_ok=True)
            for i, fig_b64 in enumerate(computational_result["figures"], 1):
                fig_bytes = base64.b64decode(fig_b64)
                (figures_dir / f"figure_{i}.png").write_bytes(fig_bytes)
                report_for_bundle = re.sub(
                    rf'!\[Figure {i}[^\]]*\]\(data:image/png;base64,[A-Za-z0-9+/=]+\)',
                    f'![Figure {i}](figures/figure_{i}.png)',
                    report_for_bundle,
                )

        (bundle_dir / "report.md").write_text(report_for_bundle, encoding="utf-8")

        # 2. Save metadata.json
        figure_specs = (computational_result or {}).get("figure_specs", [])
        metadata = {
            "query": context.request.query if context.request else "N/A",
            "mode": "deep_research",
            "model": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": context.response.metadata.get("total_duration_ms", 0),
            "tokens": context.response.metadata.get("total_tokens", {}),
            "citations": {
                "cited_count": len(cited_refs) if cited_refs else 0,
            },
            "figures": {
                "count": (
                    len(computational_result.get("figures", []))
                    if computational_result else 0
                ),
                "titles": [s.get("title", "") for s in figure_specs],
            },
            "stages": context.response.metadata.get("stages", []),
        }
        (bundle_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self.logger.info(
            f"Report bundle saved: {bundle_dir}",
            "deep_research", "bundle_saved"
        )
        return str(bundle_dir)
