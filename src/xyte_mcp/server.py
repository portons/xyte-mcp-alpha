"""MCP server for Xyte Organization API."""

import logging
import sys
import os
import json
from typing import Any, Dict, TYPE_CHECKING
import inspect
from starlette.applications import Starlette
from xyte_mcp.auth_xyte import RequireXyteKey

# Fix import paths for mcp dev
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import everything using absolute imports
import xyte_mcp.plugin as plugin
from xyte_mcp.config import get_settings, validate_settings
from xyte_mcp.events import push_event, pull_event
from mcp.server.fastmcp.server import Context
from xyte_mcp.logging_utils import instrument, request_var
import xyte_mcp.resources as resources
import xyte_mcp.tools as tools
import xyte_mcp.tasks as tasks
import xyte_mcp.prompts as prompts

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mcp.server.fastmcp.resources.types import FunctionResource, Resource
import pydantic_core

# ---------------------------------------------------------------------------
# Patch FunctionResource.read
# ---------------------------------------------------------------------------

async def _patched_function_resource_read(self: FunctionResource) -> str | bytes:
    """Patched version that awaits decorated coroutine functions."""
    try:
        result = self.fn()
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, Resource):
            return await result.read()
        if isinstance(result, bytes):
            return result
        if isinstance(result, str):
            return result
        return pydantic_core.to_json(result, fallback=str, indent=2).decode()
    except Exception as exc:  # pragma: no cover - passthrough errors
        raise ValueError(f"Error reading resource {self.uri}: {exc}")

FunctionResource.read = _patched_function_resource_read  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - optional dependency typing
    from fastapi import FastAPI  # type: ignore
else:  # pragma: no cover - fallback when fastapi is absent
    FastAPI = Any  # type: ignore

# Delay logging configuration until runtime
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")

# Starlette application with per-request Xyte key middleware
# Disable access logging
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn").disabled = True

app = Starlette()
app.add_middleware(RequireXyteKey)

# Optional Swagger UI using FastAPI
settings = get_settings()
if settings.enable_swagger:
    try:
        from fastapi import FastAPI  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        logging.getLogger(__name__).warning("FastAPI not installed; Swagger disabled")
    else:
        fast = FastAPI(openapi_url="/openapi.json", docs_url="/docs")
        fast.mount("", app)
        app = fast

# Initialize MCP server
mcp = FastMCP(
    name="Xyte MCP",
    instructions="Live Xyte API (devices/tickets/incidents). Use search tool. ALWAYS start queries with type:<devices|tickets|incidents>."
)


@mcp.custom_route("/healthz", methods=["GET"])
async def health(_: Request) -> Response:
    """Liveness probe."""
    return Response("ok")


@mcp.custom_route("/readyz", methods=["GET"])
async def ready(_: Request) -> Response:
    """Readiness probe."""
    return Response("ok")


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(_: Request) -> Response:
    """Expose Prometheus metrics."""
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)


@mcp.custom_route("/config", methods=["GET"])
async def config_endpoint(request: Request) -> JSONResponse:
    """Return sanitized configuration for debugging purposes."""
    settings = get_settings()
    api_key = request.headers.get("Authorization") or request.headers.get("X-API-Key")
    if settings.multi_tenant or api_key != settings.xyte_api_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    cfg = settings.model_dump()
    cfg["xyte_api_key"] = "***"
    return JSONResponse({"config": cfg})


@mcp.custom_route("/webhook", methods=["POST"])
async def webhook(req: Request) -> JSONResponse:
    """Receive external events and enqueue them for streaming."""
    payload = await req.json()
    await push_event(
        {
            "type": payload.get("type", "unknown"),
            "data": payload.get("data", {}),
        }
    )
    return JSONResponse({"queued": True})


@mcp.custom_route("/events", methods=["GET"])
async def stream_events(_: Request) -> Response:
    """Stream events to clients using Server-Sent Events."""

    import uuid

    async def event_gen():
        consumer = str(uuid.uuid4())
        while True:
            ev = await pull_event(consumer)
            if ev:
                yield f"event: {ev['type']}\ndata: {json.dumps(ev['data'])}\n\n"

    return Response(event_gen(), media_type="text/event-stream")


