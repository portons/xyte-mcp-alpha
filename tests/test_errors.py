import unittest
import httpx
import pytest
from xyte_mcp_alpha.server import app

from xyte_mcp_alpha.utils import handle_api, MCPError

class ErrorMappingTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_http_status_error_mapping_invalid_params(self):
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(400, request=request, text="bad")
        exc = httpx.HTTPStatusError("bad", request=request, response=response)

        async def failing():
            raise exc

        with self.assertRaises(MCPError) as cm:
            await handle_api("test", failing())
        self.assertEqual(cm.exception.code, "invalid_params")

    async def test_request_error_mapping_network_error(self):
        request = httpx.Request("GET", "http://example.com")
        exc = httpx.ConnectError("boom", request=request)

        async def failing():
            raise exc

        with self.assertRaises(MCPError) as cm:
            await handle_api("test", failing())
        self.assertEqual(cm.exception.code, "network_error")

    async def test_http_status_device_not_found(self):
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(404, request=request, text="not found")
        exc = httpx.HTTPStatusError("missing", request=request, response=response)

        async def failing():
            raise exc

        with self.assertRaises(MCPError) as cm:
            await handle_api("get_device", failing())
        self.assertEqual(cm.exception.code, "device_not_found")


OK = {"X-XYTE-API-KEY": "X" * 40}


transport = httpx.ASGITransport(app=app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_missing_key():
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/devices")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_rate_limit(monkeypatch):
    async def deny(*a, **k):
        return False

    monkeypatch.setattr("xyte_mcp_alpha.rate_limiter.consume", deny)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/devices", headers=OK)
    assert r.status_code == 429

if __name__ == "__main__":
    unittest.main()
