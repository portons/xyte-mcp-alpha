"""Simple plugin system used by the MCP server."""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
from typing import Iterable, List, Protocol

class MCPPlugin(Protocol):
    """Plugin interface for AI agent integration."""

    def on_event(self, event: dict) -> None:
        ...

    def on_log(self, message: str, level: int) -> None:
        ...


API_VERSION = 1

ENTRYPOINT_GROUP = "xyte_mcp_alpha.plugins"

_PLUGINS: List[MCPPlugin] = []


def validate_plugin(plugin: MCPPlugin) -> None:
    """Validate a plugin instance.

    A valid plugin implements at least one of ``on_event`` or ``on_log`` and has
    a compatible ``API_VERSION`` attribute if provided.
    """

    if not callable(getattr(plugin, "on_event", None)) and not callable(
        getattr(plugin, "on_log", None)
    ):
        raise ValueError("plugin missing required hooks")

    api_version = getattr(plugin, "API_VERSION", API_VERSION)
    if api_version != API_VERSION:
        raise ValueError("incompatible plugin API version")


def register_plugin(plugin: MCPPlugin) -> None:
    """Register a plugin instance after validation."""

    validate_plugin(plugin)
    _PLUGINS.append(plugin)


def _load_from_paths(paths: Iterable[str]) -> None:
    for path in paths:
        try:
            module = importlib.import_module(path)
            register_plugin(getattr(module, "plugin", module))
        except Exception:  # pragma: no cover - plugin loading should not fail tests
            logging.exception("Failed to load plugin %s", path)


def _load_from_entrypoints() -> None:
    try:
        eps = importlib.metadata.entry_points()
        group_eps = (
            eps.select(group=ENTRYPOINT_GROUP) if hasattr(eps, "select") else eps.get(ENTRYPOINT_GROUP, [])
        )
        for ep in group_eps:
            try:
                register_plugin(getattr(ep.load(), "plugin", ep.load()))
            except Exception:  # pragma: no cover - don't break on plugin errors
                logging.exception("Failed to load entry point plugin %s", ep.name)
    except Exception:  # pragma: no cover - optional feature
        logging.exception("Failed to discover entry point plugins")


def load_plugins(force_reload: bool = False) -> None:
    """Load plugins specified in ``XYTE_PLUGINS`` and entry points."""

    if force_reload:
        _PLUGINS.clear()

    env_paths = [p.strip() for p in os.getenv("XYTE_PLUGINS", "").split(",") if p.strip()]
    _load_from_paths(env_paths)
    _load_from_entrypoints()


def reload_plugins() -> None:
    """Clear existing plugins and reload them."""

    load_plugins(force_reload=True)


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
