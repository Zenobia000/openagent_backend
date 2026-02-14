"""
WorkflowOrchestrator - Multi-step workflow planning and execution.
"""

from typing import List, Callable, Any, Awaitable

from ..models import WorkflowState, ProcessingContext
from ..logger import structured_logger


class WorkflowOrchestrator:
    """Orchestrates multi-step workflows with state tracking.

    Each step is an async callable that receives the context and
    workflow state, returning a result string.
    """

    def __init__(self):
        self._logger = structured_logger
        self._steps: List[tuple] = []  # (name, callable)

    def add_step(self, name: str, fn: Callable[[ProcessingContext, WorkflowState], Awaitable[str]]):
        """Register a workflow step."""
        self._steps.append((name, fn))

    async def run(self, context: ProcessingContext) -> str:
        """Execute all steps in order, tracking state."""
        state = WorkflowState(
            steps=[name for name, _ in self._steps],
            status="running",
        )

        results = []
        for name, fn in self._steps:
            state.advance(name)
            self._logger.info(f"Workflow step: {name}")

            result = await fn(context, state)
            state.checkpoint(name, result[:200] if result else "")
            results.append(result)

        state.complete()
        # Return the last step's result (typically the final report)
        return results[-1] if results else ""
