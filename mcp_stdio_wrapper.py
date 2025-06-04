#!/usr/bin/env python3
"""MCP stdio wrapper that ensures clean stdout for Claude Desktop."""

import sys
import os

# CRITICAL: Redirect ALL stdout to stderr before ANY imports
# This must happen before any module imports that might print
original_stdout = sys.stdout
sys.stdout = sys.stderr

# Now we can safely import
try:
    # Suppress all logging during import
    import logging
    logging.disable(logging.CRITICAL)
    
    # Set environment to suppress any startup messages
    os.environ['PYTHONWARNINGS'] = 'ignore'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # In case TensorFlow is used
    
    # Import the server
    from xyte_mcp_alpha.server import get_server
    
    # Re-enable logging but only to stderr
    logging.disable(logging.NOTSET)
    
    # Restore stdout for MCP protocol
    sys.stdout = original_stdout
    
    # Run the server
    server = get_server()
    server.run(transport="stdio")
    
except Exception as e:
    # Any errors go to stderr
    sys.stderr.write(f"Error: {e}\n")
    sys.exit(1)