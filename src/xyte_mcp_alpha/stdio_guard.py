"""Guard against stdout pollution during MCP stdio mode."""

import sys
import os
import io
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def silence_stdout() -> Iterator[None]:
    """Temporarily redirect stdout to devnull to prevent pollution."""
    old_stdout = sys.stdout
    try:
        # Redirect stdout to devnull
        sys.stdout = open(os.devnull, 'w')
        yield
    finally:
        sys.stdout.close()
        sys.stdout = old_stdout


class StdoutGuard:
    """Guard that redirects stdout to stderr during module import."""
    
    def __init__(self) -> None:
        self.original_stdout = sys.stdout
        self.active = False
        
    def __enter__(self) -> 'StdoutGuard':
        if not self.active:
            sys.stdout = sys.stderr
            self.active = True
        return self
        
    def __exit__(self, *args) -> None:
        if self.active:
            sys.stdout = self.original_stdout
            self.active = False