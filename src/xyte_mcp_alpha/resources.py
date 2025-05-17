"""Resource handlers providing read-only data to MCP clients."""

from typing import Any, Dict

from .deps import get_client
from .utils import handle_api, validate_device_id, validate_ticket_id


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
