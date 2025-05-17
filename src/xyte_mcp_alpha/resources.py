from datetime import datetime
from typing import Any, Dict

from .deps import get_client
from .utils import handle_api
from .models import SearchDeviceHistoriesRequest


async def list_devices() -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api("get_devices", client.get_devices())


async def list_device_commands(device_id: str) -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api("get_device_commands", client.get_commands(device_id))


async def list_device_histories(device_id: str) -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api(
            "get_device_histories", client.get_device_histories(device_id=device_id)
        )


async def organization_info(device_id: str) -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api(
            "get_organization_info", client.get_organization_info(device_id)
        )


async def list_incidents() -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api("get_incidents", client.get_incidents())


async def list_tickets() -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api("get_tickets", client.get_tickets())


async def get_ticket(ticket_id: str) -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api("get_ticket", client.get_ticket(ticket_id))
