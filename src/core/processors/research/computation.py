"""
Computation Engine - Chart planning and sandbox execution

Contains chart planning, code generation, sandbox execution, and code fixing.
Extracted from DeepResearchProcessor (~250 lines).
"""

import os
import re
import json
from typing import Dict, List, Optional, Any, Callable, Awaitable

from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger
from .analyzer import summarize_search_results


class ComputationEngine:
    """Chart planning and computational analysis via sandbox."""

    def __init__(self, call_llm: Callable[..., Awaitable[str]],
                 sandbox_service=None):
        self._call_llm = call_llm
        self.sandbox_service = sandbox_service
        self.logger = structured_logger

    async def plan_report_charts(self, context: ProcessingContext,
                                 search_results: List[Dict],
                                 report_plan: str,
                                 synthesis: str = None) -> List[Dict]:
        """Plan specific charts for the report — always runs, no sandbox gate."""
        self.logger.info("Planning report charts...", "deep_research", "chart_plan")

        research_summary = synthesis or summarize_search_results(search_results)
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

    async def execute_chart_plan(self, context: ProcessingContext,
                                 chart_specs: List[Dict],
                                 search_results: List[Dict],
                                 synthesis: str = None) -> Optional[Dict[str, Any]]:
        """Execute chart plan: generate and run code for each chart individually."""
        self.logger.progress("computational-analysis", "start")

        research_summary = synthesis or summarize_search_results(search_results)
        all_figures = []
        all_stdout = []
        total_time = 0.0
        consecutive_failures = 0
        max_chart_failures = int(os.environ.get("SANDBOX_MAX_CHART_FAILURES", "2"))

        for i, spec in enumerate(chart_specs):
            if consecutive_failures >= max_chart_failures:
                self.logger.warning(
                    f"Aborting chart plan: {consecutive_failures} consecutive failures, "
                    f"skipping remaining {len(chart_specs) - i} charts",
                    "deep_research", "chart_abort"
                )
                break

            self.logger.info(
                f"Generating chart {i+1}/{len(chart_specs)}: {spec.get('title', '?')}",
                "deep_research", "chart_gen"
            )
            try:
                prompt = PromptTemplates.get_single_chart_code_prompt(spec, research_summary)
                response = await self._call_llm(prompt, context)
                code = self.extract_code_block(response)
                if not code:
                    consecutive_failures += 1
                    continue

                result = await self.execute_analysis_code(code)
                if result and result.get("figures"):
                    for fig in result["figures"]:
                        all_figures.append({"base64": fig, "spec": spec})
                    all_stdout.append(result.get("stdout", ""))
                    total_time += result.get("execution_time", 0)
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
            except Exception as e:
                self.logger.warning(
                    f"Chart {i+1} failed: {e}", "deep_research", "chart_fail"
                )
                consecutive_failures += 1
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

    async def generate_analysis_code(self, context: ProcessingContext,
                                     search_results: List[Dict],
                                     report_plan: str) -> Optional[str]:
        """Ask LLM to generate Python code for computational analysis."""
        research_summary = summarize_search_results(search_results)
        prompt = PromptTemplates.get_computational_analysis_prompt(
            query=context.request.query,
            research_summary=research_summary,
            report_plan=report_plan
        )

        response = await self._call_llm(prompt, context)
        code = self.extract_code_block(response)
        if not code:
            self.logger.warning(
                "LLM did not produce a valid code block for analysis",
                "deep_research", "compute_no_code"
            )
        return code

    def extract_code_block(self, response: str) -> Optional[str]:
        """Extract Python code from markdown fenced code block."""
        match = re.search(r'```(?:python)?\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        stripped = response.strip()
        if stripped.startswith(('import ', 'from ', '# ', 'def ', 'class ')):
            return stripped
        return None

    async def execute_analysis_code(self, code: str, retry: bool = True) -> Optional[Dict[str, Any]]:
        """Execute analysis code in sandbox. Retry once on failure with error feedback."""
        if not self.sandbox_service:
            return None

        compute_timeout = int(os.environ.get("SANDBOX_COMPUTE_TIMEOUT", "60"))

        try:
            result = await self.sandbox_service.execute("execute_python", {
                "code": code,
                "timeout": compute_timeout
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
                fixed_code = await self.fix_analysis_code(code, error_msg)
                if fixed_code:
                    return await self.execute_analysis_code(fixed_code, retry=False)

            return None

        except Exception as e:
            self.logger.warning(
                f"Sandbox execution exception: {e}",
                "deep_research", "compute_exception"
            )
            return None

    async def fix_analysis_code(self, original_code: str, error: str) -> Optional[str]:
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
        return self.extract_code_block(response)

    async def requires_computational_analysis(self, context: ProcessingContext,
                                              search_results: List[Dict]) -> bool:
        """Determine if computational analysis would add value — LLM decides dynamically."""
        if not self.sandbox_service:
            return False

        research_summary = summarize_search_results(search_results)
        triage_prompt = PromptTemplates.get_computational_triage_prompt(
            query=context.request.query,
            research_summary=research_summary
        )

        try:
            response = await self._call_llm(triage_prompt, context)
            return response.strip().upper().startswith("YES")
        except Exception:
            return False

    async def computational_analysis_stage(self, context: ProcessingContext,
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
        code = await self.generate_analysis_code(context, search_results, report_plan)

        if not code:
            self.logger.info(
                "Computational analysis: no viable code generated, skipping",
                "deep_research", "compute_skip"
            )
            self.logger.progress("computational-analysis", "end")
            return None

        # Step 2: Execute the code
        self.logger.reasoning("Executing computational analysis in sandbox...", streaming=True)
        result = await self.execute_analysis_code(code)

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
