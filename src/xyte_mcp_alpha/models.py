"""Pydantic models used by server tools and resources.

NOTE: Most tool-specific request/argument models have been co-located
with their respective tool functions in the 'tools' submodules.
This file should primarily contain generic response models or models
not specific to a single tool's arguments.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class OrgInfoRequest(BaseModel):
    """Request model for getting organization info.""" # Not tied to a specific tool

    device_id: str = Field(
        ..., description="Device identifier for which to retrieve organization info"
    )

class ToolResponse(BaseModel):
    """Standard response model for tools with optional guidance.""" # Generic

    data: Any
    summary: Optional[str] = None
    next_steps: Optional[list[str]] = None
    related_tools: Optional[list[str]] = None

# Models that were here and are now co-located with tools:
# - ClaimDeviceRequest -> tools/device.py
# - UpdateDeviceRequest (and its variant UpdateDeviceArgs) -> tools/device.py (UpdateDeviceArgs)
# - CommandRequest (and its variants SendCommandArgs, CancelCommandRequest, SendCommandRequest) -> tools/device.py (SendCommandArgs, CancelCommandRequest)
# - TicketUpdateRequest (and its variant UpdateTicketRequest) -> tools/ticket.py (UpdateTicketRequest)
# - TicketMessageRequest (and its variant SendTicketMessageRequest) -> tools/ticket.py (SendTicketMessageRequest)
# - DeviceId -> tools/device.py
# - TicketId -> tools/ticket.py
# - CommandId -> tools/device.py
# - MarkTicketResolvedRequest -> tools/ticket.py
# - DeleteDeviceArgs -> tools/device.py
# - SearchDeviceHistoriesRequest -> tools/device.py and tools/room.py
# - FindAndControlDeviceRequest -> tools/device.py
# - DiagnoseAVIssueRequest -> tools/room.py

# --- Models imported by client.py ---
# These are restored here to ensure client.py can import them directly.
# Tools will use their own co-located models for argument parsing.

class ClaimDeviceRequest(BaseModel):
    """Request model for claiming a device (used by client.py)."""
    name: str = Field(..., description="Friendly name for the device")
    space_id: int = Field(..., description="Identifier of the space to assign the device")
    mac: Optional[str] = Field(None, description="Device MAC address (optional)")
    sn: Optional[str] = Field(None, description="Device serial number (optional)")
    cloud_id: str = Field("", description="Cloud identifier for the device (optional)")

class UpdateDeviceRequest(BaseModel):
    """Request model for updating a device (used by client.py)."""
    configuration: Dict[str, Any] = Field(
        ..., description="Configuration parameters for the device"
    )

class CommandRequest(BaseModel):
    """Request model for sending a command to device (used by client.py)."""
    name: str = Field(..., description="Command name")
    friendly_name: str = Field(..., description="Human-friendly command name")
    file_id: Optional[str] = Field(
        None, description="File identifier if the command includes a file"
    )
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")

class TicketUpdateRequest(BaseModel):
    """Request model for updating a ticket (used by client.py)."""
    title: str = Field(..., description="New title for the ticket")
    description: str = Field(..., description="New description for the ticket")

class TicketMessageRequest(BaseModel):
    """Request model for sending a ticket message (used by client.py)."""
    message: str = Field(..., description="Message content to send in ticket")

# --- Base Identifier Models (restored for utils.py and other potential shared use) ---
class DeviceId(BaseModel):
    """Model identifying a device."""
    device_id: str = Field(..., description="Unique device identifier")

class TicketId(BaseModel):
    """Model identifying a ticket."""
    ticket_id: str = Field(..., description="Unique ticket identifier")

class SendCommandRequest(DeviceId, CommandRequest): # Restored for tasks.py
    """Parameters for sending a command (used by tasks.py)."""
    pass
