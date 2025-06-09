# Hosting Xyte MCP as a Remote Service

## What is SSE?

SSE (Server-Sent Events) is a standard for servers to push real-time updates to clients over HTTP. In the context of MCP, it allows:
- Claude to connect to your MCP server over the internet
- Real-time streaming of responses
- No need for local installation on user machines

## Architecture for Hosted MCP

### Current Setup (Local)
```
Claude Desktop → Local Process → MCP Server → Xyte API
```

### Hosted Setup (Remote)
```
Claude Desktop → HTTPS/SSE → Your Server → MCP Server → Xyte API
```

## How to Host Xyte MCP

### Option 1: Deploy to Cloud (Recommended)

1. **Modify the server to support SSE transport**:
```python
# In server.py or a new file
from mcp.server.sse import SseServerTransport
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/sse")
async def sse_endpoint(request: Request):
    # Create SSE transport
    transport = SseServerTransport()
    
    # Handle MCP protocol over SSE
    server = get_server()
    return StreamingResponse(
        server.run_sse(transport),
        media_type="text/event-stream"
    )
```

2. **Add authentication**:
```python
@app.get("/sse")
async def sse_endpoint(
    request: Request,
    api_key: str = Header(None, alias="Authorization")
):
    if not api_key or not validate_api_key(api_key):
        raise HTTPException(401, "Invalid API key")
    
    # ... rest of SSE handling
```

3. **Deploy to a platform**:
   - **Heroku**: Easy deployment with `Procfile`
   - **AWS**: Use ECS or Lambda with API Gateway
   - **Google Cloud Run**: Serverless with automatic scaling
   - **DigitalOcean App Platform**: Simple container deployment

### Option 2: Quick Setup with ngrok (Testing)

1. **Run the HTTP server**:
```bash
python -m xyte_mcp.http
```

2. **Expose with ngrok**:
```bash
ngrok http 8080
```

3. **Configure Claude**:
```json
{
  "mcpServers": {
    "xyte-remote": {
      "command": "curl",
      "args": [
        "-N",
        "-H", "Authorization: YOUR_API_KEY",
        "https://your-ngrok-url.ngrok.io/sse"
      ]
    }
  }
}
```

## Implementation Plan

### 1. Create SSE Endpoint
```python
# src/xyte_mcp/sse_server.py
import asyncio
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import StreamingResponse
from mcp.server.sse import SseServerTransport
from .server import get_server
from .config import get_settings

app = FastAPI()

async def validate_request(api_key: str, org_id: str = None):
    """Validate API key and optional org filtering."""
    if not api_key:
        raise HTTPException(401, "API key required")
    
    # Add validation logic
    return True

@app.get("/sse")
async def mcp_sse(
    request: Request,
    authorization: str = Header(None),
    x_org_id: str = Header(None)
):
    """MCP over Server-Sent Events endpoint."""
    await validate_request(authorization, x_org_id)
    
    async def event_generator():
        # Initialize MCP server with the API key
        server = get_server()
        server.context.api_key = authorization
        
        # Create SSE transport
        transport = SseServerTransport()
        
        # Run the server
        async for event in server.run_sse(transport, request):
            yield f"data: {event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )

@app.get("/health")
async def health():
    return {"status": "ok", "service": "xyte-mcp"}
```

### 2. Deployment Configuration

**Dockerfile for production**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8080
CMD ["uvicorn", "xyte_mcp.sse_server:app", "--host", "0.0.0.0", "--port", "8080"]
```

**docker-compose.yml**:
```yaml
version: '3.8'
services:
  mcp-sse:
    build: .
    ports:
      - "8080:8080"
    environment:
      - XYTE_BASE_URL=https://hub.xyte.io/core/v1/organization
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
```

### 3. Client Configuration

Users would configure Claude like this:

```json
{
  "mcpServers": {
    "xyte": {
      "command": "curl",
      "args": [
        "-N",
        "-H", "Authorization: YOUR_API_KEY",
        "https://mcp.xyte.io/sse"
      ]
    }
  }
}
```

Or with environment variables:
```json
{
  "mcpServers": {
    "xyte": {
      "command": "sh",
      "args": [
        "-c",
        "curl -N -H \"Authorization: $XYTE_API_KEY\" https://mcp.xyte.io/sse"
      ],
      "env": {
        "XYTE_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

## Benefits of Hosted MCP

1. **No local installation** - Users just need Claude Desktop
2. **Centralized updates** - Update server once, all users get it
3. **Access control** - Manage permissions server-side
4. **Usage analytics** - Track how PM uses the system
5. **Multi-tenant** - One server, multiple organizations
6. **Cross-platform** - Works on any OS with Claude

## Security Considerations

1. **Use HTTPS only** - Encrypt all traffic
2. **API key validation** - Verify keys server-side
3. **Rate limiting** - Prevent abuse
4. **Audit logging** - Track all operations
5. **CORS headers** - Restrict origins if needed
6. **Input validation** - Sanitize all inputs

## Next Steps

1. Implement SSE endpoint in the codebase
2. Add proper error handling and reconnection
3. Set up deployment pipeline
4. Configure monitoring and logging
5. Create subdomain (mcp.xyte.io)
6. Add to Anthropic's MCP directory