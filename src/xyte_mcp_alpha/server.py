"""MCP server for Xyte Organization API."""

import logging
import sys
import os
import json
from typing import Any, Dict

# Import the GetNextEventRequest class directly
from xyte_mcp_alpha.events import GetNextEventRequest

# Handle different import scenarios
if __name__ == "__main__" or __name__ == "xyte_mcp_alpha.server":
    # When run as a script or imported as part of the package
    try:
        # When imported as part of the package
        from .logging_utils import configure_logging, instrument
        from . import resources, tools, tasks, events, prompts
    except ImportError:
        # When run directly as a script
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        from xyte_mcp_alpha.logging_utils import configure_logging, instrument
        import xyte_mcp_alpha.resources as resources
        import xyte_mcp_alpha.tools as tools
        import xyte_mcp_alpha.tasks as tasks
        import xyte_mcp_alpha.events as events
        import xyte_mcp_alpha.prompts as prompts
else:
    # When imported by MCP dev or other external tools
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from xyte_mcp_alpha.logging_utils import configure_logging, instrument
    import xyte_mcp_alpha.resources as resources
    import xyte_mcp_alpha.tools as tools
    import xyte_mcp_alpha.tasks as tasks
    import xyte_mcp_alpha.events as events
    import xyte_mcp_alpha.prompts as prompts

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from .config import get_settings

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

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


@mcp.custom_route("/config", methods=["GET"])
async def config_endpoint(request: Request) -> JSONResponse:
    """Return sanitized configuration for debugging purposes."""
    settings = get_settings()
    api_key = request.headers.get("X-API-Key")
    if api_key != settings.xyte_api_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    cfg = settings.model_dump()
    cfg["xyte_api_key"] = "***"
    if cfg.get("xyte_user_token"):
        cfg["xyte_user_token"] = "***"
    return JSONResponse({"config": cfg})


@mcp.custom_route("/webhook", methods=["POST"])
async def webhook(req: Request) -> JSONResponse:
    """Receive external events and enqueue them for streaming."""
    payload = await req.json()
    event = events.Event(type=payload.get("type", "unknown"), data=payload.get("data", {}))
    await events.push_event(event)
    return JSONResponse({"queued": True})


@mcp.custom_route("/events", methods=["GET"])
async def stream_events(_: Request) -> Response:
    """Stream events to clients using Server-Sent Events."""
    async def event_gen():
        while True:
            ev = await events.get_next_event(events.GetNextEventRequest())
            yield f"event: {ev['type']}\ndata: {json.dumps(ev['data'])}\n\n"

    return Response(event_gen(), media_type="text/event-stream")


@mcp.custom_route("/tools", methods=["GET"])
async def list_tools(_: Request) -> JSONResponse:
    """List available tools."""
    tool_infos = await mcp.list_tools()
    tools_list = [
        {
            "name": t.name,
            "description": t.description,
            "readOnlyHint": t.annotations.readOnlyHint if t.annotations else True,
            "destructiveHint": t.annotations.destructiveHint if t.annotations else False,
        }
        for t in tool_infos
    ]
    return JSONResponse(tools_list)


@mcp.custom_route("/resources", methods=["GET"])
async def list_resources_route(_: Request) -> JSONResponse:
    """List available resources."""
    resources_list = [
        {"uri": str(r.uri), "name": r.name, "description": r.description}
        for r in await mcp.list_resources()
    ]
    return JSONResponse(resources_list)


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
    description="Find and control a device with natural language hints",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(instrument("tool", "find_and_control_device")(tools.find_and_control_device))
mcp.tool(
    description="Diagnose an AV issue in a room",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "diagnose_av_issue")(tools.diagnose_av_issue))
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


@mcp.custom_route("/task/{task_id}", methods=["GET"])
async def task_status(task_id: str) -> JSONResponse:
    """Expose async task status via HTTP."""
    result = await tasks.get_task_status(task_id)
    return JSONResponse(result)
# Create a wrapper function with explicit type annotation
async def get_next_event_wrapper(params: GetNextEventRequest) -> Dict[str, Any]:
    """Wrapper for get_next_event with explicit type annotation."""
    return await events.get_next_event(params)

# Register the wrapper function as a tool
mcp.tool(
    description="Retrieve the next queued event",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_next_event")(get_next_event_wrapper))

# Prompt registrations
mcp.prompt()(prompts.reboot_device_workflow)
mcp.prompt()(prompts.check_projectors_health)
mcp.prompt()(prompts.proactive_projector_maintenance_check)
mcp.prompt()(prompts.troubleshoot_offline_device_workflow)


def get_server() -> Any:
    """Get the MCP server instance."""
    return mcp


# Allow direct execution for development
if __name__ == "__main__":
    print("Starting MCP server in development mode...", file=sys.stderr)
    import asyncio
    from mcp.server.stdio import stdio_server

    asyncio.run(stdio_server(mcp))
