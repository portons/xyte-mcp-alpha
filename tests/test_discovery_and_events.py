import os
import asyncio
import unittest
from starlette.testclient import TestClient

os.environ.setdefault("XYTE_API_KEY", "test")
from xyte_mcp import http as http_mod
import importlib
from xyte_mcp import events
from tests.dummy_redis import DummyRedis


class DiscoveryEventTestCase(unittest.TestCase):
    def setUp(self):
        importlib.reload(http_mod)
        self.client = TestClient(http_mod.app)
        events.redis = DummyRedis()

    def test_tool_and_resource_listing(self):
        resp = self.client.get("/v1/tools")
        self.assertEqual(resp.status_code, 200)
        tools = resp.json()
        self.assertTrue(any(t["name"] == "claim_device" for t in tools))

        resp = self.client.get("/v1/resources")
        self.assertEqual(resp.status_code, 200)
        resources_list = resp.json()
        self.assertTrue(any(r["uri"] == "devices://" for r in resources_list))

    def test_event_flow(self):
        payload = {"type": "device_offline", "data": {"id": "abc"}}
        resp = self.client.post("/v1/webhook", json=payload)
        self.assertEqual(resp.status_code, 200)

        async def wait_event():
            return await asyncio.wait_for(events.pull_event("test"), 1)

        event = asyncio.run(wait_event())
        assert event is not None
        self.assertEqual(event["data"]["id"], "abc")


if __name__ == "__main__":
    unittest.main()
