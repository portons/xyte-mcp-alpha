#!/bin/bash
set -e

# Load .env file if it exists
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Check if XYTE_API_KEY is set
if [ -z "$XYTE_API_KEY" ]; then
    echo "Error: XYTE_API_KEY not found in .env file or environment"
    echo "Create a .env file with: XYTE_API_KEY=your-api-key-here"
    exit 1
fi

echo "Starting Docker containers..."
docker compose -f docker-compose.local.yml up -d

echo "Waiting for services to be ready..."
sleep 10

# Check if MCP server is running
echo "Checking MCP server health..."
curl -s http://localhost:8000/healthz || echo "Warning: MCP server not responding yet"

echo ""
echo "Docker services started!"
echo "MCP server is available at: http://localhost:8000"
echo ""
echo "To connect with ngrok for ChatGPT MCP:"
echo "1. Install ngrok if not already: brew install ngrok"
echo "2. Run: ngrok http 8000"
echo "3. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)"
echo ""
echo "Once ngrok is running, add to ChatGPT:"
echo "1. Go to ChatGPT Settings > Beta features > Enable MCP"
echo "2. Add MCP server with the ngrok HTTPS URL"
echo "3. The server uses SSE (Server-Sent Events) for MCP protocol"
echo ""
echo "The MCP server provides:"
echo "- SSE endpoint at /sse for real-time communication"
echo "- Messages endpoint at /messages/?session_id=XXX for JSON-RPC"
echo "- Full MCP protocol support with tools, resources, and prompts"
echo ""
echo "To view logs: docker compose -f docker-compose.local.yml logs -f mcp"
echo "To stop: docker compose -f docker-compose.local.yml down"