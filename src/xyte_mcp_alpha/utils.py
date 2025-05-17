import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict, Awaitable

from pydantic import ValidationError
from .config import get_settings

from .models import DeviceId, TicketId

import httpx
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)


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
        value = DeviceId(device_id=device_id).device_id.strip()
        if not value:
            raise ValueError("device_id must not be empty")
        return value
    except (ValidationError, ValueError) as exc:  # pragma: no cover - simple validation
        raise MCPError(code="invalid_params", message=str(exc))


def validate_ticket_id(ticket_id: str) -> str:
    """Validate and sanitize a ticket identifier."""
    try:
        value = TicketId(ticket_id=ticket_id).ticket_id.strip()
        if not value:
            raise ValueError("ticket_id must not be empty")
        return value
    except (ValidationError, ValueError) as exc:  # pragma: no cover - simple validation
        raise MCPError(code="invalid_params", message=str(exc))


async def handle_api(name: str, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute an API call, track metrics and translate errors."""
    enforce_rate_limit()
    audit_logger.info("%s", name)
    start = asyncio.get_event_loop().time()
    try:
        result = await coro
        STATUS_COUNT.labels("200").inc()
        return result
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        STATUS_COUNT.labels(str(status)).inc()
        if status in {401, 403}:
            code = "unauthorized"
        elif status in {400, 422}:
            code = "invalid_params"
        elif status == 404:
            code = "not_found"
        elif status == 405:
            code = "method_not_allowed"
        elif status == 429:
            code = "rate_limited"
        elif 500 <= status <= 599:
            code = "xyte_server_error"
        else:
            code = "xyte_api_error"
        ERROR_COUNT.labels(name, code).inc()
        logger.error("%s %s: %s", name, status, e.response.text)
        raise MCPError(code=code, message=e.response.text)
    except httpx.RequestError as e:
        ERROR_COUNT.labels(name, "network_error").inc()
        logger.error("%s network error: %s", name, str(e))
        raise MCPError(code="network_error", message=str(e))
    except httpx.TimeoutException as e:
        ERROR_COUNT.labels(name, "timeout").inc()
        logger.error("%s timeout: %s", name, str(e))
        raise MCPError(code="deadline_exceeded", message=str(e))
    except Exception as e:  # pragma: no cover - fallback
        ERROR_COUNT.labels(name, "unknown").inc()
        logger.exception("%s unknown error: %s", name, str(e))
        raise MCPError(code="xyte_api_error", message=str(e))
    finally:
        REQUEST_LATENCY.labels(name).observe(asyncio.get_event_loop().time() - start)
