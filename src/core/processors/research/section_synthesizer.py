"""
Section-Aware Hierarchical Synthesis + Evidence Citation Index

Provides section-level retrieval and synthesis for deep research reports.
Inserted between the search loop and final report generation:

  search loop → [section_synthesizer] → final report

Components:
- parse_sections: Extract section structure from report plan (regex, no LLM)
- classify_results_to_sections: Map search results to sections (1 LLM call)
- synthesize_section: Per-section detailed synthesis (N parallel LLM calls)
- build_hierarchical_context: Orchestrator entry point
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Callable, Awaitable, Optional

from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger


class SectionSynthesizer:
    """Section-aware retrieval and hierarchical synthesis."""

    def __init__(self, call_llm: Callable[..., Awaitable[str]]):
        self._call_llm = call_llm
        self.logger = structured_logger

    # ------------------------------------------------------------------
    # 1. Parse sections from report plan (no LLM)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_sections(report_plan: str) -> List[Dict[str, str]]:
        """Extract section structure from report plan markdown.

        Splits on ## headings. Returns [{id, title, description}].
        """
        sections = []
        parts = re.split(r'^##\s+', report_plan, flags=re.MULTILINE)
        for i, part in enumerate(parts[1:], 1):  # skip preamble
            lines = part.strip().split('\n', 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            sections.append({
                "id": str(i),
                "title": title,
                "description": description[:300],
            })
        # Fallback: if no ## headings found, treat entire plan as one section
        if not sections:
            sections.append({
                "id": "1",
                "title": "Research Findings",
                "description": report_plan[:300],
            })
        return sections

    # ------------------------------------------------------------------
    # 2. Classify search results into sections (1 LLM call)
    # ------------------------------------------------------------------

    async def classify_results_to_sections(
        self,
        context: ProcessingContext,
        sections: List[Dict[str, str]],
        search_results: List[Dict],
    ) -> Dict[str, List[int]]:
        """Classify search results into report sections via single LLM call.

        Returns mapping: {section_title: [result_indices]}.
        Results can appear in multiple sections.
        """
        self.logger.progress("section-classify", "start")

        # Build compact summaries (index + query + goal + snippet)
        result_summaries = []
        for i, r in enumerate(search_results):
            inner = r.get('result', {}) if isinstance(r.get('result'), dict) else {}
            summary = inner.get('summary', '')[:200]
            result_summaries.append({
                "index": i,
                "query": r.get('query', ''),
                "goal": r.get('goal', ''),
                "snippet": summary,
            })

        prompt = PromptTemplates.get_section_classification_prompt(
            sections, result_summaries,
        )
        response = await self._call_llm(prompt, context)

        # Parse JSON response
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            raw = json.loads(json_match.group(1)) if json_match else json.loads(response)
            mapping = raw.get("mapping", raw)
        except (json.JSONDecodeError, TypeError, AttributeError):
            # Fallback: assign all results to all sections
            all_indices = list(range(len(search_results)))
            mapping = {s["title"]: all_indices for s in sections}

        # Ensure every section has an entry
        for s in sections:
            mapping.setdefault(s["title"], [])

        self.logger.progress("section-classify", "end")
        return mapping

    # ------------------------------------------------------------------
    # 3. Per-section synthesis (1 LLM call each, run in parallel)
    # ------------------------------------------------------------------

    async def synthesize_section(
        self,
        context: ProcessingContext,
        section: Dict[str, str],
        section_results: List[Dict],
        report_plan: str,
        references: List[Dict],
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Produce detailed synthesis for one report section.

        Returns {synthesis, evidence_index, key_data_points}.
        """
        if not section_results:
            return {
                "synthesis": "",
                "evidence_index": [],
                "key_data_points": [],
            }

        # Build results context with full detail
        max_per_result = 8000
        max_total = 30000
        context_parts = []
        total = 0
        for i, r in enumerate(section_results, 1):
            inner = r.get('result', {}) if isinstance(r.get('result'), dict) else {}
            content = (
                inner.get('full_content')
                or inner.get('processed')
                or inner.get('summary', '')
            )
            if isinstance(content, str) and len(content) > max_per_result:
                content = content[:max_per_result] + "... [truncated]"

            sources = inner.get('sources', [])
            source_refs = []
            for s in sources[:5]:
                # Find matching reference ID
                ref_id = None
                for ref in references:
                    if ref.get('url') == s.get('url'):
                        ref_id = ref['id']
                        break
                if ref_id:
                    source_refs.append(f"[{ref_id}] {s.get('title', '')}")

            entry = (
                f"--- Result {i} ---\n"
                f"Query: {r.get('query', '')}\n"
                f"Goal: {r.get('goal', '')}\n"
                f"Sources: {', '.join(source_refs) if source_refs else 'N/A'}\n"
                f"Content:\n{content}\n"
            )
            total += len(entry)
            if total > max_total:
                context_parts.append(f"... [{len(section_results) - i} more results truncated]")
                break
            context_parts.append(entry)

        results_context = "\n\n".join(context_parts)

        # Build section-relevant references
        section_refs = []
        for r in section_results:
            inner = r.get('result', {}) if isinstance(r.get('result'), dict) else {}
            for s in inner.get('sources', []):
                for ref in references:
                    if ref.get('url') == s.get('url') and ref not in section_refs:
                        section_refs.append(ref)

        prompt = PromptTemplates.get_section_synthesis_prompt(
            section=section,
            results_context=results_context,
            references=section_refs,
            language=language,
        )
        response = await self._call_llm(prompt, context)

        # Parse JSON
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            result = json.loads(json_match.group(1)) if json_match else json.loads(response)
        except (json.JSONDecodeError, TypeError):
            result = {
                "synthesis": response,
                "evidence_index": [],
                "key_data_points": [],
            }

        result.setdefault("synthesis", "")
        result.setdefault("evidence_index", [])
        result.setdefault("key_data_points", [])

        return result

    # ------------------------------------------------------------------
    # 4. Orchestrator: build hierarchical context
    # ------------------------------------------------------------------

    async def build_hierarchical_context(
        self,
        context: ProcessingContext,
        report_plan: str,
        search_results: List[Dict],
        references_list: List[Dict],
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Main entry point for section-aware hierarchical synthesis.

        Returns {structured_context, evidence_index, section_syntheses}.
        """
        self.logger.progress("hierarchical-synthesis", "start")

        # Step 1: Parse sections
        sections = self.parse_sections(report_plan)
        self.logger.info(
            f"Parsed {len(sections)} sections from report plan",
            "deep_research", "section_parse",
            sections=[s["title"] for s in sections],
        )

        # Step 2: Classify results to sections (1 LLM call)
        section_mapping = await self.classify_results_to_sections(
            context, sections, search_results,
        )

        # Step 3: Per-section synthesis (parallel LLM calls)
        async def _synth(section):
            indices = section_mapping.get(section["title"], [])
            section_results = [search_results[i] for i in indices if i < len(search_results)]
            return section["title"], await self.synthesize_section(
                context, section, section_results, report_plan,
                references_list, language,
            )

        results = await asyncio.gather(*[_synth(s) for s in sections])
        section_syntheses = dict(results)

        # Step 4: Assemble structured context
        all_evidence = []
        context_parts = []

        for section in sections:
            title = section["title"]
            data = section_syntheses.get(title, {})
            synthesis = data.get("synthesis", "")
            evidence = data.get("evidence_index", [])
            key_points = data.get("key_data_points", [])
            all_evidence.extend(evidence)

            part = f"## {title}\n\n"

            if synthesis:
                part += f"### Detailed Findings\n{synthesis}\n\n"

            if evidence:
                part += "### Evidence Index\n"
                for e in evidence:
                    sources = ", ".join(f"[{sid}]" for sid in e.get("source_ids", []))
                    conf = e.get("confidence", "medium").capitalize()
                    part += f"- \"{e.get('claim', '')}\" -> {sources} ({conf})\n"
                part += "\n"

            if key_points:
                part += "### Key Data Points\n"
                for kp in key_points:
                    part += f"- {kp}\n"
                part += "\n"

            context_parts.append(part)

        structured_context = "\n---\n\n".join(context_parts)

        self.logger.info(
            f"Hierarchical synthesis complete: {len(sections)} sections, "
            f"{len(all_evidence)} evidence claims, "
            f"{len(structured_context)} chars",
            "deep_research", "hierarchical_complete",
        )
        self.logger.progress("hierarchical-synthesis", "end")

        return {
            "structured_context": structured_context,
            "evidence_index": all_evidence,
            "section_syntheses": section_syntheses,
        }
