from typing import List
from mcp.server.fastmcp.prompts import base


def reboot_device_workflow(device_id: str) -> List[base.Message]:
    """Workflow instructions for rebooting an unresponsive device."""
    return [
        base.UserMessage(
            f"Check available commands with resource device://{device_id}/commands"
        ),
        base.UserMessage(
            "If a reboot command exists, call the send_command tool with name='reboot'."
        ),
        base.UserMessage(
            f"Verify success via device://{device_id}/histories after execution."
        ),
    ]


def check_projectors_health() -> str:
    """Guide for checking health of all projectors."""
    return (
        "List devices with devices:// and filter for projectors. "
        "For each, inspect device histories via device://{device_id}/histories "
        "and check open incidents using incidents://."
    )
