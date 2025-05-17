"""MCP server for Xyte Organization API."""

import logging
from typing import Any

from .logging_utils import configure_logging, instrument

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import resources, tools, tasks, events, prompts

# Configure structured logging
configure_logging()
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Initialize MCP server
mcp = FastMCP("Xyte Organization MCP Server")


@mcp.custom_route("/healthz", methods=["GET"])
async def health(_: Request) -> Response:
    """Liveness probe."""
    return Response("ok")


@mcp.custom_route("/readyz", methods=["GET"])
async def ready(_: Request) -> Response:
    """Readiness probe."""
    return Response("ok")


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(_: Request) -> Response:
    """Expose Prometheus metrics."""
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)


@mcp.custom_route("/tools", methods=["GET"])
async def list_tools(_: Request) -> JSONResponse:
    """List available tools."""
    tools_list = []
    for tool_name, tool_def in mcp.server.tools.items():
        tools_list.append({
            "name": tool_name,
            "description": tool_def.description,
            "readOnlyHint": tool_def.annotations.readOnlyHint if tool_def.annotations else True,
            "destructiveHint": tool_def.annotations.destructiveHint if tool_def.annotations else False,
        })
    return JSONResponse({"tools": tools_list})


# Resource registrations
mcp.resource("devices://", description="List all devices")(
    instrument("resource", "list_devices")(resources.list_devices)
)
mcp.resource(
    "device://{device_id}/commands",
    description="Commands issued to a device",
)(instrument("resource", "list_device_commands")(resources.list_device_commands))
mcp.resource(
    "device://{device_id}/histories",
    description="History records for a device",
)(instrument("resource", "list_device_histories")(resources.list_device_histories))
mcp.resource(
    "device://{device_id}/status",
    description="Current status of a device",
)(instrument("resource", "device_status")(resources.device_status))
mcp.resource(
    "organization://info/{device_id}",
    description="Organization info for a device",
)(instrument("resource", "organization_info")(resources.organization_info))
mcp.resource("incidents://", description="Current incidents")(
    instrument("resource", "list_incidents")(resources.list_incidents)
)
mcp.resource("tickets://", description="All support tickets")(
    instrument("resource", "list_tickets")(resources.list_tickets)
)
mcp.resource("ticket://{ticket_id}", description="Single support ticket")(
    instrument("resource", "get_ticket")(resources.get_ticket)
)
mcp.resource(
    "user://{user_token}/preferences",
    description="Preferences for a user",
)(resources.get_user_preferences)
mcp.resource(
    "user://{user_token}/devices",
    description="Devices filtered by user",
)(resources.list_user_devices)

# Tool registrations
mcp.tool(
    description="Register a new device",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "claim_device")(tools.claim_device))
mcp.tool(
    description="Remove a device from the organization",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "delete_device")(tools.delete_device))
mcp.tool(
    description="Update configuration for a device",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "update_device")(tools.update_device))
mcp.tool(
    description="Send a command to a device",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "send_command")(tools.send_command))
mcp.tool(
    description="Cancel a previously sent command",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)(instrument("tool", "cancel_command")(tools.cancel_command))
mcp.tool(
    description="Update ticket details",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "update_ticket")(tools.update_ticket))
mcp.tool(
    description="Resolve a ticket",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "mark_ticket_resolved")(tools.mark_ticket_resolved))
mcp.tool(
    description="Send a message to a ticket",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)(instrument("tool", "send_ticket_message")(tools.send_ticket_message))
mcp.tool(
    description="Search device history records",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "search_device_histories")(tools.search_device_histories))
mcp.tool(
    description="Retrieve usage analytics for a device",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_device_analytics_report")(tools.get_device_analytics_report))
mcp.tool(
    description="Set context defaults",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)(instrument("tool", "set_context")(tools.set_context))
mcp.tool(
    description="Start meeting room preset",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "start_meeting_room_preset")(tools.start_meeting_room_preset))
mcp.tool(
    description="Shutdown meeting room",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "shutdown_meeting_room")(tools.shutdown_meeting_room))
mcp.tool(
    description="Log automation attempt",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)(instrument("tool", "log_automation_attempt")(tools.log_automation_attempt))
mcp.tool(
    description="Send a command asynchronously",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tasks.send_command_async)
mcp.tool(
    description="Get status of an asynchronous task",
    annotations=ToolAnnotations(readOnlyHint=True),
)(tasks.get_task_status)
mcp.tool(
    description="Retrieve the next queued event",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_next_event")(events.get_next_event))

# Prompt registrations
mcp.prompt()(prompts.reboot_device_workflow)
mcp.prompt()(prompts.check_projectors_health)
mcp.prompt()(prompts.proactive_projector_maintenance_check)
mcp.prompt()(prompts.troubleshoot_offline_device_workflow)


def get_server() -> Any:
    """Get the MCP server instance."""
    return mcp