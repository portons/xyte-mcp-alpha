"""Setup Swagger documentation for the MCP API."""

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# Security scheme
security = HTTPBearer()


def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract API key from Authorization header."""
    return credentials.credentials


# Models for documentation
class Device(BaseModel):
    id: str
    name: str
    status: str
    model: Dict[str, Any]
    space: Dict[str, Any]


class DeviceList(BaseModel):
    items: List[Device]


class HealthResponse(BaseModel):
    status: str = "ok"


class ConfigResponse(BaseModel):
    environment: str
    rate_limit_per_minute: int
    multi_tenant: bool


def create_documented_app(base_app) -> FastAPI:
    """Create a FastAPI app with proper documentation."""
    
    app = FastAPI(
        title="Xyte MCP API",
        description="MCP server for Xyte organization API - manage devices, tickets, and automation",
        version="1.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Devices", "description": "Device management operations"},
            {"name": "Health", "description": "Health check endpoints"},
            {"name": "Configuration", "description": "Server configuration"},
            {"name": "Events", "description": "Event streaming"},
            {"name": "Tasks", "description": "Async task management"},
        ]
    )
    
    # Don't create actual routes - just document the API
    # The actual implementation is handled by the mounted Starlette app
    
    # Just mount the base app - it will handle all requests
    app.mount("/", base_app)
    
    # Override the OpenAPI schema to document our actual endpoints
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = {
            "openapi": "3.0.0",
            "info": {
                "title": "Xyte MCP API",
                "version": "1.1.0",
                "description": "MCP server for Xyte organization API"
            },
            "servers": [{"url": "/"}],
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "description": "Enter your Xyte API key"
                    }
                }
            },
            "security": [{"ApiKeyAuth": []}],
            "paths": {
                "/v1/devices": {
                    "get": {
                        "tags": ["Devices"],
                        "summary": "List all devices",
                        "operationId": "list_devices",
                        "security": [{"ApiKeyAuth": []}],
                        "responses": {
                            "200": {
                                "description": "List of devices",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "items": {
                                                    "type": "array",
                                                    "items": {"type": "object"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/v1/healthz": {
                    "get": {
                        "tags": ["Health"],
                        "summary": "Liveness probe",
                        "operationId": "healthz",
                        "responses": {
                            "200": {
                                "description": "Service is alive",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/v1/readyz": {
                    "get": {
                        "tags": ["Health"],
                        "summary": "Readiness probe",
                        "operationId": "readyz",
                        "responses": {
                            "200": {
                                "description": "Service is ready",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/v1/config": {
                    "get": {
                        "tags": ["Configuration"],
                        "summary": "Get server configuration",
                        "operationId": "get_config",
                        "security": [{"ApiKeyAuth": []}],
                        "responses": {
                            "200": {
                                "description": "Server configuration",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "environment": {"type": "string"},
                                                "rate_limit_per_minute": {"type": "integer"},
                                                "multi_tenant": {"type": "boolean"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/v1/events": {
                    "get": {
                        "tags": ["Events"],
                        "summary": "Stream events",
                        "operationId": "stream_events",
                        "responses": {
                            "200": {
                                "description": "Server-sent event stream",
                                "content": {
                                    "text/event-stream": {
                                        "schema": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "/v1/tickets": {
                    "get": {
                        "tags": ["Devices"],
                        "summary": "List all tickets",
                        "operationId": "list_tickets",
                        "security": [{"ApiKeyAuth": []}],
                        "responses": {
                            "200": {
                                "description": "List of tickets",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/v1/metrics": {
                    "get": {
                        "tags": ["Health"],
                        "summary": "Prometheus metrics",
                        "operationId": "metrics",
                        "responses": {
                            "200": {
                                "description": "Prometheus metrics",
                                "content": {
                                    "text/plain": {
                                        "schema": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    return app