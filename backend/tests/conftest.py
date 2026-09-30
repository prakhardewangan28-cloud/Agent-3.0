"""Pytest configuration and fixtures."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(autouse=True)
def reset_gemini_counter():
    """Reset Gemini session counter before each test."""
    from app.services.gemini_client import reset_session_counter
    reset_session_counter()
    yield
    reset_session_counter()


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.
    
    Returns:
        TestClient: Configured test client
    """
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """
    Mock settings for testing.
    
    Returns:
        Dict with test configuration
    """
    return {
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
        "serpapi_key": "test-serpapi-key",
        "openai_api_key": "test-openai-key",
        "log_level": "DEBUG",
        "max_search_results": 5,
    }
