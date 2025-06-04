#!/usr/bin/env python3
"""Minimal MCP server to test stdout pollution."""

import sys
import os

# Redirect ALL output to stderr before any imports
sys.stdout = open(os.devnull, 'w')
original_stdout = sys.__stdout__

# Minimal imports
from mcp.server.fastmcp import FastMCP

# Create minimal server
mcp = FastMCP("TestServer")

@mcp.tool()
def test_tool() -> str:
    return "test"

# Restore stdout for protocol
sys.stdout.close()
sys.stdout = original_stdout

# Run
if __name__ == "__main__":
    mcp.run(transport="stdio")