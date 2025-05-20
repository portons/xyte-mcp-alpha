"""Common utility tool implementations."""

import logging
import json
from pathlib import Path # For log_automation_attempt
from typing import Optional

from ..utils import get_session_state, MCPError, validate_device_id
from ..models import ToolResponse # Assuming ToolResponse remains in models for now
from mcp.server.fastmcp.server import Context # For type hinting

# Pydantic models will be defined here if specific, otherwise imported or standard types used.
# For the tools being moved, they primarily use basic types or the common ToolResponse.

logger = logging.getLogger(__name__)


async def set_context(
    device_id: Optional[str] = None,
    space_id: Optional[str] = None,
    ctx: Context | None = None,
) -> ToolResponse:
    """Set session context defaults for subsequent tool calls."""
    if ctx is None:
        raise MCPError(code="missing_context", message="Context required")

    state = get_session_state(ctx)
    if device_id is not None:
        state["current_device_id"] = device_id
    if space_id is not None:
        state["current_space_id"] = space_id

    return ToolResponse(data=state, summary="Context updated")


async def log_automation_attempt(
    workflow_name: str,
    device_id: str, # validate_device_id could be used here if strict validation is needed
    steps_taken: list[str],
    outcome: str,
    user_feedback: Optional[str] = None,
    error_details: Optional[str] = None,
    ctx: Context | None = None, # Added ctx as per original definition in device.py
) -> ToolResponse:
    """Record the result of an automated workflow."""
    entry = {
        "workflow_name": workflow_name,
        "device_id": device_id,
        "steps_taken": steps_taken,
        "outcome": outcome,
        "user_feedback": user_feedback,
        "error_details": error_details,
    }
    # Using logger instead of direct file write for better practice,
    # but sticking to original file writing logic for now.
    path = Path("logs") / "automation.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    # The original also had: logger.info("automation_attempt", extra=entry)
    # Replicating the original `log_json` call from tools.py (which was then removed from tools/device.py)
    # For now, I'll use a standard logger.info call as log_json is not available here.
    logger.info(f"Automation attempt logged: {entry}")
    if ctx:
        await ctx.info("Automation attempt logged")
    return ToolResponse(data=entry, summary="Attempt recorded")


async def echo_command(device_id: str, message: str) -> ToolResponse:
    """Example command that echoes a message back."""
    validate_device_id(device_id) # Requires validate_device_id from ..utils
    # Replicating the original `log_json` call from tools.py (which was then removed from tools/device.py)
    # Using standard logger.info for now.
    logger.info(f"Echo command called for device {device_id} with message: {message}")
    return ToolResponse(data={"device_id": device_id, "echo": message})

# Check imports:
# import logging (used)
# import json (used)
# from pathlib import Path (used)
# from typing import Optional (used)
# from ..utils import get_session_state, MCPError, validate_device_id (used)
# from ..models import ToolResponse (used)
# from mcp.server.fastmcp.server import Context (used)
