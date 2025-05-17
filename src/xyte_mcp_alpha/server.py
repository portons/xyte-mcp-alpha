"""MCP server for Xyte Organization API."""

from typing import Any

from .logging_utils import configure_logging, instrument, RequestLoggingMiddleware

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response

from mcp.server.fastmcp import FastMCP

from . import resources, tools

# Configure structured logging
configure_logging()

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
mcp.resource("devices://")(instrument("resource", "list_devices")(resources.list_devices))
mcp.resource("device://{device_id}/commands")(instrument("resource", "list_device_commands")(resources.list_device_commands))
mcp.resource("device://{device_id}/histories")(instrument("resource", "list_device_histories")(resources.list_device_histories))
mcp.resource("organization://info/{device_id}")(instrument("resource", "organization_info")(resources.organization_info))
mcp.resource("incidents://")(instrument("resource", "list_incidents")(resources.list_incidents))
mcp.resource("tickets://")(instrument("resource", "list_tickets")(resources.list_tickets))
mcp.resource("ticket://{ticket_id}")(instrument("resource", "get_ticket")(resources.get_ticket))

# Tool registrations
mcp.tool()(instrument("tool", "claim_device")(tools.claim_device))
mcp.tool()(instrument("tool", "delete_device")(tools.delete_device))
mcp.tool()(instrument("tool", "update_device")(tools.update_device))
mcp.tool()(instrument("tool", "send_command")(tools.send_command))
mcp.tool()(instrument("tool", "cancel_command")(tools.cancel_command))
mcp.tool()(instrument("tool", "update_ticket")(tools.update_ticket))
mcp.tool()(instrument("tool", "mark_ticket_resolved")(tools.mark_ticket_resolved))
mcp.tool()(instrument("tool", "send_ticket_message")(tools.send_ticket_message))
mcp.tool()(instrument("tool", "search_device_histories")(tools.search_device_histories))


def get_server() -> Any:
    """Get the MCP server instance."""
    return mcp
