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
from .auth import AuthHeaderMiddleware
from starlette.middleware.cors import CORSMiddleware


def build_openapi(app: Starlette) -> Dict[str, Any]:
    """Return a minimal OpenAPI schema describing the mounted routes."""

    paths: Dict[str, Any] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        if path:
            paths["/v1" + path] = {}
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
cors_origins = ["*"] if settings.allow_all_cors else []
internal_app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
internal_app.add_middleware(AuthHeaderMiddleware)

routes = [Mount("/v1", app=internal_app)]

app = Starlette(routes=routes)

# Optional Swagger UI using FastAPI
if settings.enable_swagger:
    try:
        from .swagger_setup import create_documented_app
    except ImportError:
        import logging
        logging.getLogger(__name__).warning("FastAPI not installed; Swagger disabled")
    else:
        app = create_documented_app(app)


async def openapi_spec(request) -> JSONResponse:
    schema = build_openapi(internal_app)
    return JSONResponse(schema)


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

app.add_route("/v1/openapi.json", openapi_spec, methods=["GET"])
app.add_route("/v1/docs", api_docs, methods=["GET"])


def main() -> None:
    """Run the HTTP server using Uvicorn."""
    import uvicorn

    settings = get_settings()
    import os
    
    # Use PORT env var if available (for Render), otherwise use settings
    port = int(os.environ.get("PORT", settings.mcp_inspector_port))
    
    # Always bind to 0.0.0.0 in production environments like Render
    host = "0.0.0.0" if os.environ.get("PORT") else settings.mcp_inspector_host
    
    uvicorn.run(
        "xyte_mcp.http:app",
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()