@mcp.custom_route("/tools", methods=["GET"])
async def list_tools(_: Request) -> JSONResponse:
    """List available tools."""
    tool_infos = await mcp.list_tools()
    tools_list = [
        {
            "name": t.name,
            "description": t.description,
            "readOnlyHint": t.annotations.readOnlyHint if t.annotations else True,
            "destructiveHint": (t.annotations.destructiveHint if t.annotations else False),
        }
        for t in tool_infos
    ]
    return JSONResponse(tools_list)


@mcp.custom_route("/resources", methods=["GET"])
async def list_resources_route(_: Request) -> JSONResponse:
    """List available resources."""
    resources_list = [
        {"uri": str(r.uri), "name": r.name, "description": r.description}
        for r in await mcp.list_resources()
    ]
    return JSONResponse(resources_list)


@mcp.custom_route("/devices", methods=["GET"])
async def list_devices_route(request: Request) -> JSONResponse:
    """Compatibility endpoint returning all devices."""
    devices = await resources.list_devices(request)
    return JSONResponse(devices)


def _req() -> Request | None:
    """Return the current request if available, otherwise ``None``."""
    return request_var.get()


async def _list_devices_wrapper() -> Dict[str, Any]:
    return await resources.list_devices(_req())


async def _list_device_commands_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.list_device_commands(_req(), device_id)


async def _list_device_histories_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.list_device_histories(_req(), device_id)


async def _device_status_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.device_status(_req(), device_id)




async def _organization_info_wrapper(device_id: str) -> Dict[str, Any]:
    return await resources.organization_info(_req(), device_id)


async def _list_incidents_wrapper() -> Dict[str, Any]:
    return await resources.list_incidents(_req())


async def _list_tickets_wrapper() -> Dict[str, Any]:
    return await resources.list_tickets(_req())


async def _get_ticket_wrapper(ticket_id: str) -> Dict[str, Any]:
    return await resources.get_ticket(_req(), ticket_id)


async def _get_prefs_wrapper(user_token: str) -> Dict[str, Any]:
    return await resources.get_user_preferences(_req(), user_token)


async def _list_user_devices_wrapper(user_token: str) -> Any:
    return await resources.list_user_devices(_req(), user_token)


# Resource registrations
mcp.resource("devices://", description="List all devices")(
    instrument("resource", "list_devices")(_list_devices_wrapper)
)
mcp.resource(
    "device://{device_id}/commands",
    description="Commands issued to a device",
)(instrument("resource", "list_device_commands")(_list_device_commands_wrapper))
mcp.resource(
    "device://{device_id}/histories",
    description="History records for a device",
)(instrument("resource", "list_device_histories")(_list_device_histories_wrapper))
mcp.resource(
    "device://{device_id}/status",
    description="Current status of a device",
)(instrument("resource", "device_status")(_device_status_wrapper))
if get_settings().enable_experimental_apis:
    async def _device_logs_wrapper(device_id: str) -> Dict[str, Any]:
        return await resources.device_logs(_req(), device_id)

    mcp.resource(
        "device://{device_id}/logs",
        description="Recent logs for a device",
    )(
        instrument("resource", "device_logs")(_device_logs_wrapper)
    )
mcp.resource(
    "organization://info/{device_id}",
    description="Organization info for a device",
)(instrument("resource", "organization_info")(_organization_info_wrapper))
mcp.resource("incidents://", description="Current incidents")(
    instrument("resource", "list_incidents")(_list_incidents_wrapper)
)
mcp.resource("tickets://", description="All support tickets")(
    instrument("resource", "list_tickets")(_list_tickets_wrapper)
)
mcp.resource("ticket://{ticket_id}", description="Single support ticket")(
    instrument("resource", "get_ticket")(_get_ticket_wrapper)
)
mcp.resource(
    "user://{user_token}/preferences",
    description="Preferences for a user",
)(_get_prefs_wrapper)
mcp.resource(
    "user://{user_token}/devices",
    description="Devices filtered by user",
)(_list_user_devices_wrapper)

# Tool registrations
mcp.tool(
        description="Register a new device",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "claim_device")(tools.claim_device))
