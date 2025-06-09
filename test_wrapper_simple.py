"""Simple test to verify the OpenAI wrapper works."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock the dependencies
from unittest.mock import Mock, AsyncMock

# Create mocks
mock_server = Mock()
mock_server.tools = []
mock_server.resources = []

mock_settings = Mock()
mock_settings.log_level = "INFO"
mock_settings.mcp_inspector_port = 8081

# Import and mock
import xyte_mcp.openai_wrapper as wrapper
wrapper.get_server = lambda: mock_server
wrapper.get_settings = lambda: mock_settings
wrapper.validate_api_key = AsyncMock()

app = wrapper.app
from fastapi.testclient import TestClient

# Create test client
client = TestClient(app)

# Run tests
print("Testing health endpoint...")
response = client.get("/v1/healthz")
assert response.status_code == 200
assert response.text == '"ok"'
print("✓ Health check passed")

print("\nTesting tools endpoint...")
response = client.get("/v1/tools", headers={"X-API-Key": "test"})
assert response.status_code == 200
assert response.json() == []
print("✓ Tools endpoint passed")

print("\nTesting resources endpoint...")
response = client.get("/v1/resources", headers={"X-API-Key": "test"})
assert response.status_code == 200
assert response.json() == []
print("✓ Resources endpoint passed")

print("\nTesting missing auth...")
response = client.get("/v1/tools")
assert response.status_code == 422
print("✓ Auth validation passed")

print("\n✅ All tests passed!")
print("\nTo run the wrapper:")
print("1. export XYTE_API_KEY='your-api-key'")
print("2. docker compose -f docker-compose.local.yml up")
print("3. The wrapper will be available on port 8001")
print("4. Use ngrok: ngrok http 8001 --domain fe.ngrok.io")