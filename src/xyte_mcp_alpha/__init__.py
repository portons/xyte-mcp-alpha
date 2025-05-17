"""xyte-mcp-alpha package."""

from dotenv import load_dotenv

from .server import get_server
from .config import get_settings

load_dotenv()

__version__ = "1.0.0"
__all__ = ["get_server", "get_settings", "__version__"]


def serve():
    """Entry point for serving the MCP server."""
    import asyncio
    from mcp.server.stdio import stdio_server

    server = get_server()
    asyncio.run(stdio_server(server))
