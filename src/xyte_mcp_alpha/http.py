"""HTTP entrypoint for the MCP server with versioned routing."""

from __future__ import annotations

from typing import Any, Dict

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.responses import JSONResponse, HTMLResponse

from .server import get_server
from .logging_utils import RequestLoggingMiddleware
from .config import get_settings
from .http_utils import RateLimitMiddleware
from starlette.middleware.cors import CORSMiddleware


def build_openapi(app: Starlette) -> Dict[str, Any]:
    """Return a minimal OpenAPI schema describing the mounted routes."""

    paths: Dict[str, Any] = {}
    for route in app.routes:
        if hasattr(route, "path"):
            paths["/v1" + route.path] = {}
    return {
        "openapi": "3.0.0",
        "info": {"title": "Xyte MCP API", "version": "1.0"},
        "paths": paths,
    }


internal_app = get_server().streamable_http_app()
internal_app.add_middleware(RequestLoggingMiddleware)
settings = get_settings()
internal_app.add_middleware(
    RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute
)
internal_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

routes = [Mount("/v1", app=internal_app)]

app = Starlette(routes=routes)


@app.route("/v1/openapi.json")
async def openapi_spec(request) -> JSONResponse:
    schema = build_openapi(internal_app)
    return JSONResponse(schema)


@app.route("/v1/docs")
async def api_docs(request) -> HTMLResponse:
    html = """
    <html>
      <body>
        <h1>Xyte MCP API</h1>
        <p>OpenAPI specification available at <a href='/v1/openapi.json'>/v1/openapi.json</a></p>
      </body>
    </html>
    """
    return HTMLResponse(html)


def main():
    """Run the HTTP server using Uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run("xyte_mcp_alpha.http:app", host="0.0.0.0", port=settings.mcp_inspector_port)


if __name__ == "__main__":
    main()

