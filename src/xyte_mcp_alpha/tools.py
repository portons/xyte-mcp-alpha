from typing import Any, Dict

from .deps import get_client
from .utils import handle_api
from .client import (
    ClaimDeviceRequest,
    UpdateDeviceRequest,
    CommandRequest,
    TicketUpdateRequest,
    TicketMessageRequest,
)
from .models import (
    DeviceId,
    UpdateDeviceArgs,
    MarkTicketResolvedRequest,
    SendTicketMessageRequest,
    SendCommandRequest,
    CancelCommandRequest,
    UpdateTicketRequest,
    SearchDeviceHistoriesRequest,
)


async def claim_device(request: ClaimDeviceRequest) -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api("claim_device", client.claim_device(request))


async def delete_device(data: DeviceId) -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api("delete_device", client.delete_device(data.device_id))


async def update_device(data: UpdateDeviceArgs) -> Dict[str, Any]:
    async with get_client() as client:
        req = UpdateDeviceRequest(configuration=data.configuration)
        return await handle_api(
            "update_device", client.update_device(data.device_id, req)
        )


async def send_command(data: SendCommandRequest) -> Dict[str, Any]:
    async with get_client() as client:
        req = CommandRequest(
            name=data.name,
            friendly_name=data.friendly_name,
            file_id=data.file_id,
            extra_params=data.extra_params or {},
        )
        return await handle_api(
            "send_command", client.send_command(data.device_id, req)
        )


async def cancel_command(data: CancelCommandRequest) -> Dict[str, Any]:
    async with get_client() as client:
        req = CommandRequest(
            name=data.name,
            friendly_name=data.friendly_name,
            file_id=data.file_id,
            extra_params=data.extra_params or {},
        )
        return await handle_api(
            "cancel_command",
            client.cancel_command(data.device_id, data.command_id, req),
        )


async def update_ticket(data: UpdateTicketRequest) -> Dict[str, Any]:
    async with get_client() as client:
        req = TicketUpdateRequest(title=data.title, description=data.description)
        return await handle_api(
            "update_ticket", client.update_ticket(data.ticket_id, req)
        )


async def mark_ticket_resolved(data: MarkTicketResolvedRequest) -> Dict[str, Any]:
    async with get_client() as client:
        return await handle_api(
            "mark_ticket_resolved", client.mark_ticket_resolved(data.ticket_id)
        )


async def send_ticket_message(data: SendTicketMessageRequest) -> Dict[str, Any]:
    async with get_client() as client:
        req = TicketMessageRequest(message=data.message)
        return await handle_api(
            "send_ticket_message", client.send_ticket_message(data.ticket_id, req)
        )

async def search_device_histories(params: SearchDeviceHistoriesRequest) -> Dict[str, Any]:
    async with get_client() as client:
        from datetime import datetime
        from_dt = datetime.fromisoformat(params.from_date) if params.from_date else None
        to_dt = datetime.fromisoformat(params.to_date) if params.to_date else None
        return await handle_api(
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
