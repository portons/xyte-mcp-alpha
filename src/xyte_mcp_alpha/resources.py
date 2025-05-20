"""Resource handlers providing read-only data to MCP clients."""

from typing import Any, Dict

from .deps import get_client
from .logging_utils import instrument # Added import
from .utils import handle_api, validate_device_id, validate_ticket_id
from .user import get_preferences
# Forward declaration for mcp type hint, actual type is FastMCP
# from mcp.server.fastmcp import FastMCP -> Using Any to avoid potential circular dependencies


async def list_devices() -> Dict[str, Any]:
    """Return all devices in the organization."""
    async with get_client() as client:
        return await handle_api("get_devices", client.get_devices())


async def list_device_commands(device_id: str) -> Dict[str, Any]:
    """List commands for a specific device."""
    device_id = validate_device_id(device_id)
    async with get_client() as client:
        return await handle_api("get_device_commands", client.get_commands(device_id))


async def list_device_histories(device_id: str) -> Dict[str, Any]:
    """Return history records for a device."""
    device_id = validate_device_id(device_id)
    async with get_client() as client:
        return await handle_api(
            "get_device_histories", client.get_device_histories(device_id=device_id)
        )


async def device_status(device_id: str) -> Dict[str, Any]:
    """Return status information for a single device."""
    device_id = validate_device_id(device_id)
    async with get_client() as client:
        return await handle_api("get_device", client.get_device(device_id))


async def device_logs(device_id: str) -> Dict[str, Any]:
    """Return recent logs for a device (sample resource)."""
    device_id = validate_device_id(device_id)
    # Placeholder implementation
    return {"device_id": device_id, "logs": ["log entry 1", "log entry 2"]}


async def organization_info(device_id: str) -> Dict[str, Any]:
    """Fetch organization information for a device."""
    device_id = validate_device_id(device_id)
    async with get_client() as client:
        return await handle_api(
            "get_organization_info", client.get_organization_info(device_id)
        )


async def list_incidents() -> Dict[str, Any]:
    """List current incidents."""
    async with get_client() as client:
        return await handle_api("get_incidents", client.get_incidents())


async def list_tickets() -> Dict[str, Any]:
    """List all support tickets."""
    async with get_client() as client:
        return await handle_api("get_tickets", client.get_tickets())


async def get_ticket(ticket_id: str) -> Dict[str, Any]:
    """Retrieve a single ticket by ID."""
    ticket_id = validate_ticket_id(ticket_id)
    async with get_client() as client:
        return await handle_api("get_ticket", client.get_ticket(ticket_id))


async def get_user_preferences(user_token: str) -> Dict[str, Any]:
    """Return stored preferences for a specific user."""
    prefs = get_preferences(user_token)
    return prefs.model_dump()


async def list_user_devices(user_token: str) -> Dict[str, Any]:
    """List devices filtered by a user's preferred devices."""
    prefs = get_preferences(user_token)
    async with get_client(user_token) as client:
        devices = await handle_api("get_devices", client.get_devices())

    device_list = devices.get("devices", devices)
    if prefs.preferred_devices:
        device_list = [d for d in device_list if d.get("id") in prefs.preferred_devices]
    if isinstance(devices, dict) and "devices" in devices:
        devices = {"devices": device_list}
    else:
        devices = device_list
    return devices


def register_resources(mcp: Any) -> None:
    """Registers all resources with the MCP server."""
    mcp.resource("devices://", description="List all devices")(
        instrument("resource", "list_devices")(list_devices)
    )
    mcp.resource(
        "device://{device_id}/commands",
        description="Commands issued to a device",
    )(instrument("resource", "list_device_commands")(list_device_commands))
    mcp.resource(
        "device://{device_id}/histories",
        description="History records for a device",
    )(instrument("resource", "list_device_histories")(list_device_histories))
    mcp.resource(
        "device://{device_id}/status",
        description="Current status of a device",
    )(instrument("resource", "device_status")(device_status))
    mcp.resource(
        "device://{device_id}/logs",
        description="Recent logs for a device",
    )(instrument("resource", "device_logs")(device_logs))
    mcp.resource(
        "organization://info/{device_id}",
        description="Organization info for a device",
    )(instrument("resource", "organization_info")(organization_info))
    mcp.resource("incidents://", description="Current incidents")(
        instrument("resource", "list_incidents")(list_incidents)
    )
    mcp.resource("tickets://", description="All support tickets")(
        instrument("resource", "list_tickets")(list_tickets)
    )
    mcp.resource("ticket://{ticket_id}", description="Single support ticket")(
        instrument("resource", "get_ticket")(get_ticket)
    )
    mcp.resource(
        "user://{user_token}/preferences",
        description="Preferences for a user",
    )(get_user_preferences) # instrument decorator not used here in original
    mcp.resource(
        "user://{user_token}/devices",
        description="Devices filtered by user",
    )(list_user_devices) # instrument decorator not used here in original

