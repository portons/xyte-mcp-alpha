#!/usr/bin/env python3
"""Standalone runner for OpenAI wrapper."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up minimal environment
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://mcp:pass@localhost/mcp')

if __name__ == "__main__":
    import uvicorn
    from xyte_mcp.openai_wrapper import app
    
    print("Starting OpenAI REST API wrapper...")
    print("Make sure XYTE_API_KEY is set in your environment")
    print("The wrapper will be available at http://localhost:8081")
    
    uvicorn.run(app, host="0.0.0.0", port=8081)