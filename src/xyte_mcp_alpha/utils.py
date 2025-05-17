import asyncio
import logging
import time
from typing import Any, Dict, Awaitable
from collections import deque

from pydantic import ValidationError
from .config import get_settings

from .models import DeviceId, TicketId

import httpx
from prometheus_client import Counter, Histogram
from .logging_utils import log_json


class MCPError(Exception):
    """Simple error class used for MCP responses."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    "xyte_request_latency_seconds", "Latency of API calls", ["endpoint"]
)
ERROR_COUNT = Counter("xyte_errors_total", "XYTE API errors", ["endpoint", "code"])
STATUS_COUNT = Counter("xyte_status_total", "XYTE API status codes", ["status"])

# Audit logger for security related events
audit_logger = logging.getLogger("audit")

# Simple in-memory rate limiter
_REQUEST_TIMESTAMPS: deque[float] = deque()


def enforce_rate_limit() -> None:
    """Raise MCPError if request rate exceeds configured threshold."""
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    window = 60.0
    now = time.monotonic()
    while _REQUEST_TIMESTAMPS and now - _REQUEST_TIMESTAMPS[0] > window:
        _REQUEST_TIMESTAMPS.popleft()
    if len(_REQUEST_TIMESTAMPS) >= limit:
        audit_logger.warning("rate limit exceeded")
        raise MCPError(code="rate_limited", message="Too many requests")
    _REQUEST_TIMESTAMPS.append(now)


def validate_device_id(device_id: str) -> str:
    """Validate and sanitize a device identifier."""
    try:
        return DeviceId(device_id=device_id).device_id.strip()
    except ValidationError as exc:  # pragma: no cover - simple validation
        raise MCPError(code="invalid_params", message=str(exc))


def validate_ticket_id(ticket_id: str) -> str:
    """Validate and sanitize a ticket identifier."""
    try:
        return TicketId(ticket_id=ticket_id).ticket_id.strip()
    except ValidationError as exc:  # pragma: no cover - simple validation
        raise MCPError(code="invalid_params", message=str(exc))


async def handle_api(name: str, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute an API call, track metrics and translate errors."""
    enforce_rate_limit()
    audit_logger.info("%s", name)
    start = asyncio.get_event_loop().time()
    try:
        result = await coro
        STATUS_COUNT.labels("200").inc()
        log_json(logging.INFO, event="xyte_api_success", endpoint=name)
        return result
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        STATUS_COUNT.labels(str(status)).inc()
        if status in {401, 403}:
            code = "unauthorized"
        elif status == 404:
            code = "not_found"
        elif status == 429:
            code = "rate_limited"
        elif 500 <= status <= 599:
            code = "xyte_server_error"
        else:
            code = "xyte_api_error"
        ERROR_COUNT.labels(name, code).inc()
        log_json(logging.ERROR, event="xyte_api_error", endpoint=name, status=status)
        raise MCPError(code=code, message=e.response.text)
    except httpx.TimeoutException as e:
        ERROR_COUNT.labels(name, "timeout").inc()
        log_json(logging.ERROR, event="xyte_api_timeout", endpoint=name)
        raise MCPError(code="deadline_exceeded", message=str(e))
    except Exception as e:  # pragma: no cover - fallback
        ERROR_COUNT.labels(name, "unknown").inc()
        log_json(logging.ERROR, event="xyte_api_error", endpoint=name)
        raise MCPError(code="xyte_api_error", message=str(e))
    finally:
        duration = asyncio.get_event_loop().time() - start
        REQUEST_LATENCY.labels(name).observe(duration)
        log_json(logging.INFO, event="xyte_api_latency", endpoint=name, duration_ms=round(duration * 1000))
