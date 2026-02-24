"""
Research Planner - Research planning, query generation, and completeness review

Contains domain identification, report planning, SERP query generation,
follow-up query generation, and research completeness review.
Extracted from DeepResearchProcessor (~250 lines).
"""

import json
import re
from typing import Dict, List, Optional, Any, Callable, Awaitable

from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger
from .config import SearchEngineConfig


class ResearchPlanner:
    """Research planning and query generation."""

    def __init__(self, call_llm: Callable[..., Awaitable[str]]):
        self._call_llm = call_llm
        self.logger = structured_logger

    async def identify_research_domains(self, context: ProcessingContext,
                                        report_plan: str) -> List[Dict[str, Any]]:
        """Identify research domains and search angles for multi-domain coverage."""
        self.logger.progress("domain-identification", "start")

        prompt = PromptTemplates.get_domain_identification_prompt(
            query=context.request.query,
            report_plan=report_plan,
        )

        response = await self._call_llm(prompt, context)

        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(response)
            domains = result.get("domains", [])
        except (json.JSONDecodeError, KeyError, TypeError):
            domains = []

        self.logger.info(
            f"Identified {len(domains)} research domains",
            "deep_research", "domains",
            domains=[d.get("name") for d in domains]
        )

        context.response.metadata["research_domains"] = [d.get("name") for d in domains]
        self.logger.progress("domain-identification", "end")

        return domains

    async def write_report_plan(self, context: ProcessingContext) -> str:
        """Phase 1: Generate research report plan."""
        self.logger.progress("report-plan", "start")

        self.logger.info(
            f"Planning: Creating research plan for '{context.request.query[:50]}...'",
            "deep_research", "planning",
            phase="report-plan",
            query_length=len(context.request.query)
        )

        plan_prompt = PromptTemplates.get_report_plan_prompt(context.request.query)

        self.logger.reasoning("開始分析研究需求...", streaming=True)
        plan = await self._call_llm(plan_prompt, context)

        self.logger.info(
            f"Research plan created: {plan[:300]}...",
            "deep_research", "plan_result",
            plan_length=len(plan)
        )

        self.logger.progress("report-plan", "end", {"plan": plan[:200]})
        return plan

    async def generate_serp_queries(self, context: ProcessingContext, plan: str,
                                    domains: Optional[List[Dict]] = None,
                                    search_config: SearchEngineConfig = None) -> List[Dict]:
        """Phase 2: Generate SERP queries — domain-aware when domains are provided."""
        self.logger.progress("serp-query", "start")

        self.logger.info(
            "SERP Generation: Extracting search queries from plan",
            "deep_research", "serp",
            phase="serp-query"
        )

        config = search_config or SearchEngineConfig()
        budget = config.queries_first_iteration

        output_schema = {
            "type": "array",
            "maxItems": budget,
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "researchGoal": {"type": "string"},
                    "priority": {"type": "number"}
                }
            }
        }

        # Build domain-aware plan supplement
        domain_supplement = ""
        if domains:
            domain_lines = []
            for d in domains:
                angles = ", ".join(d.get("search_angles", []))
                domain_lines.append(f"- {d['name']} (weight {d.get('weight', 0):.1f}): {angles}")
            domain_supplement = (
                "\n\nResearch Domains (ensure queries cover ALL domains proportionally):\n"
                + "\n".join(domain_lines)
            )

        serp_prompt = PromptTemplates.get_serp_queries_prompt(
            plan + domain_supplement, output_schema, query_budget=budget
        )
        response = await self._call_llm(serp_prompt, context)

        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                queries = json.loads(json_match.group(1))
            else:
                queries = json.loads(response)
        except Exception:
            queries = [{"query": context.request.query, "researchGoal": "General research", "priority": 1}]

        # Safety net: if LLM ignores budget, keep top N by priority
        if len(queries) > budget:
            queries = sorted(queries, key=lambda q: q.get("priority", 0), reverse=True)[:budget]

        self.logger.info(
            f"SERP Queries: Generated {len(queries)} search queries",
            "deep_research", "serp",
            queries_count=len(queries),
            queries=queries[:3]
        )

        self.logger.progress("serp-query", "end", {"queries": queries})
        return queries

    async def generate_followup_queries(self, context: ProcessingContext,
                                        report_plan: str,
                                        existing_results: List[Dict],
                                        executed_queries: List[str] = None,
                                        search_config: SearchEngineConfig = None,
                                        prepare_context_fn=None) -> List[Dict]:
        """Generate follow-up queries to fill research gaps — budget-aware.

        Args:
            prepare_context_fn: callable(search_results) -> str for formatting learnings.
                Falls back to simple summary if not provided.
        """
        config = search_config or SearchEngineConfig()
        used = len(executed_queries) if executed_queries else 0
        remaining = max(0, config.max_total_queries - used)
        budget = min(config.queries_followup_iteration, remaining)

        if budget <= 0:
            self.logger.info("Search budget exhausted, skipping follow-up", "deep_research", "budget")
            return []

        self.logger.progress("followup-query", "start")

        # Prepare learnings from existing results
        if prepare_context_fn:
            learnings = prepare_context_fn(existing_results)
        else:
            from .reporter import prepare_report_context
            learnings = prepare_report_context(existing_results)

        output_schema = {
            "type": "array",
            "maxItems": budget,
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "researchGoal": {"type": "string"},
                    "priority": {"type": "number"}
                }
            }
        }

        # Dedup notice
        dedup_suggestion = "Focus on filling knowledge gaps and getting more specific details"
        if executed_queries:
            queries_list = "\n".join(f"- {q}" for q in executed_queries)
            dedup_suggestion += (
                f"\n\nIMPORTANT: The following queries have already been executed. "
                f"Do NOT generate similar or duplicate queries:\n{queries_list}"
            )

        review_prompt = PromptTemplates.get_review_prompt(
            plan=report_plan,
            learnings=learnings,
            suggestion=dedup_suggestion,
            output_schema=output_schema,
            remaining_budget=budget,
        )

        response = await self._call_llm(review_prompt, context)

        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                queries = json.loads(json_match.group(1))
            else:
                queries = json.loads(response)
        except Exception:
            queries = []

        # Safety net: enforce budget
        if len(queries) > budget:
            queries = sorted(queries, key=lambda q: q.get("priority", 0), reverse=True)[:budget]

        self.logger.info(
            f"Follow-up Queries: {len(queries)} queries (budget: {budget}, total used: {used})",
            "deep_research", "followup"
        )

        self.logger.progress("followup-query", "end")
        return queries

    async def review_research_completeness(self, context: ProcessingContext,
                                           report_plan: str,
                                           search_results: List[Dict],
                                           iteration: int,
                                           section_coverage: Optional[Dict] = None) -> tuple:
        """Evaluate research completeness — returns (is_sufficient, gap_report)."""
        self.logger.progress("review", "start")

        review_prompt = PromptTemplates.get_completeness_review_prompt(
            report_plan=report_plan,
            section_coverage=section_coverage or {},
            iteration=iteration,
            max_iterations=3,
        )

        response = await self._call_llm(review_prompt, context)

        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(response)

            is_sufficient = bool(result.get("is_sufficient", False))
            gap_report = {
                "overall_coverage": result.get("overall_coverage", 0),
                "sections": result.get("sections", []),
                "priority_gaps": result.get("priority_gaps", []),
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            is_sufficient = "YES" in response.upper()[:10]
            gap_report = {"overall_coverage": 0, "sections": [], "priority_gaps": []}

        self.logger.info(
            f"Research Completeness: {'Sufficient' if is_sufficient else 'Needs more'}",
            "deep_research", "review",
            iteration=iteration, is_sufficient=is_sufficient
        )

        self.logger.progress("review", "end", {"is_sufficient": is_sufficient})
        return is_sufficient, gap_report
