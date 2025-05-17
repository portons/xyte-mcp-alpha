"""Xyte Organization API client."""

import logging
from typing import Any, Dict, Optional
import httpx
from cachetools import TTLCache
from pydantic import BaseModel, Field
from datetime import datetime
import anyio
from prometheus_client import Counter
from .config import get_settings

logger = logging.getLogger(__name__)


class ClaimDeviceRequest(BaseModel):
    """Request model for claiming a device."""

    name: str = Field(..., description="Friendly name for the device")
    space_id: int = Field(..., description="Identifier of the space to assign the device")
    mac: Optional[str] = Field(None, description="Device MAC address (optional)")
    sn: Optional[str] = Field(None, description="Device serial number (optional)")
    cloud_id: str = Field("", description="Cloud identifier for the device (optional)")


class UpdateDeviceRequest(BaseModel):
    """Request model for updating a device."""

    configuration: Dict[str, Any] = Field(
        ..., description="Configuration parameters for the device"
    )


class CommandRequest(BaseModel):
    """Request model for sending a command to device."""

    name: str = Field(..., description="Command name")
    friendly_name: str = Field(..., description="Human-friendly command name")
    file_id: Optional[str] = Field(
        None, description="File identifier if the command includes a file"
    )
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")


class OrgInfoRequest(BaseModel):
    """Request model for getting organization info."""

    device_id: str = Field(
        ..., description="Device identifier for which to retrieve organization info"
    )


class TicketUpdateRequest(BaseModel):
    """Request model for updating a ticket."""

    title: str = Field(..., description="New title for the ticket")
    description: str = Field(..., description="New description for the ticket")


class TicketMessageRequest(BaseModel):
    """Request model for sending a ticket message."""

    message: str = Field(..., description="Message content to send in ticket")


