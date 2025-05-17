from collections import deque
import time
from typing import Callable
from starlette.responses import Response

class RateLimitMiddleware:
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app: Callable, limit_per_minute: int) -> None:
        self.app = app
        self.limit = limit_per_minute
        self.timestamps: deque[float] = deque()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        now = time.time()
        while self.timestamps and self.timestamps[0] < now - 60:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.limit:
            resp = Response("Rate limit exceeded", status_code=429)
            await resp(scope, receive, send)
            return
        self.timestamps.append(now)
        await self.app(scope, receive, send)
