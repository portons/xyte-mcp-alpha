from __future__ import annotations

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

from .config import get_settings


class AuthHeaderMiddleware(BaseHTTPMiddleware):
    """Validate Authorization header depending on deployment mode."""

    def __init__(self, app: Any) -> None:  # type: ignore[override]
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {
            "/healthz",
            "/readyz",
            "/metrics",
            "/v1/healthz",
            "/v1/readyz",
            "/v1/metrics",
        }:
            return await call_next(request)

        header = request.headers.get("authorization")
        env_key = self.settings.xyte_api_key

        if env_key is None:
            if not header or not header.strip():
                return JSONResponse({"error": "missing_xyte_key"}, status_code=401)
            request.state.xyte_key = header.strip()
            return await call_next(request)

        if header:
            if header.strip() != env_key:
                return JSONResponse({"error": "invalid_token"}, status_code=403)
            request.state.xyte_key = header.strip()

        return await call_next(request)
