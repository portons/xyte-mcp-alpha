"""HTTP entrypoint for the MCP server."""

from .server import get_server
from .logging_utils import RequestLoggingMiddleware
from .config import get_settings
from starlette.responses import JSONResponse, HTMLResponse
from starlette.requests import Request

# Expose ASGI app for Uvicorn or other ASGI servers
app = get_server().streamable_http_app()
app.add_middleware(RequestLoggingMiddleware)


async def openapi_spec(_: Request) -> JSONResponse:
    """Return a minimal OpenAPI schema."""
    schema = {"openapi": "3.0.0", "info": {"title": "Xyte MCP API", "version": "1.0"}}
    return JSONResponse(schema)


async def api_docs(_: Request) -> HTMLResponse:
    """Return a very small HTML docs placeholder."""
    html = "<html><body><pre>Xyte MCP API Docs</pre></body></html>"
    return HTMLResponse(html)


app.add_route("/openapi.json", openapi_spec, methods=["GET"])
app.add_route("/api/docs", api_docs, methods=["GET"])


def main():
    """Run the HTTP server using Uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run("xyte_mcp_alpha.http:app", host="0.0.0.0", port=settings.mcp_inspector_port)


if __name__ == "__main__":
    main()
