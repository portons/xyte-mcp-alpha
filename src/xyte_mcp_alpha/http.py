"""HTTP entrypoint for the MCP server."""

from .server import get_server
from .logging_utils import RequestLoggingMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, HTMLResponse

# Expose ASGI app for Uvicorn or other ASGI servers
app = get_server().streamable_http_app()
app.add_middleware(RequestLoggingMiddleware)


@app.get("/openapi.json")
async def openapi_spec() -> JSONResponse:
    schema = get_openapi(title="Xyte MCP API", version="1.0", routes=app.routes)
    return JSONResponse(schema)


@app.get("/api/docs")
async def api_docs() -> HTMLResponse:
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Xyte MCP API")


def main():
    """Run the HTTP server using Uvicorn."""
    import uvicorn

    uvicorn.run("xyte_mcp_alpha.http:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
