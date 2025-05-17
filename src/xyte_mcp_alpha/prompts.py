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


def proactive_projector_maintenance_check() -> List[base.Message]:
    """Prompt to analyze projector usage and suggest maintenance."""
    return [
        base.UserMessage("List all projector devices."),
        base.UserMessage(
            "For each projector, call get_device_analytics_report with period='last_30_days'."
        ),
        base.UserMessage(
            "If lamp hours exceed 80% of expected lifespan, advise creating a support ticket for lamp replacement."
        ),
    ]


def troubleshoot_offline_device_workflow(device_id: str, room_name: str) -> List[base.Message]:
    """Detailed steps for recovering an offline device."""
    return [
        base.UserMessage(
            f"A user reports device {device_id} in room {room_name} is offline."
        ),
        base.UserMessage(
            f"Access resource device://{device_id}/status. If online, inform user."
        ),
        base.UserMessage(
            f"If offline, access device://{device_id}/histories for recent error events."
        ),
        base.UserMessage(
            f"Attempt send_command with name='reboot' to {device_id}. Wait 2 minutes."
        ),
        base.UserMessage(
            f"Re-check device://{device_id}/status. If still offline, create a ticket detailing steps taken and escalate."
        ),
    ]
