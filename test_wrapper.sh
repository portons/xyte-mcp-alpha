#!/bin/bash

echo "Testing OpenAI wrapper..."

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# First, try to run with uv
if command -v uv &> /dev/null; then
    echo "Using uv to run tests..."
    uv pip install pytest pytest-cov pytest-asyncio
    uv run python -m pytest tests/test_openai_wrapper.py -v
else
    echo "Using standard Python..."
    python -m pytest tests/test_openai_wrapper.py -v
fi