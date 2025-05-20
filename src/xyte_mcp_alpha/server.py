"""MCP server for Xyte Organization API."""

import logging
import sys
import os
import json
from typing import Any # Dict removed

# Fix import paths for mcp dev
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import everything using absolute imports
import xyte_mcp_alpha.plugin as plugin
from xyte_mcp_alpha.config import get_settings, validate_settings
# from xyte_mcp_alpha.events import GetNextEventRequest # No longer directly used here
from xyte_mcp_alpha.logging_utils import configure_logging, instrument
# import xyte_mcp_alpha.resources as resources # Registrations moved
# import xyte_mcp_alpha.tools as tools # Registrations moved
import xyte_mcp_alpha.tasks as tasks # Still needed for /task/{task_id} route
import xyte_mcp_alpha.events as events # Still needed for webhook, event stream, and GetNextEventRequest in events.py
# import xyte_mcp_alpha.prompts as prompts # Registrations moved

# Import registration functions
from .resources import register_resources
from .tools import register_tools
from .prompts import register_prompts

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from mcp.server.fastmcp import FastMCP
# from mcp.types import ToolAnnotations # Registrations that used this are moved

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
    event = events.Event(
        type=payload.get("type", "unknown"), data=payload.get("data", {})
    )
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
            "destructiveHint": (
                t.annotations.destructiveHint if t.annotations else False
            ),
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


# Resource registrations (MOVED to resources.py)

# Tool registrations (MOVED to tools/__init__.py)
# Note: The registration for get_next_event_wrapper was here and is now also moved.


@mcp.custom_route("/task/{task_id}", methods=["GET"])
async def task_status(task_id: str) -> JSONResponse: # tasks.get_task_status is still used here
    """Expose async task status via HTTP."""
    result = await tasks.get_task_status(task_id)
    return JSONResponse(result)


# Create a wrapper function with explicit type annotation (MOVED to events.py)

# Register the wrapper function as a tool (MOVED to tools/__init__.py)

# Prompt registrations (MOVED to prompts.py)


def get_server() -> Any:
    """Get the MCP server instance."""
    settings = get_settings()
    validate_settings(settings)

    # Register resources, tools, and prompts
    register_resources(mcp)
    register_tools(mcp)
    register_prompts(mcp)

    plugin.load_plugins()
    if get_settings().enable_experimental_apis:
        from .experimental import echo
        # Re-import ToolAnnotations if needed for this experimental tool, or move this registration too.
        from mcp.types import ToolAnnotations # Added back for this specific registration
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
