
import asyncio
from uuid import uuid4
from typing import Dict, Any
import logging

from mcp.server.fastmcp import Context

from .deps import get_client
from .utils import handle_api
from .models import SendCommandRequest
from .logging_utils import log_json


class TaskInfo:
    def __init__(self) -> None:
        self.status: str = "pending"
        self.result: Dict[str, Any] | None = None
        self.error: str | None = None


TASKS: Dict[str, TaskInfo] = {}


async def send_command_async(
    data: SendCommandRequest, ctx: Context | None = None
) -> Dict[str, Any]:
    """Initiate a command asynchronously and return a task ID."""

    if ctx is None:
        raise ValueError("Context required")

    task_id = str(uuid4())
    info = TaskInfo()
    TASKS[task_id] = info
    log_json(logging.INFO, event="task_created", task_id=task_id)

    async def _runner() -> None:
        try:
            await ctx.report_progress(0, 100)
            async with get_client() as client:
                result = await handle_api("send_command", client.send_command(data.device_id, data))
            info.result = result
            info.status = "done"
            await ctx.report_progress(100, 100)
            log_json(logging.INFO, event="task_complete", task_id=task_id)
        except Exception as e:  # pragma: no cover - background
            info.status = "error"
            info.error = str(e)
            log_json(logging.ERROR, event="task_error", task_id=task_id, error=str(e))

    asyncio.create_task(_runner())
    return {"task_id": task_id}


async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Return status information about a previously started task."""
    info = TASKS.get(task_id)
    if not info:
        log_json(logging.INFO, event="task_status_unknown", task_id=task_id)
        return {"status": "unknown"}
    log_json(logging.INFO, event="task_status", task_id=task_id, status=info.status)
    return {"status": info.status, "result": info.result, "error": info.error}

