from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .api_client import CommandRequest


class DeviceId(BaseModel):
    """Model identifying a device."""
    device_id: str = Field(..., description="Unique device identifier")


class CommandId(DeviceId):
    """Model identifying a command for a device."""
    command_id: str = Field(..., description="Unique command identifier")


class UpdateDeviceArgs(DeviceId):
    """Parameters for updating a device."""
    configuration: Dict[str, Any] = Field(..., description="Configuration parameters")


class MarkTicketResolvedRequest(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier")


class SendTicketMessageRequest(MarkTicketResolvedRequest):
    message: str = Field(..., description="Message content to send")


class SendCommandRequest(DeviceId, CommandRequest):
    """Parameters for sending a command."""
    pass


class CancelCommandRequest(CommandId, CommandRequest):
    """Parameters for canceling a command."""
    pass


class UpdateTicketRequest(MarkTicketResolvedRequest):
    title: str = Field(..., description="New title for the ticket")
    description: str = Field(..., description="New description")


class SearchDeviceHistoriesRequest(BaseModel):
    status: Optional[str] = Field(None, description="Filter by status")
    from_date: Optional[str] = Field(None, description="Start ISO time")
    to_date: Optional[str] = Field(None, description="End ISO time")
    device_id: Optional[str] = Field(None, description="Filter by device")
    space_id: Optional[int] = Field(None, description="Filter by space")
    name: Optional[str] = Field(None, description="Filter by name")
