#!/usr/bin/env python
"""Run MCP server with HTTPS support."""

import sys
import os
import uvicorn

# Add the src directory to the path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

if __name__ == "__main__":
    # Check if certificates exist
    cert_file = "certs/localhost+2.pem"
    key_file = "certs/localhost+2-key.pem"
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("ERROR: SSL certificates not found!")
        print("Please run ./setup-https.sh first to generate certificates.")
        sys.exit(1)
    
    print("Starting HTTPS server on https://localhost:8080")
    
    uvicorn.run(
        "xyte_mcp.http:app",
        host="0.0.0.0",
        port=8080,
        ssl_keyfile=key_file,
        ssl_certfile=cert_file,
        reload=True,
        log_level="info"
    )