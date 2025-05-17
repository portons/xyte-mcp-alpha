"""MCP server for Xyte Organization API."""

import os
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional
import httpx
from datetime import datetime
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from mcp.server.fastmcp import FastMCP
from mcp.server.const import ServerCapabilities
from mcp.server.errors import MCPError
from starlette.requests import Request
from starlette.responses import Response
import asyncio

from .client import (
    XyteAPIClient,
    ClaimDeviceRequest,
    UpdateDeviceRequest,
    CommandRequest,
    OrgInfoRequest,
    TicketUpdateRequest,
    TicketMessageRequest,
)
from .models import (
    DeviceId,
    CommandId,
    UpdateDeviceArgs,
    MarkTicketResolvedRequest,
    SendTicketMessageRequest,
    SendCommandRequest,
    CancelCommandRequest,
    UpdateTicketRequest,
    SearchDeviceHistoriesRequest,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    "xyte_request_latency_seconds", "Latency of API calls", ["endpoint"]
)
ERROR_COUNT = Counter("xyte_errors_total", "XYTE API errors", ["endpoint", "code"])
STATUS_COUNT = Counter("xyte_status_total", "XYTE API status codes", ["status"])

# Initialize MCP server
mcp = FastMCP("Xyte Organization MCP Server")


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(_: Request) -> Response:
    """Expose Prometheus metrics."""
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)


# Global API client (will be initialized at startup)
api_client: Optional[XyteAPIClient] = None


def _ensure_client() -> XyteAPIClient:
    """Return the API client or raise if not initialized."""
    if not api_client:
        raise MCPError(code="init_error", message="API client not initialized")
    return api_client