class XyteAPIClient:
    """Client for interacting with Xyte Organization API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the API client.

        Args:
            api_key: API key for authentication. If not provided, will try to get from env.
            base_url: Base URL for the API. Defaults to production URL.
        """
        settings = get_settings()
        self.api_key = api_key or settings.xyte_api_key
        if not self.api_key:
            raise ValueError("XYTE_API_KEY must be provided or set in environment")

        self.base_url = base_url or settings.xyte_base_url
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        transport = httpx.AsyncHTTPTransport(retries=3, limits=limits)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
            transport=transport,
        )
        self.cache = TTLCache(maxsize=128, ttl=settings.xyte_cache_ttl)

        # Prometheus counters for cache monitoring
        self.cache_hits = Counter(
            "xyte_cache_hits_total",
            "Number of cache hits",
            ["key"],
        )
        self.cache_misses = Counter(
            "xyte_cache_misses_total",
            "Number of cache misses",
            ["key"],
        )

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

    async def __aenter__(self) -> "XyteAPIClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    # Device Operations
    async def get_devices(self) -> Dict[str, Any]:
        """List all devices in the organization."""
        if "devices" in self.cache:
            self.cache_hits.labels(key="devices").inc()
            return self.cache["devices"]
        self.cache_misses.labels(key="devices").inc()
        response = await self.client.get("/devices", timeout=self._request_timeout())
        response.raise_for_status()
        data = response.json()
        self.cache["devices"] = data
        return data

    async def claim_device(self, device_data: ClaimDeviceRequest) -> Dict[str, Any]:
        """Register (claim) a new device under the organization."""
        response = await self.client.post(
            "/devices/claim",
            json=device_data.model_dump(exclude_none=True),
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """Return details and status for a single device."""
        cache_key = f"device:{device_id}"
        if cache_key in self.cache:
            self.cache_hits.labels(key="device").inc()
            return self.cache[cache_key]
        self.cache_misses.labels(key="device").inc()
        response = await self.client.get(f"/devices/{device_id}", timeout=self._request_timeout())
        response.raise_for_status()
        data = response.json()
        self.cache[cache_key] = data
        return data

    async def delete_device(self, device_id: str) -> Dict[str, Any]:
        """Delete (remove) a device by its ID."""
        response = await self.client.delete(
            f"/devices/{device_id}", timeout=self._request_timeout()
        )
        response.raise_for_status()
        return response.json()

    async def update_device(
        self, device_id: str, device_data: UpdateDeviceRequest
    ) -> Dict[str, Any]:
        """Update configuration or details of a specific device."""
        response = await self.client.patch(
            f"/devices/{device_id}",
            json=device_data.model_dump(),
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

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

        response = await self.client.get(
            "/devices/histories",
            params=params,
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

    async def get_device_analytics(
        self, device_id: str, period: str = "last_30_days"
    ) -> Dict[str, Any]:
        """Retrieve usage analytics for a device."""
        response = await self.client.get(
            f"/devices/{device_id}/analytics",
            params={"period": period},
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

    # Command Operations
    async def send_command(self, device_id: str, command_data: CommandRequest) -> Dict[str, Any]:
        """Send a command to the specified device."""
        response = await self.client.post(
            f"/devices/{device_id}/commands",
            json=command_data.model_dump(),
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

    async def cancel_command(
        self, device_id: str, command_id: str, command_data: CommandRequest
    ) -> Dict[str, Any]:
        """Cancel a previously sent command on the device."""
        response = await self.client.delete(
            f"/devices/{device_id}/commands/{command_id}",
            json=command_data.model_dump(),
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

    async def get_commands(self, device_id: str) -> Dict[str, Any]:
        """List all commands for the specified device."""
        response = await self.client.get(
            f"/devices/{device_id}/commands", timeout=self._request_timeout()
        )
        response.raise_for_status()
        return response.json()

    # Organization Operations
    async def get_organization_info(self, device_id: str) -> Dict[str, Any]:
        """Retrieve information about the organization."""
        # Note: This is a GET request with a body, which is unusual but as specified in the API
        response = await self.client.request(
            "GET",
            "/info",
            json={"device_id": device_id},
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

    # Incident Operations
    async def get_incidents(self) -> Dict[str, Any]:
        """Retrieve all incidents for the organization."""
        if "incidents" in self.cache:
            self.cache_hits.labels(key="incidents").inc()
            return self.cache["incidents"]
        self.cache_misses.labels(key="incidents").inc()
        response = await self.client.get("/incidents", timeout=self._request_timeout())
        response.raise_for_status()
        data = response.json()
        self.cache["incidents"] = data
        return data

    # Ticket Operations
    async def get_tickets(self) -> Dict[str, Any]:
        """Retrieve all support tickets for the organization."""
        if "tickets" in self.cache:
            self.cache_hits.labels(key="tickets").inc()
            return self.cache["tickets"]
        self.cache_misses.labels(key="tickets").inc()
        response = await self.client.get("/tickets", timeout=self._request_timeout())
        response.raise_for_status()
        data = response.json()
        self.cache["tickets"] = data
        return data

    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Retrieve a specific support ticket by ID."""
        response = await self.client.get(f"/tickets/{ticket_id}", timeout=self._request_timeout())
        response.raise_for_status()
        return response.json()

    async def update_ticket(
        self, ticket_id: str, ticket_data: TicketUpdateRequest
    ) -> Dict[str, Any]:
        """Update the details of a specific ticket."""
        response = await self.client.put(
            f"/tickets/{ticket_id}",
            json=ticket_data.model_dump(),
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()

    async def mark_ticket_resolved(self, ticket_id: str) -> Dict[str, Any]:
        """Mark the specified ticket as resolved."""
        response = await self.client.post(
            f"/tickets/{ticket_id}/resolved", timeout=self._request_timeout()
        )
        response.raise_for_status()
        return response.json()

    async def send_ticket_message(
        self, ticket_id: str, message_data: TicketMessageRequest
    ) -> Dict[str, Any]:
        """Send a new message to the specified ticket thread."""
        response = await self.client.post(
            f"/tickets/{ticket_id}/message",
            json=message_data.model_dump(),
            timeout=self._request_timeout(),
        )
        response.raise_for_status()
        return response.json()
