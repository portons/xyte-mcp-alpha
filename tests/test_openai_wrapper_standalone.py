"""Standalone tests for OpenAI wrapper that avoid circular imports."""

import json
import sys
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock all the dependencies before importing
sys.modules['xyte_mcp'] = MagicMock()
sys.modules['xyte_mcp.server'] = MagicMock()
sys.modules['xyte_mcp.config'] = MagicMock()
sys.modules['xyte_mcp.auth'] = MagicMock()
sys.modules['xyte_mcp.logging_utils'] = MagicMock()
sys.modules['xyte_mcp.plugin'] = MagicMock()
sys.modules['xyte_mcp.utils'] = MagicMock()
sys.modules['xyte_mcp.plugins'] = MagicMock()
sys.modules['xyte_mcp.plugins.sample'] = MagicMock()

# Mock mcp module
mock_mcp = MagicMock()
mock_mcp.types.TextContent = Mock
sys.modules['mcp'] = mock_mcp
sys.modules['mcp.types'] = mock_mcp.types

# Now we can import just the openai_wrapper module
import importlib.util
spec = importlib.util.spec_from_file_location(
    "openai_wrapper", 
    str(Path(__file__).parent.parent / "src" / "xyte_mcp" / "openai_wrapper.py")
)
openai_wrapper = importlib.util.module_from_spec(spec)
sys.modules['openai_wrapper'] = openai_wrapper

# Mock get_server and get_settings before executing the module
openai_wrapper.get_server = MagicMock()
openai_wrapper.get_settings = MagicMock()

# Execute the module
spec.loader.exec_module(openai_wrapper)

# Import what we need from the module
app = openai_wrapper.app
call_mcp_tool = openai_wrapper.call_mcp_tool
read_mcp_resource = openai_wrapper.read_mcp_resource
CommandRequest = openai_wrapper.CommandRequest
DeviceUpdateRequest = openai_wrapper.DeviceUpdateRequest
TicketUpdateRequest = openai_wrapper.TicketUpdateRequest
TextContent = openai_wrapper.TextContent
validate_api_key = openai_wrapper.validate_api_key

# Import FastAPI's test client
from fastapi.testclient import TestClient
from fastapi import HTTPException


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_server():
    """Create mock MCP server."""
    server = Mock()
    
    # Mock tools
    tool1 = Mock()
    tool1.name = "send_command"
    tool1.description = "Send command to device"
    tool1.func = AsyncMock()
    tool1.inputSchema = {"type": "object"}
    
    tool2 = Mock()
    tool2.name = "update_device"
    tool2.description = "Update device"
    tool2.func = AsyncMock()
    
    tool3 = Mock()
    tool3.name = "update_ticket"
    tool3.description = "Update ticket"
    tool3.func = AsyncMock()
    
    server.tools = [tool1, tool2, tool3]
    
    # Mock resources
    resource1 = Mock()
    resource1.uri = "devices://"
    resource1.name = "devices"
    resource1.description = "List devices"
    resource1.mimeType = "application/json"
    resource1.read = AsyncMock()
    
    resource2 = Mock()
    resource2.uri = "tickets://"
    resource2.name = "tickets"
    resource2.description = "List tickets"
    resource2.read = AsyncMock()
    
    server.resources = [resource1, resource2]
    
    return server


@pytest.fixture
def api_key():
    """Test API key."""
    return "test-api-key-123"


class TestMCPHelpers:
    """Test MCP helper functions."""
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool_success(self, mock_server):
        """Test successful tool call."""
        openai_wrapper.get_server.return_value = mock_server
        
        # Test with TextContent response
        text_content = Mock()
        text_content.text = "Command sent successfully"
        mock_result = Mock()
        mock_result.content = [text_content]
        mock_server.tools[0].func.return_value = mock_result
        
        result = await call_mcp_tool("send_command", {"device_id": "123"}, "api-key")
        assert result == {"result": "Command sent successfully"}
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool_string_response(self, mock_server):
        """Test tool call with string response."""
        openai_wrapper.get_server.return_value = mock_server
        mock_server.tools[0].func.return_value = "Success"
        
        result = await call_mcp_tool("send_command", {"device_id": "123"}, "api-key")
        assert result == {"result": "Success"}
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool_not_found(self, mock_server):
        """Test tool not found."""
        openai_wrapper.get_server.return_value = mock_server
        
        with pytest.raises(HTTPException) as exc:
            await call_mcp_tool("nonexistent_tool", {}, "api-key")
        assert exc.value.status_code == 404
        assert "Tool nonexistent_tool not found" in str(exc.value.detail)
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool_error(self, mock_server):
        """Test tool execution error."""
        openai_wrapper.get_server.return_value = mock_server
        mock_server.tools[0].func.side_effect = Exception("Tool error")
        
        with pytest.raises(HTTPException) as exc:
            await call_mcp_tool("send_command", {}, "api-key")
        assert exc.value.status_code == 500
        assert "Error executing tool" in str(exc.value.detail)
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_json(self, mock_server):
        """Test reading resource with JSON response."""
        openai_wrapper.get_server.return_value = mock_server
        mock_server.resources[0].read.return_value = '{"items": [{"id": "123"}]}'
        
        result = await read_mcp_resource("devices://", "api-key")
        assert result == {"items": [{"id": "123"}]}
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_plain_text(self, mock_server):
        """Test reading resource with plain text response."""
        openai_wrapper.get_server.return_value = mock_server
        mock_server.resources[0].read.return_value = "Plain text content"
        
        result = await read_mcp_resource("devices://", "api-key")
        assert result == {"content": "Plain text content"}
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_not_found(self, mock_server):
        """Test resource not found."""
        openai_wrapper.get_server.return_value = mock_server
        
        with pytest.raises(HTTPException) as exc:
            await read_mcp_resource("nonexistent://", "api-key")
        assert exc.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_error(self, mock_server):
        """Test resource read error."""
        openai_wrapper.get_server.return_value = mock_server
        mock_server.resources[0].read.side_effect = Exception("Read error")
        
        with pytest.raises(HTTPException) as exc:
            await read_mcp_resource("devices://", "api-key")
        assert exc.value.status_code == 500


