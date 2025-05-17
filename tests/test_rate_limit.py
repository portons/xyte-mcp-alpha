import os
import unittest

from xyte_mcp_alpha.utils import handle_api, MCPError, _REQUEST_TIMESTAMPS
from xyte_mcp_alpha.config import get_settings


class DummyClient:
    async def do(self):
        return {}


dummy = DummyClient()


class RateLimitTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limit_exceeded(self):
        os.environ["XYTE_RATE_LIMIT"] = "2"
        _REQUEST_TIMESTAMPS.clear()
        get_settings.cache_clear()

        await handle_api("dummy", dummy.do())
        await handle_api("dummy", dummy.do())
        coro = dummy.do()
        with self.assertRaises(MCPError) as cm:
            await handle_api("dummy", coro)
        coro.close()
        self.assertEqual(cm.exception.code, "rate_limited")


if __name__ == "__main__":
    unittest.main()
