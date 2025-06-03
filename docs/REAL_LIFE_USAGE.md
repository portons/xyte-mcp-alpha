# Real-Life Usage Examples

## Curl

```bash
curl -H "X-XYTE-API-KEY: XYTE_live_ABC..." \
     -H "Content-Type: application/json" \
     -d '{"method":"tools/call","params":{"name":"start_meeting_room_preset","arguments":{"room":"Board"}}, "id":1,"jsonrpc":"2.0"}' \
     https://mcp.example.com
```

## Claude Desktop `host.json`

```json
{
  "url": "https://mcp.example.com",
  "headers": {
    "x-xyte-api-key": "XYTE_live_ABC..."
  }
}
```
