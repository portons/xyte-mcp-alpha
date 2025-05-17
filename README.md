# Xyte MCP Server

An MCP (Model Context Protocol) server that provides access to the Xyte Organization API, enabling AI assistants to interact with Xyte devices, commands, tickets, and more.

## Quickstart

1. Ensure Python 3.11+ is installed and clone the repo.
2. Create a virtualenv and install the project: `pip install -e .`.
3. Copy `.env.example` to `.env` and set `XYTE_API_KEY` (and optional `XYTE_USER_TOKEN`).
4. Run the server with `serve` or `python -m xyte_mcp_alpha`.

## Features

This MCP server exposes the following capabilities:

All resources and tools return structured JSON objects rather than plain strings.

### Resources (Read-only)
- `devices://` - List all devices in the organization
- `device://{device_id}/commands` - List commands for a specific device
- `device://{device_id}/histories` - Get history records for a device
- `device://{device_id}/status` - Get current status for a device
- `organization://info/{device_id}` - Get organization info for a device context
- `incidents://` - Retrieve all incidents
- `tickets://` - List all support tickets
- `ticket://{ticket_id}` - Get a specific ticket
- `user://{user_token}/preferences` - Get user preferences
- `user://{user_token}/devices` - List devices filtered by user

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
- `send_command_async` - Send a command asynchronously
- `get_task_status` - Query async task status

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

If port 6277 is already in use, you can specify a different port:

```bash
MCP_INSPECTOR_PORT=6278 mcp dev src/xyte_mcp_alpha/server.py
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
- `XYTE_OAUTH_TOKEN` (optional) - OAuth2 access token instead of API key
- `XYTE_BASE_URL` (optional) - Override the API base URL (defaults to production)
- `XYTE_USER_TOKEN` (optional) - Per-user token to override the global API key
- `XYTE_CACHE_TTL` (optional) - TTL in seconds for cached API responses (default 60)
- `XYTE_ENV` (optional) - Deployment environment name (`dev`, `staging`, `prod`)
- `XYTE_RATE_LIMIT` (optional) - Maximum MCP requests per minute (default 60)
- `MCP_INSPECTOR_PORT` (optional) - Port for the MCP inspector to use (default 6277)
- `XYTE_EXPERIMENTAL_APIS` (optional) - Enable registration of experimental tools
- `XYTE_API_MAPPING` (optional) - Path to JSON file overriding API endpoint mapping
- `XYTE_HOOKS_MODULE` (optional) - Python module providing request/response hooks

These variables can also be configured when deploying via Helm. See `helm/values.yaml` for defaults.

### Security Considerations

Ensure the value provided for `XYTE_API_KEY` has only the permissions required
for the tools you expose. Avoid logging this key or any per-user token. Store
all secrets in an `.env` file or a dedicated secrets manager and never commit
them to version control. Rotate keys and tokens periodically and reload the
server after updating the `.env` file. Run `scripts/security_scan.sh` regularly
to check dependencies for vulnerabilities.

### Error Handling

Errors are surfaced to clients using `MCPError` exceptions. Xyte API status codes are translated to
meaningful MCP error codes such as `unauthorized`, `invalid_params`, `not_found`, `method_not_allowed`,
`rate_limited`, or `xyte_server_error`. Network issues are returned as `network_error`.
All errors are logged for debugging purposes.

### Context Defaults

Use the new `set_context` tool to store a default `device_id` or `space_id` for the session. Tools like
`send_command` will automatically fall back to these values if parameters are omitted.

### Device Analytics

The `get_device_analytics_report` tool exposes advanced analytics from the Xyte API to AI agents.

### Room Preset Tools

Use `start_meeting_room_preset` and `shutdown_meeting_room` to quickly prepare or power down a room. These tools abstract multiple device commands into a single call.

### Dry Run Mode

Destructive tools like `send_command` and `delete_device` now accept a `dry_run` flag. When true, the server will log the intended action but skip calling the Xyte API.

## Troubleshooting

If you receive `unauthorized` errors, verify that `XYTE_API_KEY` is correct and has the required permissions. Use `XYTE_USER_TOKEN` when acting on behalf of a specific user. Increase `XYTE_RATE_LIMIT` if you hit rate limit errors during development.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
