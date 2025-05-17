"""MCP server for Xyte Organization API."""

import logging
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import resources, tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


# Resource registrations
mcp.resource("devices://", description="List all devices")(
    resources.list_devices
)
mcp.resource(
    "device://{device_id}/commands",
    description="Commands issued to a device",
)(resources.list_device_commands)
mcp.resource(
    "device://{device_id}/histories",
    description="History records for a device",
)(resources.list_device_histories)
mcp.resource(
    "device://{device_id}/status",
    description="Current status of a device",
)(resources.device_status)
mcp.resource(
    "organization://info/{device_id}",
    description="Organization info for a device",
)(resources.organization_info)
mcp.resource("incidents://", description="Current incidents")(
    resources.list_incidents
)
mcp.resource("tickets://", description="All support tickets")(
    resources.list_tickets
)
mcp.resource("ticket://{ticket_id}", description="Single support ticket")(
    resources.get_ticket
)

# Tool registrations
mcp.tool(
    description="Register a new device",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tools.claim_device)
mcp.tool(
    description="Remove a device from the organization",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tools.delete_device)
mcp.tool(
    description="Update configuration for a device",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tools.update_device)
mcp.tool(
    description="Send a command to a device",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tools.send_command)
mcp.tool(
    description="Cancel a previously sent command",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)(tools.cancel_command)
mcp.tool(
    description="Update ticket details",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tools.update_ticket)
mcp.tool(
    description="Resolve a ticket",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tools.mark_ticket_resolved)
mcp.tool(
    description="Send a message to a ticket",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)(tools.send_ticket_message)
mcp.tool(
    description="Search device history records",
    annotations=ToolAnnotations(readOnlyHint=True),
)(tools.search_device_histories)


def get_server() -> Any:
    """Get the MCP server instance."""
    return mcp
