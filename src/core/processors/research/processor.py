"""
Deep Research Processor - Agent-level research orchestrator

Thin orchestrator that composes specialized sub-modules:
- ResearchPlanner: domain identification, query generation, completeness review
- SearchExecutor: multi-engine search execution with parallel/race strategies
- ResearchAnalyzer: progressive synthesis and critical analysis
- ComputationEngine: chart planning and sandbox execution
- ReportGenerator: final report generation and persistence
- StreamingManager: SSE event infrastructure

Public API (process, process_with_streaming) is unchanged.
All internal methods delegate to sub-modules for backward compatibility.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator

from ..base import BaseProcessor
from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger

from .config import SearchEngineConfig, SearchProviderType
from .events import ResearchEvent
from .planner import ResearchPlanner
from .search_executor import SearchExecutor
from .analyzer import ResearchAnalyzer, summarize_search_results
from .computation import ComputationEngine
from .reporter import ReportGenerator, prepare_report_context
from .streaming import StreamingManager


class DeepResearchProcessor(BaseProcessor):
    """
    深度研究處理器 - Agent Level with Enhanced Features

    Orchestrates research workflow by composing specialized sub-modules.
    All internal _methods delegate to sub-modules for backward compatibility.
    """

    def __init__(self,
                 llm_client=None,
                 services: Optional[Dict[str, Any]] = None,
                 search_config: Optional[SearchEngineConfig] = None,
                 event_callback: Optional[Callable[[ResearchEvent], None]] = None,
                 mcp_client=None):
        super().__init__(llm_client, services, mcp_client=mcp_client)
        self.search_config = search_config or SearchEngineConfig()

        # Sub-modules (composed, not inherited)
        self.streaming = StreamingManager(event_callback)
        self.planner = ResearchPlanner(self._call_llm)
        self.analyzer = ResearchAnalyzer(self._call_llm)
        self.search_exec = SearchExecutor(
            call_llm=self._call_llm,
            search_service=self.services.get("search"),
            search_config=self.search_config,
            emit_event=self.streaming.emit_event,
            log_dir=getattr(self.logger, 'log_dir', 'logs'),
        )
        self.computation = ComputationEngine(
            call_llm=self._call_llm,
            sandbox_service=self.services.get("sandbox"),
        )
        self.reporter = ReportGenerator(
            call_llm=self._call_llm,
            log_dir=getattr(self.logger, 'log_dir', 'logs'),
            model_name=getattr(
                self.llm_client, 'model',
                getattr(self.llm_client, 'model_name', 'unknown')
            ) if self.llm_client else 'unknown',
        )

        # Legacy attributes (for backward compat with tests)
        self.event_callback = event_callback
        self.event_queue = self.streaming.event_queue
        self._streaming_enabled = False

    # ================================================================
    # Public API (unchanged)
    # ================================================================

    async def process(self, context: ProcessingContext) -> str:
        """Execute the complete deep research workflow."""
        workflow_state = {
            "status": "running",
            "steps": ["plan", "search", "synthesize"],
            "current_step": None,
            "iterations": 0,
            "errors": []
        }
        context.response.metadata["workflow_state"] = workflow_state

        await self._log_tool_decision(
            "deep_research",
            "執行全面的深度研究以回答複雜問題",
            0.95
        )

        try:
            return await self._execute_with_retry(context, workflow_state)
        except Exception as e:
            workflow_state["status"] = "failed"
            workflow_state["errors"].append({
                "error": str(e),
                "step": workflow_state["current_step"],
                "timestamp": datetime.now().isoformat()
            })
            self.logger.error(
                f"Research workflow failed: {e}",
                "deep_research", "workflow_failed"
            )
            raise

    async def process_with_streaming(self, context: ProcessingContext) -> AsyncGenerator[str, None]:
        """SSE Streaming version of process."""
        self._streaming_enabled = True
        self.streaming._streaming_enabled = True

        async for event in self.streaming.process_with_streaming(self.process, context):
            yield event

        self._streaming_enabled = False

    # ================================================================
    # Orchestration (kept in processor)
    # ================================================================

    async def _execute_with_retry(self, context: ProcessingContext,
                                  workflow_state: dict) -> str:
        """Execute research workflow with retry mechanism."""
        from core.errors import ErrorClassifier

        MAX_RETRIES = 2
        retry_count = 0
        last_error = None

        while retry_count <= MAX_RETRIES:
            try:
                return await self._execute_research_workflow(context, workflow_state)
            except Exception as e:
                error_category = ErrorClassifier.classify(e)

                workflow_state["errors"].append({
                    "error": str(e),
                    "category": error_category,
                    "retry_count": retry_count,
                    "step": workflow_state["current_step"]
                })

                if error_category in ["NETWORK", "LLM"] and retry_count < MAX_RETRIES:
                    retry_count += 1
                    delay = 2 ** retry_count
                    self.logger.warning(
                        f"Retryable error ({error_category}), retrying "
                        f"{retry_count}/{MAX_RETRIES} after {delay}s",
                        "deep_research", "retry"
                    )
                    await asyncio.sleep(delay)
                    last_error = e
                else:
                    raise e

        if last_error:
            raise last_error

    async def _execute_research_workflow(self, context: ProcessingContext,
                                         workflow_state: dict) -> str:
        """Execute core research workflow with progressive synthesis."""

        # 1. Report plan
        workflow_state["current_step"] = "plan"
        report_plan = await self.planner.write_report_plan(context)

        # 1.5. Domain identification
        workflow_state["current_step"] = "domain_identification"
        research_domains = await self.planner.identify_research_domains(context, report_plan)

        # Research iteration loop with progressive synthesis
        MAX_ITERATIONS = 3
        all_search_results = []
        executed_queries: List[str] = []
        accumulated_synthesis = None
        iteration = 0

        while iteration < MAX_ITERATIONS:
            iteration += 1
            workflow_state["iterations"] = iteration
            self.logger.info(
                f"Research Iteration {iteration}/{MAX_ITERATIONS}",
                "deep_research", "iteration"
            )

            # 2. Generate search queries
            workflow_state["current_step"] = "search"
            if iteration == 1:
                search_tasks = await self.planner.generate_serp_queries(
                    context, report_plan,
                    domains=research_domains,
                    search_config=self.search_config,
                )
            else:
                search_tasks = await self.planner.generate_followup_queries(
                    context, report_plan, all_search_results,
                    executed_queries=executed_queries,
                    search_config=self.search_config,
                )

            if not search_tasks:
                break

            # 3. Execute search tasks
            search_results = await self.search_exec.execute_search_tasks(
                context, search_tasks
            )
            all_search_results.extend(search_results)
            executed_queries.extend(t.get('query', '') for t in search_tasks)

            # 4. Progressive intermediate synthesis
            workflow_state["current_step"] = "synthesis"
            synthesis_result = await self.analyzer.intermediate_synthesis(
                context, report_plan, search_results, accumulated_synthesis,
            )
            accumulated_synthesis = synthesis_result.get("synthesis", "")
            section_coverage = synthesis_result.get("section_coverage", {})

            # 5. Structured completeness review
            is_sufficient, gap_report = await self.planner.review_research_completeness(
                context, report_plan, all_search_results, iteration,
                section_coverage=section_coverage,
            )

            if is_sufficient:
                self.logger.info(
                    "Research is sufficient, proceeding to report",
                    "deep_research", "complete"
                )
                break

            if len(executed_queries) >= self.search_config.max_total_queries:
                self.logger.info(
                    f"Search budget exhausted "
                    f"({len(executed_queries)}/{self.search_config.max_total_queries})",
                    "deep_research", "budget_exhausted"
                )
                break

            self.logger.info(
                "Research needs more depth, continuing...",
                "deep_research", "continue"
            )

        # Save full research data to file
        self.search_exec.save_research_data(context, all_search_results)
        synthesis = accumulated_synthesis or summarize_search_results(all_search_results)

        # 6. Critical analysis
        workflow_state["current_step"] = "critical_analysis"
        critical_analysis = await self.analyzer.critical_analysis_stage(
            context, all_search_results, report_plan,
            synthesis=synthesis,
        )

        # 7. Chart planning + execution
        chart_specs = await self.computation.plan_report_charts(
            context, all_search_results, report_plan,
            synthesis=synthesis,
        )

        computational_result = None
        if chart_specs and self.services.get("sandbox"):
            workflow_state["current_step"] = "computational_analysis"
            computational_result = await self.computation.execute_chart_plan(
                context, chart_specs, all_search_results,
                synthesis=synthesis,
            )

        # 8. Final report
        workflow_state["current_step"] = "synthesize"
        final_report = await self.reporter.write_final_report(
            context, all_search_results, report_plan,
            critical_analysis, computational_result,
            synthesis=synthesis,
        )

        workflow_state["status"] = "completed"
        self.logger.info(
            "Research workflow completed successfully",
            "deep_research", "workflow_complete"
        )

        return final_report

    # ================================================================
    # Clarification (kept in processor — awaiting SSE interactive impl)
    # ================================================================

    async def _should_clarify(self, context: ProcessingContext) -> bool:
        """Determine if research direction needs clarification."""
        complexity_indicators = ['比較', '分析', '評估', '深度', '全面', '詳細', '對比']
        query_lower = context.request.query.lower()
        return any(indicator in query_lower for indicator in complexity_indicators)

    async def _ask_clarifying_questions(self, context: ProcessingContext):
        """Ask clarifying questions to better understand research needs."""
        self.logger.progress("clarification", "start")

        question_prompt = PromptTemplates.get_system_question_prompt(context.request.query)
        questions = await self._call_llm(question_prompt, context)

        self.logger.info(
            f"Clarifying Questions Generated:\n{questions}",
            "deep_research", "clarification"
        )

        context.response.metadata["clarifying_questions"] = questions
        self.logger.progress("clarification", "end")

    # ================================================================
    # Delegation wrappers (backward compatibility for tests)
    # ================================================================

    # -- Planner --
    async def _identify_research_domains(self, context, report_plan):
        return await self.planner.identify_research_domains(context, report_plan)

    async def _write_report_plan(self, context):
        return await self.planner.write_report_plan(context)

    async def _generate_serp_queries(self, context, plan, domains=None):
        return await self.planner.generate_serp_queries(
            context, plan, domains=domains, search_config=self.search_config
        )

    async def _generate_followup_queries(self, context, report_plan,
                                         existing_results, executed_queries=None):
        return await self.planner.generate_followup_queries(
            context, report_plan, existing_results,
            executed_queries=executed_queries,
            search_config=self.search_config,
        )

    async def _review_research_completeness(self, context, report_plan,
                                            search_results, iteration,
                                            section_coverage=None):
        return await self.planner.review_research_completeness(
            context, report_plan, search_results, iteration,
            section_coverage=section_coverage,
        )

    # -- Analyzer --
    async def _intermediate_synthesis(self, context, report_plan,
                                      wave_results, previous_synthesis=None):
        return await self.analyzer.intermediate_synthesis(
            context, report_plan, wave_results, previous_synthesis
        )

    async def _critical_analysis_stage(self, context, search_results,
                                       report_plan, synthesis=None):
        return await self.analyzer.critical_analysis_stage(
            context, search_results, report_plan, synthesis=synthesis
        )

    def _summarize_search_results(self, search_results,
                                  max_per_result=8000, max_total=200000):
        return summarize_search_results(search_results, max_per_result, max_total)

    # -- Search Executor --
    async def _execute_search_tasks(self, context, search_tasks):
        return await self.search_exec.execute_search_tasks(context, search_tasks)

    async def _execute_single_search_task(self, index, task, query, goal, priority):
        return await self.search_exec._execute_single_search_task(
            index, task, query, goal, priority
        )

    async def _perform_parallel_deep_search(self, query, goal):
        return await self.search_exec._perform_parallel_deep_search(query, goal)

    async def _perform_race_search(self, query, goal):
        return await self.search_exec._perform_race_search(query, goal)

    async def _try_search_provider_with_timeout(self, provider, query, goal):
        return await self.search_exec._try_search_provider_with_timeout(
            provider, query, goal
        )

    async def _perform_deep_search(self, query, goal):
        return await self.search_exec._perform_deep_search(query, goal)

    async def _perform_deep_search_enhanced(self, query, goal):
        return await self.search_exec._perform_deep_search_enhanced(query, goal)

    async def _try_search_provider(self, provider, query, goal):
        return await self.search_exec._try_search_provider(provider, query, goal)

    async def _exa_search(self, query, goal):
        return await self.search_exec._exa_search(query, goal)

    async def _model_based_search(self, query, goal):
        return await self.search_exec._model_based_search(query, goal)

    def _format_search_results(self, results, provider):
        return self.search_exec._format_search_results(results, provider)

    def _empty_search_result(self, query):
        return self.search_exec._empty_search_result(query)

    async def _enrich_with_full_content(self, search_result, top_n=None):
        return await self.search_exec.enrich_with_full_content(search_result, top_n)

    def _save_research_data(self, context, search_results):
        return self.search_exec.save_research_data(context, search_results)

    # -- Computation --
    async def _plan_report_charts(self, context, search_results,
                                  report_plan, synthesis=None):
        return await self.computation.plan_report_charts(
            context, search_results, report_plan, synthesis=synthesis
        )

    async def _execute_chart_plan(self, context, chart_specs,
                                  search_results, synthesis=None):
        return await self.computation.execute_chart_plan(
            context, chart_specs, search_results, synthesis=synthesis
        )

    async def _generate_analysis_code(self, context, search_results, report_plan):
        return await self.computation.generate_analysis_code(
            context, search_results, report_plan
        )

    async def _execute_analysis_code(self, code, retry=True):
        return await self.computation.execute_analysis_code(code, retry)

    async def _fix_analysis_code(self, original_code, error):
        return await self.computation.fix_analysis_code(original_code, error)

    def _extract_code_block(self, response):
        return self.computation.extract_code_block(response)

    async def _requires_computational_analysis(self, context, search_results):
        return await self.computation.requires_computational_analysis(
            context, search_results
        )

    async def _computational_analysis_stage(self, context, search_results, report_plan):
        return await self.computation.computational_analysis_stage(
            context, search_results, report_plan
        )

    # -- Reporter --
    async def _write_final_report(self, context, search_results, report_plan,
                                  critical_analysis=None,
                                  computational_result=None,
                                  synthesis=None):
        return await self.reporter.write_final_report(
            context, search_results, report_plan,
            critical_analysis, computational_result,
            synthesis=synthesis,
        )

    def _prepare_report_context(self, search_results,
                                max_per_result=6000, max_total=200000):
        return prepare_report_context(search_results, max_per_result, max_total)

    def _extract_report_sections(self, report):
        return self.reporter.extract_report_sections(report)

    def _extract_references(self, search_results):
        return self.reporter.extract_references(search_results)

    def _build_academic_report_prompt(self, plan, context, references,
                                     requirement, critical_analysis=None,
                                     computational_result=None):
        return self.reporter.build_academic_report_prompt(
            plan, context, references, requirement,
            critical_analysis, computational_result
        )

    def _analyze_citations(self, report_body, references):
        return self.reporter.analyze_citations(report_body, references)

    def _format_report_with_categorized_references(self, report_body,
                                                   cited_refs, uncited_refs,
                                                   context=None,
                                                   has_critical_analysis=False,
                                                   citation_stats=None,
                                                   computational_result=None):
        return self.reporter.format_report_with_categorized_references(
            report_body, cited_refs, uncited_refs, context,
            has_critical_analysis, citation_stats, computational_result
        )

    def _save_report_bundle(self, full_report, context,
                            computational_result=None, cited_refs=None):
        return self.reporter.save_report_bundle(
            full_report, context, computational_result, cited_refs
        )

    # -- Streaming --
    async def _emit_event(self, event):
        return await self.streaming.emit_event(event)

    async def _event_stream_handler(self):
        return await self.streaming._event_stream_handler()

    async def _call_event_callback(self, event):
        return await self.streaming._call_event_callback(event)

    def configure_search_engines(self, config: SearchEngineConfig):
        """Dynamically configure search engines."""
        self.search_config = config
        self.search_exec.search_config = config
        self.logger.info(
            f"Search engines configured: primary={config.primary.value}, "
            f"fallback={[p.value for p in config.fallback_chain]}",
            "deep_research", "config_update"
        )

    def enable_streaming(self, enabled: bool = True):
        self._streaming_enabled = enabled
        self.streaming.enable_streaming(enabled)

    def set_event_callback(self, callback: Callable[[ResearchEvent], None]):
        self.event_callback = callback
        self.streaming.set_event_callback(callback)
