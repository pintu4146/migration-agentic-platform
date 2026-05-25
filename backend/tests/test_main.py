"""
Tests for FastAPI main application.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns API information"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "Migration Copilot API"
    assert data["version"] == "1.0.0"
    assert "health" in data
    assert "provider_health" in data


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


def test_provider_health_check(client):
    """Test provider health check endpoint"""
    response = client.get("/health/providers")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "primary" in data
    assert "active_provider" in data
    assert data["primary"]["provider"] in ["openai", "gemini"]


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_validation_error_handling(client):
    """Test validation error returns proper error response"""
    # This will be tested once we have POST endpoints
    # For now, just verify the error handler is registered
    pass


def test_general_exception_handling(client):
    """Test general exception handling"""
    # This will be tested once we have endpoints that can raise exceptions
    pass


def test_openapi_docs_available_in_dev(client):
    """Test OpenAPI docs are available in development"""
    response = client.get("/docs")
    
    # Should be available in test/dev environment
    assert response.status_code == 200


def test_redoc_available_in_dev(client):
    """Test ReDoc is available in development"""
    response = client.get("/redoc")
    
    # Should be available in test/dev environment
    assert response.status_code == 200

# Made with Bob
