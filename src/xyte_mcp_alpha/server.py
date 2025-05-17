"""MCP server for Xyte Organization API."""

import logging
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response

from mcp.server.fastmcp import FastMCP

from . import resources, tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Xyte Organization MCP Server")


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(_: Request) -> Response:
    """Expose Prometheus metrics."""
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)


# Resource registrations
mcp.resource("devices://")(resources.list_devices)
mcp.resource("device://{device_id}/commands")(resources.list_device_commands)
mcp.resource("device://{device_id}/histories")(resources.list_device_histories)
mcp.resource("organization://info/{device_id}")(resources.organization_info)
mcp.resource("incidents://")(resources.list_incidents)
mcp.resource("tickets://")(resources.list_tickets)
mcp.resource("ticket://{ticket_id}")(resources.get_ticket)

# Tool registrations
mcp.tool()(tools.claim_device)
mcp.tool()(tools.delete_device)
mcp.tool()(tools.update_device)
mcp.tool()(tools.send_command)
mcp.tool()(tools.cancel_command)
mcp.tool()(tools.update_ticket)
mcp.tool()(tools.mark_ticket_resolved)
mcp.tool()(tools.send_ticket_message)
mcp.tool()(tools.search_device_histories)


async def on_shutdown() -> None:
    """Handle server shutdown."""
    logger.info("Server shutdown complete")


mcp.server.on_shutdown(on_shutdown)


def get_server() -> Any:
    """Get the MCP server instance."""
    return mcp.server
