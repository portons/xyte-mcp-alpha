import os
import importlib.resources
from typing import Awaitable, cast
import redis.asyncio as aioredis

redis_client: aioredis.Redis = aioredis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0")
)
lua = (importlib.resources.files("xyte_mcp") / "bucket.lua").read_text()
SHA: Awaitable[str] = redis_client.script_load(lua)

async def consume(key_id: str, limit: int = 60) -> bool:
    sha = await SHA
    remain_raw = redis_client.evalsha(
        sha, 1, f"rl:{key_id}", str(limit), "60"
    )
    count = await cast(Awaitable[int], remain_raw)
    return count != 0
