import unittest
from starlette.testclient import TestClient

from xyte_mcp_alpha.http import app


class MetricsEndpointTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_metrics_endpoint(self):
        resp = self.client.get('/metrics')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.text)


if __name__ == '__main__':
    unittest.main()
