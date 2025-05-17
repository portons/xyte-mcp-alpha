"""HTTP entrypoint for the MCP server."""
from .server import get_server

# Expose ASGI app for Uvicorn or other ASGI servers
app = get_server().asgi_app()


def main():
    """Run the HTTP server using Uvicorn."""
    import uvicorn
    uvicorn.run("xyte_mcp_alpha.http:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
