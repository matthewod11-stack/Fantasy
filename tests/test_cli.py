"""
CLI tests for Fantasy TikTok Engine.

Tests the ff-post CLI tool against the local API server.
"""

import subprocess
import sys
import pytest
import httpx

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"


def is_api_running() -> bool:
    """Check if the API server is running and responsive."""
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.mark.skipif(not is_api_running(), reason="API server not running")
def test_cli_generate_start_sit():
    """Test CLI generation of start-sit content."""
    
    # Run the CLI command
    result = subprocess.run([
        sys.executable, "-m", "apps.cli.ff_post",
        "--player", "Test Player",
        "--week", "5", 
        "--type", "start-sit"
    ], capture_output=True, text=True, timeout=30)
    
    # Check command succeeded
    assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"
    
    # Check output contains expected content
    output = result.stdout
    assert "Content generated successfully" in output
    assert "Generated Script" in output
    assert "Test Player" in output
    assert "WEEK 5" in output


@pytest.mark.skipif(not is_api_running(), reason="API server not running")
def test_cli_generate_waiver_wire():
    """Test CLI generation of waiver-wire content."""
    
    result = subprocess.run([
        sys.executable, "-m", "apps.cli.ff_post",
        "--player", "Waiver Pickup",
        "--week", "3",
        "--type", "waiver-wire"
    ], capture_output=True, text=True, timeout=30)
    
    assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"
    
    output = result.stdout
    assert "Content generated successfully" in output
    assert "Waiver Pickup" in output


@pytest.mark.skipif(not is_api_running(), reason="API server not running") 
def test_cli_health_command():
    """Test CLI health check command."""
    
    result = subprocess.run([
        sys.executable, "-m", "apps.cli.ff_post",
        "health"
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0, f"Health command failed: {result.stderr}"
    assert "API server is healthy" in result.stdout


def test_cli_invalid_week():
    """Test CLI validation for invalid week numbers."""
    
    result = subprocess.run([
        sys.executable, "-m", "apps.cli.ff_post", 
        "--player", "Test Player",
        "--week", "25",  # Invalid week number
        "--type", "start-sit"
    ], capture_output=True, text=True, timeout=10)
    
    # Should fail with validation error
    assert result.returncode != 0
    assert "Week must be between 1 and 18" in result.stderr


def test_cli_missing_required_args():
    """Test CLI behavior with missing required arguments."""
    
    result = subprocess.run([
        sys.executable, "-m", "apps.cli.ff_post"
        # Missing all required arguments
    ], capture_output=True, text=True, timeout=10)
    
    # Should fail and show help
    assert result.returncode != 0