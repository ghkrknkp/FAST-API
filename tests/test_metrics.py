import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_endpoint_exposition():
    """Verify GET /metrics returns Prometheus format exposition text."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text

    # Core required metric declarations
    assert "fastapi_requests_total" in text
    assert "fastapi_request_duration_seconds" in text
    assert "fastapi_active_requests" in text
    assert "fastapi_auth_failures_total" in text
    assert "fastapi_rate_limit_exceeded_total" in text
    assert "fastapi_app_health_status" in text


def test_request_counter_increments():
    """Verify that calling an endpoint records a request with its status code."""
    # Hit /users
    resp = client.get("/users")
    assert resp.status_code == 200

    # Fetch metrics
    metrics_resp = client.get("/metrics")
    metrics_text = metrics_resp.text
    # Should contain entry for /users with status 200
    assert 'endpoint="/users"' in metrics_text
    assert 'status_code="200"' in metrics_text


def test_auth_failure_metric_increments():
    """Verify auth failures increment fastapi_auth_failures_total."""
    # Trigger missing key 401
    client.get("/protected")

    metrics_resp = client.get("/metrics")
    assert 'fastapi_auth_failures_total{endpoint="/protected",reason="missing_header"}' in metrics_resp.text


def test_rate_limit_metric_increments():
    """Verify rate limit triggers increment fastapi_rate_limit_exceeded_total."""
    client.get("/simulate-rate-limit")

    metrics_resp = client.get("/metrics")
    assert 'fastapi_rate_limit_exceeded_total{endpoint="/simulate-rate-limit"}' in metrics_resp.text


def test_active_requests_gauge_lifecycle():
    """Verify active requests gauge is cleanly maintained and doesn't leak."""
    response = client.get("/metrics")
    # In idle state after test completion, gauge should be 0.0
    assert "fastapi_active_requests 0.0" in response.text
