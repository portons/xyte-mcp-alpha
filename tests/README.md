# Tests

This directory contains unit and integration tests for the Xyte MCP server.

## Running the tests

Activate the provided virtual environment and execute:

```bash
pytest --cov=src --cov-report=term
```

A coverage report will be displayed after the test run. The suite uses
`pytest` with the builtin `unittest` style tests.
