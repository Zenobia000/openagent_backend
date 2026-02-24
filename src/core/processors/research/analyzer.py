"""
Research Analyzer - Synthesis and critical analysis

Contains progressive synthesis, critical analysis, and search result summarization.
Extracted from DeepResearchProcessor (~120 lines).
"""

import json
import re
from typing import Dict, List, Optional, Any, Callable, Awaitable

from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger


def summarize_search_results(search_results: List[Dict],
                             max_per_result: int = 8000,
                             max_total: int = 200000) -> str:
    """Summarize search results — prefer full_content over snippets.

    Standalone function used across multiple sub-modules.
    Truncates per-result and total output to stay within LLM context limits.
    """
    summaries = []
    total_chars = 0
    for i, result in enumerate(search_results, 1):
        query = result.get('query', 'Unknown')
        inner = result.get('result', {}) if isinstance(result.get('result'), dict) else {}
        content = (
            inner.get('full_content')
            or result.get('results', '')
            or inner.get('processed', '')
            or inner.get('summary', '')
        )
        if isinstance(content, str) and len(content) > max_per_result:
            content = content[:max_per_result] + "... [truncated]"
        entry = f"Search {i} - Query: {query}\nFindings: {content}"
        total_chars += len(entry)
        if total_chars > max_total:
            summaries.append(
                f"... [{len(search_results) - i} more results truncated for context limit]"
            )
            break
        summaries.append(entry)

    return "\n\n".join(summaries)


class ResearchAnalyzer:
    """Synthesis and critical analysis for research results."""

    def __init__(self, call_llm: Callable[..., Awaitable[str]]):
        self._call_llm = call_llm
        self.logger = structured_logger

    async def intermediate_synthesis(self, context: ProcessingContext,
                                     report_plan: str,
                                     wave_results: List[Dict],
                                     previous_synthesis: Optional[str] = None) -> Dict[str, Any]:
        """Progressive synthesis — integrate new findings with prior understanding."""
        self.logger.progress("intermediate-synthesis", "start")

        wave_summary = summarize_search_results(wave_results)
        prompt = PromptTemplates.get_intermediate_synthesis_prompt(
            query=context.request.query,
            report_plan=report_plan,
            wave_results=wave_summary,
            previous_synthesis=previous_synthesis,
        )

        response = await self._call_llm(prompt, context)

        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            result = {
                "synthesis": response,
                "section_coverage": {},
                "knowledge_gaps": [],
                "cross_domain_links": [],
            }

        result.setdefault("synthesis", "")
        result.setdefault("section_coverage", {})
        result.setdefault("knowledge_gaps", [])
        result.setdefault("cross_domain_links", [])

        context.response.metadata.setdefault("synthesis_history", [])
        context.response.metadata["synthesis_history"].append(
            result.get("synthesis", "")[:500]
        )

        self.logger.progress("intermediate-synthesis", "end")
        return result

    async def critical_analysis_stage(self, context: ProcessingContext,
                                      search_results: List[Dict],
                                      report_plan: str,
                                      synthesis: str = None) -> str:
        """Critical analysis stage — multi-perspective thinking."""
        self.logger.progress("critical-analysis", "start")
        self.logger.info(
            "Critical Analysis: Analyzing research findings from multiple perspectives",
            "deep_research", "critical_analysis",
            phase="critical-analysis"
        )

        research_summary = synthesis or summarize_search_results(search_results)

        critical_prompt = PromptTemplates.get_critical_thinking_prompt(
            question=context.request.query,
            context=f"Research Plan:\n{report_plan}\n\nResearch Findings:\n{research_summary}"
        )

        self.logger.reasoning("進行批判性分析和多角度思考...", streaming=True)
        critical_analysis = await self._call_llm(critical_prompt, context)

        self.logger.info(
            f"Critical Analysis Result: {critical_analysis[:300]}...",
            "deep_research", "critical_analysis_result",
            full_length=len(critical_analysis)
        )

        context.response.metadata["critical_analysis"] = critical_analysis
        self.logger.progress("critical-analysis", "end")
        return critical_analysis
