"""Interactive API playground for the Xyte MCP server."""

import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters


async def main() -> None:
    params = StdioServerParameters(command=["serve"])
    async with stdio_client(params) as client:
        print("Interactive MCP API playground. Type 'quit' to exit.")
        while True:
            try:
                command = input("mcp> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not command:
                continue
            if command in {"quit", "exit"}:
                break
            if command.startswith("tool "):
                parts = command.split(" ", 2)
                name = parts[1]
                payload = json.loads(parts[2]) if len(parts) > 2 else {}
                result = await client.call_tool(name, **payload)
                print(json.dumps(result, indent=2))
            elif command.startswith("get "):
                path = command[4:]
                result = await client.call_resource(path)
                print(json.dumps(result, indent=2))
            else:
                print("Commands:\n  tool <name> <json> - call a tool\n  get <path> - get a resource")


if __name__ == "__main__":
    asyncio.run(main())
