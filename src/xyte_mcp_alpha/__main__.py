"""Main entry point for xyte-mcp-alpha."""

import sys
import asyncio
import os

# Add the parent directory to the path to help with imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from xyte_mcp_alpha.server import get_server

def main():
    """Main function."""
    print("Starting Xyte MCP server...", file=sys.stderr)
    
    # Set up the server
    server = get_server()
    
    # Run the MCP server
    from mcp.server.stdio import stdio_server
    asyncio.run(stdio_server(server))


if __name__ == "__main__":
    main()