"""REST API wrapper for OpenAI/ChatGPT integration."""

import json
import asyncio
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

# Import dependencies
from .server import get_server
from .config import get_settings
from mcp.types import TextContent

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Xyte MCP REST API",
    description="REST wrapper for MCP server to work with ChatGPT",
    version="1.0.0",
    servers=[{"url": "https://fe.ngrok.io", "description": "Xyte MCP via ngrok"}]
)

# Request/Response Models
class CommandRequest(BaseModel):
    device_id: str
    command: str
    args: Optional[Dict[str, Any]] = None

class DeviceUpdateRequest(BaseModel):
    device_id: str
    name: Optional[str] = None
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TicketUpdateRequest(BaseModel):
    ticket_id: str
    status: Optional[str] = None
    comment: Optional[str] = None

# Helper to call MCP tools
async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], api_key: str) -> Any:
    """Call an MCP tool and return the result."""
    server = get_server()
    
    # Find the tool
    tool = None
    for t in server.tools:
        if t.name == tool_name:
            tool = t
            break
    
    if not tool:
        raise HTTPException(404, f"Tool {tool_name} not found")
    
    # Create a mock context with the API key
    class MockContext:
        def __init__(self, api_key):
            self.api_key = api_key
    
    # Call the tool
    try:
        result = await tool.func(MockContext(api_key), **arguments)
        
        # Handle TextContent response
        if hasattr(result, 'content') and isinstance(result.content, list):
            for content in result.content:
                if isinstance(content, TextContent):
                    return {"result": content.text}
        
        return {"result": str(result)}
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        raise HTTPException(500, f"Error executing tool: {str(e)}")

# Helper to read MCP resources
async def read_mcp_resource(uri: str, api_key: str) -> Any:
    """Read an MCP resource and return the result."""
    server = get_server()
    
    # Find matching resource
    resource = None
    for r in server.resources:
        if r.uri == uri:
            resource = r
            break
    
    if not resource:
        raise HTTPException(404, f"Resource {uri} not found")
    
    # Create a mock context
    class MockContext:
        def __init__(self, api_key):
            self.api_key = api_key
    
    # Read the resource
    try:
        result = await resource.read(MockContext(api_key))
        
        # Parse JSON if possible
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"content": result}
        
        return {"content": str(result)}
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        raise HTTPException(500, f"Error reading resource: {str(e)}")

# Endpoints
@app.get("/v1/tools")
async def list_tools(authorization: str = Header(...)):
    """List available MCP tools."""
    server = get_server()
    tools = []
    for tool in server.tools:
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": str(tool.inputSchema) if hasattr(tool, 'inputSchema') else {}
        })
    return tools

@app.get("/v1/resources")
async def list_resources(authorization: str = Header(...)):
    """List available MCP resources."""
    server = get_server()
    resources = []
    for resource in server.resources:
        resources.append({
            "uri": resource.uri,
            "name": resource.name,
            "description": resource.description,
            "mimeType": getattr(resource, 'mimeType', 'application/json')
        })
    return resources

@app.get("/v1/resources/devices")
async def list_devices(
    authorization: str = Header(...),
    status: Optional[str] = None
):
    """List all devices."""
    result = await read_mcp_resource("devices://", authorization)
    
    # Filter by status if provided
    if status and isinstance(result, dict) and 'items' in result:
        result['items'] = [d for d in result['items'] if d.get('status') == status]
    
    return result

@app.get("/v1/resources/device/{device_id}")
async def get_device(device_id: str, authorization: str = Header(...)):
    """Get device details."""
    # First get all devices then filter
    devices = await read_mcp_resource("devices://", authorization)
    
    if isinstance(devices, dict) and 'items' in devices:
        for device in devices['items']:
            if device.get('id') == device_id:
                return device
    
    raise HTTPException(404, f"Device {device_id} not found")

@app.post("/v1/tools/send_command")
async def send_command(request: CommandRequest, authorization: str = Header(...)):
    """Send command to a device."""
    args = {
        "device_id": request.device_id,
        "command": request.command
    }
    if request.args:
        args["args"] = json.dumps(request.args)
    
    return await call_mcp_tool("send_command", args, authorization)

@app.post("/v1/tools/update_device")
async def update_device(request: DeviceUpdateRequest, authorization: str = Header(...)):
    """Update device configuration."""
    args = {"device_id": request.device_id}
    
    if request.name:
        args["name"] = request.name
    if request.location:
        args["location"] = request.location
    if request.metadata:
        args["metadata"] = json.dumps(request.metadata)
    
    return await call_mcp_tool("update_device", args, authorization)

@app.get("/v1/resources/tickets")
async def list_tickets(
    authorization: str = Header(...),
    status: Optional[str] = None
):
    """List tickets."""
    result = await read_mcp_resource("tickets://", authorization)
    
    # Filter by status if provided
    if status and isinstance(result, dict) and 'items' in result:
        result['items'] = [t for t in result['items'] if t.get('status') == status]
    
    return result

@app.post("/v1/tools/update_ticket")
async def update_ticket(request: TicketUpdateRequest, authorization: str = Header(...)):
    """Update a ticket."""
    args = {"ticket_id": request.ticket_id}
    
    if request.status:
        args["status"] = request.status
    if request.comment:
        args["comment"] = request.comment
    
    return await call_mcp_tool("update_ticket", args, authorization)

@app.get("/v1/healthz")
async def health_check():
    """Health check endpoint."""
    return "ok"

@app.get("/v1/openapi.json")
async def get_openapi():
    """Get OpenAPI schema."""
    # Return the schema with dynamic server URL
    with open("chatgpt-openapi.json", "r") as f:
        schema = json.load(f)
    return schema

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081,  # Different port from main MCP
        log_level=settings.log_level.lower()
    )