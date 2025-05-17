import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable, Awaitable
from functools import wraps
from prometheus_client import Histogram, Counter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from typing import Sequence

# Context variable to store request ID for each incoming request
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Prometheus metrics for HTTP and tool/resource handling
HTTP_REQUEST_LATENCY = Histogram(
    "xyte_http_request_latency_seconds",
    "Latency of HTTP requests",
    ["method", "path"],
)
HTTP_REQUEST_COUNT = Counter(
    "xyte_http_requests_total",
    "HTTP request count",
    ["method", "path", "status"],
)
TOOL_LATENCY = Histogram("xyte_tool_latency_seconds", "Latency of tool handlers", ["tool"])
RESOURCE_LATENCY = Histogram(
    "xyte_resource_latency_seconds",
    "Latency of resource handlers",
    ["resource"],
)
TOOL_COUNT = Counter(
    "xyte_tool_invocations_total",
    "Tool invocations",
    ["tool", "status"],
)
DEVICE_ACTIONS = Counter(
    "xyte_device_actions_total",
    "Device operations",
    ["action"],
)
COMMAND_ACTIONS = Counter(
    "xyte_command_actions_total",
    "Command operations",
    ["action"],
)

DEVICE_TOOL_ACTIONS = {
    "claim_device": "claim",
    "delete_device": "delete",
    "update_device": "update",
}
COMMAND_TOOL_ACTIONS = {
    "send_command": "send",
    "cancel_command": "cancel",
}


class StderrConsoleSpanExporter(ConsoleSpanExporter):
    """Console span exporter that writes to stderr instead of stdout."""
    
    def export(self, spans: Sequence[ReadableSpan]) -> None:
        """Export spans to stderr instead of stdout."""
        for span in spans:
            print(self._span_to_str(span), file=sys.stderr)
    
    def _span_to_str(self, span: ReadableSpan) -> str:
        """Convert span to string format."""
        # Use the parent class implementation if available
        if hasattr(super(), "_span_to_str"):
            return super()._span_to_str(span)
        else:
            # Basic fallback implementation
            return f"[{span.name}] {span.start_time} - {span.end_time}"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application-wide structured logging."""
    # Configure logging to stderr to avoid interfering with MCP protocol
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    provider = TracerProvider()
    # Use our custom stderr exporter instead of the default ConsoleSpanExporter
    provider.add_span_processor(SimpleSpanProcessor(StderrConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


def log_json(level: int, **fields: Any) -> None:
    """Log a JSON-formatted message, injecting the request ID if present."""
    request_id = request_id_var.get()
    if request_id is not None:
        fields.setdefault("request_id", request_id)
    # Get the logger and ensure it logs to stderr
    logger = logging.getLogger("xyte_mcp_alpha")
    logger.log(level, json.dumps(fields))


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

        log_json(
            logging.INFO, event="request_start", method=method, path=path, request_id=request_id
        )

        status_code: int | None = None

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                log_json(logging.INFO, event="response_start", status=status_code, request_id=request_id)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                duration = time.monotonic() - start
                duration_ms = duration * 1000
                log_json(
                    logging.INFO,
                    event="request_complete",
                    duration_ms=round(duration_ms),
                    request_id=request_id,
                )
                HTTP_REQUEST_LATENCY.labels(method, path).observe(duration)
                HTTP_REQUEST_COUNT.labels(method, path, status_code or 200).inc()
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)





def instrument(kind: str, name: str):
    """Decorator to log and measure execution of tools and resources."""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            status = "success"
            log_json(logging.INFO, event=f"{kind}_start", name=name)
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(f"{kind}:{name}"):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    status = "error"
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
                        TOOL_COUNT.labels(name, status).inc()
                        if name in DEVICE_TOOL_ACTIONS:
                            DEVICE_ACTIONS.labels(DEVICE_TOOL_ACTIONS[name]).inc()
                        if name in COMMAND_TOOL_ACTIONS:
                            COMMAND_ACTIONS.labels(COMMAND_TOOL_ACTIONS[name]).inc()
                    else:
                        RESOURCE_LATENCY.labels(name).observe(duration)

        from inspect import signature

        wrapper.__signature__ = getattr(func, "__signature__", signature(func))
        return wrapper

    return decorator
