#!/usr/bin/env python
"""Basic profiling helper for the MCP server."""

import cProfile
import pstats
import asyncio

from xyte_mcp_alpha import get_server
from mcp.server.stdio import stdio_server


async def _run_for(duration: float) -> None:
    """Run the stdio server for a limited duration."""
    async with asyncio.timeout(duration):
        await stdio_server(get_server())


def main() -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        asyncio.run(_run_for(5))
    finally:
        profiler.disable()
        pstats.Stats(profiler).sort_stats("cumtime").print_stats(20)


if __name__ == "__main__":
    main()
