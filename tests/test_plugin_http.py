import os
import unittest
from starlette.testclient import TestClient

from xyte_mcp_alpha import plugin
from xyte_mcp_alpha.http import app


class PluginHTTPIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["XYTE_PLUGINS"] = "tests.helper_plugin"
        plugin._PLUGINS.clear()  # type: ignore[attr-defined]
        plugin.load_plugins()
        import tests.helper_plugin as helper
        helper.received_events.clear()
        self.client = TestClient(app)

    def test_webhook_triggers_plugin(self):
        payload = {"type": "test", "data": {"x": 1}}
        resp = self.client.post("/v1/webhook", json=payload)
        self.assertEqual(resp.status_code, 200)
        import tests.helper_plugin as helper
        self.assertTrue(helper.received_events)


if __name__ == "__main__":
    unittest.main()
