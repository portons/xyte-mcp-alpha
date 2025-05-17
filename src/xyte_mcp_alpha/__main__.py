"""Main entry point for xyte-mcp-alpha."""

from __future__ import annotations

import asyncio
import sys

from mcp.server.stdio import stdio_server

from xyte_mcp_alpha.server import get_server


def main() -> None:
    """Launch the MCP server."""
    print("Starting Xyte MCP server...", file=sys.stderr)
    server = get_server()
    asyncio.run(stdio_server(server))


if __name__ == "__main__":
    main()
