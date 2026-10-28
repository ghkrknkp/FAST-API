import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint returns operational metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "api-monitoring-dashboard"
    assert "version" in data
    assert data["docs_url"] == "/docs"
    assert data["metrics_url"] == "/metrics"
    assert data["dashboard_url"] == "/dashboard"


def test_dashboard_ui_html():
    """Verify frontend monitoring dashboard returns 200 and renders HTML."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Live Alerts" in response.text
    assert "Prometheus Alert Rules Status" in response.text


def test_alerts_api():
    """Verify live alerts evaluation API returns structured alerts list."""
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "alerts" in data
    assert any(a["name"] == "SlowAPIResponse" for a in data["alerts"])
    assert any(a["name"] == "HTTP500Error" for a in data["alerts"])


def test_send_test_email_validation():
    """Verify email endpoint returns 400 when to_email is missing."""
    response = client.post("/api/alerts/send-test-email", json={})
    assert response.status_code == 400
    data = response.json()
    assert "required" in data["message"]


def test_send_test_call_validation():
    """Verify phone call alert endpoint responds correctly."""
    # When phone number is provided, verifies call dispatch logic returns 200
    response = client.post("/api/alerts/send-test-call", json={"to_phone": "+14155552671"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "simulation_only"]


def test_send_test_slack_validation():
    """Verify Slack alert endpoint responds correctly with configured webhook."""
    response = client.post("/api/alerts/send-test-slack", json={"alert_name": "HTTP500Error"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_health_endpoint_healthy():
    """Verify health endpoint default state is healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-monitoring-dashboard"
    assert data["uptime_seconds"] >= 0


def test_health_endpoint_unhealthy_simulation():
    """Verify health endpoint can be toggled to return 503 Service Unavailable."""
    response = client.get("/health?simulate_fail=true")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "Deliberately simulated" in data["details"]["error"]


def test_users_endpoint():
    """Verify /users returns structured list of mock users."""
    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1
    assert "username" in users[0]
    assert "email" in users[0]
    assert "role" in users[0]


def test_products_endpoint():
    """Verify /products returns structured product catalog."""
    response = client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) >= 1
    assert "name" in products[0]
    assert "price" in products[0]


def test_simulate_error_endpoint():
    """Verify /simulate-error returns HTTP 500 without leaking sensitive tracebacks."""
    response = client.get("/simulate-error")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["status_code"] == 500
    # Confirm no Python internal traceback file paths are leaked
    assert "Traceback" not in response.text


def test_simulate_timeout_endpoint():
    """Verify /simulate-timeout handles delay parameter correctly."""
    response = client.get("/simulate-timeout?delay=0.1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["requested_delay_seconds"] == 0.1
    assert data["actual_duration_seconds"] >= 0.1


def test_simulate_rate_limit_endpoint():
    """Verify /simulate-rate-limit returns HTTP 429 and Retry-After header."""
    response = client.get("/simulate-rate-limit")
    assert response.status_code == 429
    assert response.headers.get("retry-after") == "60"
    data = response.json()
    assert "Rate limit exceeded" in data["detail"]
