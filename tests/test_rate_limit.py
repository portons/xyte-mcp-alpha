import os
import pytest

from xyte_mcp_alpha.utils import handle_api, MCPError

class DummyClient:
    async def do(self):
        return {}

dummy = DummyClient()

@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    os.environ['XYTE_RATE_LIMIT'] = '2'
    from xyte_mcp_alpha.config import get_settings
    get_settings.cache_clear()

    await handle_api('dummy', dummy.do())
    await handle_api('dummy', dummy.do())
    with pytest.raises(MCPError) as exc:
        await handle_api('dummy', dummy.do())
    assert exc.value.code == 'rate_limited'
