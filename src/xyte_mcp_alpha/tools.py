from typing import Any, Dict

from .deps import get_client
from .utils import handle_api, get_session_state
from mcp.server.fastmcp.server import Context
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
    """Claim a new device and assign it to the organization.

    Example:
        `claim_device({"name": "Display", "space_id": 1})`
    """
    async with get_client() as client:
        return await handle_api("claim_device", client.claim_device(request))


async def delete_device(data: DeviceId) -> Dict[str, Any]:
    """Delete an existing device by its identifier."""
    async with get_client() as client:
        return await handle_api("delete_device", client.delete_device(data.device_id))


async def update_device(data: UpdateDeviceArgs) -> Dict[str, Any]:
    """Apply configuration updates to a device."""
    async with get_client() as client:
        req = UpdateDeviceRequest(configuration=data.configuration)
        return await handle_api(
            "update_device", client.update_device(data.device_id, req)
        )


async def send_command(
    data: SendCommandRequest,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Send a command to a device."""
    async with get_client() as client:
        req = CommandRequest(
            name=data.name,
            friendly_name=data.friendly_name,
            file_id=data.file_id,
            extra_params=data.extra_params or {},
        )
        if ctx:
            state = get_session_state(ctx)
            state["last_command"] = data.name
            await ctx.info(
                f"Sending command {data.name} to device {data.device_id}"
            )
            await ctx.report_progress(0.0, 1.0, "sending")
        result = await handle_api(
            "send_command", client.send_command(data.device_id, req)
        )
        if ctx:
            await ctx.report_progress(1.0, 1.0, "done")
        return result


async def cancel_command(data: CancelCommandRequest) -> Dict[str, Any]:
    """Cancel a previously sent command."""
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
    """Modify the title or description of a support ticket."""
    async with get_client() as client:
        req = TicketUpdateRequest(title=data.title, description=data.description)
        return await handle_api(
            "update_ticket", client.update_ticket(data.ticket_id, req)
        )


async def mark_ticket_resolved(data: MarkTicketResolvedRequest) -> Dict[str, Any]:
    """Mark a ticket as resolved."""
    async with get_client() as client:
        return await handle_api(
            "mark_ticket_resolved", client.mark_ticket_resolved(data.ticket_id)
        )


async def send_ticket_message(data: SendTicketMessageRequest) -> Dict[str, Any]:
    """Post a new message to a ticket conversation."""
    async with get_client() as client:
        req = TicketMessageRequest(message=data.message)
        return await handle_api(
            "send_ticket_message", client.send_ticket_message(data.ticket_id, req)
        )

async def search_device_histories(
    params: SearchDeviceHistoriesRequest,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Search device history records with optional filters."""
    async with get_client() as client:
        from datetime import datetime

        from_dt = (
            datetime.fromisoformat(params.from_date) if params.from_date else None
        )
        to_dt = datetime.fromisoformat(params.to_date) if params.to_date else None

        if ctx:
            await ctx.info("Fetching device histories")
            await ctx.report_progress(0.0, 1.0)

        result = await handle_api(
            "search_device_histories",
            client.get_device_histories(
                status=params.status,
                from_date=from_dt,
                to_date=to_dt,
                device_id=params.device_id,
                order=params.order or "DESC",
                page=params.page,
                limit=params.limit,
            ),
        )

        if ctx:
            await ctx.report_progress(1.0, 1.0)

        return result