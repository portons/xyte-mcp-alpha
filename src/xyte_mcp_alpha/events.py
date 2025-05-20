"""Event handling utilities for asynchronous automation."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional # ForwardRef removed

from . import plugin
from .logging_utils import log_json
import logging

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
    log_json(logging.INFO, event="push_event", event_type=event.type)
    # Notify plugins about the new event
    plugin.fire_event(event.model_dump())


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
            log_json(logging.INFO, event="get_next_event", event_type=event.type)
            return event.model_dump()
        # Otherwise, put it back at the end of the queue and continue searching
        await _event_queue.put(event)


# Wrapper for get_next_event with explicit type annotation for tool registration (MOVED FROM SERVER.PY)
# This is the single, corrected definition.
async def get_next_event_wrapper(params: GetNextEventRequest) -> Dict[str, Any]:
    """Wrapper for get_next_event with explicit type annotation."""
    return await get_next_event(params)

# Rebuild model to resolve forward references
GetNextEventRequest.model_rebuild() # Keep this, it's good practice for Pydantic models
