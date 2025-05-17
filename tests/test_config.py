import os
import unittest

from xyte_mcp_alpha.config import Settings, get_settings


class SettingsTestCase(unittest.TestCase):
    def test_load_settings_from_env(self):
        os.environ['XYTE_API_KEY'] = 'abc'
        os.environ['XYTE_BASE_URL'] = 'http://test'
        get_settings.cache_clear()
        s = Settings()
        self.assertEqual(s.xyte_api_key, 'abc')
        self.assertEqual(s.xyte_base_url, 'http://test')


if __name__ == '__main__':
    unittest.main()
