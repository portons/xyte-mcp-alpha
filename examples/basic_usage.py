"""Example usage of the Xyte MCP server using mcp-client."""

import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters


async def main() -> None:
    params = StdioServerParameters(command=["serve"])
    async with stdio_client(params) as client:
        result = await client.call_tool("list_devices")
        print("Devices:", result)
        if result.get("devices"):
            dev_id = result["devices"][0]["id"]
            status = await client.call_resource(f"device://{dev_id}/status")
            print("Status:", status)


if __name__ == "__main__":
    asyncio.run(main())
