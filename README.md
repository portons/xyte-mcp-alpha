# Xyte MCP Server

An MCP (Model Context Protocol) server that provides access to the Xyte Organization API, enabling AI assistants to interact with Xyte devices, commands, tickets, and more.

## Features

This MCP server exposes the following capabilities:

All resources and tools return structured JSON objects rather than plain strings.

### Resources (Read-only)
- `devices://` - List all devices in the organization
- `device://{device_id}/commands` - List commands for a specific device
- `device://{device_id}/histories` - Get history records for a device
- `organization://info/{device_id}` - Get organization info for a device context
- `incidents://` - Retrieve all incidents
- `tickets://` - List all support tickets
- `ticket://{ticket_id}` - Get a specific ticket

### Tools (Actions)
- `claim_device` - Register a new device
- `delete_device` - Remove a device
- `update_device` - Update device configuration
- `send_command` - Send a command to a device
- `cancel_command` - Cancel a pending command
- `update_ticket` - Update ticket details
- `mark_ticket_resolved` - Mark a ticket as resolved
- `send_ticket_message` - Send a message to a ticket
- `search_device_histories` - Search device histories with filters

## Installation

1. Clone the repository:
```bash
git clone https://github.com/portons/xyte-mcp-alpha.git
cd xyte-mcp-alpha
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in editable mode:
```bash
pip install -e .
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Xyte API key:
```
XYTE_API_KEY=your-actual-api-key-here
```

## Usage

### Running the Server

There are several ways to run the MCP server:

1. Using the installed command:
```bash
serve
```

2. Using Python module:
```bash
python -m xyte_mcp_alpha
```

3. Using MCP CLI for development:
```bash
mcp dev src/xyte_mcp_alpha/server.py
```

4. Running over HTTP with Uvicorn:
```bash
python -m xyte_mcp_alpha.http
```

### Connecting to Claude Desktop

To use this server with Claude Desktop, add it to your configuration file:

**macOS/Linux:** `~/.claude/config.json`
**Windows:** `%APPDATA%\claude\config.json`

```json
{
  "mcpServers": {
    "xyte": {
      "command": "serve",
      "env": {
        "XYTE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Alternatively, with a Python virtual environment:

```json
{
  "mcpServers": {
    "xyte": {
      "command": "/path/to/xyte-mcp-alpha/venv/bin/python",
      "args": ["-m", "xyte_mcp_alpha"],
      "env": {
        "XYTE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Example Usage

![mcp dev demo](docs/mcp-dev.gif)

## Development

### Running Tests

```bash
pytest
```

### Using the MCP Inspector

For development and debugging:

```bash
mcp dev src/xyte_mcp_alpha/server.py
```

This opens an interactive UI where you can test tools and resources.

## Logging and Monitoring

Structured JSON logs are produced for every HTTP request and Xyte API call. Each
log entry includes a unique `request_id` for easy tracing. Prometheus metrics are
available at the `/metrics` endpoint, including latency histograms for tools,
resources and underlying API calls.

## API Reference

### Environment Variables

- `XYTE_API_KEY` (required) - Your Xyte organization API key
- `XYTE_BASE_URL` (optional) - Override the API base URL (defaults to production)
- `XYTE_USER_TOKEN` (optional) - Per-user token to override the global API key
- `XYTE_CACHE_TTL` (optional) - TTL in seconds for cached API responses (default 60)

### Error Handling

Errors are surfaced to clients using `MCPError` exceptions. XYTE API status codes are translated to
meaningful MCP error codes like `unauthorized`, `not_found` and `rate_limited`.
All errors are logged for debugging purposes.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.