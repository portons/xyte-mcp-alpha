"""xyte-mcp-alpha package."""

from dotenv import load_dotenv

from .server import get_server
from .config import get_settings, reload_settings
from .plugins import sample  # noqa: F401
from . import plugin
import signal


def _setup_reload() -> None:
    """Install SIGHUP handler to reload configuration."""

    def handler(_sig, _frame) -> None:
        reload_settings()
        plugin.reload_plugins()

    signal.signal(signal.SIGHUP, handler)


_setup_reload()

load_dotenv()

__version__ = "1.1.0"
__all__ = ["get_server", "get_settings", "__version__"]


def serve():
    """Entry point for serving the MCP server."""
    import asyncio
    from mcp.server.stdio import stdio_server

    server = get_server()
    asyncio.run(stdio_server(server))
