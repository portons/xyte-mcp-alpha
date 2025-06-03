import asyncio
from typing import Any, Dict, List

class DummyRedis:
    def __init__(self) -> None:
        self.stream: List[Dict[str, Any]] = []
        self.groups: Dict[str, int] = {}

    async def xadd(self, stream: str, fields: Dict[str, Any], maxlen=None, approximate=None):
        self.stream.append(fields)
        return len(self.stream)

    async def xgroup_create(self, stream: str, group: str, id: str = "$", mkstream: bool = False):
        if group in self.groups:
            raise Exception("BUSYGROUP")
        self.groups[group] = 0

    async def xreadgroup(self, group: str, consumer: str, streams: Dict[str, str], count: int, block: int):
        idx = self.groups.get(group, 0)
        if idx < len(self.stream):
            self.groups[group] = idx + 1
            data = self.stream[idx]
            stream_name = list(streams.keys())[0]
            return [(stream_name, [(str(idx), {k.encode(): v.encode() if isinstance(v, str) else str(v).encode() for k, v in data.items()})])]
        await asyncio.sleep(block / 1000)
        return []

    async def xack(self, stream: str, group: str, eid: Any):
        pass
