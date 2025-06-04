#!/usr/bin/env python3
"""Dead simple MCP runner that ensures clean stdio."""

if __name__ == "__main__":
    # Before ANY imports, redirect ALL output to stderr
    import sys
    import os
    
    # Save original stdout
    original_stdout = sys.stdout
    
    # Redirect stdout to stderr
    sys.stdout = sys.stderr
    
    # Disable all env vars that might cause output
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    # Now safe to import
    from xyte_mcp_alpha.server import mcp
    
    # Restore stdout for MCP protocol
    sys.stdout = original_stdout
    
    # Run it
    mcp.run(transport="stdio")