#!/usr/bin/env python3
"""Minimal MCP server test to diagnose the issue."""

import sys
import os

# Ensure all output goes to stderr during initialization
sys.stdout = sys.stderr

# Set required env var
if not os.environ.get('XYTE_API_KEY'):
    os.environ['XYTE_API_KEY'] = 'test'

# Now restore stdout for MCP protocol
sys.stdout = sys.__stdout__

# Import and run
from xyte_mcp_alpha.server import get_server

if __name__ == "__main__":
    server = get_server()
    server.run(transport="stdio")