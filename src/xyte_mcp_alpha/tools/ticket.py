"""Support ticket related tools."""

from typing import Any, Dict

from ..deps import get_client
from ..utils import handle_api
from ..client import TicketUpdateRequest, TicketMessageRequest
from ..models import (
    UpdateTicketRequest,
    MarkTicketResolvedRequest,
    SendTicketMessageRequest,
)


from mcp.server.fastmcp.server import Context


async def update_ticket(data: UpdateTicketRequest, ctx: Context | None = None) -> Dict[str, Any]:
    """Modify the title or description of a support ticket."""
    req_obj = ctx.request_context.request if ctx else None
    async with get_client(req_obj) as client:
        req = TicketUpdateRequest(title=data.title, description=data.description)
        return await handle_api("update_ticket", client.update_ticket(data.ticket_id, req))


async def mark_ticket_resolved(
    data: MarkTicketResolvedRequest, ctx: Context | None = None
) -> Dict[str, Any]:
    """Mark a ticket as resolved."""
    req_obj = ctx.request_context.request if ctx else None
    async with get_client(req_obj) as client:
        return await handle_api("mark_ticket_resolved", client.mark_ticket_resolved(data.ticket_id))


async def send_ticket_message(
    data: SendTicketMessageRequest, ctx: Context | None = None
) -> Dict[str, Any]:
    """Post a new message to a ticket conversation."""
    req_obj = ctx.request_context.request if ctx else None
    async with get_client(req_obj) as client:
        req = TicketMessageRequest(message=data.message)
        return await handle_api(
            "send_ticket_message", client.send_ticket_message(data.ticket_id, req)
        )
