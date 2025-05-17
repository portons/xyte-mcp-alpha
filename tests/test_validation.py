import unittest

from xyte_mcp_alpha import resources
from xyte_mcp_alpha.utils import MCPError

class ValidationTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_device_id(self):
        with self.assertRaises(MCPError) as cm:
            await resources.list_device_commands("")
        self.assertEqual(cm.exception.code, "invalid_params")

if __name__ == "__main__":
    unittest.main()
