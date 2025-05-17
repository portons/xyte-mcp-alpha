import importlib
import logging
import os
from typing import List, Protocol
from .logging_utils import log_json

class MCPPlugin(Protocol):
    """Plugin interface for AI agent integration."""

    def on_event(self, event: dict) -> None:
        ...

    def on_log(self, message: str, level: int) -> None:
        ...

_PLUGINS: List[MCPPlugin] = []


def load_plugins() -> None:
    """Load plugins specified in the ``XYTE_PLUGINS`` environment variable."""
    paths = os.getenv("XYTE_PLUGINS", "")
    for path in [p.strip() for p in paths.split(",") if p.strip()]:
        try:
            module = importlib.import_module(path)
            plugin = getattr(module, "plugin", module)
            if hasattr(plugin, "on_event") or hasattr(plugin, "on_log"):
                _PLUGINS.append(plugin)  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - plugin loading should not fail tests
            log_json(logging.ERROR, event="plugin_load_error", plugin=path, error=str(exc))


def fire_event(event: dict) -> None:
    """Dispatch an event to all loaded plugins."""
    for plugin in list(_PLUGINS):
        hook = getattr(plugin, "on_event", None)
        if hook:
            try:
                hook(event)
            except Exception as exc:
                log_json(logging.ERROR, event="plugin_event_error", error=str(exc))


def fire_log(message: str, level: int) -> None:
    """Dispatch a log message to all loaded plugins."""
    for plugin in list(_PLUGINS):
        hook = getattr(plugin, "on_log", None)
        if hook:
            try:
                hook(message, level)
            except Exception as exc:
                log_json(logging.ERROR, event="plugin_log_error", error=str(exc))
