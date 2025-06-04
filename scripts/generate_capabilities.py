from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import asyncio
import json
from mcp.server.lowlevel.server import NotificationOptions

from xyte_mcp.server import get_server


async def main() -> None:
    server = get_server()
    tools = [t.model_dump(mode="json") for t in await server.list_tools()]
    resources = [r.model_dump(mode="json") for r in await server.list_resources()]
    prompts = [p.model_dump(mode="json") for p in await server.list_prompts()]

    mcp_server = server._mcp_server
    capabilities = mcp_server.get_capabilities(NotificationOptions(), {})

    spec = {
        "capabilities": capabilities.model_dump(mode="json"),
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
    }

    out_file = Path("docs/capabilities.json")
    out_file.write_text(json.dumps(spec, indent=2))
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
