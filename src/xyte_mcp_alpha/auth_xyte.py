import hashlib
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_PUBLIC = {"/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"}

class RequireXyteKey(BaseHTTPMiddleware):
    """Middleware enforcing presence of per-request Xyte API key."""

    async def dispatch(self, req, call_next):
        if req.url.path in _PUBLIC:
            return await call_next(req)

        raw = (
            req.headers.get("x-xyte-api-key")
            or (req.headers.get("authorization") or "").removeprefix("Bearer ")
        )
        if not raw:
            return JSONResponse({"error": "missing_xyte_key"}, 401)
        if len(raw.strip()) < 32:
            return JSONResponse({"error": "invalid_xyte_key"}, 403)

        req.state.xyte_key = raw.strip()
        req.state.key_id = hashlib.sha256(raw.encode()).hexdigest()[:8]
        return await call_next(req)
