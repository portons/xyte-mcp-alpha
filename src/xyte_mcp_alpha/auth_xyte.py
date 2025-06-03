import hashlib
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_PUBLIC = {"/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"}


class RequireXyteKey(BaseHTTPMiddleware):
    """Middleware enforcing presence of per-request Xyte API key."""

    async def dispatch(self, req, call_next):
        if req.url.path in _PUBLIC:
            return await call_next(req)

        raw = req.headers.get("x-xyte-api-key") or (
            req.headers.get("authorization") or ""
        ).removeprefix("Bearer ")
        if not raw:
            return JSONResponse({"error": "missing_xyte_key"}, 401)
        if len(raw.strip()) < 32:
            return JSONResponse({"error": "invalid_xyte_key"}, 403)

        req.state.xyte_key = raw.strip()
        req.state.key_id = hashlib.sha256(raw.encode()).hexdigest()[:8]

        from xyte_mcp_alpha.rate_limiter import consume

        if not await consume(req.state.key_id, limit=60):
            return JSONResponse({"error": "rate_limit"}, 429)

        return await call_next(req)


class AuthHeaderMiddleware(BaseHTTPMiddleware):
    """Require Authorization header when running in multi-tenant mode."""

    def __init__(self, app):
        super().__init__(app)
        from .config import get_settings

        self.settings = get_settings()

    async def dispatch(self, req, call_next):
        if req.url.path in {
            "/healthz",
            "/readyz",
            "/metrics",
            "/v1/healthz",
            "/v1/readyz",
            "/v1/metrics",
        }:
            return await call_next(req)

        header = req.headers.get("authorization")
        if self.settings.multi_tenant and not header:
            return JSONResponse({"error": "missing_xyte_key"}, 401)
        if header:
            req.state.xyte_key = header.strip()
        return await call_next(req)
