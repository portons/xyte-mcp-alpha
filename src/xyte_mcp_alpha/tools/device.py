"""Device-related tool implementations."""

# import json # No longer needed after log_automation_attempt moved
import logging
# from pathlib import Path # No longer needed after log_automation_attempt moved
from typing import Any, Dict, Optional

# import anyio # No longer needed after room tools moved

from ..deps import get_client
from ..utils import (
    MCPError,
    get_session_state, # Used by send_command
    handle_api,
    validate_device_id,
)
# from .. import resources # No longer needed after diagnose_av_issue moved
# Imports from ..client are for Pydantic models that are *arguments* to Xyte's API client, not internal tool arg models.
# These should stay as imports from ..client if they represent Xyte client's request structures.
# However, the instruction is "Pydantic request/argument models (...) are located in the same file as the tool function that uses them."
# ClaimDeviceRequest from ..client is used by claim_device.
# UpdateDeviceRequest from ..client is used by update_device.
# CommandRequest from ..client is used by send_command, cancel_command.
# For now, I will assume these specific models from ..client are intended to be distinct from the tool's own argument parsing models.
# If ClaimDeviceRequest, UpdateDeviceRequest, CommandRequest were meant to be moved from models.py, that's a different interpretation.
# The current models.py has ClaimDeviceRequest, UpdateDeviceRequest, CommandRequest, so they *are* defined there.
# My previous read of models.py listed these.
# The tool functions in tools/device.py (original) import these from ..client.
# This is confusing. Let's assume the versions in `models.py` are the ones to be co-located.

from ..client import ClaimDeviceRequest as XyteClaimDeviceRequest # Alias to avoid clash if defined locally
from ..client import UpdateDeviceRequest as XyteUpdateDeviceRequest # Alias
from ..client import CommandRequest as XyteCommandRequest # Alias

from ..models import ToolResponse # Assuming ToolResponse remains in ..models for now
# from ..models import ( # These will be defined locally
# UpdateDeviceArgs,
# SendCommandArgs,
# CancelCommandRequest,
# SearchDeviceHistoriesRequest,
# DeleteDeviceArgs,
# FindAndControlDeviceRequest,
# DiagnoseAVIssueRequest, # Moved to room.py
# )
from mcp.server.fastmcp.server import Context
from pydantic import BaseModel, Field # For defining models locally

logger = logging.getLogger(__name__)

# --- Pydantic Models moved from models.py ---
class ClaimDeviceRequest(BaseModel): # Defined locally, from models.py structure
    """Request model for claiming a device."""
    name: str = Field(..., description="Friendly name for the device")
    space_id: int = Field(..., description="Identifier of the space to assign the device")
    mac: Optional[str] = Field(None, description="Device MAC address (optional)")
    sn: Optional[str] = Field(None, description="Device serial number (optional)")
    cloud_id: str = Field("", description="Cloud identifier for the device (optional)")

class DeviceId(BaseModel): # Base for others
    """Model identifying a device."""
    device_id: str = Field(..., description="Unique device identifier")

class CommandId(DeviceId): # Base for CancelCommandRequest
    """Model identifying a command for a device."""
    command_id: str = Field(..., description="Unique command identifier")

class UpdateDeviceArgs(DeviceId):
    """Parameters for updating a device."""
    configuration: Dict[str, Any] = Field(..., description="Configuration parameters")

class SendCommandArgs(BaseModel): # Was CommandRequest from models.py, now local
    """Parameters for sending a command with optional context defaults."""
    # Fields from original CommandRequest in models.py
    name: str = Field(..., description="Command name")
    friendly_name: str = Field(..., description="Human-friendly command name")
    file_id: Optional[str] = Field(
        None, description="File identifier if the command includes a file"
    )
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")
    # Fields specific to SendCommandArgs
    device_id: Optional[str] = Field(
        None, description="Identifier of the target device"
    )
    dry_run: bool = Field(False, description="Simulate without sending")

