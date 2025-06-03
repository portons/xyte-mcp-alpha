import os
from celery import Celery

celery_app = Celery(
    "xyte_mcp",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv(
        "RESULT_BACKEND_URL",
        os.getenv("DATABASE_URL", "postgresql+asyncpg://mcp:pass@127.0.0.1/mcp"),
    ),
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={"xyte_mcp_alpha.worker.long.*": {"queue": "long"}},
)
