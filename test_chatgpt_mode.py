#!/usr/bin/env python3
"""Test script to verify ChatGPT mode behavior."""

import asyncio
import os
import json
from xyte_mcp.server import get_server

async def test_chatgpt_mode():
    """Test that ChatGPT mode only exposes search and fetch tools."""
    
    # Test normal mode first
    os.environ["CHATGPT_MODE"] = "false"
    # Force module reload
    import importlib
    import xyte_mcp.server
    importlib.reload(xyte_mcp.server)
    
    server = xyte_mcp.server.get_server()
    normal_tools = await server.list_tools()
    print(f"Normal mode tools: {len(normal_tools)}")
    print("Tool names:", [t.name for t in normal_tools])
    
    # Test ChatGPT mode
    os.environ["CHATGPT_MODE"] = "true"
    # Force module reload again
    importlib.reload(xyte_mcp.server)
    
    server = xyte_mcp.server.get_server()
    chatgpt_tools = await server.list_tools()
    print(f"\nChatGPT mode tools: {len(chatgpt_tools)}")
    print("Tool names:", [t.name for t in chatgpt_tools])
    
    # Verify only search and fetch are exposed
    chatgpt_tool_names = {t.name for t in chatgpt_tools}
    assert chatgpt_tool_names == {"search", "fetch"}, f"Expected only search and fetch, got {chatgpt_tool_names}"
    
    # Test search tool description
    search_tool = next(t for t in chatgpt_tools if t.name == "search")
    print(f"\nSearch tool description in ChatGPT mode:\n{search_tool.description}")
    
    # Verify description is short
    assert len(search_tool.description) < 200, f"Description too long: {len(search_tool.description)} chars"
    
    print("\n✅ ChatGPT mode test passed!")

if __name__ == "__main__":
    asyncio.run(test_chatgpt_mode())