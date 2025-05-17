import os
import unittest
from starlette.testclient import TestClient

os.environ.setdefault("XYTE_API_KEY", "secret")
from xyte_mcp_alpha.http import app
from xyte_mcp_alpha.config import get_settings


class ConfigEndpointTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["XYTE_API_KEY"] = "secret"
        get_settings.cache_clear()
        self.client = TestClient(app)

    def test_config_unauthorized(self):
        resp = self.client.get("/v1/config")
        self.assertEqual(resp.status_code, 401)

    def test_config_authorized(self):
        resp = self.client.get("/v1/config", headers={"X-API-Key": "secret"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["config"]
        self.assertEqual(data["xyte_api_key"], "***")


if __name__ == "__main__":
    unittest.main()
