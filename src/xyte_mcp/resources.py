"""Resource handlers providing read-only data to MCP clients."""

from typing import Any, Dict
import json

from .deps import get_client
from .utils import handle_api, validate_device_id, validate_ticket_id
from .user import get_preferences


from starlette.requests import Request
from typing import Optional


async def list_devices(request: Optional[Request]) -> Dict[str, Any]:
    """Return all devices in the organization."""
    async with get_client(request) as client:
        return await handle_api("get_devices", client.get_devices())


async def list_device_commands(request: Optional[Request], device_id: str) -> Dict[str, Any]:
    """List commands for a specific device."""
    device_id = validate_device_id(device_id)
    async with get_client(request) as client:
        return await handle_api("get_device_commands", client.get_commands(device_id))


async def list_device_histories(request: Optional[Request], device_id: str) -> Dict[str, Any]:
    """Return history records for a device."""
    device_id = validate_device_id(device_id)
    async with get_client(request) as client:
        return await handle_api(
            "get_device_histories", client.get_device_histories(device_id=device_id)
        )


async def device_status(request: Optional[Request], device_id: str) -> Dict[str, Any]:
    """Return status information for a single device."""
    device_id = validate_device_id(device_id)
    async with get_client(request) as client:
        return await handle_api("get_device", client.get_device(device_id))


async def device_logs(request: Optional[Request], device_id: str) -> Dict[str, Any]:
    """Return recent logs for a device (sample resource)."""
    device_id = validate_device_id(device_id)
    # Placeholder implementation
    return {"device_id": device_id, "logs": ["log entry 1", "log entry 2"]}


async def organization_info(request: Optional[Request], device_id: str) -> Dict[str, Any]:
    """Fetch organization information for a device."""
    device_id = validate_device_id(device_id)
    async with get_client(request) as client:
        return await handle_api("get_organization_info", client.get_organization_info(device_id))


async def list_incidents(request: Optional[Request]) -> Dict[str, Any]:
    """List current incidents."""
    import logging
    logger = logging.getLogger(__name__)
    
    async with get_client(request) as client:
        result = await handle_api("get_incidents", client.get_incidents())
        logger.info(f"[RESOURCES] list_incidents returning: {json.dumps(result, default=str)[:1000]}")
        return result


async def list_tickets(request: Optional[Request]) -> Dict[str, Any]:
    """List all support tickets."""
    async with get_client(request) as client:
        return await handle_api("get_tickets", client.get_tickets())


async def get_ticket(request: Optional[Request], ticket_id: str) -> Dict[str, Any]:
    """Retrieve a single ticket by ID."""
    ticket_id = validate_ticket_id(ticket_id)
    async with get_client(request) as client:
        return await handle_api("get_ticket", client.get_ticket(ticket_id))


async def get_user_preferences(request: Optional[Request], user_token: str) -> Dict[str, Any]:
    """Return stored preferences for a specific user."""
    prefs = get_preferences(user_token)
    return prefs.model_dump()


async def list_user_devices(request: Optional[Request], user_token: str) -> Any:
    """List devices filtered by a user's preferred devices."""
    prefs = get_preferences(user_token)
    async with get_client(request) as client:
        devices = await handle_api("get_devices", client.get_devices())

    device_list = devices.get("devices", devices)
    if prefs.preferred_devices:
        device_list = [d for d in device_list if d.get("id") in prefs.preferred_devices]
    if isinstance(devices, dict) and "devices" in devices:
        devices = {"devices": device_list}
    else:
        devices = device_list
    return devices
