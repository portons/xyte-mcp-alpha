"""Pydantic models used by server tools and resources."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .client import CommandRequest


class DeviceId(BaseModel):
    """Model identifying a device."""

    device_id: str = Field(..., description="Unique device identifier")


class TicketId(BaseModel):
    """Model identifying a ticket."""

    ticket_id: str = Field(..., description="Unique ticket identifier")


class CommandId(DeviceId):
    """Model identifying a command for a device."""

    command_id: str = Field(..., description="Unique command identifier")


class UpdateDeviceArgs(DeviceId):
    """Parameters for updating a device."""

    configuration: Dict[str, Any] = Field(..., description="Configuration parameters")


class MarkTicketResolvedRequest(TicketId):
    """Request model for marking a ticket resolved."""


class SendTicketMessageRequest(MarkTicketResolvedRequest):
    message: str = Field(..., description="Message content to send")


class DeleteDeviceArgs(DeviceId):
    """Arguments for deleting a device."""

    dry_run: bool = Field(False, description="Simulate deletion without action")


class SendCommandArgs(CommandRequest):
    """Parameters for sending a command with optional context defaults."""

    device_id: Optional[str] = Field(
        None, description="Identifier of the target device"
    )
    dry_run: bool = Field(False, description="Simulate without sending")


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


class ToolResponse(BaseModel):
    """Standard response model for tools with optional guidance."""

    data: Any
    summary: Optional[str] = None
    next_steps: Optional[list[str]] = None
    related_tools: Optional[list[str]] = None


class FindAndControlDeviceRequest(BaseModel):
    """Parameters for the find_and_control_device tool."""

    room_name: str = Field(..., description="Name of the room to search")
    device_type_hint: Optional[str] = Field(
        None, description="Optional device type hint (projector, display, etc.)"
    )
    action: str = Field(..., description="Action to perform, e.g. power_on")
    input_source_hint: Optional[str] = Field(
        None, description="Optional input source hint"
    )


class DiagnoseAVIssueRequest(BaseModel):
    """Parameters for the diagnose_av_issue tool."""

    room_name: str = Field(..., description="Room to diagnose")
    issue_description: str = Field(..., description="Description of the problem")
