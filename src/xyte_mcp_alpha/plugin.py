import importlib
import logging
import os
from typing import Any, List, Protocol

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
        except Exception:  # pragma: no cover - plugin loading should not fail tests
            logging.exception("Failed to load plugin %s", path)


def fire_event(event: dict) -> None:
    """Dispatch an event to all loaded plugins."""
    for plugin in list(_PLUGINS):
        hook = getattr(plugin, "on_event", None)
        if hook:
            try:
                hook(event)
            except Exception:
                logging.exception("Plugin error in on_event")


def fire_log(message: str, level: int) -> None:
    """Dispatch a log message to all loaded plugins."""
    for plugin in list(_PLUGINS):
        hook = getattr(plugin, "on_log", None)
        if hook:
            try:
                hook(message, level)
            except Exception:
                logging.exception("Plugin error in on_log")
