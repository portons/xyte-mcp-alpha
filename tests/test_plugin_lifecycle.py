import os
import unittest
from unittest import mock
import logging

from xyte_mcp_alpha import plugin, events
from xyte_mcp_alpha.logging_utils import log_json
from tests.dummy_redis import DummyRedis


class PluginLifecycleTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        plugin._PLUGINS.clear()  # type: ignore[attr-defined]
        import tests.helper_plugin as helper
        helper.received_events.clear()
        helper.received_logs.clear()
        events.redis = DummyRedis()

    async def test_reload_and_entrypoint_discovery(self):
        os.environ["XYTE_PLUGINS"] = ""

        class DummyEP:
            name = "helper"

            def load(self):
                import tests.helper_plugin as helper
                return helper.plugin

        eps = [DummyEP()]

        def fake_entry_points():
            class EPs(list):
                def select(self, group):
                    return eps if group == plugin.ENTRYPOINT_GROUP else []
            return EPs(eps)

        with mock.patch("importlib.metadata.entry_points", fake_entry_points):
            plugin.reload_plugins()

        await events.push_event(events.Event(type="ep", data={} ))
        log_json(logging.INFO, msg="test")

        import tests.helper_plugin as helper
        self.assertTrue(helper.received_events)
        self.assertTrue(helper.received_logs)

    async def test_invalid_plugin_skipped(self):
        os.environ["XYTE_PLUGINS"] = "tests.bad_plugin"
        plugin.reload_plugins()
        self.assertFalse(plugin._PLUGINS)


if __name__ == "__main__":
    unittest.main()
