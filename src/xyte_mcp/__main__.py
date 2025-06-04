"""Main entry point for xyte-mcp."""
# ruff: noqa: E402

from __future__ import annotations

import sys


from xyte_mcp.server import get_server



def main() -> None:
    """Launch the MCP server."""
    print("Starting Xyte MCP server...", file=sys.stderr)
    server = get_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()