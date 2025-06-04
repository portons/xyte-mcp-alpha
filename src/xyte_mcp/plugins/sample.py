from typing import Any, Dict
from ..utils import register_payload_transform

PLUGIN_API_VERSION = "1.0"

def add_transformed_flag(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload["transformed"] = True
    return payload

register_payload_transform(add_transformed_flag)
