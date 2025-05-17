"""Main entry point for xyte-mcp-alpha."""

import asyncio
import sys

from mcp.server.stdio import stdio_server

from .server import get_server


def main() -> None:
    """Start the MCP server via stdio."""
    print("Starting Xyte MCP server...", file=sys.stderr)
    server = get_server()
    asyncio.run(stdio_server(server))


if __name__ == "__main__":
    main()
