import asyncio
import unittest
from starlette.testclient import TestClient

from xyte_mcp_alpha.http import app
from xyte_mcp_alpha import events


class DiscoveryEventTestCase(unittest.TestCase):
    def setUp(self):
        import os
        os.environ.setdefault("XYTE_API_KEY", "test")
        self.client = TestClient(app)
        # Clear event queue
        while not events._event_queue.empty():
            events._event_queue.get_nowait()

    def test_tool_and_resource_listing(self):
        resp = self.client.get('/v1/tools')
        self.assertEqual(resp.status_code, 200)
        tools = resp.json()
        self.assertTrue(any(t['name'] == 'claim_device' for t in tools))

        resp = self.client.get('/v1/resources')
        self.assertEqual(resp.status_code, 200)
        resources_list = resp.json()
        self.assertTrue(any(r['uri'] == 'devices://' for r in resources_list))

    def test_event_flow(self):
        payload = {"type": "device_offline", "data": {"id": "abc"}}
        resp = self.client.post('/v1/webhook', json=payload)
        self.assertEqual(resp.status_code, 200)

        async def wait_event():
            return await asyncio.wait_for(
                events.get_next_event(events.GetNextEventRequest(event_type="device_offline")),
                1,
            )

        event = asyncio.run(wait_event())
        self.assertEqual(event['data']['id'], 'abc')


if __name__ == '__main__':
    unittest.main()
