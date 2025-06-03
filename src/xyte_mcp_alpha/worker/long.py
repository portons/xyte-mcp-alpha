import asyncio
from xyte_mcp_alpha.celery_app import celery_app
from xyte_mcp_alpha.tasks import save, Task
from xyte_mcp_alpha.client import XyteAPIClient


@celery_app.task(name="xyte_mcp_alpha.worker.long.send_command")
def send_command_long(task_id: str, payload: dict, xyte_key: str) -> None:
    async def _run() -> None:
        await save(Task(id=task_id, status="running"))
        client = XyteAPIClient(api_key=xyte_key)
        try:
            result = await client.send_command(**payload)
            await save(Task(id=task_id, status="done", result=result))
        except Exception as exc:  # pragma: no cover - best effort
            await save(Task(id=task_id, status="error", result={"msg": str(exc)}))
        finally:
            await client.close()

    asyncio.run(_run())
