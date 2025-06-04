import os
import unittest
from starlette.testclient import TestClient

from xyte_mcp import plugin, events
from xyte_mcp import http as http_mod
import importlib
from tests.dummy_redis import DummyRedis


class PluginHTTPIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["XYTE_PLUGINS"] = "tests.helper_plugin"
        plugin._PLUGINS.clear()  # type: ignore[attr-defined]
        plugin.load_plugins()
        import tests.helper_plugin as helper

        helper.received_events.clear()
        os.environ.setdefault("XYTE_API_KEY", "test")
        importlib.reload(http_mod)
        self.client = TestClient(http_mod.app)
        events.redis = DummyRedis()

    def test_webhook_triggers_plugin(self):
        payload = {"type": "test", "data": {"x": 1}}
        resp = self.client.post("/v1/webhook", json=payload)
        self.assertEqual(resp.status_code, 200)
        import tests.helper_plugin as helper

        self.assertTrue(helper.received_events)


if __name__ == "__main__":
    unittest.main()
