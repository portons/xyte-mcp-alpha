"""Main entry point for xyte-mcp-alpha."""
# ruff: noqa: E402

from __future__ import annotations

import os
import sys


from xyte_mcp_alpha.server import get_server

from mcp.server.stdio import stdio_server


def main() -> None:
    """Launch the MCP server."""
    print("Starting Xyte MCP server...", file=sys.stderr)
    server = get_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()