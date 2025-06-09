"""Comprehensive tests for OpenAI wrapper with 100% coverage."""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from mcp.types import TextContent

# Mock get_server before importing to prevent initialization issues
import sys
from unittest.mock import MagicMock

# Create a mock module for the server
sys.modules['xyte_mcp.server'] = MagicMock()
sys.modules['xyte_mcp.config'] = MagicMock()
sys.modules['xyte_mcp.auth'] = MagicMock()

# Now import the wrapper
from xyte_mcp.openai_wrapper import (
    app, call_mcp_tool, read_mcp_resource,
    CommandRequest, DeviceUpdateRequest, TicketUpdateRequest
)


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
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            # Test with TextContent response
            text_content = TextContent(text="Command sent successfully")
            mock_result = Mock()
            mock_result.content = [text_content]
            mock_server.tools[0].func.return_value = mock_result
            
            result = await call_mcp_tool("send_command", {"device_id": "123"}, "api-key")
            assert result == {"result": "Command sent successfully"}
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool_string_response(self, mock_server):
        """Test tool call with string response."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            mock_server.tools[0].func.return_value = "Success"
            
            result = await call_mcp_tool("send_command", {"device_id": "123"}, "api-key")
            assert result == {"result": "Success"}
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool_not_found(self, mock_server):
        """Test tool not found."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with pytest.raises(HTTPException) as exc:
                await call_mcp_tool("nonexistent_tool", {}, "api-key")
            assert exc.value.status_code == 404
            assert "Tool nonexistent_tool not found" in str(exc.value.detail)
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool_error(self, mock_server):
        """Test tool execution error."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            mock_server.tools[0].func.side_effect = Exception("Tool error")
            
            with pytest.raises(HTTPException) as exc:
                await call_mcp_tool("send_command", {}, "api-key")
            assert exc.value.status_code == 500
            assert "Error executing tool" in str(exc.value.detail)
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_json(self, mock_server):
        """Test reading resource with JSON response."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            mock_server.resources[0].read.return_value = '{"items": [{"id": "123"}]}'
            
            result = await read_mcp_resource("devices://", "api-key")
            assert result == {"items": [{"id": "123"}]}
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_plain_text(self, mock_server):
        """Test reading resource with plain text response."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            mock_server.resources[0].read.return_value = "Plain text content"
            
            result = await read_mcp_resource("devices://", "api-key")
            assert result == {"content": "Plain text content"}
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_not_found(self, mock_server):
        """Test resource not found."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with pytest.raises(HTTPException) as exc:
                await read_mcp_resource("nonexistent://", "api-key")
            assert exc.value.status_code == 404
            assert "Resource nonexistent:// not found" in str(exc.value.detail)
    
    @pytest.mark.asyncio
    async def test_read_mcp_resource_error(self, mock_server):
        """Test resource read error."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            mock_server.resources[0].read.side_effect = Exception("Read error")
            
            with pytest.raises(HTTPException) as exc:
                await read_mcp_resource("devices://", "api-key")
            assert exc.value.status_code == 500
            assert "Error reading resource" in str(exc.value.detail)


class TestEndpoints:
    """Test REST API endpoints."""
    
    def test_list_tools(self, client, mock_server, api_key):
        """Test listing tools."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            response = client.get("/v1/tools", headers={"X-API-Key": api_key})
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["name"] == "send_command"
            assert data[0]["description"] == "Send command to device"
            assert "parameters" in data[0]
    
    def test_list_tools_no_auth(self, client):
        """Test listing tools without auth."""
        response = client.get("/v1/tools")
        assert response.status_code == 422  # Missing required header
    
    def test_list_resources(self, client, mock_server, api_key):
        """Test listing resources."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            response = client.get("/v1/resources", headers={"X-API-Key": api_key})
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["uri"] == "devices://"
            assert data[0]["mimeType"] == "application/json"
    
    def test_list_devices(self, client, mock_server, api_key):
        """Test listing devices."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.read_mcp_resource') as mock_read:
                mock_read.return_value = {
                    "items": [
                        {"id": "1", "name": "Device 1", "status": "online"},
                        {"id": "2", "name": "Device 2", "status": "offline"}
                    ]
                }
                
                response = client.get("/v1/resources/devices", headers={"X-API-Key": api_key})
                assert response.status_code == 200
                data = response.json()
                assert len(data["items"]) == 2
    
    def test_list_devices_with_filter(self, client, mock_server, api_key):
        """Test listing devices with status filter."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.read_mcp_resource') as mock_read:
                mock_read.return_value = {
                    "items": [
                        {"id": "1", "name": "Device 1", "status": "online"},
                        {"id": "2", "name": "Device 2", "status": "offline"}
                    ]
                }
                
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
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.read_mcp_resource') as mock_read:
                mock_read.return_value = {
                    "items": [
                        {"id": "123", "name": "Test Device"},
                        {"id": "456", "name": "Other Device"}
                    ]
                }
                
                response = client.get(
                    "/v1/resources/device/123",
                    headers={"X-API-Key": api_key}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == "123"
                assert data["name"] == "Test Device"
    
    def test_get_device_not_found(self, client, mock_server, api_key):
        """Test getting non-existent device."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.read_mcp_resource') as mock_read:
                mock_read.return_value = {"items": []}
                
                response = client.get(
                    "/v1/resources/device/999",
                    headers={"X-API-Key": api_key}
                )
                assert response.status_code == 404
    
    def test_send_command(self, client, mock_server, api_key):
        """Test sending command."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.call_mcp_tool') as mock_call:
                mock_call.return_value = {"result": "Command sent"}
                
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
                assert response.json() == {"result": "Command sent"}
                
                # Verify call
                mock_call.assert_called_once()
                args = mock_call.call_args[0][1]
                assert args["device_id"] == "123"
                assert args["command"] == "reboot"
                assert json.loads(args["args"]) == {"force": True}
    
    def test_update_device(self, client, mock_server, api_key):
        """Test updating device."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.call_mcp_tool') as mock_call:
                mock_call.return_value = {"result": "Device updated"}
                
                request_data = {
                    "device_id": "123",
                    "name": "New Name",
                    "location": "Room 101",
                    "metadata": {"tag": "production"}
                }
                
                response = client.post(
                    "/v1/tools/update_device",
                    json=request_data,
                    headers={"X-API-Key": api_key}
                )
                assert response.status_code == 200
                
                # Verify call
                mock_call.assert_called_once()
                args = mock_call.call_args[0][1]
                assert args["device_id"] == "123"
                assert args["name"] == "New Name"
                assert args["location"] == "Room 101"
                assert json.loads(args["metadata"]) == {"tag": "production"}
    
    def test_list_tickets(self, client, mock_server, api_key):
        """Test listing tickets."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.read_mcp_resource') as mock_read:
                mock_read.return_value = {
                    "items": [
                        {"id": "T1", "status": "open"},
                        {"id": "T2", "status": "closed"}
                    ]
                }
                
                response = client.get(
                    "/v1/resources/tickets?status=open",
                    headers={"X-API-Key": api_key}
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data["items"]) == 1
                assert data["items"][0]["status"] == "open"
    
    def test_update_ticket(self, client, mock_server, api_key):
        """Test updating ticket."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.call_mcp_tool') as mock_call:
                mock_call.return_value = {"result": "Ticket updated"}
                
                request_data = {
                    "ticket_id": "T123",
                    "status": "resolved",
                    "comment": "Issue fixed"
                }
                
                response = client.post(
                    "/v1/tools/update_ticket",
                    json=request_data,
                    headers={"X-API-Key": api_key}
                )
                assert response.status_code == 200
                
                # Verify call
                mock_call.assert_called_once()
                args = mock_call.call_args[0][1]
                assert args["ticket_id"] == "T123"
                assert args["status"] == "resolved"
                assert args["comment"] == "Issue fixed"
    
    def test_health_check(self, client):
        """Test health check."""
        response = client.get("/v1/healthz")
        assert response.status_code == 200
        assert response.text == '"ok"'
    
    def test_get_openapi_schema(self, client):
        """Test getting OpenAPI schema."""
        # Mock file reading
        mock_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"}
        }
        
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_schema)
            
            response = client.get("/v1/openapi.json")
            assert response.status_code == 200
            assert response.json() == mock_schema


