"""Simple plugin system used by the MCP server."""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
from typing import Iterable, List, Protocol, cast
from .logging_utils import log_json

PLUGIN_API_VERSION = "1.0"

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
            candidate = cast(MCPPlugin, getattr(module, "plugin", module))
            register_plugin(candidate)
        except Exception as exc:  # pragma: no cover - plugin loading should not fail tests
            log_json(logging.ERROR, event="plugin_load_error", plugin=path, error=str(exc))


def _load_from_entrypoints() -> None:
    try:
        eps = importlib.metadata.entry_points()
        if hasattr(eps, "select"):
            group_eps = eps.select(group=ENTRYPOINT_GROUP)
        else:
            # Handle older API - just return empty list if not found
            group_eps = eps.get(ENTRYPOINT_GROUP, [])  # type: ignore[arg-type]
        for ep in group_eps:
            try:
                candidate = cast(MCPPlugin, getattr(ep.load(), "plugin", ep.load()))
                register_plugin(candidate)
            except Exception as exc:  # pragma: no cover - don't break on plugin errors
                log_json(logging.ERROR, event="plugin_entry_point_error", plugin=ep.name, error=str(exc))
    except Exception as exc:  # pragma: no cover - optional feature
        log_json(logging.ERROR, event="plugin_discovery_error", error=str(exc))


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