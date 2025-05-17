"""xyte-mcp-alpha package."""

from __future__ import annotations

import signal
from types import FrameType

from dotenv import load_dotenv

from .server import get_server
from .config import get_settings, reload_settings
from .plugins import sample  # noqa: F401


def _setup_reload() -> None:
    """Install SIGHUP handler to reload configuration."""

    def handler(_sig: int, _frame: FrameType | None) -> None:
        reload_settings()

    signal.signal(signal.SIGHUP, handler)


_setup_reload()

load_dotenv()

__version__ = "1.1.0"
__all__ = ["get_server", "get_settings", "__version__"]


def serve() -> None:
    """Entry point for serving the MCP server."""
    import asyncio
    from mcp.server.stdio import stdio_server

    server = get_server()
    asyncio.run(stdio_server(server))