mcp.tool(
    description="Remove a device from the organization",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "delete_device")(tools.delete_device))
mcp.tool(
    description="Update configuration for a device",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "update_device")(tools.update_device))
mcp.tool(
    description="Send a command to a device",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "send_command")(tools.send_command))
mcp.tool(
    description="Cancel a previously sent command",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "cancel_command")(tools.cancel_command))
mcp.tool(
    description="Update ticket details",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "update_ticket")(tools.update_ticket))
mcp.tool(
    description="Resolve a ticket",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "mark_ticket_resolved")(tools.mark_ticket_resolved))
mcp.tool(
    description="Send a message to a ticket",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "send_ticket_message")(tools.send_ticket_message))
mcp.tool(
    description="Search device history records",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(instrument("tool", "search_device_histories")(tools.search_device_histories))
mcp.tool(
    description="Retrieve usage analytics for a device",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(instrument("tool", "get_device_analytics_report")(tools.get_device_analytics_report))
mcp.tool(
    description="Set context defaults",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "set_context")(tools.set_context))
mcp.tool(
    description="Find and control a device with natural language hints",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "find_and_control_device")(tools.find_and_control_device))
mcp.tool(
    description="Diagnose an AV issue in a room",
        annotations=ToolAnnotations(readOnlyHint=True),
    )(instrument("tool", "diagnose_av_issue")(tools.diagnose_av_issue))
mcp.tool(
    description="Start meeting room preset",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "start_meeting_room_preset")(tools.start_meeting_room_preset))
mcp.tool(
    description="Shutdown meeting room",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )(instrument("tool", "shutdown_meeting_room")(tools.shutdown_meeting_room))
mcp.tool(
    description="Log automation attempt",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "log_automation_attempt")(tools.log_automation_attempt))
mcp.tool(
    description="Echo a message back",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )(instrument("tool", "echo_command")(tools.echo_command))

# Store for fetch tool - maps IDs to full objects
_search_cache: Dict[str, Dict[str, Any]] = {}

