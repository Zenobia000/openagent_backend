"""
Base runtime - shared infrastructure for all runtimes.
"""

from abc import abstractmethod
from ..protocols import RuntimeProtocol
from ..models import ProcessingContext, ProcessingMode


class BaseRuntime(RuntimeProtocol):
    """Base class for all runtimes with common logging."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    @abstractmethod
    async def execute(self, context: ProcessingContext) -> str:
        pass

    @abstractmethod
    def supports(self, mode: ProcessingMode) -> bool:
        pass
