import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

client = TestClient(app)


def test_protected_missing_api_key():
    """Verify missing X-API-Key header returns HTTP 401 Unauthorized."""
    response = client.get("/protected")
    assert response.status_code == 401
    data = response.json()
    assert "Missing required authentication header" in data["detail"]
    assert response.headers.get("www-authenticate") == "ApiKey"


def test_protected_invalid_api_key():
    """Verify invalid API key returns HTTP 401 Unauthorized."""
    response = client.get("/protected", headers={"X-API-Key": "completely-invalid-key-xyz"})
    assert response.status_code == 401
    data = response.json()
    assert "Invalid authentication credentials" in data["detail"]
    # Ensure key value itself is never reflected in the output
    assert "completely-invalid-key-xyz" not in response.text


def test_protected_valid_api_key():
    """Verify valid configured API key returns HTTP 200 OK."""
    response = client.get("/protected", headers={"X-API-Key": settings.API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Authenticated successfully" in data["message"]
    assert "accessed_at" in data
