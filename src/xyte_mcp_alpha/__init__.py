"""xyte-mcp-alpha package."""

from __future__ import annotations

import signal
from types import FrameType

from dotenv import load_dotenv

from .server import get_server
from .config import get_settings, reload_settings
from .plugins import sample  # noqa: F401
from . import plugin


def _setup_reload() -> None:
    """Install SIGHUP handler to reload configuration."""

    def handler(_sig: int, _frame: FrameType | None) -> None:
        reload_settings()
        plugin.reload_plugins()

    signal.signal(signal.SIGHUP, handler)


_setup_reload()

# Load environment variables silently
load_dotenv(verbose=False)

__version__ = "1.1.0"
__all__ = ["get_server", "get_settings", "__version__"]


def serve() -> None:
    """Entry point for serving the MCP server."""
    import sys
    import io
    
    # Capture ALL stdout to find what's polluting it
    original_stdout = sys.stdout
    capture_buffer = io.StringIO()
    
    class TeeStdout:
        def __init__(self, original, capture):
            self.original = original
            self.capture = capture
            
        def write(self, data):
            self.capture.write(data)
            # Log any non-JSON stdout to stderr for debugging
            if data.strip() and not data.strip().startswith('{'):
                sys.stderr.write(f"[STDOUT POLLUTION]: {repr(data)}\n")
            self.original.write(data)
            
        def flush(self):
            self.original.flush()
            self.capture.flush()
    
    # Install the tee to catch pollution
    sys.stdout = TeeStdout(original_stdout, capture_buffer)
    
    try:
        # Now run the server
        from .server import get_server
        server = get_server()
        server.run(transport="stdio")
    except Exception as e:
        sys.stderr.write(f"Server error: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        # Show what was captured
        captured = capture_buffer.getvalue()
        if captured:
            sys.stderr.write(f"[CAPTURED STDOUT]: {repr(captured)}\n")
