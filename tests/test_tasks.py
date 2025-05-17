import asyncio
import unittest

from xyte_mcp_alpha import tasks
from xyte_mcp_alpha.models import SendCommandRequest


class DummyCtx:
    async def report_progress(self, current: int, total: int) -> None:
        pass


class TaskStatusTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_task_status_unknown(self):
        status = await tasks.get_task_status("missing")
        self.assertEqual(status["status"], "unknown")

    async def test_send_command_async(self):
        async def fake_send_command(device_id, data):
            return {"ok": True}

        class DummyClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

            async def send_command(self, device_id, data):
                return await fake_send_command(device_id, data)

        def get_client(*args, **kwargs):
            return DummyClient()

        original_get_client = tasks.get_client
        tasks.get_client = get_client  # type: ignore
        try:
            req = SendCommandRequest(device_id="1", name="ping", friendly_name="Ping")
            result = await tasks.send_command_async(req, DummyCtx())
            self.assertIn("task_id", result)
            status = await tasks.get_task_status(result["task_id"])
            # Wait a short time for background task
            await asyncio.sleep(0.1)
            status = await tasks.get_task_status(result["task_id"])
            self.assertEqual(status["status"], "done")
        finally:
            tasks.get_client = original_get_client  # type: ignore
            tasks.TASKS.clear()


if __name__ == "__main__":
    unittest.main()
