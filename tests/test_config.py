import os
import unittest

from xyte_mcp_alpha.config import Settings, get_settings, validate_settings
from pydantic_settings import SettingsConfigDict


class SettingsTestCase(unittest.TestCase):
    def test_load_settings_from_env(self):
        os.environ["XYTE_API_KEY"] = "abc"
        os.environ["XYTE_BASE_URL"] = "http://test"
        os.environ["XYTE_CACHE_TTL"] = "30"
        os.environ["XYTE_RATE_LIMIT"] = "10"
        get_settings.cache_clear()
        s = Settings()
        self.assertEqual(s.xyte_api_key, "abc")
        self.assertEqual(s.xyte_base_url, "http://test")
        self.assertEqual(s.xyte_cache_ttl, 30)
        self.assertEqual(s.rate_limit_per_minute, 10)

    def test_missing_required_api_key(self):
        os.environ.pop("XYTE_API_KEY", None)
        os.environ.pop("XYTE_OAUTH_TOKEN", None)
        get_settings.cache_clear()

        # Create a settings class with no env file
        class TestSettings(Settings):
            model_config = SettingsConfigDict(env_file=None, case_sensitive=False)

        settings = TestSettings()
        with self.assertRaises(ValueError):
            validate_settings(settings)


if __name__ == "__main__":
    unittest.main()
