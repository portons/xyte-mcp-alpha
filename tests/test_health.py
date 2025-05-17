import unittest
from starlette.testclient import TestClient

from xyte_mcp_alpha.http import app


class HealthEndpointTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_endpoints(self):
        for path in ['/healthz', '/readyz']:
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.text, 'ok')


if __name__ == '__main__':
    unittest.main()
