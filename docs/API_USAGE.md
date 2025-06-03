# API Usage Guide

This document lists the available HTTP routes exposed by the MCP server.
Each example uses JSON-RPC 2.0 over HTTP.

## Resources

| Purpose | Method & Route | Minimal Request | Example Response |
|---------|---------------|-----------------|-----------------|
| List devices | `GET /v1/devices` | n/a | `{ "devices": [...] }` |
| Device status | `GET /v1/device/{id}/status` | n/a | `{ "status": "online" }` |

## Tools

| Purpose | Method & Route | Minimal Request |
|---------|---------------|-----------------|
| Send command | `POST /v1/tools/send_command` | `{ "device_id": "1", "name": "ping" }` |
| Cancel command | `POST /v1/tools/cancel_command` | `{ "device_id": "1", "command_id": "abc" }` |

Responses follow JSON-RPC conventions:

```json
{"jsonrpc":"2.0","result":{"ok":true},"id":1}
```

Common errors include:
- `missing_xyte_key` – Authorization header required in multi-tenant mode.
- `invalid_parameters` – request validation failed.
