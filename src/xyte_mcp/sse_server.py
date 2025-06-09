"""SSE (Server-Sent Events) server for remote MCP access."""

import logging
import uvicorn
from .server import get_server
from .config import get_settings

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


if __name__ == "__main__":
    # Set up detailed logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting MCP SSE server with FastMCP SSE app")
    logger.info(f"Using API key from environment: {settings.xyte_api_key[:10]}..." if settings.xyte_api_key else "No API key found!")
    
    # Get the MCP server instance
    mcp_server = get_server()
    
    # Get the SSE app from FastMCP
    sse_app = mcp_server.sse_app()
    
    # Run with uvicorn
    uvicorn.run(
        sse_app,
        host="0.0.0.0",
        port=settings.mcp_inspector_port,
        log_level=settings.log_level.lower()
    )