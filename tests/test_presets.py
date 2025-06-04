import pytest
from contextlib import asynccontextmanager

from xyte_mcp.tools.presets import start_meeting_room_preset


class DummyClient:
    def __init__(self) -> None:
        self.commands = []

    async def send_command(self, device_id: str, command_data):
        self.commands.append((device_id, command_data.name))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_start_meeting_room_preset(monkeypatch):
    client = DummyClient()

    @asynccontextmanager
    async def fake_get_client(request=None):
        yield client

    monkeypatch.setattr("xyte_mcp.tools.presets.get_client", fake_get_client)
    monkeypatch.setattr(
        "yaml.safe_load",
        lambda _: [
            {"device_id": "1", "command": "on"},
            {"device_id": "2", "command": "mute"},
        ],
    )

    result = await start_meeting_room_preset("Board")
    assert result.summary == "2 commands executed"
    assert client.commands == [("1", "on"), ("2", "mute")]