class TestEndpoints:
    """Test REST API endpoints."""
    
    def test_list_tools(self, client, mock_server, api_key):
        """Test listing tools."""
        openai_wrapper.get_server.return_value = mock_server
        
        response = client.get("/v1/tools", headers={"X-API-Key": api_key})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["name"] == "send_command"
    
    def test_list_tools_no_auth(self, client):
        """Test listing tools without auth."""
        response = client.get("/v1/tools")
        assert response.status_code == 422
    
    def test_list_resources(self, client, mock_server, api_key):
        """Test listing resources."""
        openai_wrapper.get_server.return_value = mock_server
        
        response = client.get("/v1/resources", headers={"X-API-Key": api_key})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_list_devices(self, client, mock_server, api_key):
        """Test listing devices."""
        openai_wrapper.get_server.return_value = mock_server
        
        # Mock read_mcp_resource
        async def mock_read(*args, **kwargs):
            return {
                "items": [
                    {"id": "1", "name": "Device 1", "status": "online"},
                    {"id": "2", "name": "Device 2", "status": "offline"}
                ]
            }
        
        with patch.object(openai_wrapper, 'read_mcp_resource', side_effect=mock_read):
            response = client.get("/v1/resources/devices", headers={"X-API-Key": api_key})
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
    
    def test_list_devices_with_filter(self, client, mock_server, api_key):
        """Test listing devices with status filter."""
        openai_wrapper.get_server.return_value = mock_server
        
        async def mock_read(*args, **kwargs):
            return {
                "items": [
                    {"id": "1", "name": "Device 1", "status": "online"},
                    {"id": "2", "name": "Device 2", "status": "offline"}
                ]
            }
        
        with patch.object(openai_wrapper, 'read_mcp_resource', side_effect=mock_read):
            response = client.get(
                "/v1/resources/devices?status=online",
                headers={"X-API-Key": api_key}
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["status"] == "online"
    
    def test_get_device(self, client, mock_server, api_key):
        """Test getting specific device."""
        openai_wrapper.get_server.return_value = mock_server
        
        async def mock_read(*args, **kwargs):
            return {
                "items": [
                    {"id": "123", "name": "Test Device"},
                    {"id": "456", "name": "Other Device"}
                ]
            }
        
        with patch.object(openai_wrapper, 'read_mcp_resource', side_effect=mock_read):
            response = client.get(
                "/v1/resources/device/123",
                headers={"X-API-Key": api_key}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "123"
    
    def test_send_command(self, client, mock_server, api_key):
        """Test sending command."""
        openai_wrapper.get_server.return_value = mock_server
        
        async def mock_call(*args, **kwargs):
            return {"result": "Command sent"}
        
        with patch.object(openai_wrapper, 'call_mcp_tool', side_effect=mock_call):
            request_data = {
                "device_id": "123",
                "command": "reboot",
                "args": {"force": True}
            }
            
            response = client.post(
                "/v1/tools/send_command",
                json=request_data,
                headers={"X-API-Key": api_key}
            )
            assert response.status_code == 200
    
    def test_health_check(self, client):
        """Test health check."""
        response = client.get("/v1/healthz")
        assert response.status_code == 200
        assert response.text == '"ok"'
    
    def test_get_openapi_schema(self, client):
        """Test getting OpenAPI schema."""
        mock_schema = {"openapi": "3.0.0"}
        
        m = mock_open(read_data=json.dumps(mock_schema))
        with patch("builtins.open", m):
            response = client.get("/v1/openapi.json")
            assert response.status_code == 200
            assert response.json() == mock_schema


class TestErrorHandling:
    """Test error handling."""
    
    def test_general_exception_handler(self, client, mock_server, api_key):
        """Test general exception handling."""
        openai_wrapper.get_server.return_value = mock_server
        
        async def mock_read(*args, **kwargs):
            raise RuntimeError("Unexpected error")
        
        with patch.object(openai_wrapper, 'read_mcp_resource', side_effect=mock_read):
            response = client.get(
                "/v1/resources/devices",
                headers={"X-API-Key": api_key}
            )
            assert response.status_code == 500
            assert response.json() == {"error": "Internal server error"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])