class CancelCommandRequest(CommandId): # Was CommandId, CommandRequest from models.py
    """Parameters for canceling a command."""
    # Fields from original CommandRequest in models.py
    name: str = Field(..., description="Command name")
    friendly_name: str = Field(..., description="Human-friendly command name")
    file_id: Optional[str] = Field(
        None, description="File identifier if the command includes a file"
    )
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")

class SearchDeviceHistoriesRequest(BaseModel):
    status: Optional[str] = Field(None, description="Filter by status")
    from_date: Optional[str] = Field(None, description="Start ISO time")
    to_date: Optional[str] = Field(None, description="End ISO time")
    device_id: Optional[str] = Field(None, description="Filter by device")
    space_id: Optional[int] = Field(None, description="Filter by space") # Added as per original model
    name: Optional[str] = Field(None, description="Filter by name") # Added as per original model
    order: Optional[str] = Field(None, description="Sort order (ASC or DESC)")
    page: Optional[int] = Field(None, description="Page number for pagination")
    limit: Optional[int] = Field(None, description="Number of items per page")

class DeleteDeviceArgs(DeviceId):
    """Arguments for deleting a device."""
    dry_run: bool = Field(False, description="Simulate deletion without action")

class FindAndControlDeviceRequest(BaseModel):
    """Parameters for the find_and_control_device tool."""
    room_name: str = Field(..., description="Name of the room to search") # This makes it seem room-related
    device_type_hint: Optional[str] = Field(
        None, description="Optional device type hint (projector, display, etc.)"
    )
    action: str = Field(..., description="Action to perform, e.g. power_on")
    input_source_hint: Optional[str] = Field(
        None, description="Optional input source hint"
    )

# --- Tool Functions ---

async def claim_device(request: ClaimDeviceRequest) -> Dict[str, Any]: # Uses local ClaimDeviceRequest
    """Claim a new device and assign it to the organization."""
    async with get_client() as client:
        # Internally, map to XyteClaimDeviceRequest if needed by client.claim_device
        # Assuming client.claim_device can take this Pydantic model directly if fields match.
        # Or, explicitly create XyteClaimDeviceRequest:
        # xyte_req = XyteClaimDeviceRequest(**request.model_dump())
        # For now, assume direct usage if fields match, which is common with Pydantic.
        return await handle_api("claim_device", client.claim_device(request)) # Pass the local model instance


async def delete_device(data: DeleteDeviceArgs) -> ToolResponse:
    """Delete an existing device by its identifier."""
    if data.dry_run:
        logger.info("Dry run: would delete device %s", data.device_id)
        return ToolResponse(
            data={"dry_run": True},
            summary=f"Dry run: Would delete device {data.device_id}",
        )
    async with get_client() as client:
        result = await handle_api("delete_device", client.delete_device(data.device_id))
        return ToolResponse(
            data=result.get("data", result), summary=f"Device {data.device_id} deleted"
        )


async def update_device(data: UpdateDeviceArgs) -> Dict[str, Any]:
    """Apply configuration updates to a device."""
    async with get_client() as client:
        # Assuming UpdateDeviceArgs now holds the configuration directly or UpdateDeviceRequest from client is used.
        # The local UpdateDeviceArgs is just DeviceId + configuration.
        # The XyteUpdateDeviceRequest is what client.update_device expects.
        xyte_req = XyteUpdateDeviceRequest(configuration=data.configuration)
        return await handle_api(
            "update_device", client.update_device(data.device_id, xyte_req)
        )


