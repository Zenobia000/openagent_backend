"""SSE streaming adapter - bridges engine events to EventSourceResponse."""

import asyncio
import json
from typing import AsyncGenerator

from core.models import EventType, SSEEvent


async def engine_event_generator(
    engine,
    request,
) -> AsyncGenerator[dict, None]:
    """Async generator that yields SSE events from engine processing.

    Bridges the engine's callback-based SSE system into a true async
    generator suitable for sse-starlette's EventSourceResponse.
    """
    event_queue: asyncio.Queue = asyncio.Queue()
    done = asyncio.Event()

    def sse_callback(signal: str, data):
        event_queue.put_nowait({"event": signal, "data": data})

    # Yield connection start
    yield _format_event(EventType.START.value, {"status": "connected"})

    # Wire up callback and run engine in background
    engine.logger.set_sse_callback(sse_callback)

    async def _run():
        try:
            response = await engine.process(request)
            # Final result event
            event_queue.put_nowait({
                "event": EventType.RESULT.value,
                "data": {"response": response.result, "trace_id": response.trace_id},
            })
        except Exception as e:
            event_queue.put_nowait({
                "event": EventType.ERROR.value,
                "data": {"message": str(e)},
            })
        finally:
            done.set()

    task = asyncio.create_task(_run())

    try:
        while not done.is_set() or not event_queue.empty():
            try:
                evt = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield _format_event(evt["event"], evt["data"])
            except asyncio.TimeoutError:
                continue
    finally:
        if not task.done():
            task.cancel()
        # Yield stream end
        yield _format_event(EventType.END.value, {"status": "complete"})


def _format_event(event_type: str, data) -> dict:
    """Format an event for EventSourceResponse."""
    return {
        "event": event_type,
        "data": json.dumps(data) if not isinstance(data, str) else data,
    }
