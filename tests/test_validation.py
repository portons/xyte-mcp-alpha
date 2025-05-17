import pytest

from xyte_mcp_alpha import resources
from xyte_mcp_alpha.utils import MCPError

@pytest.mark.asyncio
async def test_invalid_device_id():
    with pytest.raises(MCPError) as exc:
        await resources.list_device_commands("")
    assert exc.value.code == "invalid_params"
