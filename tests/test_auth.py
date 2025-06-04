import os
import importlib

import httpx
import pytest

os.environ.pop("XYTE_API_KEY", None)

from xyte_mcp import http as http_mod
from xyte_mcp.config import reload_settings

transport = httpx.ASGITransport(app=http_mod.app)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    async def noop(self):
        return {}

    monkeypatch.setattr(
        "xyte_mcp.client.XyteAPIClient.get_devices", noop
    )


@pytest.mark.parametrize(
    "env_key,header,expected",
    [
        (None, None, 401),
        (None, "Bearer test", 200),
        ("envkey", None, 200),
        ("envkey", "wrong", 403),
    ],
)
async def test_auth_modes(env_key, header, expected, monkeypatch):
    if env_key is not None:
        os.environ["XYTE_API_KEY"] = env_key
    else:
        os.environ.pop("XYTE_API_KEY", None)
    reload_settings()
    importlib.reload(http_mod)
    transport2 = httpx.ASGITransport(app=http_mod.app)
    headers = {"Authorization": header} if header else None
    async with httpx.AsyncClient(transport=transport2, base_url="http://t") as c:
        r = await c.get("/v1/devices", headers=headers)
    assert r.status_code == expected
    os.environ.pop("XYTE_API_KEY", None)
    reload_settings()
    importlib.reload(http_mod)
