import os
import importlib.resources
import redis.asyncio as aioredis

redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
lua = (importlib.resources.files("xyte_mcp_alpha") / "bucket.lua").read_text()
SHA = redis.script_load(lua)

async def consume(key_id: str, limit: int = 60) -> bool:
    remain = await redis.evalsha(await SHA, 1, f"rl:{key_id}", limit, 60)
    return remain != 0
