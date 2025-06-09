from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from starlette.requests import Request
from .logging_utils import request_var

from .client import XyteAPIClient
from .config import get_settings


@asynccontextmanager
async def get_client(request: Optional[Request] = None) -> AsyncIterator[XyteAPIClient]:
    """Yield a new API client instance for a request.

    Args:
        request: Current HTTP request providing the authorization header.
    """
    settings = get_settings()
    if request is None:
        request = request_var.get()
    key = getattr(request.state, "xyte_key", None) if request else None
    api_key = key or settings.xyte_api_key
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"get_client: request={request}, key from state={key}, key from settings={settings.xyte_api_key[:10] if settings.xyte_api_key else None}")
    
    client = XyteAPIClient(api_key=api_key, base_url=settings.xyte_base_url)
    try:
        yield client
    finally:
        await client.close()
