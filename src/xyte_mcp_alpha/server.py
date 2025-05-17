"""MCP server for Xyte Organization API."""

import logging
from typing import Any

from .logging_utils import configure_logging, instrument

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import resources, tools

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


def get_server() -> Any:
    """Get the MCP server instance."""
    return mcp
