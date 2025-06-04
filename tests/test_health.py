import os
import unittest
from starlette.testclient import TestClient

os.environ.setdefault("XYTE_API_KEY", "test")
from xyte_mcp import http as http_mod
import importlib


class HealthEndpointTestCase(unittest.TestCase):
    def setUp(self):
        importlib.reload(http_mod)
        self.client = TestClient(http_mod.app)

    def test_health_endpoint(self):
        resp = self.client.get("/v1/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "ok")

    def test_ready_endpoint(self):
        resp = self.client.get("/v1/readyz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "ok")


if __name__ == "__main__":
    unittest.main()
