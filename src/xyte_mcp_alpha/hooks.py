import importlib
import os
from typing import Any

_hooks = None


def _load_hooks():
    global _hooks
    if _hooks is not None:
        return _hooks
    module_path = os.getenv("XYTE_HOOKS_MODULE")
    if not module_path:
        _hooks = None
        return None
    try:
        _hooks = importlib.import_module(module_path)
    except Exception:
        _hooks = None
    return _hooks


def transform_request(name: str, payload: Any) -> Any:
    hooks = _load_hooks()
    if hooks and hasattr(hooks, "transform_request"):
        try:
            return hooks.transform_request(name, payload)
        except Exception:
            return payload
    return payload


def transform_response(name: str, payload: Any) -> Any:
    hooks = _load_hooks()
    if hooks and hasattr(hooks, "transform_response"):
        try:
            return hooks.transform_response(name, payload)
        except Exception:
            return payload
    return payload