async def _handle(name: str, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute an API call, track metrics and translate errors."""
    start = asyncio.get_event_loop().time()
    try:
        result = await coro
        STATUS_COUNT.labels("200").inc()
        return result
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        STATUS_COUNT.labels(str(status)).inc()
        if status == 401 or status == 403:
            code = "unauthorized"
        elif status == 404:
            code = "not_found"
        elif status == 429:
            code = "rate_limited"
        elif 500 <= status <= 599:
            code = "xyte_server_error"
        else:
            code = "xyte_api_error"
        ERROR_COUNT.labels(name, code).inc()
        raise MCPError(code=code, message=e.response.text)
    except Exception as e:  # pragma: no cover - fallback
        ERROR_COUNT.labels(name, "unknown").inc()
        raise MCPError(code="xyte_api_error", message=str(e))
    finally:
        REQUEST_LATENCY.labels(name).observe(asyncio.get_event_loop().time() - start)


@mcp.server.on_initialize
async def on_initialize():
    """Initialize the server and set up the API client."""
    global api_client

    api_key = os.getenv("XYTE_API_KEY")
    if not api_key:
        logger.error("XYTE_API_KEY environment variable not set")
        raise ValueError("XYTE_API_KEY must be set in environment")

    api_client = XyteAPIClient(api_key=api_key)
    logger.info("Xyte API client initialized")


# Resources (read-only operations)


@mcp.resource("devices://")
async def get_devices() -> Dict[str, Any]:
    """List all devices in the organization."""
    client = _ensure_client()
    return await _handle("get_devices", client.get_devices())


@mcp.resource("device://{device_id}/commands")
async def get_device_commands(device_id: str) -> Dict[str, Any]:
    """List all commands for a specific device."""
    client = _ensure_client()
    return await _handle("get_device_commands", client.get_commands(device_id))


@mcp.resource("device://{device_id}/histories")
async def get_device_histories(device_id: str) -> Dict[str, Any]:
    """Get history records for a specific device."""
    client = _ensure_client()
    return await _handle(
        "get_device_histories",
        client.get_device_histories(device_id=device_id),
    )


@mcp.resource("organization://info/{device_id}")
async def get_organization_info(device_id: str) -> Dict[str, Any]:
    """Get organization information for a device context."""
    client = _ensure_client()
    return await _handle(
        "get_organization_info", client.get_organization_info(device_id)
    )


@mcp.resource("incidents://")
async def get_incidents() -> Dict[str, Any]:
    """Retrieve all incidents for the organization."""
    client = _ensure_client()
    return await _handle("get_incidents", client.get_incidents())


@mcp.resource("tickets://")
async def get_tickets() -> Dict[str, Any]:
    """Retrieve all support tickets for the organization."""
    client = _ensure_client()
    return await _handle("get_tickets", client.get_tickets())


@mcp.resource("ticket://{ticket_id}")
async def get_ticket(ticket_id: str) -> Dict[str, Any]:
    """Retrieve a specific support ticket by ID."""
    client = _ensure_client()
    return await _handle("get_ticket", client.get_ticket(ticket_id))


# Tools (write operations)


@mcp.tool()
async def claim_device(request: ClaimDeviceRequest) -> Dict[str, Any]:
    """Register (claim) a new device under the organization."""
    client = _ensure_client()
    return await _handle("claim_device", client.claim_device(request))


@mcp.tool()
async def delete_device(data: DeviceId) -> Dict[str, Any]:
    """Delete (remove) a device by its ID."""
    client = _ensure_client()
    return await _handle("delete_device", client.delete_device(data.device_id))


@mcp.tool()
async def update_device(data: UpdateDeviceArgs) -> Dict[str, Any]:
    """Update configuration or details of a specific device."""
    client = _ensure_client()
    request = UpdateDeviceRequest(configuration=data.configuration)
    return await _handle("update_device", client.update_device(data.device_id, request))


@mcp.tool()
async def send_command(data: SendCommandRequest) -> Dict[str, Any]:
    """Send a command to the specified device."""
    client = _ensure_client()
    request = CommandRequest(
        name=data.name,
        friendly_name=data.friendly_name,
        file_id=data.file_id,
        extra_params=data.extra_params or {},
    )
    return await _handle("send_command", client.send_command(data.device_id, request))


@mcp.tool()
async def cancel_command(data: CancelCommandRequest) -> Dict[str, Any]:
    """Cancel a previously sent command on the device."""
    client = _ensure_client()
    request = CommandRequest(
        name=data.name,
        friendly_name=data.friendly_name,
        file_id=data.file_id,
        extra_params=data.extra_params or {},
    )
    return await _handle(
        "cancel_command",
        client.cancel_command(data.device_id, data.command_id, request),
    )


@mcp.tool()
async def update_ticket(data: UpdateTicketRequest) -> Dict[str, Any]:
    """Update the details of a specific ticket."""
    client = _ensure_client()
    request = TicketUpdateRequest(title=data.title, description=data.description)
    return await _handle("update_ticket", client.update_ticket(data.ticket_id, request))


@mcp.tool()
async def mark_ticket_resolved(data: MarkTicketResolvedRequest) -> Dict[str, Any]:
    """Mark the specified ticket as resolved."""
    client = _ensure_client()
    return await _handle(
        "mark_ticket_resolved", client.mark_ticket_resolved(data.ticket_id)
    )


@mcp.tool()
async def send_ticket_message(data: SendTicketMessageRequest) -> Dict[str, Any]:
    """Send a new message to the specified ticket thread."""
    client = _ensure_client()
    request = TicketMessageRequest(message=data.message)
    return await _handle(
        "send_ticket_message", client.send_ticket_message(data.ticket_id, request)
    )


@mcp.tool()
async def search_device_histories(
    params: SearchDeviceHistoriesRequest,
) -> Dict[str, Any]:
    """Search device history records with filters."""
    client = _ensure_client()
    from_dt = datetime.fromisoformat(params.from_date) if params.from_date else None
    to_dt = datetime.fromisoformat(params.to_date) if params.to_date else None

    return await _handle(
        "search_device_histories",
        client.get_device_histories(
            status=params.status,
            from_date=from_dt,
            to_date=to_dt,
            device_id=params.device_id,
            space_id=params.space_id,
            name=params.name,
        ),
    )


# Server lifecycle management
async def cleanup():
    """Clean up resources."""
    global api_client
    if api_client:
        await api_client.close()
        api_client = None


@mcp.server.on_shutdown
async def on_shutdown():
    """Handle server shutdown."""
    await cleanup()
    logger.info("Server shutdown complete")


def get_server():
    """Get the MCP server instance."""
    return mcp.server
