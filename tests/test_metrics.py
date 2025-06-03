import os
import unittest
from starlette.testclient import TestClient

os.environ.setdefault("XYTE_API_KEY", "test")
from xyte_mcp_alpha import http as http_mod
import importlib


class MetricsEndpointTestCase(unittest.TestCase):
    def setUp(self):
        importlib.reload(http_mod)
        self.client = TestClient(http_mod.app)

    def test_metrics_endpoint(self):
        # trigger a simple request to generate metrics
        self.client.get("/v1/healthz")
        resp = self.client.get("/v1/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.text
        # basic sanity checks that our metrics are present
        self.assertIn("xyte_http_requests_total", data)
        self.assertIn("xyte_http_request_latency_seconds", data)


if __name__ == "__main__":
    unittest.main()
