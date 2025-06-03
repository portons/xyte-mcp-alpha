"""MCP server for Xyte Organization API."""

import logging
import sys
import os
import json
from typing import Any, Dict
from starlette.applications import Starlette
from xyte_mcp_alpha.auth_xyte import RequireXyteKey

# Fix import paths for mcp dev
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import everything using absolute imports
import xyte_mcp_alpha.plugin as plugin
from xyte_mcp_alpha.config import get_settings, validate_settings
from xyte_mcp_alpha.events import push_event, pull_event
from mcp.server.fastmcp.server import Context
from xyte_mcp_alpha.logging_utils import configure_logging, instrument, request_var
import xyte_mcp_alpha.resources as resources
import xyte_mcp_alpha.tools as tools
import xyte_mcp_alpha.tasks as tasks
import xyte_mcp_alpha.prompts as prompts

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

# Configure structured logging
configure_logging()
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Starlette application with per-request Xyte key middleware
app = Starlette()
app.add_middleware(RequireXyteKey)

# Optional Swagger UI using FastAPI
settings = get_settings()
if settings.enable_swagger:
    try:
        from fastapi import FastAPI
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        logging.getLogger(__name__).warning("FastAPI not installed; Swagger disabled")
    else:
        fast = FastAPI(openapi_url="/openapi.json", docs_url="/docs")
        fast.mount("", app)
        app = fast

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
    return JSONResponse({"config": cfg})


@mcp.custom_route("/webhook", methods=["POST"])
async def webhook(req: Request) -> JSONResponse:
    """Receive external events and enqueue them for streaming."""
    payload = await req.json()
    await push_event(
        {
            "type": payload.get("type", "unknown"),
            "data": payload.get("data", {}),
        }
    )
    return JSONResponse({"queued": True})


@mcp.custom_route("/events", methods=["GET"])
async def stream_events(_: Request) -> Response:
    """Stream events to clients using Server-Sent Events."""

    import uuid

    async def event_gen():
        consumer = str(uuid.uuid4())
        while True:
            ev = await pull_event(consumer)
            if ev:
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
            "destructiveHint": (t.annotations.destructiveHint if t.annotations else False),
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


@mcp.custom_route("/devices", methods=["GET"])
async def list_devices_route(request: Request) -> JSONResponse:
    """Compatibility endpoint returning all devices."""
    devices = await resources.list_devices(request)
    return JSONResponse(devices)


def _req() -> Request | None:
    return request_var.get()


async def _list_devices_wrapper() -> Dict[str, Any]:
    return await resources.list_devices(_req())


async def _list_device_commands_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.list_device_commands(_req(), device_id)


async def _list_device_histories_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.list_device_histories(_req(), device_id)


async def _device_status_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.device_status(_req(), device_id)


async def _device_logs_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.device_logs(_req(), device_id)


async def _organization_info_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.organization_info(_req(), device_id)


async def _list_incidents_wrapper() -> Dict[str, Any]:
    return await resources.list_incidents(_req())


async def _list_tickets_wrapper() -> Dict[str, Any]:
    return await resources.list_tickets(_req())


async def _get_ticket_wrapper(ticket_id: str) -> Dict[str, Any]:
    return await resources.get_ticket(_req(), ticket_id)


async def _get_prefs_wrapper(user_token: str) -> Dict[str, Any]:
    return await resources.get_user_preferences(_req(), user_token)


async def _list_user_devices_wrapper(user_token: str) -> Any:
    return await resources.list_user_devices(_req(), user_token)


# Resource registrations
mcp.resource("devices://", description="List all devices")(
    instrument("resource", "list_devices")(_list_devices_wrapper)
)
mcp.resource(
    "device://{device_id}/commands",
    description="Commands issued to a device",
)(instrument("resource", "list_device_commands")(_list_device_commands_wrapper))
mcp.resource(
    "device://{device_id}/histories",
    description="History records for a device",
)(instrument("resource", "list_device_histories")(_list_device_histories_wrapper))
mcp.resource(
    "device://{device_id}/status",
    description="Current status of a device",
)(instrument("resource", "device_status")(_device_status_wrapper))
mcp.resource(
    "device://{device_id}/logs",
    description="Recent logs for a device",
)(instrument("resource", "device_logs")(_device_logs_wrapper))
mcp.resource(
    "organization://info/{device_id}",
    description="Organization info for a device",
)(instrument("resource", "organization_info")(_organization_info_wrapper))
mcp.resource("incidents://", description="Current incidents")(
    instrument("resource", "list_incidents")(_list_incidents_wrapper)
)
mcp.resource("tickets://", description="All support tickets")(
    instrument("resource", "list_tickets")(_list_tickets_wrapper)
)
mcp.resource("ticket://{ticket_id}", description="Single support ticket")(
    instrument("resource", "get_ticket")(_get_ticket_wrapper)
)
mcp.resource(
    "user://{user_token}/preferences",
    description="Preferences for a user",
)(_get_prefs_wrapper)
mcp.resource(
    "user://{user_token}/devices",
    description="Devices filtered by user",
)(_list_user_devices_wrapper)

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
    description="Echo a message back",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)(instrument("tool", "echo_command")(tools.echo_command))
mcp.tool(
    description="Send a command asynchronously",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tasks.send_command_async)
mcp.tool(
    description="Get status of an asynchronous task",
    annotations=ToolAnnotations(readOnlyHint=True),
)(tasks.get_task_status)


@mcp.custom_route("/task/{task_id}", methods=["GET"])
async def task_status(request: Request) -> JSONResponse:
    """Expose async task status via HTTP."""
    tid = request.path_params.get("task_id", "")
    result = await tasks.get_task_status(tid)
    return JSONResponse(result)


# Create a wrapper function with explicit type annotation
async def get_next_event_wrapper(ctx: Context) -> Dict[str, Any]:
    """Return the next queued event for this context."""
    evt = await pull_event(ctx.request_id)
    return evt or {}


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
    settings = get_settings()
    validate_settings(settings)

    plugin.load_plugins()
    if get_settings().enable_experimental_apis:
        from .experimental import echo

        mcp.tool(
            description="Echo a message (experimental)",
            annotations=ToolAnnotations(readOnlyHint=True),
        )(instrument("tool", "experimental_echo")(echo))

    return mcp


# Allow direct execution for development
if __name__ == "__main__":
    from .logging_utils import log_json

    log_json(logging.INFO, event="server_start", mode="development")
    mcp.run(transport="stdio")
