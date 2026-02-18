"""
Deep Research Processor - Agent-level research with multi-provider search

Comprehensive research processor with:
- Multi-iteration workflow with retry mechanism
- Multi-provider search engine support (Tavily, Exa, etc.)
- SSE streaming for real-time updates
- Academic-style reference formatting with citation tracking
- Critical analysis integration
- Event-driven architecture

Extracted from monolithic processor.py (1487 lines)
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from collections import Counter

from ..base import BaseProcessor
from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger
from .config import SearchEngineConfig, SearchProviderType
from .events import ResearchEvent


class DeepResearchProcessor(BaseProcessor):
    """
    深度研究處理器 - Agent Level with Enhanced Features

    Features:
    - WorkflowState tracking and retry mechanism
    - SSE Streaming support
    - Multi-search engine configuration
    - Event-driven architecture
    - Closed-loop iteration (max 3 iterations)
    - Academic-style reference formatting
    """

    def __init__(self,
                 llm_client=None,
                 services: Optional[Dict[str, Any]] = None,
                 search_config: Optional[SearchEngineConfig] = None,
                 event_callback: Optional[Callable[[ResearchEvent], None]] = None,
                 mcp_client=None):
        """
        初始化增強版處理器

        Args:
            llm_client: LLM客戶端
            services: 服務字典
            search_config: 搜索引擎配置
            event_callback: 事件回調函數
            mcp_client: MCP 客戶端管理器
        """
        super().__init__(llm_client, services, mcp_client=mcp_client)
        self.search_config = search_config or SearchEngineConfig()
        self.event_callback = event_callback
        self.event_queue: asyncio.Queue = asyncio.Queue()

        self._streaming_enabled = False

    async def process(self, context: ProcessingContext) -> str:
        """執行完整的深度研究流程 - 符合 AgentRuntime 規範"""

        # Step 1: Init Workflow (符合狀態機 InitWorkflow)
        workflow_state = {
            "status": "running",
            "steps": ["plan", "search", "synthesize"],
            "current_step": None,
            "iterations": 0,
            "errors": []
        }
        context.response.metadata["workflow_state"] = workflow_state

        # 記錄深度研究決策
        await self._log_tool_decision(
            "deep_research",
            "執行全面的深度研究以回答複雜問題",
            0.95
        )

        try:
            # 執行研究流程 (包裹在 retry 邏輯中)
            return await self._execute_with_retry(context, workflow_state)
        except Exception as e:
            # WorkflowFailed: 記錄失敗狀態
            workflow_state["status"] = "failed"
            workflow_state["errors"].append({
                "error": str(e),
                "step": workflow_state["current_step"],
                "timestamp": datetime.now().isoformat()
            })
            self.logger.error(f"Research workflow failed: {e}", "deep_research", "workflow_failed")
            raise

    async def _execute_with_retry(self, context: ProcessingContext, workflow_state: dict) -> str:
        """執行研究流程，支援重試機制 (符合狀態機 RetryBoundary)"""
        from core.errors import ErrorClassifier

        MAX_RETRIES = 2
        retry_count = 0
        last_error = None

        while retry_count <= MAX_RETRIES:
            try:
                # 執行核心研究流程
                return await self._execute_research_workflow(context, workflow_state)

            except Exception as e:
                # Error Classification (符合狀態機 ErrorHandling)
                error_category = ErrorClassifier.classify(e)

                workflow_state["errors"].append({
                    "error": str(e),
                    "category": error_category,
                    "retry_count": retry_count,
                    "step": workflow_state["current_step"]
                })

                if error_category in ["NETWORK", "LLM"] and retry_count < MAX_RETRIES:
                    # Retryable error - 指數退避重試
                    retry_count += 1
                    delay = 2 ** retry_count  # Exponential backoff
                    self.logger.warning(
                        f"Retryable error ({error_category}), retrying {retry_count}/{MAX_RETRIES} after {delay}s",
                        "deep_research", "retry"
                    )
                    await asyncio.sleep(delay)
                    last_error = e
                else:
                    # Non-retryable or max retries exceeded
                    raise e

        # 如果所有重試都失敗
        if last_error:
            raise last_error

    async def _execute_research_workflow(self, context: ProcessingContext, workflow_state: dict) -> str:
        """Execute core research workflow with progressive synthesis."""

        # NOTE: clarification is disabled — awaiting SSE interactive implementation.
        # When ready, re-enable _should_clarify / _ask_clarifying_questions here.

        # 1. Report plan (WriteReportPlan)
        workflow_state["current_step"] = "plan"
        report_plan = await self._write_report_plan(context)

        # 1.5. Domain identification (drives multi-domain query distribution)
        workflow_state["current_step"] = "domain_identification"
        research_domains = await self._identify_research_domains(context, report_plan)

        # Research iteration loop with progressive synthesis
        MAX_ITERATIONS = 3
        all_search_results = []
        executed_queries: List[str] = []
        accumulated_synthesis = None
        iteration = 0

        while iteration < MAX_ITERATIONS:
            iteration += 1
            workflow_state["iterations"] = iteration
            self.logger.info(f"Research Iteration {iteration}/{MAX_ITERATIONS}", "deep_research", "iteration")

            # 2. Generate search queries
            workflow_state["current_step"] = "search"
            if iteration == 1:
                search_tasks = await self._generate_serp_queries(
                    context, report_plan, domains=research_domains
                )
            else:
                search_tasks = await self._generate_followup_queries(
                    context, report_plan, all_search_results,
                    executed_queries=executed_queries,
                )

            if not search_tasks:
                break

            # 3. Execute search tasks
            search_results = await self._execute_search_tasks(context, search_tasks)
            all_search_results.extend(search_results)
            executed_queries.extend(t.get('query', '') for t in search_tasks)

            # 4. Progressive intermediate synthesis
            workflow_state["current_step"] = "synthesis"
            synthesis_result = await self._intermediate_synthesis(
                context, report_plan, search_results, accumulated_synthesis,
            )
            accumulated_synthesis = synthesis_result.get("synthesis", "")
            section_coverage = synthesis_result.get("section_coverage", {})

            # 5. Structured completeness review
            is_sufficient, gap_report = await self._review_research_completeness(
                context, report_plan, all_search_results, iteration,
                section_coverage=section_coverage,
            )

            if is_sufficient:
                self.logger.info("Research is sufficient, proceeding to report", "deep_research", "complete")
                break

            # Budget exhaustion check
            if len(executed_queries) >= self.search_config.max_total_queries:
                self.logger.info(
                    f"Search budget exhausted ({len(executed_queries)}/{self.search_config.max_total_queries})",
                    "deep_research", "budget_exhausted"
                )
                break

            self.logger.info("Research needs more depth, continuing...", "deep_research", "continue")

        # Reversible compression: save full research data to file,
        # use accumulated_synthesis (LLM-condensed) for downstream prompts
        research_data_path = self._save_research_data(context, all_search_results)
        synthesis = accumulated_synthesis or self._summarize_search_results(all_search_results)

        # 6. Critical analysis (always-on for deep research)
        workflow_state["current_step"] = "critical_analysis"
        critical_analysis = await self._critical_analysis_stage(
            context, all_search_results, report_plan,
            synthesis=synthesis,
        )

        # 7. Chart planning (always-on) + execution (requires sandbox)
        chart_specs = await self._plan_report_charts(
            context, all_search_results, report_plan,
            synthesis=synthesis,
        )

        computational_result = None
        if chart_specs and self.services.get("sandbox"):
            workflow_state["current_step"] = "computational_analysis"
            computational_result = await self._execute_chart_plan(
                context, chart_specs, all_search_results,
                synthesis=synthesis,
            )

        # 8. Final report generation
        workflow_state["current_step"] = "synthesize"
        final_report = await self._write_final_report(
            context, all_search_results, report_plan,
            critical_analysis, computational_result,
            synthesis=synthesis,
        )

        # WorkflowComplete: 標記成功完成
        workflow_state["status"] = "completed"
        self.logger.info("✅ Research workflow completed successfully", "deep_research", "workflow_complete")

        return final_report

    async def _should_clarify(self, context: ProcessingContext) -> bool:
        """判斷是否需要澄清研究方向"""
        # 基於查詢複雜度判斷
        complexity_indicators = ['比較', '分析', '評估', '深度', '全面', '詳細', '對比']
        query_lower = context.request.query.lower()
        return any(indicator in query_lower for indicator in complexity_indicators)

    async def _ask_clarifying_questions(self, context: ProcessingContext):
        """詢問澄清問題以更好理解研究需求"""
        self.logger.progress("clarification", "start")

        question_prompt = PromptTemplates.get_system_question_prompt(context.request.query)
        questions = await self._call_llm(question_prompt, context)

        self.logger.info(
            f"❓ Clarifying Questions Generated:\n{questions}",
            "deep_research",
            "clarification"
        )

        # 這裡可以實際發送給用戶並獲取回應
        # 目前先記錄供參考
        context.response.metadata["clarifying_questions"] = questions

        self.logger.progress("clarification", "end")

    async def _identify_research_domains(self, context: ProcessingContext,
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
            # Fallback: empty domains — SERP generation proceeds without domain guidance
            domains = []

        self.logger.info(
            f"Identified {len(domains)} research domains",
            "deep_research", "domains",
            domains=[d.get("name") for d in domains]
        )

        context.response.metadata["research_domains"] = [d.get("name") for d in domains]
        self.logger.progress("domain-identification", "end")

        return domains

    async def _intermediate_synthesis(self, context: ProcessingContext,
                                      report_plan: str,
                                      wave_results: List[Dict],
                                      previous_synthesis: Optional[str] = None) -> Dict[str, Any]:
        """Progressive synthesis — integrate new findings with prior understanding."""

        self.logger.progress("intermediate-synthesis", "start")

        wave_summary = self._summarize_search_results(wave_results)
        prompt = PromptTemplates.get_intermediate_synthesis_prompt(
            query=context.request.query,
            report_plan=report_plan,
            wave_results=wave_summary,
            previous_synthesis=previous_synthesis,
        )

        response = await self._call_llm(prompt, context)

        # Parse JSON
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat entire response as synthesis text
            result = {
                "synthesis": response,
                "section_coverage": {},
                "knowledge_gaps": [],
                "cross_domain_links": [],
            }

        # Ensure required keys exist
        result.setdefault("synthesis", "")
        result.setdefault("section_coverage", {})
        result.setdefault("knowledge_gaps", [])
        result.setdefault("cross_domain_links", [])

        context.response.metadata.setdefault("synthesis_history", [])
        context.response.metadata["synthesis_history"].append(result.get("synthesis", "")[:500])

        self.logger.progress("intermediate-synthesis", "end")
        return result

    async def _critical_analysis_stage(self, context: ProcessingContext,
                                     search_results: List[Dict],
                                     report_plan: str,
                                     synthesis: str = None) -> str:
        """批判性分析階段 - 借鑒 ThinkingProcessor 的能力"""

        self.logger.progress("critical-analysis", "start")
        self.logger.info(
            f"🧠 Critical Analysis: Analyzing research findings from multiple perspectives",
            "deep_research",
            "critical_analysis",
            phase="critical-analysis"
        )

        # Use accumulated synthesis (bounded) instead of raw search results
        research_summary = synthesis or self._summarize_search_results(search_results)

        # 借用 ThinkingProcessor 的批判性思維提示詞
        critical_prompt = PromptTemplates.get_critical_thinking_prompt(
            question=context.request.query,
            context=f"Research Plan:\n{report_plan}\n\nResearch Findings:\n{research_summary}"
        )

        # 執行批判性分析
        self.logger.reasoning("進行批判性分析和多角度思考...", streaming=True)
        critical_analysis = await self._call_llm(critical_prompt, context)

        # 記錄分析結果到日誌
        self.logger.info(
            f"💭 Critical Analysis Result: {critical_analysis[:300]}...",
            "deep_research",
            "critical_analysis_result",
            full_length=len(critical_analysis)
        )

        # 儲存到中間結果
        context.response.metadata["critical_analysis"] = critical_analysis

        self.logger.progress("critical-analysis", "end")
        return critical_analysis

    # ============================================================
    # Chart Planning Phase (always-on)
    # ============================================================

    async def _plan_report_charts(self, context: ProcessingContext,
                                   search_results: List[Dict],
                                   report_plan: str,
                                   synthesis: str = None) -> List[Dict]:
        """Plan specific charts for the report — always runs, no sandbox gate."""
        self.logger.info("Planning report charts...", "deep_research", "chart_plan")

        research_summary = synthesis or self._summarize_search_results(search_results)
        prompt = PromptTemplates.get_chart_planning_prompt(
            query=context.request.query,
            research_summary=research_summary,
            report_plan=report_plan,
        )

        try:
            response = await self._call_llm(prompt, context)
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(response)
            charts = result.get("charts", [])
            self.logger.info(
                f"Planned {len(charts)} charts",
                "deep_research", "chart_plan_done"
            )
            return charts[:5]
        except Exception as e:
            self.logger.warning(f"Chart planning failed: {e}", "deep_research", "chart_plan_fail")
            return []

    # ============================================================
    # Computational Analysis Phase
    # ============================================================

    async def _requires_computational_analysis(self, context: ProcessingContext,
                                                search_results: List[Dict]) -> bool:
        """Determine if computational analysis would add value — LLM decides dynamically."""

        # Hard gate: sandbox must be available
        sandbox_service = self.services.get("sandbox")
        if not sandbox_service:
            return False

        # LLM triage: ask whether the data warrants computation
        research_summary = self._summarize_search_results(search_results)
        triage_prompt = PromptTemplates.get_computational_triage_prompt(
            query=context.request.query,
            research_summary=research_summary
        )

        try:
            response = await self._call_llm(triage_prompt, context)
            return response.strip().upper().startswith("YES")
        except Exception:
            return False

    async def _computational_analysis_stage(self, context: ProcessingContext,
                                             search_results: List[Dict],
                                             report_plan: str) -> Optional[Dict[str, Any]]:
        """Computational analysis — generate Python code, execute in sandbox, return results."""

        self.logger.progress("computational-analysis", "start")
        self.logger.info(
            "Computational Analysis: Generating analysis code from research data",
            "deep_research", "computational_analysis"
        )

        # Step 1: Generate analysis code
        self.logger.reasoning("Generating computational analysis code...", streaming=True)
        code = await self._generate_analysis_code(context, search_results, report_plan)

        if not code:
            self.logger.info(
                "Computational analysis: no viable code generated, skipping",
                "deep_research", "compute_skip"
            )
            self.logger.progress("computational-analysis", "end")
            return None

        # Step 2: Execute the code
        self.logger.reasoning("Executing computational analysis in sandbox...", streaming=True)
        result = await self._execute_analysis_code(code)

        if not result:
            self.logger.info(
                "Computational analysis: execution failed, continuing without computation",
                "deep_research", "compute_failed"
            )
            self.logger.progress("computational-analysis", "end")
            return None

        # Store in context metadata
        figure_count = len(result.get("figures", []))
        context.response.metadata["computational_analysis"] = {
            "code": result["code"],
            "stdout": result["stdout"][:500],
            "figure_count": figure_count,
            "execution_time": result["execution_time"]
        }

        self.logger.info(
            f"Computational analysis complete: {figure_count} figures, "
            f"{len(result.get('stdout', ''))} chars output, "
            f"{result.get('execution_time', 0):.2f}s",
            "deep_research", "compute_complete"
        )
        self.logger.progress("computational-analysis", "end")
        return result

    async def _execute_chart_plan(self, context: ProcessingContext,
                                   chart_specs: List[Dict],
                                   search_results: List[Dict],
                                   synthesis: str = None) -> Optional[Dict[str, Any]]:
        """Execute chart plan: generate and run code for each chart individually."""
        self.logger.progress("computational-analysis", "start")

        research_summary = synthesis or self._summarize_search_results(search_results)
        all_figures = []
        all_stdout = []
        total_time = 0.0

        for i, spec in enumerate(chart_specs):
            self.logger.info(
                f"Generating chart {i+1}/{len(chart_specs)}: {spec.get('title', '?')}",
                "deep_research", "chart_gen"
            )
            try:
                prompt = PromptTemplates.get_single_chart_code_prompt(spec, research_summary)
                response = await self._call_llm(prompt, context)
                code = self._extract_code_block(response)
                if not code:
                    continue

                result = await self._execute_analysis_code(code)
                if result and result.get("figures"):
                    for fig in result["figures"]:
                        all_figures.append({"base64": fig, "spec": spec})
                    all_stdout.append(result.get("stdout", ""))
                    total_time += result.get("execution_time", 0)
            except Exception as e:
                self.logger.warning(
                    f"Chart {i+1} failed: {e}", "deep_research", "chart_fail"
                )
                continue

        if not all_figures:
            self.logger.info(
                "No charts generated successfully", "deep_research", "no_charts"
            )
            self.logger.progress("computational-analysis", "end")
            return None

        combined = {
            "figures": [f["base64"] for f in all_figures],
            "figure_specs": [f["spec"] for f in all_figures],
            "stdout": "\n".join(all_stdout),
            "code": f"# {len(all_figures)} charts generated individually",
            "execution_time": total_time,
        }

        context.response.metadata["computational_analysis"] = {
            "figure_count": len(all_figures),
            "execution_time": total_time,
            "chart_titles": [f["spec"].get("title", "") for f in all_figures],
        }

        self.logger.info(
            f"Chart plan complete: {len(all_figures)} figures in {total_time:.2f}s",
            "deep_research", "chart_plan_complete"
        )
        self.logger.progress("computational-analysis", "end")
        return combined

    async def _generate_analysis_code(self, context: ProcessingContext,
                                       search_results: List[Dict],
                                       report_plan: str) -> Optional[str]:
        """Ask LLM to generate Python code for computational analysis."""

        research_summary = self._summarize_search_results(search_results)
        prompt = PromptTemplates.get_computational_analysis_prompt(
            query=context.request.query,
            research_summary=research_summary,
            report_plan=report_plan
        )

        response = await self._call_llm(prompt, context)
        code = self._extract_code_block(response)
        if not code:
            self.logger.warning(
                "LLM did not produce a valid code block for analysis",
                "deep_research", "compute_no_code"
            )
        return code

    def _extract_code_block(self, response: str) -> Optional[str]:
        """Extract Python code from markdown fenced code block."""
        import re
        match = re.search(r'```(?:python)?\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback: if entire response looks like bare code
        stripped = response.strip()
        if stripped.startswith(('import ', 'from ', '# ', 'def ', 'class ')):
            return stripped
        return None

    async def _execute_analysis_code(self, code: str, retry: bool = True) -> Optional[Dict[str, Any]]:
        """Execute analysis code in sandbox. Retry once on failure with error feedback."""

        sandbox_service = self.services.get("sandbox")
        if not sandbox_service:
            return None

        try:
            result = await sandbox_service.execute("execute_python", {
                "code": code,
                "timeout": 30
            })

            if result.get("success"):
                return {
                    "stdout": result.get("stdout", ""),
                    "figures": result.get("figures", []),
                    "return_value": result.get("return_value"),
                    "code": code,
                    "execution_time": result.get("execution_time", 0)
                }

            error_msg = result.get("error", "Unknown error")
            self.logger.warning(
                f"Computational analysis code failed: {error_msg}",
                "deep_research", "compute_exec_fail"
            )

            if retry:
                fixed_code = await self._fix_analysis_code(code, error_msg)
                if fixed_code:
                    return await self._execute_analysis_code(fixed_code, retry=False)

            return None

        except Exception as e:
            self.logger.warning(
                f"Sandbox execution exception: {e}",
                "deep_research", "compute_exception"
            )
            return None

    async def _fix_analysis_code(self, original_code: str, error: str) -> Optional[str]:
        """Ask LLM to fix failed analysis code."""

        prompt = f"""The following Python code failed with an error. Fix it and return ONLY the corrected code in a ```python code block.

Original code:
```python
{original_code}
```

Error:
{error}

Rules:
- Fix the error while preserving the original intent
- Use only: numpy, scipy, sympy, pandas, matplotlib, seaborn, plotly, sklearn
- Store final results in a variable named `result`
- Use print() for key findings"""

        response = await self._call_llm(prompt, None)
        return self._extract_code_block(response)

    async def _enrich_with_full_content(self, search_result: Dict, top_n: int = None) -> Dict:
        """Fetch full page content for top search result URLs.

        Uses search_service.fetch_multiple() to grab full text from the
        highest-relevance URLs, then stores the combined content in
        search_result['full_content']. Fails silently — if anything goes
        wrong the original result is returned as-is.
        """
        if top_n is None:
            top_n = self.search_config.urls_per_query
        search_service = self.services.get("search")
        if not search_service or not hasattr(search_service, 'fetch_multiple'):
            return search_result

        sources = search_result.get('sources', [])
        if not sources:
            return search_result

        # Pick top N by relevance (already sorted in most code paths)
        top_sources = sorted(sources, key=lambda s: s.get('relevance', 0), reverse=True)[:top_n]
        urls = [s['url'] for s in top_sources if s.get('url')]

        if not urls:
            return search_result

        try:
            content_map = await search_service.fetch_multiple(urls)
            if content_map:
                full_texts = []
                for url in urls:
                    text = content_map.get(url)
                    if text:
                        full_texts.append(text)
                if full_texts:
                    search_result['full_content'] = "\n\n---\n\n".join(full_texts)
        except Exception as e:
            self.logger.warning(
                f"Full-content extraction failed: {e}",
                "deep_research", "fetch_content_error"
            )

        return search_result

    def _save_research_data(self, context: ProcessingContext,
                             search_results: List[Dict]) -> Optional[str]:
        """Reversible compression: save full search results to file.

        Full raw data is preserved on disk. Downstream stages use the
        LLM-condensed accumulated_synthesis instead, keeping prompts bounded.
        """
        try:
            from pathlib import Path

            trace_id = context.request.trace_id
            data_dir = Path(self.logger.log_dir) / "research_data"
            data_dir.mkdir(parents=True, exist_ok=True)

            filepath = data_dir / f"{trace_id[:8]}_search_results.json"

            # Extract serializable subset (skip raw HTML etc.)
            serializable = []
            for r in search_results:
                inner = r.get('result', {}) if isinstance(r.get('result'), dict) else {}
                serializable.append({
                    "query": r.get("query", ""),
                    "goal": r.get("goal", ""),
                    "priority": r.get("priority", 1),
                    "summary": inner.get("summary", ""),
                    "processed": inner.get("processed", ""),
                    "sources": inner.get("sources", []),
                })

            filepath.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.logger.info(
                f"Research data saved: {filepath} ({len(search_results)} results)",
                "deep_research", "data_saved",
            )
            return str(filepath)
        except Exception as e:
            self.logger.warning(f"Failed to save research data: {e}", "deep_research", "data_save_error")
            return None

    def _summarize_search_results(self, search_results: List[Dict],
                                   max_per_result: int = 8000,
                                   max_total: int = 200000) -> str:
        """Summarize search results — prefer full_content over snippets.

        Truncates per-result and total output to stay within LLM context limits.
        """

        summaries = []
        total_chars = 0
        for i, result in enumerate(search_results, 1):
            query = result.get('query', 'Unknown')
            # Prefer full_content (from fetch) → result.full_content → result.results
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
                summaries.append(f"... [{len(search_results) - i} more results truncated for context limit]")
                break
            summaries.append(entry)

        return "\n\n".join(summaries)

    async def _generate_followup_queries(self, context: ProcessingContext,
                                        report_plan: str,
                                        existing_results: List[Dict],
                                        executed_queries: List[str] = None) -> List[Dict]:
        """Generate follow-up queries to fill research gaps — budget-aware."""
        # Calculate remaining budget
        used = len(executed_queries) if executed_queries else 0
        remaining = max(0, self.search_config.max_total_queries - used)
        budget = min(self.search_config.queries_followup_iteration, remaining)

        if budget <= 0:
            self.logger.info("Search budget exhausted, skipping follow-up", "deep_research", "budget")
            return []

        self.logger.progress("followup-query", "start")

        learnings = self._prepare_report_context(existing_results)

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
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                queries = json.loads(json_match.group(1))
            else:
                queries = json.loads(response)
        except:
            queries = []

        # Safety net: enforce budget
        if len(queries) > budget:
            queries = sorted(queries, key=lambda q: q.get("priority", 0), reverse=True)[:budget]

        self.logger.info(
            f"📋 Follow-up Queries: {len(queries)} queries (budget: {budget}, total used: {used})",
            "deep_research",
            "followup"
        )

        self.logger.progress("followup-query", "end")
        return queries

    async def _review_research_completeness(self, context: ProcessingContext,
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

        # Parse structured JSON response
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
            # Fallback: simple YES/NO parsing for backward compatibility
            is_sufficient = "YES" in response.upper()[:10]
            gap_report = {"overall_coverage": 0, "sections": [], "priority_gaps": []}

        self.logger.info(
            f"Research Completeness: {'Sufficient' if is_sufficient else 'Needs more'}",
            "deep_research", "review",
            iteration=iteration, is_sufficient=is_sufficient
        )

        self.logger.progress("review", "end", {"is_sufficient": is_sufficient})

        return is_sufficient, gap_report

    async def _write_report_plan(self, context: ProcessingContext) -> str:
        """Phase 1: 生成研究報告計畫"""
        self.logger.progress("report-plan", "start")

        # 記錄計劃階段
        self.logger.info(
            f"📝 Planning: Creating research plan for '{context.request.query[:50]}...'",
            "deep_research",
            "planning",
            phase="report-plan",
            query_length=len(context.request.query)
        )

        # 使用報告計劃 prompt
        plan_prompt = PromptTemplates.get_report_plan_prompt(context.request.query)

        # 推理過程
        self.logger.reasoning("開始分析研究需求...", streaming=True)
        plan = await self._call_llm(plan_prompt, context)

        # 記錄計劃到日誌
        self.logger.info(
            f"📋 Research plan created: {plan[:300]}...",
            "deep_research",
            "plan_result",
            plan_length=len(plan)
        )

        self.logger.progress("report-plan", "end", {"plan": plan[:200]})

        return plan

    async def _generate_serp_queries(self, context: ProcessingContext, plan: str,
                                      domains: Optional[List[Dict]] = None) -> List[Dict]:
        """Phase 2: 生成 SERP 查詢 — domain-aware when domains are provided."""
        self.logger.progress("serp-query", "start")

        # 記錄查詢生成
        self.logger.info(
            f"🔍 SERP Generation: Extracting search queries from plan",
            "deep_research",
            "serp",
            phase="serp-query"
        )

        # Budget from config
        budget = self.search_config.queries_first_iteration

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

        # Budget-aware SERP prompt
        serp_prompt = PromptTemplates.get_serp_queries_prompt(
            plan + domain_supplement, output_schema, query_budget=budget
        )
        response = await self._call_llm(serp_prompt, context)

        # Parse queries
        try:
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                queries = json.loads(json_match.group(1))
            else:
                queries = json.loads(response)
        except:
            queries = [{"query": context.request.query, "researchGoal": "General research", "priority": 1}]

        # Safety net: if LLM ignores budget, keep top N by priority
        if len(queries) > budget:
            queries = sorted(queries, key=lambda q: q.get("priority", 0), reverse=True)[:budget]

        # 記錄生成的查詢
        self.logger.info(
            f"📋 SERP Queries: Generated {len(queries)} search queries",
            "deep_research",
            "serp",
            queries_count=len(queries),
            queries=queries[:3]  # 只記錄前3個
        )

        self.logger.progress("serp-query", "end", {"queries": queries})

        return queries

    async def _execute_search_tasks(self, context: ProcessingContext, search_tasks: List[Dict]) -> List[Dict]:
        """Phase 3: 執行搜索任務 - 支援批次平行搜索"""
        self.logger.progress("task-list", "start")

        # 記錄任務列表
        self.logger.info(
            f"📋 Task List: Executing {len(search_tasks)} search tasks (parallel batch size: {self.search_config.parallel_searches})",
            "deep_research",
            "tasks",
            phase="task-list",
            total_tasks=len(search_tasks),
            parallel_batch_size=self.search_config.parallel_searches
        )

        results = []

        # 將任務分批執行
        batch_size = self.search_config.parallel_searches

        for batch_start in range(0, len(search_tasks), batch_size):
            batch_end = min(batch_start + batch_size, len(search_tasks))
            batch_tasks = search_tasks[batch_start:batch_end]

            self.logger.info(
                f"🚀 Executing batch {batch_start//batch_size + 1}: Tasks {batch_start+1}-{batch_end}",
                "deep_research",
                "batch_execution",
                batch_index=batch_start//batch_size + 1,
                batch_size=len(batch_tasks)
            )

            # 準備批次搜索任務
            async_tasks = []
            for i, task in enumerate(batch_tasks, batch_start + 1):
                query = task.get('query', '')
                goal = task.get('researchGoal', '')
                priority = task.get('priority', 1)

                # 記錄搜索任務
                self.logger.info(
                    f"🔎 Search Task {i}/{len(search_tasks)}: {query}",
                    "deep_research",
                    "search_task",
                    task_index=i,
                    query=query,
                    goal=goal,
                    priority=priority,
                    provider=self.search_config.primary.value
                )

                # 添加到異步任務列表
                async_tasks.append(
                    self._execute_single_search_task(i, task, query, goal, priority)
                )

            # 平行執行批次搜索
            batch_results = await asyncio.gather(*async_tasks, return_exceptions=True)

            # 處理批次結果
            for task, result in zip(batch_tasks, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"❌ Search task failed: {str(result)}",
                        "deep_research",
                        "search_error",
                        error=str(result)
                    )
                    # 創建錯誤結果
                    result = {
                        'query': task.get('query', ''),
                        'goal': task.get('researchGoal', ''),
                        'priority': task.get('priority', 1),
                        'result': {
                            'error': str(result),
                            'sources': [],
                            'summary': f"Search failed: {str(result)}"
                        }
                    }

                results.append(result)

        self.logger.progress("task-list", "end")

        # 記錄總結
        total_sources = sum(len(r.get('result', {}).get('sources', [])) for r in results)
        self.logger.info(
            f"📊 Search Summary: {total_sources} total sources from {len(search_tasks)} tasks",
            "deep_research",
            "summary",
            phase="search-complete",
            total_sources=total_sources,
            total_tasks=len(search_tasks)
        )

        return results

    async def _execute_single_search_task(self, index: int, task: Dict, query: str, goal: str, priority: int) -> Dict:
        """執行單個搜索任務"""
        try:
            # 開始單個搜索任務
            self.logger.progress("search-task", "start", {"name": query})

            # 推理過程
            self.logger.reasoning(f"正在搜索：{query}...", streaming=True)

            # 執行搜索（支援多引擎平行搜索）
            search_result = await self._perform_parallel_deep_search(query, goal)

            # Enrich with full page content
            search_result = await self._enrich_with_full_content(search_result)

            # 記錄搜索結果
            self.logger.info(
                f"✅ Search Result {index}: Found {len(search_result.get('sources', []))} sources",
                "deep_research",
                "search_result",
                task_index=index,
                sources_count=len(search_result.get('sources', [])),
                relevance_score=search_result.get('relevance', 0)
            )

            # 消息輸出
            self.logger.message(f"搜索 {index}: {query}\n結果: {search_result.get('summary', '')[:200]}...")

            # 結束單個搜索任務
            self.logger.progress("search-task", "end", {
                "name": query,
                "data": search_result
            })

            return {
                'query': query,
                'goal': goal,
                'priority': priority,
                'result': search_result
            }
        except Exception as e:
            self.logger.error(
                f"Error in search task: {str(e)}",
                "deep_research",
                "task_error"
            )
            raise

    async def _perform_parallel_deep_search(self, query: str, goal: str) -> Dict:
        """執行平行深度搜索 - 同時使用多個搜索引擎"""

        # 如果啟用了 race 模式，同時啟動所有搜索引擎
        if hasattr(self.search_config, 'enable_race_mode') and self.search_config.enable_race_mode:
            return await self._perform_race_search(query, goal)

        # 否則使用增強版搜索（帶降級）
        return await self._perform_deep_search_enhanced(query, goal)

    async def _perform_race_search(self, query: str, goal: str) -> Dict:
        """競速模式：同時執行多個搜索引擎，返回第一個成功的結果"""

        # 準備所有搜索提供商
        providers = [self.search_config.primary] + (self.search_config.fallback_chain or [])

        self.logger.info(
            f"🏁 Race mode: Starting {len(providers)} search engines in parallel",
            "deep_research",
            "race_mode",
            providers=[p.value for p in providers]
        )

        # 創建所有搜索任務
        search_tasks = [
            self._try_search_provider_with_timeout(provider, query, goal)
            for provider in providers
        ]

        # 使用 asyncio.as_completed 獲取第一個成功的結果
        for future in asyncio.as_completed(search_tasks):
            try:
                result = await future
                if result and result.get('sources'):
                    provider_name = result.get('provider', 'unknown')
                    self.logger.info(
                        f"🏆 Race winner: {provider_name} returned first with {len(result.get('sources', []))} sources",
                        "deep_research",
                        "race_winner",
                        provider=provider_name
                    )
                    return result
            except Exception as e:
                # 忽略單個引擎的錯誤，繼續等待其他引擎
                continue

        # 如果所有引擎都失敗，返回空結果
        return {
            'summary': 'No search results available',
            'sources': [],
            'relevance': 0
        }

    async def _try_search_provider_with_timeout(self, provider: SearchProviderType, query: str, goal: str) -> Optional[Dict]:
        # 帶超時的搜索提供商嘗試
        try:
            # 使用配置的超時時間
            timeout = getattr(self.search_config, 'timeout', 30.0)

            result = await asyncio.wait_for(
                self._try_search_provider(provider, query, goal),
                timeout=timeout
            )

            if result:
                result['provider'] = provider.value

            return result

        except asyncio.TimeoutError:
            self.logger.warning(
                f"⏱️ Search timeout for {provider.value} after {timeout}s",
                "deep_research",
                "timeout"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Search error with {provider.value}: {str(e)}",
                "deep_research",
                "provider_error"
            )
            return None

    async def _perform_deep_search(self, query: str, goal: str) -> Dict:
        # 執行深度搜索 — 使用真實搜索服務，無則返回空結果

        search_service = self.services.get("search")

        # 記錄 Web Query
        self.logger.info(
            f"🌐 Web Query: {query}",
            "web",
            "query",
            query=query,
            goal=goal,
            search_engine="web" if search_service else "none",
            max_results=10
        )

        # Use real search service if available
        search_result = None
        if search_service:
            try:
                results = await search_service.search(query, max_results=10)
                if results:
                    sources = [
                        {'url': r.url, 'title': r.title, 'relevance': 0.9}
                        for r in results
                    ]
                    summary = "\n".join(
                        f"- {r.title}: {r.snippet}" for r in results[:5]
                    )
                    search_result = {
                        'summary': summary,
                        'sources': sources,
                        'relevance': 0.92,
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                self.logger.warning(f"Search service error in deep research: {e}", "web", "fallback")

        # Fallback: search unavailable — return empty result with disclaimer
        if not search_result:
            self.logger.warning(
                f"Web search unavailable for deep research query: {query}",
                "web", "no_results"
            )
            search_result = {
                'summary': f"[Web search unavailable] Unable to retrieve real-time results for '{query}'. "
                           f"The final report will be based on the AI model's training data only.",
                'sources': [],
                'relevance': 0.0,
                'timestamp': datetime.now().isoformat()
            }

        # 記錄搜索結果詳情
        self.logger.info(
            f"🔗 Web Results: Retrieved {len(search_result['sources'])} sources",
            "web",
            "results",
            sources=search_result['sources'][:5],
            avg_relevance=search_result['relevance']
        )

        # 如果有 LLM，處理搜索結果
        if self.llm_client:
            result_prompt = PromptTemplates.get_search_result_prompt(
                query=query,
                research_goal=goal,
                context=json.dumps(search_result, ensure_ascii=False)
            )
            processed = await self._call_llm(result_prompt, None)
            search_result['processed'] = processed

        return search_result

    async def _write_final_report(self, context: ProcessingContext,
                                  search_results: List[Dict],
                                  report_plan: str,
                                  critical_analysis: Optional[str] = None,
                                  computational_result: Optional[Dict[str, Any]] = None,
                                  synthesis: str = None) -> str:
        # Phase 4: 生成最終報告 - 學術論文格式（區分引用/未引用）
        self.logger.progress("final-report", "start")

        # 記錄最終報告生成
        self.logger.info(
            f"📑 Final Report: Synthesizing {len(search_results)} search results",
            "deep_research",
            "final_report",
            phase="final-report",
            results_count=len(search_results),
            plan_length=len(report_plan)
        )

        # Use accumulated synthesis (bounded, LLM-condensed) as primary context.
        # Raw search results saved to file earlier (reversible compression).
        research_context = synthesis or self._prepare_report_context(search_results)
        references_list = self._extract_references(search_results)

        # 記錄記憶體操作
        self.logger.info(
            f"💾 Memory: Research context for report",
            "memory",
            "store",
            context_size=len(research_context),
            chunks=len(search_results),
            type="research_report"
        )

        # 構建增強的 prompt，包含參考文獻指引和批判性分析
        enhanced_prompt = self._build_academic_report_prompt(
            report_plan,
            research_context,
            references_list,
            context.request.query,
            critical_analysis,
            computational_result
        )

        # 推理最終報告
        self.logger.reasoning("綜合所有研究結果，生成最終報告...", streaming=True)

        # 生成報告主體
        report_body = await self._call_llm(enhanced_prompt, context)

        # 分析哪些參考文獻被實際引用（增強版）
        cited_refs, uncited_refs, citation_stats = self._analyze_citations(report_body, references_list)

        # 組合完整報告：主體 + 區分的參考文獻
        final_report = self._format_report_with_categorized_references(
            report_body, cited_refs, uncited_refs, context,
            critical_analysis is not None, citation_stats, computational_result
        )

        # 記錄記憶體回收
        self.logger.info(
            f"💾 Memory: Retrieved research synthesis",
            "memory",
            "retrieve",
            report_length=len(final_report),
            citations_included=True
        )

        # 發送最終報告
        self.logger.message(final_report, streaming=False)

        # 報告元數據
        report_metadata = {
            "title": f"Research Report: {context.request.query[:50]}",
            "sections": self._extract_report_sections(final_report),
            "sources_used": sum(len(r['result'].get('sources', [])) for r in search_results),
            "word_count": len(final_report.split()),
            "timestamp": datetime.now().isoformat()
        }

        # 記錄報告完成
        self.logger.info(
            f"✅ Report Completed: {report_metadata['word_count']} words, {report_metadata['sources_used']} sources",
            "deep_research",
            "complete",
            metadata=report_metadata
        )

        self.logger.progress("final-report", "end", {"data": report_metadata})

        return final_report

    def _prepare_report_context(self, search_results: List[Dict],
                                max_per_result: int = 6000,
                                max_total: int = 200000) -> str:
        # 準備報告上下文（含截斷保護）
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

    def _extract_report_sections(self, report: str) -> List[str]:
        # 提取報告章節
        import re
        # 匹配 Markdown 標題
        headers = re.findall(r'^#{1,3}\s+(.+)$', report, re.MULTILINE)
        return headers[:10]  # 返回前10個章節標題

    def _extract_references(self, search_results: List[Dict]) -> List[Dict]:
        # 從搜索結果中提取參考文獻
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

        # 按相關性排序
        references.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return references

    def _build_academic_report_prompt(self, plan: str, context: str,
                                     references: List[Dict], requirement: str,
                                     critical_analysis: Optional[str] = None,
                                     computational_result: Optional[Dict[str, Any]] = None) -> str:
        # 構建學術格式的報告 prompt（含批判性分析）
        # 準備參考文獻摘要
        ref_summary = "\n".join([
            f"[{ref['id']}] {ref['title']}"
            for ref in references
        ])

        # 基礎 prompt
        prompt = f"""Generate a comprehensive research report based on the following information.

Research Plan:
{plan}

Research Context and Findings:
{context}

Available References:
{ref_summary}"""

        # 如果有批判性分析，添加到 prompt 中
        if critical_analysis:
            prompt += f"""

Critical Analysis (Multi-Perspective Thinking):
{critical_analysis}

IMPORTANT: Integrate the insights from the critical analysis throughout your report.
Use the multi-perspective thinking to enrich your conclusions and provide more nuanced views."""

        # 添加要求
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

=== QUANTIFICATION ===
10. Every market claim must include specific numbers: market size ($B), growth rate (CAGR%), adoption rate (%), company names with revenue/headcount
11. Use inline citations [1], [2], [3] for every factual claim — minimum 15 unique citations across the report
12. DO NOT include a references section in your output (it will be added separately)

=== OUTPUT STANDARDS ===
13. Aim for 3000+ words with deep analysis, not surface-level summarization
14. Structure with ## for main sections, ### for sub-sections
15. Write in professional analytical tone — BANNED vague phrases: "重要的是", "值得注意的是", "眾所周知" — replace with specific analytical claims
16. Include specific company names, product names, statistics, and real-world examples"""

        # 如果有批判性分析，添加特殊要求
        req_num = 17
        if critical_analysis:
            prompt += f"""
{req_num}. Incorporate critical analysis insights to provide balanced, multi-perspective conclusions
{req_num + 1}. Address potential limitations, counterarguments, or alternative interpretations
{req_num + 2}. Demonstrate analytical depth beyond surface-level findings"""
            req_num += 3

        # 如果有計算分析結果，添加到 prompt 中
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
- If charts were generated, reference them as "Figure 1", "Figure 2", etc. in the appropriate sections
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


    def _analyze_citations(self, report_body: str, references: List[Dict]) -> tuple:
        """
        分析報告中實際引用的參考文獻（增強版）

        Returns:
            tuple: (cited_refs, uncited_refs, citation_stats)
            - cited_refs: 被引用的文獻列表（包含 citation_count 字段）
            - uncited_refs: 未被引用的文獻列表
            - citation_stats: 詳細統計信息字典
        """
        import re
        from collections import Counter

        # 找出所有引用的編號及其出現次數
        citation_pattern = r'\[(\d+)\]'
        citation_counts = Counter()
        invalid_citations = set()  # 無效引用（沒有對應文獻）

        # 建立有效參考文獻 ID 集合
        valid_ref_ids = {ref['id'] for ref in references}

        # 掃描報告中的所有引用
        for match in re.finditer(citation_pattern, report_body):
            try:
                ref_num = int(match.group(1))
                citation_counts[ref_num] += 1

                # 檢測無效引用
                if ref_num not in valid_ref_ids:
                    invalid_citations.add(ref_num)
            except ValueError:
                continue

        # 分類參考文獻並添加引用次數信息
        cited_refs = []
        uncited_refs = []

        for ref in references:
            if ref['id'] in citation_counts:
                # 添加引用次數信息（不修改原始 ref）
                ref_with_count = ref.copy()
                ref_with_count['citation_count'] = citation_counts[ref['id']]
                cited_refs.append(ref_with_count)
            else:
                uncited_refs.append(ref)

        # 按引用次數排序（從高到低）
        cited_refs.sort(key=lambda x: x.get('citation_count', 0), reverse=True)

        # 構建詳細統計信息
        citation_stats = {
            'total_citations': sum(citation_counts.values()),  # 總引用次數
            'unique_citations': len(citation_counts),  # 唯一引用數
            'invalid_citations': list(invalid_citations),  # 無效引用列表
            'most_cited': citation_counts.most_common(5),  # 最常引用的前5個
            'avg_citations_per_source': sum(citation_counts.values()) / max(1, len(citation_counts)),  # 平均每個來源的引用次數
            'citation_distribution': dict(citation_counts)  # 完整的引用分佈
        }

        return cited_refs, uncited_refs, citation_stats

    def _format_report_with_categorized_references(self, report_body: str,
                                                   cited_refs: List[Dict],
                                                   uncited_refs: List[Dict],
                                                   context: ProcessingContext = None,
                                                   has_critical_analysis: bool = False,
                                                   citation_stats: Dict = None,
                                                   computational_result: Optional[Dict[str, Any]] = None) -> str:
        """
        格式化報告，區分引用和未引用的參考文獻（增強版）

        Args:
            citation_stats: 詳細的引用統計信息（可選）
        """
        # 構建參考文獻部分
        references_section = "\n\n---\n\n"

        # 第一部分：引用的參考文獻（按引用次數排序）
        if cited_refs:
            references_section += "## 📚 參考文獻 (Cited References)\n\n"
            references_section += "*以下為報告中實際引用的文獻（按引用次數排序）：*\n\n"

            for ref in cited_refs[:30]:  # 限制最多30個
                citation_count = ref.get('citation_count', 0)
                citation_indicator = f" `×{citation_count}`" if citation_count > 1 else ""

                ref_entry = f"[{ref['id']}] **{ref['title']}**{citation_indicator}\n"
                if ref.get('url'):
                    ref_entry += f"   📍 URL: {ref['url']}\n"
                if ref.get('query'):
                    ref_entry += f"   🔍 Search context: {ref['query'][:50]}...\n"
                references_section += f"{ref_entry}\n"

        # 第二部分：相關但未引用的參考文獻
        if uncited_refs:
            references_section += "\n## 📖 相關文獻 (Related Sources - Not Cited)\n\n"
            references_section += "*以下為研究過程中查閱但未直接引用的相關資料：*\n\n"

            for ref in uncited_refs[:20]:  # 限制最多20個
                ref_entry = f"• {ref['title']}\n"
                if ref.get('url'):
                    ref_entry += f"  URL: {ref['url']}\n"
                references_section += f"{ref_entry}\n"

        # 添加統計資訊（增強版）
        references_section += f"\n---\n\n## 📊 引用統計 (Citation Statistics)\n\n"

        # 基本統計
        references_section += f"### 基本指標\n"
        references_section += f"- **實際引用文獻**: {len(cited_refs)} 篇\n"
        references_section += f"- **相關未引用文獻**: {len(uncited_refs)} 篇\n"
        references_section += f"- **總查閱文獻**: {len(cited_refs) + len(uncited_refs)} 篇\n"
        references_section += f"- **引用率**: {len(cited_refs) / max(1, len(cited_refs) + len(uncited_refs)) * 100:.1f}%\n"

        # 增強統計（如果有 citation_stats）
        if citation_stats:
            references_section += f"\n### 引用深度分析\n"
            references_section += f"- **總引用次數**: {citation_stats['total_citations']} 次\n"
            references_section += f"- **平均每篇文獻被引用**: {citation_stats['avg_citations_per_source']:.1f} 次\n"

            # 最常引用的文獻
            if citation_stats['most_cited']:
                references_section += f"- **最常引用**: "
                most_cited_strs = [f"[{ref_id}] ({count}次)" for ref_id, count in citation_stats['most_cited'][:3]]
                references_section += ", ".join(most_cited_strs) + "\n"

            # 無效引用警告
            if citation_stats['invalid_citations']:
                references_section += f"\n⚠️ **警告**: 檢測到 {len(citation_stats['invalid_citations'])} 個無效引用編號: {citation_stats['invalid_citations']}\n"

        # 分析模式說明
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

        # Embed figures inline at target sections (or fallback to bottom)
        overflow_figures = ""
        if computational_result and computational_result.get("figures"):
            figure_specs = computational_result.get("figure_specs", [])
            for i, fig_base64 in enumerate(computational_result["figures"], 1):
                spec = figure_specs[i - 1] if i - 1 < len(figure_specs) else {}
                title = spec.get("title", f"Figure {i}")
                insight = spec.get("insight", "")
                target_section = spec.get("target_section", "")

                figure_md = f"\n\n**Figure {i}: {title}**\n\n"
                figure_md += f"![Figure {i}: {title}](data:image/png;base64,{fig_base64})\n\n"
                if insight:
                    figure_md += f"*{insight}*\n\n"

                # Try to insert after the target section's first paragraph
                inserted = False
                if target_section and len(target_section) >= 4:
                    escaped = re.escape(target_section[:20])
                    pattern = re.compile(
                        rf'(#{1,3}\s+[^\n]*{escaped}[^\n]*\n(?:(?!#{1,3}\s).+\n)*)',
                        re.IGNORECASE,
                    )
                    match = pattern.search(report_body)
                    if match:
                        insert_pos = match.end()
                        report_body = report_body[:insert_pos] + figure_md + report_body[insert_pos:]
                        inserted = True

                if not inserted:
                    overflow_figures += figure_md

        # 組合完整報告
        full_report = f"{report_body}{overflow_figures}{references_section}"

        # Save report as structured bundle
        if context:
            try:
                save_path = self._save_report_bundle(
                    full_report, context, computational_result, cited_refs
                )
                if save_path:
                    self.logger.info(f"Report saved to: {save_path}", "deep_research", "report_saved")
            except Exception as e:
                self.logger.warning(f"Failed to save report: {e}", "deep_research", "save_error")

        return full_report

    def _save_report_bundle(self, full_report: str, context: ProcessingContext,
                             computational_result: Optional[Dict[str, Any]] = None,
                             cited_refs: List[Dict] = None) -> Optional[str]:
        """Save report as a structured bundle: report.md + metadata.json + figures/."""
        from pathlib import Path
        import base64

        trace_id = context.request.trace_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"{trace_id[:8]}_{timestamp}"

        reports_dir = Path(self.logger.log_dir) / "reports"
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
                # Replace base64 inline image with relative path
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
            "model": getattr(self.llm_client, 'model', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "duration_ms": context.response.metadata.get("total_duration_ms", 0),
            "tokens": context.response.metadata.get("total_tokens", {}),
            "citations": {
                "cited_count": len(cited_refs) if cited_refs else 0,
            },
            "figures": {
                "count": len(computational_result.get("figures", [])) if computational_result else 0,
                "titles": [s.get("title", "") for s in figure_specs],
            },
            "stages": context.response.metadata.get("stages", []),
        }
        (bundle_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self.logger.info(f"Report bundle saved: {bundle_dir}", "deep_research", "bundle_saved")
        return str(bundle_dir)

    # ============================================================
    # Enhanced Deep Research Methods (SSE Streaming & Events)
    # ============================================================

    async def process_with_streaming(self, context: ProcessingContext) -> AsyncGenerator[str, None]:
        # 支援 SSE Streaming 的處理方法
        # Yields: SSE 格式的事件字符串
        self._streaming_enabled = True

        # 啟動事件處理協程
        event_task = asyncio.create_task(self._event_stream_handler())

        try:
            # 發送開始事件
            await self._emit_event(ResearchEvent(
                type="progress",
                step="init",
                data={"status": "start", "query": context.request.query}
            ))

            # 執行研究流程
            result = await self.process(context)

            # 發送完成事件
            await self._emit_event(ResearchEvent(
                type="progress",
                step="complete",
                data={"status": "complete", "result_length": len(result)}
            ))

            # 發送最終結果
            yield f"data: {json.dumps({'type': 'final_report', 'data': result}, ensure_ascii=False)}\n\n"

        finally:
            # 清理
            self._streaming_enabled = False
            await self.event_queue.put(None)  # 結束信號
            await event_task

    async def _event_stream_handler(self):
        # 處理事件流
        while True:
            event = await self.event_queue.get()
            if event is None:
                break

            # 如果有回調函數，調用它
            if self.event_callback:
                try:
                    await self._call_event_callback(event)
                except Exception as e:
                    self.logger.warning(f"Event callback error: {e}", "deep_research", "callback_error")

    async def _call_event_callback(self, event: ResearchEvent):
        # 安全調用事件回調
        if asyncio.iscoroutinefunction(self.event_callback):
            await self.event_callback(event)
        else:
            self.event_callback(event)

    async def _emit_event(self, event: ResearchEvent):
        # 發送事件
        if hasattr(self, 'event_queue'):
            await self.event_queue.put(event)

        # 同時記錄到日誌
        self.logger.info(
            f"📡 Event: {event.type} - {event.step}",
            "deep_research",
            "event",
            event_type=event.type,
            event_step=event.step
        )

    # ============================================================
    # Multi-Search Engine Support
    # ============================================================

    async def _perform_deep_search_enhanced(self, query: str, goal: str) -> Dict:
        # 增強版深度搜索 - 支援多搜索引擎和智能降級
        # 發送搜索開始事件
        await self._emit_event(ResearchEvent(
            type="progress",
            step="search",
            data={
                "status": "start",
                "query": query,
                "goal": goal,
                "provider": self.search_config.primary.value
            }
        ))

        # 嘗試主要搜索引擎
        search_result = await self._try_search_provider(
            self.search_config.primary,
            query,
            goal
        )

        # 如果主要引擎失敗，嘗試備用鏈
        if not search_result or not search_result.get('sources'):
            for fallback_provider in self.search_config.fallback_chain:
                self.logger.info(
                    f"🔄 Switching to fallback: {fallback_provider.value}",
                    "deep_research",
                    "fallback"
                )

                await self._emit_event(ResearchEvent(
                    type="message",
                    step="search",
                    data={
                        "message": f"Switching to {fallback_provider.value}...",
                        "provider": fallback_provider.value
                    }
                ))

                search_result = await self._try_search_provider(
                    fallback_provider,
                    query,
                    goal
                )

                if search_result and search_result.get('sources'):
                    break

        # 發送搜索結果事件
        if search_result:
            await self._emit_event(ResearchEvent(
                type="search_result",
                step="search",
                data={
                    "query": query,
                    "sources_count": len(search_result.get('sources', [])),
                    "summary": search_result.get('summary', '')[:200]
                }
            ))

        return search_result or self._empty_search_result(query)

    async def _try_search_provider(self,
                                   provider: SearchProviderType,
                                   query: str,
                                   goal: str) -> Optional[Dict]:
        # 嘗試使用特定搜索提供商
        try:
            if provider == SearchProviderType.MODEL:
                # 使用 AI 模型內建搜索
                return await self._model_based_search(query, goal)
            elif provider == SearchProviderType.EXA:
                # 使用 Exa neural search
                return await self._exa_search(query, goal)

            # 使用其他搜索服務
            search_service = self.services.get("search")
            if search_service:
                # 如果服務支援設置提供商
                if hasattr(search_service, 'set_provider'):
                    search_service.set_provider(provider.value.lower())

                results = await search_service.search(
                    query=query,
                    max_results=self.search_config.max_results
                )

                if results:
                    return self._format_search_results(results, provider.value)

        except Exception as e:
            self.logger.warning(
                f"Search error with {provider.value}: {e}",
                "deep_research",
                "search_error"
            )

        return None

    async def _exa_search(self, query: str, goal: str) -> Optional[Dict]:
        # 使用 Exa API 進行神經搜索
        search_service = self.services.get("search")
        if not search_service:
            return None

        # 判斷搜索類型
        search_type = "general"
        if "code" in goal.lower() or "programming" in goal.lower():
            search_type = "code"
        elif "research" in goal.lower() or "paper" in goal.lower():
            search_type = "research"
        elif "news" in goal.lower() or "latest" in goal.lower():
            search_type = "news"

        try:
            # 使用整合的搜索服務（已包含 Exa）
            if hasattr(search_service, 'provider'):
                old_provider = search_service.provider
                search_service.provider = "exa"
                results = await search_service.search(
                    query=query,
                    max_results=self.search_config.max_results,
                    search_type=search_type
                )
                search_service.provider = old_provider

                if results:
                    return self._format_search_results(results, "exa")

        except Exception as e:
            self.logger.error(f"Exa search failed: {e}", "deep_research", "exa_error")

        return None

    async def _model_based_search(self, query: str, goal: str) -> Dict:
        # 使用 AI 模型的內建搜索能力
        if not self.llm_client:
            return self._empty_search_result(query)

        search_prompt = (
            f"Please search and provide information about:\n"
            f"Query: {query}\n"
            f"Research Goal: {goal}\n\n"
            f"Provide a comprehensive answer based on your knowledge, formatted as:\n"
            f"1. Summary of findings\n"
            f"2. Key facts and details\n"
            f"3. Relevant context\n\n"
            f"Focus on accuracy and relevance."
        )

        try:
            response = await self._call_llm(search_prompt, None)

            return {
                'summary': response,
                'sources': [{
                    'title': 'AI Knowledge Base',
                    'url': 'model://knowledge',
                    'relevance': 0.8
                }],
                'relevance': 0.8,
                'timestamp': datetime.now().isoformat(),
                'provider': 'model'
            }
        except Exception as e:
            self.logger.error(f"Model search failed: {e}", "deep_research", "model_search_error")
            return self._empty_search_result(query)

    def _format_search_results(self, results: List, provider: str) -> Dict:
        # 格式化搜索結果
        if not results:
            return None

        sources = []
        summary_parts = []

        for r in results[:self.search_config.max_results]:
            # 適配不同的結果格式
            if hasattr(r, 'url'):
                sources.append({
                    'url': r.url,
                    'title': getattr(r, 'title', 'Untitled'),
                    'relevance': getattr(r, 'score', 0.5)
                })
                summary_parts.append(f"- {r.title}: {getattr(r, 'snippet', '')[:100]}")
            elif isinstance(r, dict):
                sources.append({
                    'url': r.get('url', ''),
                    'title': r.get('title', 'Untitled'),
                    'relevance': r.get('score', 0.5)
                })
                summary_parts.append(f"- {r.get('title')}: {r.get('snippet', '')[:100]}")

        return {
            'summary': '\n'.join(summary_parts),
            'sources': sources,
            'relevance': sum(s['relevance'] for s in sources) / max(len(sources), 1),
            'timestamp': datetime.now().isoformat(),
            'provider': provider
        }

    def _empty_search_result(self, query: str) -> Dict:
        # 返回空搜索結果
        return {
            'summary': f"[No search results available for: {query}]",
            'sources': [],
            'relevance': 0.0,
            'timestamp': datetime.now().isoformat(),
            'provider': 'none'
        }

    # Configuration methods
    def configure_search_engines(self, config: SearchEngineConfig):
        # 動態配置搜索引擎
        self.search_config = config
        self.logger.info(
            f"Search engines configured: primary={config.primary.value}, "
            f"fallback={[p.value for p in config.fallback_chain]}",
            "deep_research",
            "config_update"
        )

    def enable_streaming(self, enabled: bool = True):
        # 啟用/禁用 streaming
        self._streaming_enabled = enabled

    def set_event_callback(self, callback: Callable[[ResearchEvent], None]):
        # 設置事件回調
        self.event_callback = callback

