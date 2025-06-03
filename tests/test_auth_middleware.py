import pytest
import httpx

from xyte_mcp_alpha import http as http_mod

transport = httpx.ASGITransport(app=http_mod.app)
OK = {"Authorization": "X" * 40}

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_missing_key():
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/v1/devices")
    assert r.status_code == 401


async def test_rate_limit(monkeypatch):
    from starlette.responses import Response

    async def deny(self, scope, receive, send):
        resp = Response("Rate limit", status_code=429)
        await resp(scope, receive, send)

    monkeypatch.setattr(http_mod.RateLimitMiddleware, "__call__", deny)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/v1/devices", headers=OK)
    assert r.status_code == 429
