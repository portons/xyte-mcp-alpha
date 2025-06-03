import os
import pytest
import httpx
from unittest.mock import patch

os.environ.pop("XYTE_API_KEY", None)

from xyte_mcp_alpha import http as http_mod

transport = httpx.ASGITransport(app=http_mod.app)
OK = {"Authorization": "X" * 40}

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    async def noop(self):
        return {}

    monkeypatch.setattr(
        "xyte_mcp_alpha.client.XyteAPIClient.get_devices", noop
    )


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, 401),
        ("Bearer test", 200),
    ],
)
async def test_multi_tenant_auth(header, expected):
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/v1/devices", headers={"Authorization": header} if header else None)
    assert r.status_code == expected


async def test_single_tenant_no_header(monkeypatch):
    os.environ["XYTE_API_KEY"] = "envkey"
    from importlib import reload
    from xyte_mcp_alpha.config import reload_settings

    reload_settings()
    reload(http_mod)
    transport2 = httpx.ASGITransport(app=http_mod.app)

    async with httpx.AsyncClient(transport=transport2, base_url="http://t") as c:
        r = await c.get("/v1/devices")
    assert r.status_code == 200


async def test_header_forwarding(monkeypatch):
    captured = {}

    class Dummy:
        def __init__(self, api_key=None, base_url=None):
            captured["key"] = api_key

        async def close(self):
            pass

        async def get_devices(self):
            return {}

    monkeypatch.setattr("xyte_mcp_alpha.deps.XyteAPIClient", Dummy)

    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        await c.get("/v1/devices", headers=OK)
    assert captured["key"] == "X" * 40


async def test_forwarding_single_tenant(monkeypatch):
    os.environ["XYTE_API_KEY"] = "envkey"
    from importlib import reload
    from xyte_mcp_alpha.config import reload_settings

    reload_settings()
    reload(http_mod)
    transport2 = httpx.ASGITransport(app=http_mod.app)

    captured = {}

    class Dummy:
        def __init__(self, api_key=None, base_url=None):
            captured["key"] = api_key

        async def close(self):
            pass

        async def get_devices(self):
            return {}

    monkeypatch.setattr("xyte_mcp_alpha.deps.XyteAPIClient", Dummy)

    async with httpx.AsyncClient(transport=transport2, base_url="http://t") as c:
        await c.get("/v1/devices")
    assert captured["key"] == "envkey"


async def test_rate_limit(monkeypatch):
    from starlette.responses import Response

    async def deny(self, scope, receive, send):
        resp = Response("Rate limit", status_code=429)
        await resp(scope, receive, send)

    monkeypatch.setattr(http_mod.RateLimitMiddleware, "__call__", deny)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/v1/devices", headers=OK)
    assert r.status_code == 429
