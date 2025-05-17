import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable, Awaitable
from functools import wraps
from prometheus_client import Histogram

# Context variable to store request ID for each incoming request
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application-wide structured logging."""
    logging.basicConfig(level=level, format="%(message)s")


def log_json(level: int, **fields: Any) -> None:
    """Log a JSON-formatted message, injecting the request ID if present."""
    request_id = request_id_var.get()
    if request_id is not None:
        fields.setdefault("request_id", request_id)
    logging.getLogger("xyte_mcp_alpha").log(level, json.dumps(fields))


class RequestLoggingMiddleware:
    """ASGI middleware that logs requests and responses."""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        token = request_id_var.set(request_id)
        method = scope.get("method")
        path = scope.get("path")
        start = time.monotonic()

        log_json(logging.INFO, event="request_start", method=method, path=path, request_id=request_id)

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status = message["status"]
                log_json(logging.INFO, event="response_start", status=status, request_id=request_id)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                duration_ms = (time.monotonic() - start) * 1000
                log_json(
                    logging.INFO,
                    event="request_complete",
                    duration_ms=round(duration_ms),
                    request_id=request_id,
                )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)


# Prometheus metrics for tools and resources

TOOL_LATENCY = Histogram("xyte_tool_latency_seconds", "Latency of tool handlers", ["tool"])
RESOURCE_LATENCY = Histogram(
    "xyte_resource_latency_seconds", "Latency of resource handlers", ["resource"]
)


def instrument(kind: str, name: str):
    """Decorator to log and measure execution of tools and resources."""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            log_json(logging.INFO, event=f"{kind}_start", name=name)
            try:
                return await func(*args, **kwargs)
            except Exception:
                log_json(logging.ERROR, event=f"{kind}_error", name=name)
                raise
            finally:
                duration = time.monotonic() - start
                log_json(
                    logging.INFO,
                    event=f"{kind}_complete",
                    name=name,
                    duration_ms=round(duration * 1000),
                )
                if kind == "tool":
                    TOOL_LATENCY.labels(name).observe(duration)
                else:
                    RESOURCE_LATENCY.labels(name).observe(duration)
        from inspect import signature

        wrapper.__signature__ = getattr(func, "__signature__", signature(func))
        return wrapper

    return decorator
