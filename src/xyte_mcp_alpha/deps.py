import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from .client import XyteAPIClient


@asynccontextmanager
async def get_client() -> AsyncIterator[XyteAPIClient]:
    """Yield a new API client instance for a request."""
    api_key = os.getenv("XYTE_API_KEY")
    if not api_key:
        raise ValueError("XYTE_API_KEY must be set in environment")
    client = XyteAPIClient(api_key=api_key)
    try:
        yield client
    finally:
        await client.close()
