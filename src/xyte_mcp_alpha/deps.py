from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from .client import XyteAPIClient
from .config import get_settings


@asynccontextmanager
async def get_client(user_token: Optional[str] = None) -> AsyncIterator[XyteAPIClient]:
    """Yield a new API client instance for a request.

    Args:
        user_token: Optional token to use instead of the default API key.
    """
    settings = get_settings()
    api_key = user_token or settings.xyte_api_key
    client = XyteAPIClient(api_key=api_key, base_url=settings.xyte_base_url)
    try:
        yield client
    finally:
        await client.close()
