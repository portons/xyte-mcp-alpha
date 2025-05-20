"""Room and AV related tool implementations."""

import logging
from typing import Optional # Removed Any, Dict

import anyio # For start_meeting_room_preset, shutdown_meeting_room

from ..deps import get_client
from ..utils import MCPError, handle_api # MCPError for find_and_control_device, handle_api
from .. import resources # For diagnose_av_issue
from ..models import ToolResponse # Assuming ToolResponse remains in models for now
from mcp.server.fastmcp.server import Context # For type hinting

# Pydantic models moved from models.py
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SearchDeviceHistoriesRequest(BaseModel): # Copied for diagnose_av_issue
    status: Optional[str] = Field(None, description="Filter by status")
    from_date: Optional[str] = Field(None, description="Start ISO time")
    to_date: Optional[str] = Field(None, description="End ISO time")
    device_id: Optional[str] = Field(None, description="Filter by device")
    space_id: Optional[int] = Field(None, description="Filter by space")
    name: Optional[str] = Field(None, description="Filter by name")
    order: Optional[str] = Field(None, description="Sort order (ASC or DESC)")
    page: Optional[int] = Field(None, description="Page number for pagination")
    limit: Optional[int] = Field(None, description="Number of items per page")

class DiagnoseAVIssueRequest(BaseModel):
    """Parameters for the diagnose_av_issue tool."""

    room_name: str = Field(..., description="Room to diagnose")
    issue_description: str = Field(..., description="Description of the problem")


async def start_meeting_room_preset(
    room_name: str,
    preset_name: str,
    ctx: Context | None = None,
) -> ToolResponse:
    """Configure a meeting room for a preset workflow."""
    if ctx:
        await ctx.info(f"Configuring {room_name} for {preset_name}")
        await ctx.report_progress(0.0, 1.0, "starting")
    await anyio.sleep(0)  # yield control
    if ctx:
        await ctx.report_progress(1.0, 1.0, "done")
    return ToolResponse(
        data={"room_name": room_name, "preset_name": preset_name},
        summary=f"Room {room_name} set to {preset_name} preset",
    )


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


async def diagnose_av_issue(
    data: DiagnoseAVIssueRequest, # Uses DiagnoseAVIssueRequest
    ctx: Context | None = None,
) -> ToolResponse:
    """Run basic diagnostics for a room based on an issue description."""
    async with get_client() as client:
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

    # Assuming search_device_histories will be available via import if needed
    # For now, this uses the local SearchDeviceHistoriesRequest model
    # and we are calling resources.device_status and client.get_device_histories (via search_device_histories if it was here)
    # The original diagnose_av_issue called a search_device_histories function.
    # This function is in device.py, so we need to import it or re-implement parts of it.
    # For now, let's assume we need to call the one from device.py, which means an import.
    # This creates a dependency: room.py -> device.py (for search_device_histories)
    # This is not ideal. Let's re-evaluate.

    # The original diagnose_av_issue in tools/device.py calls self.search_device_histories.
    # For this refactoring, it's better if diagnose_av_issue directly calls client.get_device_histories
    # or if search_device_histories is also moved to room.py if it's room-specific.
    # search_device_histories seems generic enough to be a device tool.
    # Let's make diagnose_av_issue call client.get_device_histories directly for now.

    status = await resources.device_status(device["id"]) # Requires ..resources import

    # Direct call to client.get_device_histories as search_device_histories is in device.py
    # from datetime import datetime # Removed this unused import
    histories_result = await handle_api( # Requires handle_api from ..utils
        "search_device_histories_direct", # Changed name to avoid confusion
        client.get_device_histories(device_id=device["id"]) # Simplified call
    )

    return ToolResponse(
        data={"status": status, "histories": histories_result}, # Use histories_result
        summary="Diagnostics gathered",
        next_steps=["send_command"], # This hints that send_command should be callable
    )

# Note: find_and_control_device was listed under device.py tools to keep, but seems room related.
# Instruction: "The remaining tools in device.py should be purely device-related (...) find_and_control_device"
# Instruction: "Move the identified room/AV-related tools (...) to room.py"
# find_and_control_device uses FindAndControlDeviceRequest which has room_name.
# For now, following instructions to keep find_and_control_device in device.py.
# It seems diagnose_av_issue might need `search_device_histories` from `device.py` or client call.
# The original code for diagnose_av_issue calls `search_device_histories`.
# I will adjust `diagnose_av_issue` to directly call `client.get_device_histories` to avoid inter-tool-module dependency for now.
# The definition of `SearchDeviceHistoriesRequest` is copied here for `diagnose_av_issue`.
# If `search_device_histories` (the function) also needs it, it will need its own copy in `device.py`.
# This duplication of `SearchDeviceHistoriesRequest` is not ideal but follows the co-location principle.
# A better solution might be a shared models file within tools, e.g., `tools/models.py`.

# Final check on imports for the content above:
# import logging (used)
# from typing import Any, Dict, Optional (used)
# import anyio (used)
# from ..deps import get_client (used)
# from ..utils import MCPError, handle_api (used)
# from .. import resources (used)
# from ..models import ToolResponse (used, assuming it stays in ..models)
# from mcp.server.fastmcp.server import Context (used)
# from pydantic import BaseModel, Field (used)
# from datetime import datetime (added for direct client.get_device_histories call)
