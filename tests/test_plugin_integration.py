import os
import logging
import unittest

os.environ.setdefault("XYTE_API_KEY", "test")
from xyte_mcp_alpha import plugin, events
from xyte_mcp_alpha.logging_utils import log_json

class PluginHookTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ["XYTE_PLUGINS"] = "tests.helper_plugin"
        plugin._PLUGINS.clear()  # type: ignore[attr-defined]
        plugin.load_plugins()
        # clear state
        import tests.helper_plugin as helper
        helper.received_events.clear()
        helper.received_logs.clear()

    async def test_event_and_log_hooks(self):
        await events.push_event(events.Event(type="test", data={"a": 1}))
        log_json(logging.INFO, test="log")

        import tests.helper_plugin as helper
        self.assertTrue(helper.received_events)
        self.assertTrue(helper.received_logs)

if __name__ == "__main__":
    unittest.main()
