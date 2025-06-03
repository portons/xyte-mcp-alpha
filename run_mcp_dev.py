#!/usr/bin/env python
"""Helper script to run the MCP server with proper imports."""

import sys
import os

# Add the src directory to the path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import the server
from xyte_mcp_alpha.server import get_server  # noqa: E402

# Export the server to be used by mcp dev
server = get_server()

if __name__ == "__main__":
    print("Use 'mcp dev run_mcp_dev.py' to start the server", file=sys.stderr)