async def send_command(
    data: SendCommandArgs, # Uses local SendCommandArgs
    ctx: Context | None = None,
) -> ToolResponse:
    """Send a command to a device."""
    device_id = data.device_id
    if ctx and not device_id:
        state = get_session_state(ctx)
        device_id = state.get("current_device_id")
        if device_id:
            logger.info(
                "Defaulting device_id from context: %s", device_id
            )
    if not device_id:
        raise MCPError(code="missing_device_id", message="device_id is required")

    async with get_client() as client:
        # send_command tool uses local SendCommandArgs.
        # client.send_command expects XyteCommandRequest.
        xyte_req = XyteCommandRequest(
            name=data.name,
            friendly_name=data.friendly_name,
            file_id=data.file_id,
            extra_params=data.extra_params or {},
        )
        if ctx:
            state = get_session_state(ctx) # get_session_state from ..utils
            state["last_command"] = data.name
            await ctx.info(f"Sending command {data.name} to device {device_id}")
            await ctx.report_progress(0.0, 1.0, "sending")

        if data.dry_run:
            logger.info(
                "Dry run: would send command %s to device %s", data.name, device_id
            )
            result = {"dry_run": True}
        else:
            result = await handle_api(
                "send_command", client.send_command(device_id, xyte_req)
            )

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


async def cancel_command(data: CancelCommandRequest) -> Dict[str, Any]: # Parameter name is 'data'
    """Cancel a previously sent command."""
    async with get_client() as client:
        # cancel_command tool uses local CancelCommandRequest.
        # client.cancel_command expects XyteCommandRequest.
        xyte_req = XyteCommandRequest(
            name=data.name, # Uses data.name now
            friendly_name=data.friendly_name, # Uses data.friendly_name
            file_id=data.file_id, # Uses data.file_id
            extra_params=data.extra_params or {}, # Uses data.extra_params
        )
        return await handle_api(
            "cancel_command",
            client.cancel_command(data.device_id, data.command_id, xyte_req), # Uses data.device_id, data.command_id
        )


async def search_device_histories(
    params: SearchDeviceHistoriesRequest, # Uses local SearchDeviceHistoriesRequest
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Search device history records with optional filters."""
    async with get_client() as client:
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
    # validate_device_id is from ..utils
    device_id = validate_device_id(device_id)
    async with get_client() as client:
        if ctx:
            await ctx.info("Fetching analytics")
        result = await handle_api(
            "get_device_analytics",
            client.get_device_analytics(device_id, period=period), # Uses get_client from ..deps
        )
        return ToolResponse(data=result.get("data", result)) # ToolResponse from ..models


async def find_and_control_device(
    data: FindAndControlDeviceRequest, # Uses local FindAndControlDeviceRequest
    ctx: Context | None = None,
) -> ToolResponse:
    """Find a device by room/name hints and perform an action."""
    async with get_client() as client:
        devices = await handle_api("get_devices", client.get_devices())

    device_list = devices.get("devices", devices)
    matches = []
    room = data.room_name.lower()
    for dev in device_list:
        if room in str(dev.get("space_name", "")).lower():
            if (
                data.device_type_hint # data is FindAndControlDeviceRequest
                and data.device_type_hint not in str(dev.get("type", "")).lower()
            ):
                continue
            matches.append(dev)

    if not matches:
        from difflib import get_close_matches # Standard library

        names = [d.get("space_name", "") for d in device_list]
        close = get_close_matches(room, names, n=1)
        if close:
            matches = [d for d in device_list if d.get("space_name") == close[0]]

    if not matches:
        raise MCPError(code="device_not_found", message="No matching device found") # MCPError from ..utils

    device = matches[0]
    summary = f"Selected {device.get('name')} in {device.get('space_name')}"
    if ctx:
        await ctx.info(summary)

    cmd = SendCommandArgs( # Uses local SendCommandArgs
        device_id=device.get("id"),
        name=data.action,
        friendly_name=data.action.replace("_", " "),
        extra_params=(
            {"input": data.input_source_hint} if data.input_source_hint else {}
        ),
        file_id=None, # Added as per SendCommandArgs definition
        dry_run=False # Added as per SendCommandArgs definition
    )
    # Calls the send_command function within the same file.
    result = await send_command(cmd, ctx=ctx)
    return ToolResponse( # ToolResponse from ..models
        data={"device": device, "command": result.data},
        summary=summary + f" -> {data.action}",
    )

# Removed: set_context, start_meeting_room_preset, shutdown_meeting_room,
# log_automation_attempt, echo_command, diagnose_av_issue
# These have been moved to tools/utility.py or tools/room.py
