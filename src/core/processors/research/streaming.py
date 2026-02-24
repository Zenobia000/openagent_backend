"""
Streaming Manager - SSE event infrastructure for deep research

Handles event queue, streaming lifecycle, and callback dispatch.
Extracted from DeepResearchProcessor (~80 lines).
"""

import asyncio
import json
from typing import Optional, Callable, AsyncGenerator

from ...logger import structured_logger
from .events import ResearchEvent


class StreamingManager:
    """SSE streaming and event infrastructure for research processor."""

    def __init__(self, event_callback: Optional[Callable] = None):
        self.event_callback = event_callback
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self._streaming_enabled = False
        self.logger = structured_logger

    async def process_with_streaming(self, process_fn, context) -> AsyncGenerator[str, None]:
        """Wrap a process function with SSE streaming.

        Args:
            process_fn: async callable(context) -> str
            context: ProcessingContext
        """
        self._streaming_enabled = True
        event_task = asyncio.create_task(self._event_stream_handler())

        try:
            await self.emit_event(ResearchEvent(
                type="progress",
                step="init",
                data={"status": "start", "query": context.request.query}
            ))

            result = await process_fn(context)

            await self.emit_event(ResearchEvent(
                type="progress",
                step="complete",
                data={"status": "complete", "result_length": len(result)}
            ))

            yield f"data: {json.dumps({'type': 'final_report', 'data': result}, ensure_ascii=False)}\n\n"

        finally:
            self._streaming_enabled = False
            await self.event_queue.put(None)  # End signal
            await event_task

    async def _event_stream_handler(self):
        """Process event stream until None sentinel."""
        while True:
            event = await self.event_queue.get()
            if event is None:
                break
            if self.event_callback:
                try:
                    await self._call_event_callback(event)
                except Exception as e:
                    self.logger.warning(
                        f"Event callback error: {e}",
                        "deep_research", "callback_error"
                    )

    async def _call_event_callback(self, event: ResearchEvent):
        """Safely invoke event callback (sync or async)."""
        if asyncio.iscoroutinefunction(self.event_callback):
            await self.event_callback(event)
        else:
            self.event_callback(event)

    async def emit_event(self, event: ResearchEvent):
        """Enqueue event and log it."""
        await self.event_queue.put(event)
        self.logger.info(
            f"Event: {event.type} - {event.step}",
            "deep_research", "event",
            event_type=event.type,
            event_step=event.step
        )

    def enable_streaming(self, enabled: bool = True):
        self._streaming_enabled = enabled

    def set_event_callback(self, callback: Callable):
        self.event_callback = callback
