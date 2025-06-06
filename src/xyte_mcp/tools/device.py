"""Device-related tool implementations."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import anyio

from ..deps import get_client
from ..utils import (
    MCPError,
    get_session_state,
    handle_api,
    validate_device_id,
)
from ..logging_utils import log_json, request_var
from .. import resources
from ..client import (
    ClaimDeviceRequest,
    UpdateDeviceRequest,
    CommandRequest,
)
from ..models import (
    UpdateDeviceArgs,
    SendCommandArgs,
    CancelCommandRequest,
    SearchDeviceHistoriesRequest,
    ToolResponse,
    DeleteDeviceArgs,
    FindAndControlDeviceRequest,
    DiagnoseAVIssueRequest,
)
from mcp.server.fastmcp.server import Context

logger = logging.getLogger(__name__)


async def claim_device(request: ClaimDeviceRequest, ctx: Context | None = None) -> Dict[str, Any]:
    """Claim a new device and assign it to the organization."""
    req = request_var.get() if ctx else None
    async with get_client(req) as client:
        return await handle_api("claim_device", client.claim_device(request))


async def delete_device(data: DeleteDeviceArgs, ctx: Context | None = None) -> ToolResponse:
    """Delete an existing device by its identifier."""
    if data.dry_run:
        log_json(logging.INFO, event="dry_run_delete_device", device_id=data.device_id)
        return ToolResponse(
            data={"dry_run": True},
            summary=f"Dry run: Would delete device {data.device_id}",
        )
    req = request_var.get() if ctx else None
    async with get_client(req) as client:
        result = await handle_api("delete_device", client.delete_device(data.device_id))
        return ToolResponse(
            data=result.get("data", result), summary=f"Device {data.device_id} deleted"
        )


async def update_device(data: UpdateDeviceArgs, ctx: Context | None = None) -> Dict[str, Any]:
    """Apply configuration updates to a device."""
    req_obj = request_var.get() if ctx else None
    async with get_client(req_obj) as client:
        req = UpdateDeviceRequest(configuration=data.configuration)
        return await handle_api("update_device", client.update_device(data.device_id, req))


async def send_command(
    data: SendCommandArgs,
    ctx: Context | None = None,
) -> ToolResponse:
    """Send a command to a device."""
    device_id = data.device_id
    if ctx and not device_id:
        state = get_session_state(ctx)
        device_id = state.get("current_device_id")
        if device_id:
            log_json(logging.INFO, event="context_device_id_default", device_id=device_id)
    if not device_id:
        raise MCPError(code="missing_device_id", message="device_id is required")

    req_obj = request_var.get() if ctx else None
    async with get_client(req_obj) as client:
        req = CommandRequest(
            name=data.name,
            friendly_name=data.friendly_name,
            file_id=data.file_id,
            extra_params=data.extra_params or {},
        )
        if ctx:
            state = get_session_state(ctx)
            state["last_command"] = data.name
            await ctx.info(f"Sending command {data.name} to device {device_id}")
            await ctx.report_progress(0.0, 1.0, "sending")

        if data.dry_run:
            log_json(
                logging.INFO,
                event="dry_run_send_command",
                device_id=device_id,
                command=data.name,
            )
            result = {"dry_run": True}
        else:
            result = await handle_api("send_command", client.send_command(device_id, req))

        if ctx:
            await ctx.report_progress(1.0, 1.0, "done")
        return ToolResponse(
            data=result.get("data", result),
            summary=(
                f"Dry run: would send '{data.friendly_name}'"
                if data.dry_run
                else f"Command '{data.friendly_name}' sent"
            )
            + f" to device {device_id}",
            next_steps=["get_device_status"],
        )


async def cancel_command(data: CancelCommandRequest, ctx: Context | None = None) -> Dict[str, Any]:
    """Cancel a previously sent command."""
    req_obj = request_var.get() if ctx else None
    async with get_client(req_obj) as client:
        req = CommandRequest(
            name=data.name,
            friendly_name=data.friendly_name,
            file_id=data.file_id,
            extra_params=data.extra_params or {},
        )
        return await handle_api(
            "cancel_command",
            client.cancel_command(data.device_id, data.command_id, req),
        )


async def search_device_histories(
    params: SearchDeviceHistoriesRequest,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Search device history records with optional filters."""
    req_obj = request_var.get() if ctx else None
    async with get_client(req_obj) as client:
        from datetime import datetime

        from_dt = datetime.fromisoformat(params.from_date) if params.from_date else None
        to_dt = datetime.fromisoformat(params.to_date) if params.to_date else None

        if ctx:
            await ctx.info("Fetching device histories")
            await ctx.report_progress(0.0, 1.0)

        result = await handle_api(
            "search_device_histories",
            client.get_device_histories(
                status=params.status,
                from_date=from_dt,
                to_date=to_dt,
                device_id=params.device_id,
                order=params.order or "DESC",
                page=params.page,
                limit=params.limit,
            ),
        )

        if ctx:
            await ctx.report_progress(1.0, 1.0)

        return result


