import json
import os
from pathlib import Path
from typing import Dict

DEFAULT_MAPPING: Dict[str, str] = {
    "get_devices": "/devices",
    "claim_device": "/devices/claim",
    "get_device": "/devices/{device_id}",
    "delete_device": "/devices/{device_id}",
    "update_device": "/devices/{device_id}",
    "get_device_histories": "/devices/histories",
    "get_device_analytics": "/devices/{device_id}/analytics",
    "send_command": "/devices/{device_id}/commands",
    "cancel_command": "/devices/{device_id}/commands/{command_id}",
    "get_commands": "/devices/{device_id}/commands",
    "get_organization_info": "/info",
    "get_incidents": "/incidents",
    "get_tickets": "/tickets",
    "get_ticket": "/tickets/{ticket_id}",
    "update_ticket": "/tickets/{ticket_id}",
    "mark_ticket_resolved": "/tickets/{ticket_id}/resolved",
    "send_ticket_message": "/tickets/{ticket_id}/message",
}


_def_mapping = None


def load_mapping() -> Dict[str, str]:
    """Load API mapping from JSON file if provided."""
    global _def_mapping
    if _def_mapping is not None:
        return _def_mapping
    mapping = DEFAULT_MAPPING.copy()
    path = os.getenv("XYTE_API_MAPPING")
    if path:
        try:
            data = json.loads(Path(path).read_text())
            if isinstance(data, dict):
                mapping.update({k: str(v) for k, v in data.items()})
        except Exception:
            pass
    _def_mapping = mapping
    return mapping
