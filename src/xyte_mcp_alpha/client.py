"""Xyte Organization API client."""

import logging
from typing import Any, Dict, Optional
import httpx
from cachetools import TTLCache
from datetime import datetime
import anyio
import time
from prometheus_client import Counter
from .config import get_settings
from .mapping import load_mapping
from .hooks import transform_request, transform_response

from .models import (
    ClaimDeviceRequest,
    UpdateDeviceRequest,
    CommandRequest,
    TicketUpdateRequest,
    TicketMessageRequest,
)


logger = logging.getLogger(__name__)

# Prometheus counters for cache monitoring - register at module level
CACHE_HITS = Counter(
    "xyte_cache_hits_total",
    "Number of cache hits",
    ["key"],
)
CACHE_MISSES = Counter(
    "xyte_cache_misses_total",
    "Number of cache misses",
    ["key"],
)

class XyteAPIClient:
    """Client for interacting with Xyte Organization API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the API client.

        Args:
            api_key: API key for authentication. If not provided, will try to get from env.
            base_url: Base URL for the API. Defaults to production URL.
        """
        settings = get_settings()
        self.mapping = load_mapping()

        self.api_key = api_key or settings.xyte_api_key
        self.oauth_token = settings.xyte_oauth_token
        if not (self.api_key or self.oauth_token):
            raise ValueError("XYTE_API_KEY or XYTE_OAUTH_TOKEN must be provided")

        self.base_url = base_url or settings.xyte_base_url
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        transport = httpx.AsyncHTTPTransport(retries=3, limits=limits)
        headers = {"Content-Type": "application/json"}
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        else:
            headers["Authorization"] = self.api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
            transport=transport,
        )
        self.cache = TTLCache(maxsize=128, ttl=settings.xyte_cache_ttl)

    def cache_stats(self) -> Dict[str, Any]:
        """Return simple cache statistics for monitoring."""
        return {"size": len(self.cache), "ttl": self.cache.ttl}

    def _request_timeout(self) -> float | None:
        """Return remaining time before the current cancel scope deadline."""
        try:
            deadline = anyio.current_effective_deadline()
        except RuntimeError:
            return None
        if deadline == float("inf"):
            return None
        remaining = deadline - anyio.current_time()
        if remaining <= 0:
            raise httpx.TimeoutException("Deadline exceeded")
        return remaining

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Perform an HTTP request with retries and circuit breaker."""
        if hasattr(self, "_circuit_open_until") and time.monotonic() < self._circuit_open_until:  # type: ignore[attr-defined]
            raise httpx.NetworkError("backend_unavailable")

        backoff = 0.1
        failures = getattr(self, "_failures", 0)
        for attempt in range(3):
            try:
                response = await self.client.request(method, url, timeout=self._request_timeout(), **kwargs)
                self._failures = 0  # type: ignore[attr-defined]
                return response
            except (httpx.NetworkError, httpx.TimeoutException):
                failures += 1
                self._failures = failures  # type: ignore[attr-defined]
                if failures >= 3:
                    self._circuit_open_until = time.monotonic() + 30  # type: ignore[attr-defined]
                if attempt == 2:
                    raise
                await anyio.sleep(backoff)
                backoff *= 2

    async def __aenter__(self) -> "XyteAPIClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _endpoint(self, name: str, **params: Any) -> str:
        path = self.mapping.get(name, "")
        return path.format(**params)

    # Device Operations
    async def get_devices(self) -> Dict[str, Any]:
        """List all devices in the organization."""
        if "devices" in self.cache:
            CACHE_HITS.labels(key="devices").inc()
            return self.cache["devices"]
        CACHE_MISSES.labels(key="devices").inc()
        path = self._endpoint("get_devices")
        response = await self._request("GET", path)
        response.raise_for_status()
        data = transform_response("get_devices", response.json())
        self.cache["devices"] = data
        return data

    async def claim_device(self, device_data: ClaimDeviceRequest) -> Dict[str, Any]:
        """Register (claim) a new device under the organization."""
        payload = transform_request("claim_device", device_data.model_dump(exclude_none=True))
        response = await self._request(
            "POST",
            self._endpoint("claim_device"),
            json=payload,
        )
        response.raise_for_status()
        return transform_response("claim_device", response.json())

    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """Return details and status for a single device."""
        cache_key = f"device:{device_id}"
        if cache_key in self.cache:
            CACHE_HITS.labels(key="device").inc()
            return self.cache[cache_key]
        CACHE_MISSES.labels(key="device").inc()
        response = await self._request("GET", self._endpoint("get_device", device_id=device_id))
        response.raise_for_status()
        data = transform_response("get_device", response.json())
        self.cache[cache_key] = data
        return data

    async def delete_device(self, device_id: str) -> Dict[str, Any]:
        """Delete (remove) a device by its ID."""
        response = await self._request("DELETE", self._endpoint("delete_device", device_id=device_id))
        response.raise_for_status()
        return transform_response("delete_device", response.json())

    async def update_device(
        self, device_id: str, device_data: UpdateDeviceRequest
    ) -> Dict[str, Any]:
        """Update configuration or details of a specific device."""
        payload = transform_request("update_device", device_data.model_dump())
        response = await self._request(
            "PATCH",
            self._endpoint("update_device", device_id=device_id),
            json=payload,
        )
        response.raise_for_status()
        return transform_response("update_device", response.json())

    async def get_device_histories(
        self,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        device_id: Optional[str] = None,
        space_id: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve device history records."""
        params = {}
        if status:
            params["status"] = status
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()
        if device_id:
            params["device_id"] = device_id
        if space_id:
            params["space_id"] = space_id
        if name:
            params["name"] = name

        response = await self._request(
            "GET",
            self._endpoint("get_device_histories"),
            params=transform_request("get_device_histories", params),
        )
        response.raise_for_status()
        return transform_response("get_device_histories", response.json())

    async def get_device_analytics(
        self, device_id: str, period: str = "last_30_days"
    ) -> Dict[str, Any]:
        """Retrieve usage analytics for a device."""
        response = await self._request(
            "GET",
            self._endpoint("get_device_analytics", device_id=device_id),
            params={"period": period},
        )
        response.raise_for_status()
        return transform_response("get_device_analytics", response.json())

    # Command Operations
    async def send_command(self, device_id: str, command_data: CommandRequest) -> Dict[str, Any]:
        """Send a command to the specified device."""
        payload = transform_request("send_command", command_data.model_dump())
        response = await self._request(
            "POST",
            self._endpoint("send_command", device_id=device_id),
            json=payload,
        )
        response.raise_for_status()
        return transform_response("send_command", response.json())

    async def cancel_command(
        self, device_id: str, command_id: str, command_data: CommandRequest
    ) -> Dict[str, Any]:
        """Cancel a previously sent command on the device."""
        payload = transform_request("cancel_command", command_data.model_dump())
        response = await self._request(
            "DELETE",
            self._endpoint(
                "cancel_command", device_id=device_id, command_id=command_id
            ),
            json=payload,
        )
        response.raise_for_status()
        return transform_response("cancel_command", response.json())

    async def get_commands(self, device_id: str) -> Dict[str, Any]:
        """List all commands for the specified device."""
        response = await self._request("GET", self._endpoint("get_commands", device_id=device_id))
        response.raise_for_status()
        return transform_response("get_commands", response.json())

    # Organization Operations
    async def get_organization_info(self, device_id: str) -> Dict[str, Any]:
        """Retrieve information about the organization."""
        # Note: This is a GET request with a body, which is unusual but as specified in the API
        payload = transform_request("get_organization_info", {"device_id": device_id})
        response = await self._request(
            "GET",
            self._endpoint("get_organization_info", device_id=device_id),
            json=payload,
        )
        response.raise_for_status()
        return transform_response("get_organization_info", response.json())

    # Incident Operations
    async def get_incidents(self) -> Dict[str, Any]:
        """Retrieve all incidents for the organization."""
        if "incidents" in self.cache:
            CACHE_HITS.labels(key="incidents").inc()
            return self.cache["incidents"]
        CACHE_MISSES.labels(key="incidents").inc()
        response = await self._request("GET", self._endpoint("get_incidents"))
        response.raise_for_status()
        data = transform_response("get_incidents", response.json())
        self.cache["incidents"] = data
        return data

    # Ticket Operations
    async def get_tickets(self) -> Dict[str, Any]:
        """Retrieve all support tickets for the organization."""
        if "tickets" in self.cache:
            CACHE_HITS.labels(key="tickets").inc()
            return self.cache["tickets"]
        CACHE_MISSES.labels(key="tickets").inc()
        response = await self._request("GET", self._endpoint("get_tickets"))
        response.raise_for_status()
        data = transform_response("get_tickets", response.json())
        self.cache["tickets"] = data
        return data

    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Retrieve a specific support ticket by ID."""
        response = await self._request("GET", self._endpoint("get_ticket", ticket_id=ticket_id))
        response.raise_for_status()
        return transform_response("get_ticket", response.json())

    async def update_ticket(
        self, ticket_id: str, ticket_data: TicketUpdateRequest
    ) -> Dict[str, Any]:
        """Update the details of a specific ticket."""
        payload = transform_request("update_ticket", ticket_data.model_dump())
        response = await self._request(
            "PUT",
            self._endpoint("update_ticket", ticket_id=ticket_id),
            json=payload,
        )
        response.raise_for_status()
        return transform_response("update_ticket", response.json())

    async def mark_ticket_resolved(self, ticket_id: str) -> Dict[str, Any]:
        """Mark the specified ticket as resolved."""
        response = await self._request("POST", self._endpoint("mark_ticket_resolved", ticket_id=ticket_id))
        response.raise_for_status()
        return transform_response("mark_ticket_resolved", response.json())

    async def send_ticket_message(
        self, ticket_id: str, message_data: TicketMessageRequest
    ) -> Dict[str, Any]:
        """Send a new message to the specified ticket thread."""
        payload = transform_request("send_ticket_message", message_data.model_dump())
        response = await self._request(
            "POST",
            self._endpoint("send_ticket_message", ticket_id=ticket_id),
            json=payload,
        )
        response.raise_for_status()
        return transform_response("send_ticket_message", response.json())