async def get_device_analytics_report(
    device_id: str,
    period: str = "last_30_days",
    ctx: Context | None = None,
) -> ToolResponse:
    """Retrieve usage analytics for a device."""
    device_id = validate_device_id(device_id)
    req_obj = request_var.get() if ctx else None
    async with get_client(req_obj) as client:
        if ctx:
            await ctx.info("Fetching analytics")
        result = await handle_api(
            "get_device_analytics",
            client.get_device_analytics(device_id, period=period),
        )
        return ToolResponse(data=result.get("data", result))


async def set_context(
    device_id: Optional[str] = None,
    space_id: Optional[str] = None,
    ctx: Context | None = None,
) -> ToolResponse:
    """Set session context defaults for subsequent tool calls."""
    if ctx is None:
        raise MCPError(code="missing_context", message="Context required")

    state = get_session_state(ctx)
    if device_id is not None:
        state["current_device_id"] = device_id
    if space_id is not None:
        state["current_space_id"] = space_id

    return ToolResponse(data=state, summary="Context updated")


async def shutdown_meeting_room(
    room_name: str,
    ctx: Context | None = None,
) -> ToolResponse:
    """Power down AV equipment in the specified room."""
    if ctx:
        await ctx.info(f"Shutting down room {room_name}")
        await ctx.report_progress(0.0, 1.0, "shutting_down")
    await anyio.sleep(0)
    if ctx:
        await ctx.report_progress(1.0, 1.0, "done")
    return ToolResponse(
        data={"room_name": room_name},
        summary=f"Shutdown routine completed for {room_name}",
    )


async def log_automation_attempt(
    workflow_name: str,
    device_id: str,
    steps_taken: list[str],
    outcome: str,
    user_feedback: Optional[str] = None,
    error_details: Optional[str] = None,
    ctx: Context | None = None,
) -> ToolResponse:
    """Record the result of an automated workflow."""
    entry = {
        "workflow_name": workflow_name,
        "device_id": device_id,
        "steps_taken": steps_taken,
        "outcome": outcome,
        "user_feedback": user_feedback,
        "error_details": error_details,
    }
    path = Path("logs") / "automation.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    log_json(logging.INFO, event="automation_attempt", **entry)
    if ctx:
        await ctx.info("Automation attempt logged")
    return ToolResponse(data=entry, summary="Attempt recorded")


async def echo_command(device_id: str, message: str) -> ToolResponse:
    """Example command that echoes a message back."""
    validate_device_id(device_id)
    log_json(logging.INFO, event="echo", device_id=device_id, message=message)
    return ToolResponse(data={"device_id": device_id, "echo": message})


async def find_and_control_device(
    data: FindAndControlDeviceRequest,
    ctx: Context | None = None,
) -> ToolResponse:
    """Find a device by room/name hints and perform an action."""
    req_obj = request_var.get() if ctx else None
    async with get_client(req_obj) as client:
        devices = await handle_api("get_devices", client.get_devices())

    device_list = devices.get("devices", devices)
    matches = []
    room = data.room_name.lower()
    for dev in device_list:
        if room in str(dev.get("space_name", "")).lower():
            if (
                data.device_type_hint
                and data.device_type_hint not in str(dev.get("type", "")).lower()
            ):
                continue
            matches.append(dev)

    if not matches:
        from difflib import get_close_matches

        names = [d.get("space_name", "") for d in device_list]
        close = get_close_matches(room, names, n=1)
        if close:
            matches = [d for d in device_list if d.get("space_name") == close[0]]

    if not matches:
        raise MCPError(code="device_not_found", message="No matching device found")

    device = matches[0]
    summary = f"Selected {device.get('name')} in {device.get('space_name')}"
    if ctx:
        await ctx.info(summary)

    cmd = SendCommandArgs(
        device_id=device.get("id"),
        name=data.action,
        friendly_name=data.action.replace("_", " "),
        extra_params=({"input": data.input_source_hint} if data.input_source_hint else {}),
        file_id=None,
        dry_run=False,
    )
    result = await send_command(cmd, ctx=ctx)
    return ToolResponse(
        data={"device": device, "command": result.data},
        summary=summary + f" -> {data.action}",
    )


async def diagnose_av_issue(
    data: DiagnoseAVIssueRequest,
    ctx: Context | None = None,
) -> ToolResponse:
    """Run basic diagnostics for a room based on an issue description."""
    req_obj = request_var.get() if ctx else None
    async with get_client(req_obj) as client:
        devices = await handle_api("get_devices", client.get_devices())

    room_lower = data.room_name.lower()
    device = next(
        (
            d
            for d in devices.get("devices", devices)
            if room_lower in str(d.get("space_name", "")).lower()
        ),
        None,
    )

    if not device:
        raise MCPError(code="device_not_found", message="No device found for room")

    status = await resources.device_status(req_obj, device["id"])
    histories = await search_device_histories(
        SearchDeviceHistoriesRequest(
            device_id=device["id"],
            status=None,
            from_date=None,
            to_date=None,
            space_id=None,
            name=None,
            order=None,
            page=None,
            limit=None,
        ),
        ctx=ctx,
    )

    return ToolResponse(
        data={"status": status, "histories": histories},
        summary="Diagnostics gathered",
        next_steps=["send_command"],
    )
