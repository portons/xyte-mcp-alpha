import asyncio
import unittest
from unittest.mock import patch

from sqlmodel import SQLModel, Session, create_engine

from xyte_mcp_alpha import tasks
from xyte_mcp_alpha.models import SendCommandRequest


class DummyCtx:
    def __init__(self) -> None:
        class ReqState:
            xyte_key = "X" * 40
        class Req:
            state = ReqState()
        class RC:
            request = Req()
        self.request_context = RC()

    async def report_progress(self, current: int, total: int, message: str | None = None) -> None:
        pass


class TaskStatusTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(self.engine)

        class DummyAsyncSession:
            def __init__(self, engine):
                self.session = Session(engine)

            async def merge(self, obj):
                self.session.merge(obj)

            async def commit(self):
                self.session.commit()

            async def get(self, model, pk):
                return self.session.get(model, pk)

            async def close(self):
                self.session.close()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def get_session():
            s = DummyAsyncSession(self.engine)
            try:
                yield s
            finally:
                await s.close()

        self.get_session_patch = patch("xyte_mcp_alpha.tasks.get_session", get_session)
        self.get_session_patch.start()

    async def asyncTearDown(self) -> None:
        self.get_session_patch.stop()
        self.engine.dispose()

    async def test_get_task_status_unknown(self):
        status = await tasks.get_task_status("missing")
        self.assertEqual(status["status"], "unknown")

    async def test_send_command_async(self):
        captured: dict = {}

        def fake_delay(tid: str, payload: dict, key: str) -> None:
            captured["tid"] = tid
            asyncio.get_event_loop().create_task(
                tasks.save(tasks.Task(id=tid, status="done", result={"ok": True}))
            )

        with patch("xyte_mcp_alpha.worker.long.send_command_long.delay", side_effect=fake_delay):
            ctx = DummyCtx()
            req = SendCommandRequest(
                device_id="1",
                name="ping",
                friendly_name="Ping",
                file_id=None,
            )
            resp = await tasks.send_command_async(req, ctx)
            tid = resp.data["task_id"]
            await asyncio.sleep(0.05)
            status = await tasks.get_task_status(tid)
            self.assertEqual(status["status"], "done")
            self.assertEqual(captured["tid"], tid)


if __name__ == "__main__":
    unittest.main()
