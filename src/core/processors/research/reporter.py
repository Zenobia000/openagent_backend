"""
Report Generator - Final report generation, formatting, and persistence

Contains report writing, citation analysis, reference categorization,
academic prompt construction, and report bundle saving.
Extracted from DeepResearchProcessor (~500 lines).
"""

import re
import json
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
                                 synthesis: str = None,
                                 language: str = None,
                                 evidence_index: Optional[List[Dict]] = None) -> str:
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
            language=language,
            evidence_index=evidence_index,
        )

        self.logger.reasoning("綜合所有研究結果，生成最終報告...", streaming=True)
        report_body = await self._call_llm(enhanced_prompt, context)

        cited_refs, uncited_refs, citation_stats = self.analyze_citations(
            report_body, references_list
        )

        final_report = self.format_report_with_categorized_references(
            report_body, cited_refs, uncited_refs, context,
            citation_stats=citation_stats,
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
                                     language: str = None,
                                     evidence_index: Optional[List[Dict]] = None) -> str:
        """Build report prompt — streamlined guidelines, trust model reasoning."""
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

        if evidence_index:
            evidence_lines = []
            for e in evidence_index[:50]:
                sources = ", ".join(f"[{sid}]" for sid in e.get("source_ids", []))
                conf = e.get("confidence", "medium").capitalize()
                evidence_lines.append(f"- \"{e.get('claim', '')}\" -> cite {sources} ({conf})")
            evidence_block = "\n".join(evidence_lines)
            prompt += f"""

Evidence Citation Index (pre-verified claim-source mappings):
{evidence_block}

INSTRUCTION: Use the evidence index above for accurate inline citations.
Each claim has been verified against specific sources — cite them using the exact [N] reference numbers provided."""

        prompt += f"""

Requirements:
1. Use inline citations [1], [2], [3] for factual claims throughout the report
2. DO NOT include a references section in your output (it will be added separately)
3. Structure with ## for main sections, ### for sub-sections
4. Aim for 3000+ words with substantive analysis
5. Include specific numbers, company names, statistics, and real-world examples where available
6. When using tables, use standard Markdown pipe syntax with header and separator rows
7. Cross-reference findings across different sections to build a cohesive narrative
8. Prioritize Tier 1-2 sources for core claims. When citing weaker sources for key numbers, note the limitation
9. Include a brief Methodology section near the end: research scope, sources reviewed, key limitations
10. Write naturally and analytically — avoid repetitive templates or formulaic paragraph structures

User's Research Question:
{requirement}"""

        lang_instruction = ""
        if language:
            lang_instruction = f"\n- CRITICAL: Write the ENTIRE report in {language}. All headings, body text, table content, and analysis MUST be in {language}."

        prompt += f"""

IMPORTANT:
- Use citations [1] to [{len(references)}] naturally throughout the text
- Make the report comprehensive and detailed (aim for 3000+ words)
- Structure with clear headings using ## for main sections{lang_instruction}

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
                                                  citation_stats: Dict = None) -> str:
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
        references_section += f"- **研究模式**: 深度研究\n"

        references_section += f"\n---\n"
        references_section += f"*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        references_section += f"*Powered by OpenCode Deep Research Engine*"

        full_report = f"{report_body}{references_section}"

        # Save report as structured bundle
        if context:
            try:
                save_path = self.save_report_bundle(
                    full_report, context, cited_refs
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
                           cited_refs: List[Dict] = None) -> Optional[str]:
        """Save report as a structured bundle: report.md + metadata.json."""
        log_dir = self.log_dir or getattr(self.logger, 'log_dir', 'logs')
        trace_id = context.request.trace_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"{trace_id[:8]}_{timestamp}"

        reports_dir = Path(log_dir) / "reports"
        bundle_dir = reports_dir / bundle_name
        bundle_dir.mkdir(parents=True, exist_ok=True)

        (bundle_dir / "report.md").write_text(full_report, encoding="utf-8")

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
