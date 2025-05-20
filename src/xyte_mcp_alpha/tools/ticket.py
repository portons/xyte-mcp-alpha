"""Support ticket related tools."""

from typing import Any, Dict, Optional # Added Optional for models
from pydantic import BaseModel, Field # For defining models locally

from ..deps import get_client
from ..utils import handle_api
# Alias client models to avoid name clashes if similar local models are defined
from ..client import TicketUpdateRequest as XyteTicketUpdateRequest
from ..client import TicketMessageRequest as XyteTicketMessageRequest
# Models previously imported from ..models will now be defined locally
# from ..models import (
# UpdateTicketRequest,
# MarkTicketResolvedRequest,
# SendTicketMessageRequest,
# )

# --- Pydantic Models moved from models.py ---
class TicketId(BaseModel): # Base model
    """Model identifying a ticket."""
    ticket_id: str = Field(..., description="Unique ticket identifier")

class MarkTicketResolvedRequest(TicketId): # Inherits TicketId
    """Request model for marking a ticket resolved."""
    pass # No additional fields

class UpdateTicketRequest(TicketId): # Inherits TicketId, was MarkTicketResolvedRequest in models.py
    """Parameters for updating a ticket."""
    title: str = Field(..., description="New title for the ticket")
    description: str = Field(..., description="New description")

class SendTicketMessageRequest(TicketId): # Inherits TicketId, was MarkTicketResolvedRequest in models.py
    """Parameters for sending a ticket message."""
    message: str = Field(..., description="Message content to send")

# --- Tool Functions ---
async def update_ticket(data: UpdateTicketRequest) -> Dict[str, Any]: # Uses local UpdateTicketRequest
    """Modify the title or description of a support ticket."""
    async with get_client() as client:
        # client.update_ticket expects XyteTicketUpdateRequest
        xyte_req = XyteTicketUpdateRequest(title=data.title, description=data.description)
        return await handle_api(
            "update_ticket", client.update_ticket(data.ticket_id, xyte_req)
        )


async def mark_ticket_resolved(data: MarkTicketResolvedRequest) -> Dict[str, Any]: # Uses local MarkTicketResolvedRequest
    """Mark a ticket as resolved."""
    async with get_client() as client:
        # mark_ticket_resolved client call does not take a complex request model, only ticket_id
        return await handle_api(
            "mark_ticket_resolved", client.mark_ticket_resolved(data.ticket_id)
        )


async def send_ticket_message(data: SendTicketMessageRequest) -> Dict[str, Any]: # Uses local SendTicketMessageRequest
    """Post a new message to a ticket conversation."""
    async with get_client() as client:
        # client.send_ticket_message expects XyteTicketMessageRequest
        xyte_req = XyteTicketMessageRequest(message=data.message)
        return await handle_api(
            "send_ticket_message", client.send_ticket_message(data.ticket_id, xyte_req)
        )
