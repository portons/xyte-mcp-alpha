import pytest
import httpx

from xyte_mcp_alpha.server import app

transport = httpx.ASGITransport(app=app)
OK = {"X-XYTE-API-KEY": "X" * 40}

pytestmark = pytest.mark.anyio

@pytest.fixture
def anyio_backend():
    return "asyncio"

async def test_missing_key():
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/devices")
    assert r.status_code == 401

async def test_rate_limit(monkeypatch):
    async def deny(*a, **k):
        return False
    monkeypatch.setattr("xyte_mcp_alpha.rate_limiter.consume", deny)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/devices", headers=OK)
    assert r.status_code == 429
