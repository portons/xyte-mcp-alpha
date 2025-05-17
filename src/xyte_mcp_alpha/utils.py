import asyncio
from typing import Any, Dict, Awaitable

import httpx
from prometheus_client import Counter, Histogram
from mcp.server.errors import MCPError

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    "xyte_request_latency_seconds", "Latency of API calls", ["endpoint"]
)
ERROR_COUNT = Counter("xyte_errors_total", "XYTE API errors", ["endpoint", "code"])
STATUS_COUNT = Counter("xyte_status_total", "XYTE API status codes", ["status"])


async def handle_api(name: str, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute an API call, track metrics and translate errors."""
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
        elif status == 404:
            code = "not_found"
        elif status == 429:
            code = "rate_limited"
        elif 500 <= status <= 599:
            code = "xyte_server_error"
        else:
            code = "xyte_api_error"
        ERROR_COUNT.labels(name, code).inc()
        raise MCPError(code=code, message=e.response.text)
    except httpx.TimeoutException as e:
        ERROR_COUNT.labels(name, "timeout").inc()
        raise MCPError(code="deadline_exceeded", message=str(e))
    except Exception as e:  # pragma: no cover - fallback
        ERROR_COUNT.labels(name, "unknown").inc()
        raise MCPError(code="xyte_api_error", message=str(e))
    finally:
        REQUEST_LATENCY.labels(name).observe(asyncio.get_event_loop().time() - start)
