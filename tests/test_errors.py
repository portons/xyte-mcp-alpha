import unittest
import httpx

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

if __name__ == "__main__":
    unittest.main()
