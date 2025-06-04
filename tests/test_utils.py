import os
import unittest

from xyte_mcp.utils import (
    enforce_rate_limit,
    MCPError,
    _REQUEST_TIMESTAMPS,
    convert_device_id,
)


class RateLimitTestCase(unittest.TestCase):
    def setUp(self):
        _REQUEST_TIMESTAMPS.clear()
        os.environ["XYTE_RATE_LIMIT"] = "1"
        from xyte_mcp.config import get_settings
        get_settings.cache_clear()

    def test_enforce_rate_limit(self):
        enforce_rate_limit()  # first call ok
        with self.assertRaises(MCPError) as cm:
            enforce_rate_limit()
        self.assertEqual(cm.exception.code, "rate_limited")


class ConvertIdTestCase(unittest.TestCase):
    def test_convert_device_id_missing(self):
        with self.assertRaises(MCPError) as cm:
            convert_device_id(None)
        self.assertEqual(cm.exception.code, "invalid_device_id")


if __name__ == "__main__":
    unittest.main()
