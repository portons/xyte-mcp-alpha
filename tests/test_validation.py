import asyncio
import unittest

from xyte_mcp_alpha import resources
from xyte_mcp_alpha.utils import MCPError


class ValidationTestCase(unittest.TestCase):
    def test_invalid_device_id(self):
        import os
        os.environ.setdefault("XYTE_API_KEY", "test")
        async def run():
            try:
                await resources.list_device_commands("")
            except MCPError as exc:
                return exc.code
        code = asyncio.run(run())
        self.assertEqual(code, "invalid_params")


if __name__ == "__main__":
    unittest.main()
