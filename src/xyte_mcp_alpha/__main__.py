"""Main entry point for xyte-mcp-alpha."""
# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys

from mcp.server.stdio import stdio_server

from xyte_mcp_alpha.server import get_server

# Add the parent directory to the path to help with imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def main() -> None:
    """Launch the MCP server."""
    print("Starting Xyte MCP server...", file=sys.stderr)
    server = get_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
