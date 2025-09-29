"""
Health check tests for Fantasy TikTok Engine API.

Tests the basic health and version endpoints to ensure API is responsive.
"""

import pytest
import httpx

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"


def test_health_endpoint():
    """Test that the health endpoint returns success."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        
    except httpx.ConnectError:
        pytest.skip("API server not running - start with 'make up'")


def test_version_endpoint():
    """Test that the version endpoint returns version info."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/version")
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        
    except httpx.ConnectError:
        pytest.skip("API server not running - start with 'make up'")


def test_health_endpoint_structure():
    """Test that health endpoint returns properly structured JSON."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) >= 1  # Should have at least status field
        
    except httpx.ConnectError:
        pytest.skip("API server not running - start with 'make up'")