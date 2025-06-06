import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column
from mcp.server.fastmcp import Context

from .db import get_session
from .models import SendCommandRequest, ToolResponse
from .logging_utils import log_json, request_var


class Task(SQLModel, table=True):  # type: ignore[misc,call-arg]
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    status: str
    payload: dict | None = Field(default=None, sa_column=Column(JSON))
    result: dict | None = Field(default=None, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


async def save(task: "Task") -> None:
    async with get_session() as session:
        await session.merge(task)
        await session.commit()


async def fetch(tid: str) -> Task | None:
    async with get_session() as session:
        return await session.get(Task, tid)


async def send_command_async(
    data: SendCommandRequest, ctx: Context | None = None
) -> ToolResponse:
    """Initiate a command asynchronously and return a task ID.

    When ``ENABLE_ASYNC_TASKS`` is ``False`` the command is executed
    synchronously and the final result is returned directly.
    """

    if ctx is None:
        raise ValueError("Context required")

    from .config import get_settings

    if not get_settings().enable_async_tasks:
        # Execute synchronously when async tasks are disabled
        from .tools.device import send_command, SendCommandArgs

        result = await send_command(SendCommandArgs(**data.model_dump()), ctx)
        return ToolResponse(summary="done", data={"status": "done", "result": result.data})

    req = request_var.get()
    if req is None:
        raise ValueError("Request object missing")

    tid = str(uuid.uuid4())
    await save(Task(id=tid, status="queued", payload=data.model_dump()))
    from .worker.long import send_command_long
    send_command_long.delay(tid, data.model_dump(), req.state.xyte_key)
    log_json(logging.INFO, event="task_created", task_id=tid)
    return ToolResponse(summary="queued", data={"task_id": tid})


async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Return status information about a previously started task."""
    task = await fetch(task_id)
    if not task:
        log_json(logging.INFO, event="task_status_unknown", task_id=task_id)
        return {"status": "unknown"}
    log_json(logging.INFO, event="task_status", task_id=task_id, status=task.status)
    return {"status": task.status, "result": task.result}