# Search tool required by ChatGPT
async def search(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Search Xyte's API for devices, tickets, and incidents using structured queries.
    
    CRITICAL: This is an API, NOT a file system. Do NOT search for files like .json or .csv.
    
    Query DSL Specification:
    • Tokens separated by spaces
    • Each token: key[:op]:value
      - key ∈ { type, q|query, status, severity, priority, model, name, id }
      - op (optional; default "eq") ∈ { eq, neq, contains }
      - value: unquoted or quoted (for spaces)
    
    • Semantics:
      - type (MANDATORY) → resource type: devices, tickets, or incidents
      - q/query → free-text search across all fields
      - status → filter by status (online/offline for devices, open/closed for tickets)
      - severity → filter by severity (critical/major/minor - incidents only)
      - priority → filter by priority (high/medium/low - tickets only)
      - model → filter by device model (devices only)
      - name → filter by name field
      - id → filter by exact ID
    
    EXAMPLES:
    
    user: analyze all incidents
    query: type:incidents
    
    user: show me critical incidents
    query: type:incidents severity:critical
    
    user: find offline devices
    query: type:devices status:offline
    
    user: search tickets mentioning password reset
    query: type:tickets q:"password reset"
    
    user: list all devices with model XY-100
    query: type:devices model:XY-100
    
    user: show high priority open tickets
    query: type:tickets status:open priority:high
    
    user: find major incidents
    query: type:incidents severity:major
    
    user: search for conference room devices
    query: type:devices name:contains:"Conference Room"
    
    INVALID queries (DO NOT USE):
    - incidents.json
    - incident records  
    - XYTE incident
    - 2023 incident
    
    Returns array of results with id, title, text, and url for each matching resource.
    """
    # Check ChatGPT mode at runtime
    CHATGPT_MODE = os.environ.get("CHATGPT_MODE", "false").lower() == "true"
    logger.info(f"[SEARCH] CHATGPT_MODE={CHATGPT_MODE}, Received query: '{query}' (type: {type(query)})")
    
    # In ChatGPT mode, fail immediately if query doesn't start with type:
    if CHATGPT_MODE:
        if not query or query is None:
            raise ValueError("query MUST be: type:incidents OR type:devices OR type:tickets")
        
        query = str(query).strip()
        if not query.startswith('type:'):
            raise ValueError(f"INVALID QUERY '{query}'. MUST be: type:incidents OR type:devices OR type:tickets")
    
    try:
        # Handle null/empty queries
        if not query or query is None:
            logger.warning("[SEARCH] Received null/empty query")
            return {
                "results": [{
                    "id": "error_empty_query",
                    "title": "Empty Query",
                    "text": "Query cannot be empty. Use format: type:incidents, type:devices, or type:tickets",
                    "url": None
                }]
            }
        
        # Convert to string if needed
        query = str(query).strip()
        logger.info(f"[SEARCH] Processed query: '{query}'")
        
        results = []
        
        # Validate query format
        if 'type:' not in query:
            return {
                "results": [{
                    "id": "error_invalid_query",
                    "title": "Invalid Query Format",
                    "text": f"Query must start with type:<resource>. You sent: '{query}'. Valid examples: type:incidents, type:devices status:offline, type:tickets q:password",
                    "url": None
                }]
            }
        
        # Clear previous cache
        _search_cache.clear()
        
        # Parse query DSL
        tokens = query.split()
        filters = {}
        resource_type = None
        free_text = None
        
        for token in tokens:
            if ':' in token:
                parts = token.split(':', 2)
                if len(parts) >= 2:
                    key = parts[0]
                    op = 'eq'
                    value = parts[1]
                    
                    # Handle operator
                    if len(parts) == 3:
                        op = parts[1]
                        value = parts[2]
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    if key == 'type':
                        resource_type = value.lower()
                    elif key in ['q', 'query']:
                        free_text = value.lower()
                    else:
                        filters[key] = {'op': op, 'value': value.lower()}
        
        # Validate resource type
        if not resource_type:
            if CHATGPT_MODE:
                raise ValueError("MANDATORY: query must specify type. Use: type:devices, type:tickets, or type:incidents")
            return {
                "results": [{
                    "id": "error_missing_type",
                    "title": "Missing Resource Type",
                    "text": "Query must specify type. Valid types: devices, tickets, incidents. Example: type:incidents",
                    "url": None
                }]
            }
        
        if resource_type not in ['devices', 'tickets', 'incidents', 'all']:
            if CHATGPT_MODE:
                raise ValueError(f"Invalid type '{resource_type}'. MANDATORY: Use type:devices, type:tickets, or type:incidents")
            return {
                "results": [{
                    "id": "error_invalid_type",
                    "title": "Invalid Resource Type",
                    "text": f"Invalid type '{resource_type}'. Valid types: devices, tickets, incidents",
                    "url": None
                }]
            }
        
        # Search devices
        if resource_type in ['all', 'devices']:
            devices = await resources.list_devices(_req())
            logger.info(f"[SEARCH] Devices API response: {json.dumps(devices, default=str)[:500]}")
            
            # Handle both wrapped and unwrapped responses
            device_list = []
            if isinstance(devices, dict):
                if "items" in devices:
                    device_list = devices["items"]
                elif "devices" in devices:
                    device_list = devices["devices"]
                elif "data" in devices:
                    # Check if data contains devices
                    if isinstance(devices["data"], list):
                        device_list = devices["data"]
                    elif isinstance(devices["data"], dict) and "devices" in devices["data"]:
                        device_list = devices["data"]["devices"]
                    elif isinstance(devices["data"], dict) and "items" in devices["data"]:
                        device_list = devices["data"]["items"]
                elif isinstance(devices.get("data"), list):
                    device_list = devices["data"]
            elif isinstance(devices, list):
                device_list = devices
            
            logger.info(f"[SEARCH] Processing {len(device_list)} devices")
            
            for device in device_list:
                    # Apply filters
                    match = True
                    
                    # Free text search
                    if free_text:
                        searchable_text = " ".join([
                            str(device.get("id", "")),
                            str(device.get("name", "")),
                            str(device.get("model", "")),
                            str(device.get("serial_number", "")),
                        ]).lower()
                        if free_text not in searchable_text:
                            match = False
                    
                    # Apply specific filters
                    for field, filter_info in filters.items():
                        field_value = str(device.get(field, "")).lower()
                        filter_value = filter_info['value']
                        op = filter_info['op']
                        
                        if op == 'eq' and field_value != filter_value:
                            match = False
                        elif op == 'neq' and field_value == filter_value:
                            match = False
                        elif op == 'contains' and filter_value not in field_value:
                            match = False
                    
                    if match:
                        result_id = f"device_{device.get('id')}"
                        _search_cache[result_id] = device
                        results.append({
                            "id": result_id,
                            "title": f"Device: {device.get('name', 'Unknown')}",
                            "text": f"Model: {device.get('model', 'N/A')}, Serial: {device.get('serial_number', 'N/A')}, Status: {device.get('status', 'Unknown')}",
                            "url": f"/devices/{device.get('id')}" if device.get('id') else None
                        })
        
        # Search tickets
        if resource_type in ['all', 'tickets']:
            tickets = await resources.list_tickets(_req())
            logger.info(f"[SEARCH] Tickets API response: {json.dumps(tickets, default=str)[:500]}")
            
            # Handle both wrapped and unwrapped responses
            ticket_list = []
            if isinstance(tickets, dict):
                if "items" in tickets:
                    ticket_list = tickets["items"]
                elif "tickets" in tickets:
                    ticket_list = tickets["tickets"]
                elif "data" in tickets:
                    # Check if data contains tickets
                    if isinstance(tickets["data"], list):
                        ticket_list = tickets["data"]
                    elif isinstance(tickets["data"], dict) and "tickets" in tickets["data"]:
                        ticket_list = tickets["data"]["tickets"]
                    elif isinstance(tickets["data"], dict) and "items" in tickets["data"]:
                        ticket_list = tickets["data"]["items"]
                elif isinstance(tickets.get("data"), list):
                    ticket_list = tickets["data"]
            elif isinstance(tickets, list):
                ticket_list = tickets
            
            logger.info(f"[SEARCH] Processing {len(ticket_list)} tickets")
            
            for ticket in ticket_list:
                    match = True
                    
                    if free_text:
                        searchable_text = " ".join([
                            str(ticket.get("id", "")),
                            str(ticket.get("title", "")),
                            str(ticket.get("description", "")),
                        ]).lower()
                        if free_text not in searchable_text:
                            match = False
                    
                    for field, filter_info in filters.items():
                        field_value = str(ticket.get(field, "")).lower()
                        filter_value = filter_info['value']
                        op = filter_info['op']
                        
                        if op == 'eq' and field_value != filter_value:
                            match = False
                        elif op == 'neq' and field_value == filter_value:
                            match = False
                        elif op == 'contains' and filter_value not in field_value:
                            match = False
                    
                    if match:
                        result_id = f"ticket_{ticket.get('id')}"
                        _search_cache[result_id] = ticket
                        results.append({
                            "id": result_id,
                            "title": f"Ticket: {ticket.get('title', 'Unknown')}",
                            "text": f"Status: {ticket.get('status', 'N/A')}, Priority: {ticket.get('priority', 'N/A')}, Description: {ticket.get('description', 'No description')[:100]}...",
                            "url": f"/tickets/{ticket.get('id')}" if ticket.get('id') else None
                        })
        
        # Search incidents
        if resource_type in ['all', 'incidents']:
            incidents = await resources.list_incidents(_req())
            logger.info(f"[SEARCH] Incidents API response: {json.dumps(incidents, default=str)[:500]}")
            
            # Handle both wrapped and unwrapped responses
            incident_list = []
            if isinstance(incidents, dict):
                logger.info(f"[SEARCH DEBUG] incidents is dict with keys: {list(incidents.keys())}")
                if "items" in incidents:
                    incident_list = incidents["items"]
                    logger.info(f"[SEARCH DEBUG] Found 'items' key, extracted {len(incident_list)} incidents")
                elif "incidents" in incidents:
                    incident_list = incidents["incidents"]
                    logger.info(f"[SEARCH DEBUG] Found 'incidents' key, extracted {len(incident_list)} incidents")
                elif "data" in incidents:
                    # Check if data contains incidents
                    if isinstance(incidents["data"], list):
                        incident_list = incidents["data"]
                        logger.info(f"[SEARCH DEBUG] Found 'data' key with list, extracted {len(incident_list)} incidents")
                    elif isinstance(incidents["data"], dict) and "incidents" in incidents["data"]:
                        incident_list = incidents["data"]["incidents"]
                        logger.info(f"[SEARCH DEBUG] Found 'data.incidents' key, extracted {len(incident_list)} incidents")
                    elif isinstance(incidents["data"], dict) and "items" in incidents["data"]:
                        incident_list = incidents["data"]["items"]
                        logger.info(f"[SEARCH DEBUG] Found 'data.items' key, extracted {len(incident_list)} incidents")
                elif isinstance(incidents.get("data"), list):
                    incident_list = incidents["data"]
                    logger.info(f"[SEARCH DEBUG] Found 'data' key with list (via get), extracted {len(incident_list)} incidents")
                else:
                    logger.warning(f"[SEARCH DEBUG] Dict but no recognized keys. Keys: {list(incidents.keys())}")
            elif isinstance(incidents, list):
                incident_list = incidents
                logger.info(f"[SEARCH DEBUG] incidents is a list, extracted {len(incident_list)} incidents")
            else:
                logger.warning(f"[SEARCH DEBUG] incidents is neither dict nor list: {type(incidents)}")
            
            logger.info(f"[SEARCH] Processing {len(incident_list)} incidents")
            
            for idx, incident in enumerate(incident_list):
                    logger.info(f"[SEARCH DEBUG] Processing incident {idx}: {json.dumps(incident, default=str)[:200]}")
                    match = True
                    
                    if free_text:
                        # Use uuid instead of id for incidents
                        searchable_text = " ".join([
                            str(incident.get("uuid", "")),
                            str(incident.get("id", "")),
                            str(incident.get("title", "")),
                            str(incident.get("description", "")),
                        ]).lower()
                        if free_text not in searchable_text:
                            match = False
                    
                    for field, filter_info in filters.items():
                        field_value = str(incident.get(field, "")).lower()
                        filter_value = filter_info['value']
                        op = filter_info['op']
                        
                        if op == 'eq' and field_value != filter_value:
                            match = False
                        elif op == 'neq' and field_value == filter_value:
                            match = False
                        elif op == 'contains' and filter_value not in field_value:
                            match = False
                    
                    if match:
                        # Use uuid as the identifier for incidents
                        incident_id = incident.get('uuid') or incident.get('id') or f"unknown_{idx}"
                        result_id = f"incident_{incident_id}"
                        _search_cache[result_id] = incident
                        logger.info(f"[SEARCH DEBUG] Adding incident to results: {result_id}")
                        # Handle None description properly
                        description = incident.get('description') or 'No description'
                        results.append({
                            "id": result_id,
                            "title": f"Incident: {incident.get('title', 'Unknown')}",
                            "text": f"Priority: {incident.get('priority', 'N/A')}, Status: {incident.get('status', 'N/A')}, Description: {description[:100]}...",
                            "url": f"/incidents/{incident_id}"
                        })
        
        # Return full results for ChatGPT deep research
        logger.info(f"[SEARCH] Returning {len(results)} results")
        return {"results": results}
    
    except Exception as e:
        logger.error(f"[SEARCH] Exception in search: {e}", exc_info=True)
        if CHATGPT_MODE:
            # Re-raise for ChatGPT to see the error
            raise
        return {
            "results": [{
                "id": "error_exception",
                "title": "Search Error",
                "text": f"An error occurred: {str(e)}. Please use format: type:incidents, type:devices, or type:tickets",
                "url": None
            }]
        }

# Fetch tool required by ChatGPT
async def fetch(ctx: Context, id: str) -> Dict[str, Any]:
    """
    Retrieves detailed content for a specific resource identified by the given ID.
    """
    # Check cache first
    if id not in _search_cache:
        raise ValueError(f"Unknown id: {id}")
    
    obj = _search_cache[id]
    
    # Determine type and format response
    if id.startswith("device_"):
        return {
            "id": id,
            "title": f"Device: {obj.get('name', 'Unknown')}",
            "text": json.dumps(obj, indent=2),
            "url": f"/devices/{obj.get('id')}" if obj.get('id') else None,
            "metadata": {
                "type": "device",
                "model": obj.get("model", ""),
                "serial_number": obj.get("serial_number", ""),
                "status": obj.get("status", ""),
                "organization_id": str(obj.get("organization_id", ""))
            }
        }
    elif id.startswith("ticket_"):
        return {
            "id": id,
            "title": f"Ticket: {obj.get('title', 'Unknown')}",
            "text": json.dumps(obj, indent=2),
            "url": f"/tickets/{obj.get('id')}" if obj.get('id') else None,
            "metadata": {
                "type": "ticket",
                "status": obj.get("status", ""),
                "priority": obj.get("priority", ""),
                "created_at": obj.get("created_at", "")
            }
        }
    elif id.startswith("incident_"):
        return {
            "id": id,
            "title": f"Incident: {obj.get('title', 'Unknown')}",
            "text": json.dumps(obj, indent=2),
            "url": f"/incidents/{obj.get('id')}" if obj.get('id') else None,
            "metadata": {
                "type": "incident",
                "severity": obj.get("severity", ""),
                "status": obj.get("status", ""),
                "created_at": obj.get("created_at", "")
            }
        }
    else:
        raise ValueError(f"Unknown resource type for id: {id}")

# Wrapper function to preserve the 'search' name
async def search_wrapper(ctx: Context, query: str) -> Dict[str, Any]:
    """Wrapper to ensure tool is named 'search'."""
    return await search(ctx, query)

# Wrapper function to preserve the 'fetch' name
async def fetch_wrapper(ctx: Context, id: str) -> Dict[str, Any]:
    """Wrapper to ensure tool is named 'fetch'."""
    return await fetch(ctx, id)

# Register search and fetch tools
mcp.tool(
    name="search",
    description=(
        "STRUCTURED SEARCH — NOT FILES.\n"
        "ALWAYS start with type:<devices|tickets|incidents>\n\n"
        "Examples:\n"
        "• type:incidents\n"
        "• type:incidents severity:critical\n"
        "• type:devices status:offline\n"
        "• type:tickets q:\"password reset\"\n\n"
        "Syntax: type:<resource> [field[:op]:value ...]\n"
        "Ops: eq (default), neq, contains\n"
        "Fields: status, severity, priority, model, name, id, q (free text)"
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
)(instrument("tool", "search")(search_wrapper))

mcp.tool(
    name="fetch",
    description="Fetch full details for an object previously returned by search.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
)(instrument("tool", "fetch")(fetch_wrapper))

# Tool wrappers for common resources
async def list_all_devices_tool(ctx: Context) -> Dict[str, Any]:
    """List all devices in the organization."""
    return await resources.list_devices(_req())

async def list_incidents_tool(ctx: Context) -> Dict[str, Any]:
    """Get current incidents in the system."""
    return await resources.list_incidents(_req())

async def list_tickets_tool(ctx: Context) -> Dict[str, Any]:
    """List all support tickets."""
    return await resources.list_tickets(_req())

async def get_device_status_tool(ctx: Context, device_id: str) -> Dict[str, Any]:
    """Get current status of a specific device."""
    return await resources.device_status(_req(), device_id)

async def get_device_commands_tool(ctx: Context, device_id: str) -> Dict[str, Any]:
    """Get commands issued to a specific device."""
    return await resources.list_device_commands(_req(), device_id)

async def get_device_histories_tool(ctx: Context, device_id: str) -> Dict[str, Any]:
    """Get history records for a specific device."""
    return await resources.list_device_histories(_req(), device_id)

mcp.tool(
    description="List all devices in the organization",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "list_devices")(list_all_devices_tool))
mcp.tool(
    description="Get current incidents",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_incidents")(list_incidents_tool))
mcp.tool(
    description="List all support tickets",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "list_tickets")(list_tickets_tool))
mcp.tool(
    description="Get device status by ID",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_device_status")(get_device_status_tool))
mcp.tool(
    description="Get device command history",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_device_commands")(get_device_commands_tool))
mcp.tool(
    description="Get device history records",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_device_histories")(get_device_histories_tool))
mcp.tool(
    description="Send a command asynchronously",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)(tasks.send_command_async)
mcp.tool(
    description="Get status of an asynchronous task",
    annotations=ToolAnnotations(readOnlyHint=True),
)(tasks.get_task_status)


@mcp.custom_route("/task/{task_id}", methods=["GET"])
async def task_status(request: Request) -> JSONResponse:
    """Expose async task status via HTTP."""
    tid = request.path_params.get("task_id", "")
    result = await tasks.get_task_status(tid)
    return JSONResponse(result)


# Create a wrapper function with explicit type annotation
async def get_next_event_wrapper(ctx: Context) -> Dict[str, Any]:
    """Return the next queued event for this context."""
    evt = await pull_event(ctx.request_id)
    return evt or {}


# Register the wrapper function as a tool
mcp.tool(
    description="Retrieve the next queued event",
    annotations=ToolAnnotations(readOnlyHint=True),
)(instrument("tool", "get_next_event")(get_next_event_wrapper))

# Prompt registrations
mcp.prompt()(prompts.reboot_device_workflow)
mcp.prompt()(prompts.check_projectors_health)
mcp.prompt()(prompts.proactive_projector_maintenance_check)
mcp.prompt()(prompts.troubleshoot_offline_device_workflow)


def get_server() -> Any:
    """Get the MCP server instance."""
    settings = get_settings()
    validate_settings(settings)

    # Check if we're in ChatGPT mode
    CHATGPT_MODE = os.environ.get("CHATGPT_MODE", "false").lower() == "true"
    
    if CHATGPT_MODE:
        logger.info(f"[CHATGPT_MODE] Starting in ChatGPT mode")
        # In ChatGPT mode, create a minimal server with only search and fetch
        chatgpt_mcp = FastMCP(
            name="Xyte MCP",
            instructions="ONLY use: type:incidents OR type:devices OR type:tickets"
        )
        
        # Register only search and fetch for ChatGPT
        chatgpt_mcp.tool(
            name="search",
            description="query MUST be: type:incidents OR type:devices OR type:tickets",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
        )(instrument("tool", "search")(search_wrapper))
        
        chatgpt_mcp.tool(
            name="fetch",
            description="Fetch full details for an object returned by search.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
        )(instrument("tool", "fetch")(fetch_wrapper))
        
        # Add custom routes
        chatgpt_mcp.custom_route("/healthz", methods=["GET"])(health)
        chatgpt_mcp.custom_route("/readyz", methods=["GET"])(ready)
        chatgpt_mcp.custom_route("/metrics", methods=["GET"])(metrics)
        chatgpt_mcp.custom_route("/config", methods=["GET"])(config_endpoint)
        chatgpt_mcp.custom_route("/webhook", methods=["POST"])(webhook)
        chatgpt_mcp.custom_route("/events", methods=["GET"])(stream_events)
        chatgpt_mcp.custom_route("/tools", methods=["GET"])(list_tools)
        chatgpt_mcp.custom_route("/resources", methods=["GET"])(list_resources_route)
        chatgpt_mcp.custom_route("/devices", methods=["GET"])(list_devices_route)
        
        return chatgpt_mcp
    
    # Normal mode - load all plugins and tools
    plugin.load_plugins()
    if get_settings().enable_experimental_apis:
        from .experimental import echo

        mcp.tool(
            description="Echo a message (experimental)",
            annotations=ToolAnnotations(readOnlyHint=True),
        )(instrument("tool", "experimental_echo")(echo))

    return mcp


def main() -> None:
    """Main entry point for MCP server."""
    # Suppress all stdout output during initialization
    import sys
    original_stdout = sys.stdout
    sys.stdout = sys.stderr
    
    try:
        server = get_server()
        # Restore stdout only for MCP protocol
        sys.stdout = original_stdout
        server.run(transport="stdio")
    except Exception as e:
        sys.stderr.write(f"Server error: {e}\n")
        sys.exit(1)


# Allow direct execution for development
if __name__ == "__main__":
    main()
