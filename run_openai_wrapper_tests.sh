#!/bin/bash

echo "Running OpenAI wrapper tests with coverage..."

# Check if we're in a virtual environment, if not use uv
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Using virtual environment: $VIRTUAL_ENV"
    pip install pytest pytest-cov pytest-asyncio fastapi httpx
else
    echo "No virtual environment detected, using uv..."
    # Install test dependencies with uv
    uv pip install pytest pytest-cov pytest-asyncio fastapi httpx
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run tests with coverage
if [[ "$VIRTUAL_ENV" != "" ]]; then
    pytest tests/test_openai_wrapper.py \
        -v \
        --cov=xyte_mcp.openai_wrapper \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-fail-under=100
else
    uv run pytest tests/test_openai_wrapper.py \
        -v \
        --cov=xyte_mcp.openai_wrapper \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-fail-under=100
fi

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "\n✅ All tests passed with 100% coverage!"
    echo "Coverage report available in htmlcov/index.html"
else
    echo -e "\n❌ Tests failed or coverage is below 100%"
    exit 1
fi