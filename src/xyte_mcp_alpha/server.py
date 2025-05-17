"""MCP server for Xyte Organization API."""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from mcp.server.const import ServerCapabilities
import asyncio

from .api_client import (
    XyteAPIClient,
    ClaimDeviceRequest,
    UpdateDeviceRequest,
    CommandRequest,
    OrgInfoRequest,
    TicketUpdateRequest,
    TicketMessageRequest
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Xyte Organization MCP Server")

# Global API client (will be initialized at startup)
api_client: Optional[XyteAPIClient] = None


@mcp.server.on_initialize
async def on_initialize():
    """Initialize the server and set up the API client."""
    global api_client
    
    api_key = os.getenv("XYTE_API_KEY")
    if not api_key:
        logger.error("XYTE_API_KEY environment variable not set")
        raise ValueError("XYTE_API_KEY must be set in environment")
    
    api_client = XyteAPIClient(api_key=api_key)
    logger.info("Xyte API client initialized")


# Resources (read-only operations)

@mcp.resource("devices://")
async def get_devices() -> str:
    """List all devices in the organization."""
    if not api_client:
        return '{"error": "API client not initialized"}'
    
    try:
        devices = await api_client.get_devices()
        return str(devices)
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return f'{{"error": "{str(e)}"}}'


@mcp.resource("device://{device_id}/commands")
async def get_device_commands(device_id: str) -> str:
    """List all commands for a specific device."""
    if not api_client:
        return '{"error": "API client not initialized"}'
    
    try:
        commands = await api_client.get_commands(device_id)
        return str(commands)
    except Exception as e:
        logger.error(f"Error getting commands for device {device_id}: {e}")
        return f'{{"error": "{str(e)}"}}'


@mcp.resource("device://{device_id}/histories")
async def get_device_histories(device_id: str) -> str:
    """Get history records for a specific device."""
    if not api_client:
        return '{"error": "API client not initialized"}'
    
    try:
        histories = await api_client.get_device_histories(device_id=device_id)
        return str(histories)
    except Exception as e:
        logger.error(f"Error getting histories for device {device_id}: {e}")
        return f'{{"error": "{str(e)}"}}'


@mcp.resource("organization://info/{device_id}")
async def get_organization_info(device_id: str) -> str:
    """Get organization information for a device context."""
    if not api_client:
        return '{"error": "API client not initialized"}'
    
    try:
        info = await api_client.get_organization_info(device_id)
        return str(info)
    except Exception as e:
        logger.error(f"Error getting organization info: {e}")
        return f'{{"error": "{str(e)}"}}'


@mcp.resource("incidents://")
async def get_incidents() -> str:
    """Retrieve all incidents for the organization."""
    if not api_client:
        return '{"error": "API client not initialized"}'
    
    try:
        incidents = await api_client.get_incidents()
        return str(incidents)
    except Exception as e:
        logger.error(f"Error getting incidents: {e}")
        return f'{{"error": "{str(e)}"}}'


@mcp.resource("tickets://")
async def get_tickets() -> str:
    """Retrieve all support tickets for the organization."""
    if not api_client:
        return '{"error": "API client not initialized"}'
    
    try:
        tickets = await api_client.get_tickets()
        return str(tickets)
    except Exception as e:
        logger.error(f"Error getting tickets: {e}")
        return f'{{"error": "{str(e)}"}}'


@mcp.resource("ticket://{ticket_id}")
async def get_ticket(ticket_id: str) -> str:
    """Retrieve a specific support ticket by ID."""
    if not api_client:
        return '{"error": "API client not initialized"}'
    
    try:
        ticket = await api_client.get_ticket(ticket_id)
        return str(ticket)
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        return f'{{"error": "{str(e)}"}}'


# Tools (write operations)

@mcp.tool()
async def claim_device(
    name: str,
    space_id: int,
    mac: Optional[str] = None,
    sn: Optional[str] = None,
    cloud_id: str = ""
) -> Dict[str, Any]:
    """Register (claim) a new device under the organization.
    
    Args:
        name: Friendly name for the device
        space_id: Identifier of the space to assign the device
        mac: Device MAC address (optional)
        sn: Device serial number (optional)
        cloud_id: Cloud identifier for the device (optional)
    
    Returns:
        Result of the claim operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        request = ClaimDeviceRequest(
            name=name,
            space_id=space_id,
            mac=mac,
            sn=sn,
            cloud_id=cloud_id
        )
        result = await api_client.claim_device(request)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error claiming device: {e}")
        return {"error": str(e)}


@mcp.tool()
async def delete_device(device_id: str) -> Dict[str, Any]:
    """Delete (remove) a device by its ID.
    
    Args:
        device_id: Unique device identifier
    
    Returns:
        Result of the delete operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        result = await api_client.delete_device(device_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error deleting device {device_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
async def update_device(device_id: str, configuration: Dict[str, Any]) -> Dict[str, Any]:
    """Update configuration or details of a specific device.
    
    Args:
        device_id: Unique device identifier
        configuration: Configuration parameters for the device
    
    Returns:
        Result of the update operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        request = UpdateDeviceRequest(configuration=configuration)
        result = await api_client.update_device(device_id, request)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error updating device {device_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
async def send_command(
    device_id: str,
    name: str,
    friendly_name: str,
    file_id: Optional[str] = None,
    extra_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Send a command to the specified device.
    
    Args:
        device_id: Unique device identifier
        name: Command name
        friendly_name: Human-friendly command name
        file_id: File identifier if the command includes a file (optional)
        extra_params: Additional parameters for the command (optional)
    
    Returns:
        Result of the command operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        request = CommandRequest(
            name=name,
            friendly_name=friendly_name,
            file_id=file_id,
            extra_params=extra_params or {}
        )
        result = await api_client.send_command(device_id, request)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error sending command to device {device_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
async def cancel_command(
    device_id: str,
    command_id: str,
    name: str,
    friendly_name: str,
    file_id: Optional[str] = None,
    extra_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Cancel a previously sent command on the device.
    
    Args:
        device_id: Unique device identifier
        command_id: Unique command identifier
        name: Command name
        friendly_name: Human-friendly command name
        file_id: File identifier if the command includes a file (optional)
        extra_params: Additional parameters for the command (optional)
    
    Returns:
        Result of the cancel operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        request = CommandRequest(
            name=name,
            friendly_name=friendly_name,
            file_id=file_id,
            extra_params=extra_params or {}
        )
        result = await api_client.cancel_command(device_id, command_id, request)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error canceling command {command_id} on device {device_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
async def update_ticket(
    ticket_id: str,
    title: str,
    description: str
) -> Dict[str, Any]:
    """Update the details of a specific ticket.
    
    Args:
        ticket_id: Unique ticket identifier
        title: New title for the ticket
        description: New description for the ticket
    
    Returns:
        Result of the update operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        request = TicketUpdateRequest(title=title, description=description)
        result = await api_client.update_ticket(ticket_id, request)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mark_ticket_resolved(ticket_id: str) -> Dict[str, Any]:
    """Mark the specified ticket as resolved.
    
    Args:
        ticket_id: Unique ticket identifier
    
    Returns:
        Result of the operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        result = await api_client.mark_ticket_resolved(ticket_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error marking ticket {ticket_id} as resolved: {e}")
        return {"error": str(e)}


@mcp.tool()
async def send_ticket_message(
    ticket_id: str,
    message: str
) -> Dict[str, Any]:
    """Send a new message to the specified ticket thread.
    
    Args:
        ticket_id: Unique ticket identifier
        message: Message content to send in ticket
    
    Returns:
        Result of the operation
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        request = TicketMessageRequest(message=message)
        result = await api_client.send_ticket_message(ticket_id, request)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error sending message to ticket {ticket_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
async def search_device_histories(
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    device_id: Optional[str] = None,
    space_id: Optional[int] = None,
    name: Optional[str] = None
) -> Dict[str, Any]:
    """Search device history records with filters.
    
    Args:
        status: Filter by status
        from_date: Start of time range (ISO format)
        to_date: End of time range (ISO format)
        device_id: Filter by device identifier
        space_id: Filter by space identifier
        name: Filter by name
    
    Returns:
        Filtered history records
    """
    if not api_client:
        return {"error": "API client not initialized"}
    
    try:
        from_dt = datetime.fromisoformat(from_date) if from_date else None
        to_dt = datetime.fromisoformat(to_date) if to_date else None
        
        result = await api_client.get_device_histories(
            status=status,
            from_date=from_dt,
            to_date=to_dt,
            device_id=device_id,
            space_id=space_id,
            name=name
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error searching device histories: {e}")
        return {"error": str(e)}


# Server lifecycle management
async def cleanup():
    """Clean up resources."""
    global api_client
    if api_client:
        await api_client.close()
        api_client = None


@mcp.server.on_shutdown
async def on_shutdown():
    """Handle server shutdown."""
    await cleanup()
    logger.info("Server shutdown complete")


def get_server():
    """Get the MCP server instance."""
    return mcp.server