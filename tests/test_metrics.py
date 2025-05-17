import unittest
from starlette.testclient import TestClient

from xyte_mcp_alpha.http import app


class MetricsEndpointTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_metrics_endpoint(self):
        # trigger a simple request to generate metrics
        self.client.get('/v1/healthz')
        resp = self.client.get('/v1/metrics')
        self.assertEqual(resp.status_code, 200)
        data = resp.text
        # basic sanity checks that our metrics are present
        self.assertIn('xyte_http_requests_total', data)
        self.assertIn('xyte_http_request_latency_seconds', data)


if __name__ == '__main__':
    unittest.main()