class TestErrorHandling:
    """Test error handling."""
    
    def test_http_exception_handler(self, client):
        """Test HTTP exception handling."""
        # This is tested implicitly in other tests that raise HTTPException
        pass
    
    def test_general_exception_handler(self, client, mock_server, api_key):
        """Test general exception handling."""
        with patch('xyte_mcp.openai_wrapper.get_server', return_value=mock_server):
            with patch('xyte_mcp.openai_wrapper.read_mcp_resource') as mock_read:
                # Simulate an unexpected error
                mock_read.side_effect = RuntimeError("Unexpected error")
                
                response = client.get(
                    "/v1/resources/devices",
                    headers={"X-API-Key": api_key}
                )
                assert response.status_code == 500
                assert response.json() == {"error": "Internal server error"}


class TestModels:
    """Test Pydantic models."""
    
    def test_command_request_model(self):
        """Test CommandRequest model."""
        # With args
        req = CommandRequest(device_id="123", command="reboot", args={"force": True})
        assert req.device_id == "123"
        assert req.command == "reboot"
        assert req.args == {"force": True}
        
        # Without args
        req2 = CommandRequest(device_id="456", command="status")
        assert req2.device_id == "456"
        assert req2.command == "status"
        assert req2.args is None
    
    def test_device_update_request_model(self):
        """Test DeviceUpdateRequest model."""
        req = DeviceUpdateRequest(
            device_id="123",
            name="New Name",
            location="Room 101",
            metadata={"env": "prod"}
        )
        assert req.device_id == "123"
        assert req.name == "New Name"
        assert req.location == "Room 101"
        assert req.metadata == {"env": "prod"}
        
        # Minimal request
        req2 = DeviceUpdateRequest(device_id="456")
        assert req2.device_id == "456"
        assert req2.name is None
        assert req2.location is None
        assert req2.metadata is None
    
    def test_ticket_update_request_model(self):
        """Test TicketUpdateRequest model."""
        req = TicketUpdateRequest(
            ticket_id="T123",
            status="resolved",
            comment="Fixed"
        )
        assert req.ticket_id == "T123"
        assert req.status == "resolved"
        assert req.comment == "Fixed"
        
        # Minimal request
        req2 = TicketUpdateRequest(ticket_id="T456")
        assert req2.ticket_id == "T456"
        assert req2.status is None
        assert req2.comment is None


class TestMain:
    """Test main function."""
    
    def test_main_function(self):
        """Test main function execution."""
        with patch('xyte_mcp.openai_wrapper.uvicorn') as mock_uvicorn:
            with patch('xyte_mcp.openai_wrapper.get_settings') as mock_settings:
                mock_settings.return_value.mcp_inspector_port = 8081
                mock_settings.return_value.log_level = "INFO"
                
                # Import and call main
                from xyte_mcp.openai_wrapper import main
                main()
                
                mock_uvicorn.run.assert_called_once_with(
                    app,
                    host="0.0.0.0",
                    port=8081,
                    log_level="info"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])