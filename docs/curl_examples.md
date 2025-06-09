# Curl Examples

List devices:
```bash
curl -H "Authorization: $XYTE_API_KEY" http://localhost:8080/devices
```

Send command:
```bash
curl -X POST -H "Authorization: $XYTE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"reboot","friendly_name":"Reboot"}' \
     http://localhost:8080/devices/<DEVICE_ID>/commands
```

Get OpenAPI spec:
```bash
curl http://localhost:8080/v1/openapi.json
```

List tickets:
```bash
curl -H "Authorization: $XYTE_API_KEY" http://localhost:8080/v1/tickets
```

Stream events:
```bash
curl http://localhost:8080/v1/events
```

Fetch sanitized config:
```bash
curl -H "Authorization: $XYTE_API_KEY" http://localhost:8080/v1/config
```

