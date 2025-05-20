"""Aggregated tool exports and registration."""

from typing import Any # Added
from mcp.types import ToolAnnotations # Added
from ..logging_utils import instrument # Added
from .. import tasks # Added
from .. import events # Added
# from ..events import GetNextEventRequest # Removed as it's unused

from .device import ( # Tools remaining in device.py
    claim_device,
    delete_device,
    update_device,
    send_command,
    cancel_command,
    search_device_histories,
    get_device_analytics_report,
    find_and_control_device, # This was kept in device.py as per earlier decision
)
from .ticket import ( # Tools in ticket.py (should be unchanged)
    update_ticket,
    mark_ticket_resolved,
    send_ticket_message,
)
from .room import ( # Tools moved to room.py
    start_meeting_room_preset,
    shutdown_meeting_room,
    diagnose_av_issue,
)
from .utility import ( # Tools moved to utility.py
    set_context,
    log_automation_attempt,
    echo_command,
)

__all__ = [
    # From .device
    "claim_device",
    "delete_device",
    "update_device",
    "send_command",
    "cancel_command",
    "search_device_histories",
    "get_device_analytics_report",
    "find_and_control_device",
    # From .ticket
    "update_ticket",
    "mark_ticket_resolved",
    "send_ticket_message",
    # From .room
    "start_meeting_room_preset",
    "shutdown_meeting_room",
    "diagnose_av_issue",
    # From .utility
    "set_context",
    "log_automation_attempt",
    "echo_command",
]
# Note: The `register_tools` function below uses these imported names.
# As long as the names are correctly imported here, `register_tools` itself doesn't need to change.


def register_tools(mcp: Any) -> None:
    """Registers all tools with the MCP server."""
    # Tools from .device and .ticket (already imported by __init__.py)
    mcp.tool(
        description="Register a new device",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "claim_device")(claim_device))
    mcp.tool(
        description="Remove a device from the organization",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "delete_device")(delete_device))
    mcp.tool(
        description="Update configuration for a device",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "update_device")(update_device))
    mcp.tool(
        description="Send a command to a device",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "send_command")(send_command))
    mcp.tool(
        description="Cancel a previously sent command",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "cancel_command")(cancel_command))
    mcp.tool(
        description="Update ticket details",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "update_ticket")(update_ticket))
    mcp.tool(
        description="Resolve a ticket",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "mark_ticket_resolved")(mark_ticket_resolved))
    mcp.tool(
        description="Send a message to a ticket",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "send_ticket_message")(send_ticket_message))
    mcp.tool(
        description="Search device history records",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(instrument("tool", "search_device_histories")(search_device_histories))
    mcp.tool(
        description="Retrieve usage analytics for a device",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(instrument("tool", "get_device_analytics_report")(get_device_analytics_report))
    mcp.tool(
        description="Set context defaults",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "set_context")(set_context))
    mcp.tool(
        description="Find and control a device with natural language hints",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "find_and_control_device")(find_and_control_device))
    mcp.tool(
        description="Diagnose an AV issue in a room",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(instrument("tool", "diagnose_av_issue")(diagnose_av_issue))
    mcp.tool(
        description="Start meeting room preset",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "start_meeting_room_preset")(start_meeting_room_preset))
    mcp.tool(
        description="Shutdown meeting room",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "shutdown_meeting_room")(shutdown_meeting_room))
    mcp.tool(
        description="Log automation attempt",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "log_automation_attempt")(log_automation_attempt))
    mcp.tool(
        description="Echo a message back",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "echo_command")(echo_command))

    # Tools from tasks.py
    mcp.tool(
        description="Send a command asynchronously",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(tasks.send_command_async) # instrument decorator not used here in original server.py
    mcp.tool(
        description="Get status of an asynchronous task",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(tasks.get_task_status) # instrument decorator not used here in original server.py

    # Tool from events.py (via server.py originally)
    mcp.tool(
        description="Retrieve the next queued event",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(events.get_next_event_wrapper) # Temporarily removed instrument decorator
