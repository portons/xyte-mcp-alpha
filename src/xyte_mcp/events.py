from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict

from redis.asyncio import Redis

from . import plugin
from .logging_utils import log_json
from pydantic import BaseModel, Field

redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
STREAM = "mcp_events"
GROUP = "mcp_consumers"


class Event(BaseModel):
    """Simple event model used for incoming webhooks."""

    type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")


async def push_event(evt: Event | Dict[str, Any]) -> None:
    """Publish an event to the Redis stream and plugins."""
    if isinstance(evt, Event):
        payload = evt.model_dump()
    else:
        payload = evt
    await redis.xadd(
        STREAM,
        {k: json.dumps(v) for k, v in payload.items()},
        maxlen=10000,
        approximate=True,
    )
    log_json(logging.INFO, event="push_event", event_type=payload.get("type"))
    plugin.fire_event(payload)


async def pull_event(consumer: str, block: int = 5000) -> Dict[str, Any] | None:
    """Retrieve the next event for a consumer from the Redis stream."""
    try:
        await redis.xgroup_create(STREAM, GROUP, id="$", mkstream=True)
    except Exception:
        pass
    resp = await redis.xreadgroup(GROUP, consumer, {STREAM: ">"}, 1, block)
    if not resp:
        return None
    _, evts = resp[0]
    eid, raw = evts[0]
    await redis.xack(STREAM, GROUP, eid)
    result = {k.decode(): json.loads(v) for k, v in raw.items()}
    log_json(logging.INFO, event="pull_event", event_type=result.get("type"))
    return result
