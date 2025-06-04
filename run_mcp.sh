#!/bin/bash
# Wrapper to ensure clean stdio for MCP

# Run uv with all output suppressed except the actual program
exec uv run --quiet --no-progress serve 2>&3 3>&2