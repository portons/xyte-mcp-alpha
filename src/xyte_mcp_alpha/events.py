"""Event handling utilities for asynchronous automation."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Simple event model used for incoming webhooks."""

    type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")


# Global queue storing incoming events
_event_queue: asyncio.Queue[Event] = asyncio.Queue()


async def push_event(event: Event) -> None:
    """Add an event to the queue."""
    await _event_queue.put(event)


class GetNextEventRequest(BaseModel):
    """Arguments for ``get_next_event`` tool."""

    event_type: Optional[str] = Field(
        None, description="Only return events matching this type if provided"
    )


async def get_next_event(params: GetNextEventRequest) -> Dict[str, Any]:
    """Return the next queued event matching the optional type."""
    while True:
        event = await _event_queue.get()
        if params.event_type is None or event.type == params.event_type:
            return event.model_dump()
        # Otherwise, put it back at the end of the queue and continue searching
        await _event_queue.put(event)

