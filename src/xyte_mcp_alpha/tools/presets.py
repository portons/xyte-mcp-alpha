from pathlib import Path
import yaml  # type: ignore[import-untyped]

from ..models import CommandRequest, ToolResponse
from ..deps import get_client
from mcp.server.fastmcp.server import Context


async def start_meeting_room_preset(
    room: str, preset: str = "default", ctx: Context | None = None
) -> ToolResponse:
    """Power on and configure all devices for the given room preset."""
    f = Path(__file__).resolve().parent.parent / "presets" / f"{preset}.yaml"
    steps = yaml.safe_load(f.read_text())
    async with get_client() as client:
        for step in steps:
            cmd = CommandRequest(
                name=step["command"],
                friendly_name=step["command"],
                file_id=None,
                extra_params={},
            )
            await client.send_command(step["device_id"], cmd)
    return ToolResponse(summary=f"{len(steps)} commands executed", data={"room": room})
