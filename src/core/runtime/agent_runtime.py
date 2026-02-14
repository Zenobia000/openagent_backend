"""
AgentRuntime - Stateful workflow execution for AGENT-level processing.
Wraps DeepResearchProcessor with workflow orchestration and smart retry.
"""

from typing import Set

from .base import BaseRuntime
from ..models_v2 import ProcessingContext, Modes, WorkflowState
from ..processors.factory import ProcessorFactory
from ..logger import structured_logger
from ..errors import ErrorClassifier, retry_with_backoff


# Modes handled by AgentRuntime
_AGENT_MODES = {
    Modes.DEEP_RESEARCH,
}


class AgentRuntime(BaseRuntime):
    """Stateful runtime for agent-level workflows.

    Currently wraps DeepResearchProcessor.
    Includes smart retry for retryable errors at the workflow step level.
    """

    def __init__(self, llm_client=None, processor_factory: ProcessorFactory = None):
        super().__init__(llm_client)
        self._factory = processor_factory or ProcessorFactory(llm_client)
        self._logger = structured_logger

    def supports(self, mode) -> bool:
        return mode in _AGENT_MODES

    async def execute(self, context: ProcessingContext) -> str:
        """Execute agent workflow with state tracking and retry."""
        mode = context.request.mode
        self._logger.info(f"AgentRuntime executing: {mode}")

        state = WorkflowState(
            steps=["plan", "search", "synthesize"],
            status="running",
        )

        processor = self._factory.get_processor(mode)

        try:
            result = await retry_with_backoff(
                processor.process,
                context,
                max_retries=2,
                base_delay=1.0,
            )
        except Exception as e:
            state.status = "failed"
            context.response.metadata["workflow_state"] = {
                "status": state.status,
                "error": str(e),
                "error_category": ErrorClassifier.classify(e).value,
            }
            raise

        state.complete()

        context.response.metadata["workflow_state"] = {
            "status": state.status,
            "completed_steps": state.completed_steps,
        }

        return result
