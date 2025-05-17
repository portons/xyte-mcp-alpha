import logging
import time
from typing import Any, Dict, Awaitable, TYPE_CHECKING
from collections import deque

from pydantic import ValidationError
from .config import get_settings

from .models import DeviceId, TicketId

import httpx
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - imported for type hints only
    from mcp.server.fastmcp.server import Context


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
    """Enforce rate limiting for API requests.
    
    Raises:
        MCPError: If rate limit is exceeded
    """
    now = time.time()
    limit = get_settings().rate_limit_per_minute
    
    # Remove timestamps older than 60 seconds
    while _REQUEST_TIMESTAMPS and _REQUEST_TIMESTAMPS[0] < now - 60:
        _REQUEST_TIMESTAMPS.popleft()
    
    if len(_REQUEST_TIMESTAMPS) >= limit:
        raise MCPError(
            code="rate_limited",
            message=f"Rate limit exceeded. Maximum {limit} requests per minute."
        )
    
    _REQUEST_TIMESTAMPS.append(now)


def validate_device_id(device_id: str) -> str:
    """Validate and sanitize a device identifier."""
    try:
        value = DeviceId(device_id=device_id).device_id.strip()
        if not value:
            raise ValueError("device_id cannot be empty")
        return value
    except (ValidationError, ValueError) as exc:  # pragma: no cover - simple validation
        raise MCPError(code="invalid_params", message=str(exc))


def validate_ticket_id(ticket_id: str) -> str:
    """Validate and sanitize a ticket identifier."""
    try:
        return TicketId(ticket_id=ticket_id).ticket_id.strip()
    except ValidationError as exc:  # pragma: no cover - simple validation
        raise MCPError(code="invalid_params", message=str(exc))


async def handle_api(endpoint: str, coro: Awaitable[Any]) -> Dict[str, Any]:
    """Handle API response with error conversion and metrics reporting."""
    enforce_rate_limit()
    
    start_time = time.time()
    try:
        result = await coro
        
        # Track latency
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
        
        # Convert response to dict if needed
        if hasattr(result, "model_dump"):
            return {"data": result.model_dump()}
        elif not isinstance(result, dict):
            return {"data": result}
        return result
        
    except httpx.HTTPStatusError as e:
        status = str(e.response.status_code)
        STATUS_COUNT.labels(status=status).inc()
        ERROR_COUNT.labels(endpoint=endpoint, code=status).inc()
        
        # Log security-related errors
        if e.response.status_code in [401, 403]:
            audit_logger.warning(
                f"Security error accessing {endpoint}",
                extra={"status": status, "endpoint": endpoint}
            )
        
        error_text = e.response.text
        try:
            error_data = e.response.json()
            error_message = error_data.get("error", error_text)
        except Exception:
            error_message = error_text or f"HTTP {status} error"

        code = f"http_{status}"
        if e.response.status_code == 404:
            if "device" in endpoint:
                code = "device_not_found"
            elif "ticket" in endpoint:
                code = "ticket_not_found"
        elif e.response.status_code == 503:
            code = "service_unavailable"

        raise MCPError(code=code, message=error_message)
        
    except ValidationError as e:
        ERROR_COUNT.labels(endpoint=endpoint, code="validation_error").inc()
        err_msg = str(e).replace('\n', '; ')
        raise MCPError(
            code="validation_error",
            message=f"Invalid data format: {err_msg}"
        )
        
    except httpx.TimeoutException:
        ERROR_COUNT.labels(endpoint=endpoint, code="timeout").inc()
        raise MCPError(
            code="timeout",
            message="Request timed out"
        )
        
    except httpx.NetworkError as e:
        ERROR_COUNT.labels(endpoint=endpoint, code="network_error").inc()
        raise MCPError(
            code="network_error",
            message=f"Network error: {str(e)}"
        )
        
    except Exception as e:
        ERROR_COUNT.labels(endpoint=endpoint, code="unknown_error").inc()
        logger.exception(f"Unknown error in {endpoint}")
        raise MCPError(
            code="unknown_error",
            message=f"Unexpected error: {type(e).__name__}"
        )


def get_session_state(ctx: "Context") -> Dict[str, Any]:
    """Get session state dictionary for a context."""
    if not hasattr(ctx, "_xyte_state"):
        ctx._xyte_state = {}  # type: ignore
    return ctx._xyte_state  # type: ignore


def convert_device_id(device_id: str | int | None) -> str:
    """Convert device ID to string format."""
    if device_id is None:
        raise MCPError(
            code="invalid_device_id",
            message="Device ID is required"
        )
    return str(DeviceId(device_id=device_id).device_id)


def convert_ticket_id(ticket_id: str | int | None) -> str:
    """Convert ticket ID to string format."""
    if ticket_id is None:
        raise MCPError(
            code="invalid_ticket_id", 
            message="Ticket ID is required"
        )
    return str(TicketId(ticket_id=ticket_id).ticket_id)