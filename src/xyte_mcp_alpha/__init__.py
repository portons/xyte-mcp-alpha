"""xyte-mcp-alpha package."""

from dotenv import load_dotenv

from .server import get_server
from .config import get_settings

load_dotenv()

load_dotenv()

__version__ = "0.1.0"
__all__ = ["get_server", "__version__"]


def serve():
    """Entry point for serving the MCP server."""
    import asyncio
    from mcp.server.stdio import stdio_server

    server = get_server()
    asyncio.run(stdio_server(server))
