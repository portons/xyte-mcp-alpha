from typing import Dict

async def echo(message: str) -> Dict[str, str]:
    """Simple experimental echo tool."""
    return {"echo": message}
