# FastAPI API Monitoring Dashboard

A production-grade, end-to-end API Observability and Monitoring stack built with **FastAPI**, **Prometheus**, and **Alertmanager**.

[![Loom Video Walkthrough](https://img.shields.io/badge/Loom_Demo_Video-Watch_Walkthrough-blue?style=for-the-badge&logo=loom)](https://www.loom.com/share/84959d2b553649eba5a9f97f7b4907fa)

> 🎥 **Video Walkthrough Demonstration:**  
> Watch the complete 5-minute video demonstration covering server setup, web dashboard, failure simulations, Slack notifications, and Gmail SMTP alerts:  
> **Link:** [https://www.loom.com/share/84959d2b553649eba5a9f97f7b4907fa](https://www.loom.com/share/84959d2b553649eba5a9f97f7b4907fa)

Designed to track real-time API health, monitor latency (SLA > 3.0s), analyze HTTP status distributions, detect anomalies, trigger actionable alerts, and provide systematic root-cause analysis (RCA).

---

## 1. Project Overview

This repository provides an enterprise monitoring infrastructure for FastAPI REST APIs based on modern SRE best practices (Google SRE Book & RED Method: Rate, Errors, Duration). It instruments application metrics at the ASGI middleware level, exports them in Prometheus exposition format, provisions automated Grafana visualizations, and alerts on service degradation via Prometheus Alertmanager.

---

## 2. Assignment Requirements Covered

| Requirement | Implementation Detail | Status |
| :--- | :--- | :--- |
| **Sample FastAPI REST API** | Endpoints: `/`, `/health`, `/users`, `/products` with Pydantic validation | Complete |
| **Failure Simulations** | Endpoints: `/simulate-error`, `/simulate-timeout`, `/simulate-rate-limit`, `/protected` | Complete |
| **API Availability & Uptime** | Scraped by Prometheus (`up{job="fastapi"}`), 30m rolling uptime in Grafana | Complete |
| **Latency Tracking (> 3s SLA)** | High-resolution histogram `fastapi_request_duration_seconds` + counter `fastapi_slow_requests_total` | Complete |
| **Status Codes & Error Trends** | Full tracking of 2xx, 4xx, 5xx, 401 auth failures, and 429 rate limit events | Complete |
| **Server & Host Metrics** | Background collector for process CPU, RSS memory, system CPU, and system memory | Complete |
| **Grafana Monitoring Dashboard** | 7-section dark-theme dashboard auto-provisioned via JSON (`fastapi-monitoring-dashboard`) | Complete |
| **Alert Rules Configuration** | Downtime, slow response (> 3s), HTTP 500 errors, high failure rate, health check failures | Complete |
| **Alertmanager Notifications** | Alert grouping, repeat intervals, email (SMTP) & Slack webhook receivers | Complete |
| **Automated Testing** | Pytest unit and integration test suite covering endpoints, auth, and metrics | Complete |
| **Automated Failure Script** | `scripts/run_failure_demo.py` simulating all 4 incidents and populating metrics | Complete |
| **Root Cause Analysis (RCA)** | Rigorous SRE post-incident reports documenting cause, telemetry, and remediation | Complete |

---

## 3. Technology Stack

- **Backend**: Python 3.11+, FastAPI 0.110+, Uvicorn, Pydantic v2, `prometheus-client`, `psutil`.
- **Testing**: `pytest`, `httpx`, `requests`.
- **Metrics & Alerting**: Prometheus 2.50.1, Prometheus Alertmanager 0.27.0.
- **Visualization**: Grafana 10.4.0 (Pre-provisioned Prometheus datasource and 7-section dashboard).
- **Orchestration**: Docker & Docker Compose v2.

---

## 4. Architecture & Request Flow

```text
Client Traffic
      |
      v
+-----------------------------------------------------------------------------------+
| FastAPI Application (Port 8000)                                                   |
|   |-- Business Endpoints: /, /health, /users, /products                           |
|   |-- Failure Simulations: /simulate-error, /simulate-timeout, /simulate-rate-limit|
|   |-- Security Dependency: /protected (requires X-API-Key)                         |
|   |-- PrometheusMiddleware (ASGI):                                                |
|   |     * In-flight Gauge (fastapi_active_requests)                               |
|   |     * Latency Histogram (fastapi_request_duration_seconds)                    |
|   |     * Total Request Counter (fastapi_requests_total)                          |
|   |-- System Metrics: psutil background collector                                 |
|   |-- Exposition Endpoint: GET /metrics                                           |
+-----------------------------------------------------------------------------------+
                                         ^
                                         | Scrapes every 5s
+----------------------------------------+------------------------------------------+
| Prometheus (Port 9090)                                                            |
|   |-- Scrapes fastapi:8000/metrics                                                |
|   |-- Evaluates alert rules every 5s (alert_rules.yml)                            |
+-------------------+---------------------------------------+-----------------------+
                    |                                       | Firing alerts
                    v PromQL                                v
+------------------------------------+      +---------------------------------------+
| Grafana Dashboard (Port 3000)      |      | Prometheus Alertmanager (Port 9093)   |
|   |-- Pre-provisioned Dashboards   |      |   |-- Alert deduplication & grouping  |
|   |-- 7 Visual Monitoring Sections |      |   |-- Notification Receivers:         |
|   |-- Real-time Prometheus queries |      |         * SMTP Email                  |
+------------------------------------+      |         * Slack Webhook               |
                                            +---------------------------------------+
```

---

## 5. Project Structure

```text
api-monitoring-dashboard/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # Application entrypoint & lifespan
│   ├── config.py                # Environment configuration & Pydantic settings
│   ├── schemas.py               # Response data models
│   ├── logging_config.py        # Structured JSON logger
│   ├── metrics.py               # Prometheus metric registry & psutil collector
│   ├── middleware.py            # High-reliability ASGI metrics middleware
│   ├── auth.py                  # API Key security dependency
│   └── routers/
│       ├── __init__.py
│       ├── health.py            # /health probe & state toggle
│       ├── users.py             # GET /users
│       ├── products.py          # GET /products
│       └── simulations.py       # /simulate-error, /simulate-timeout, /simulate-rate-limit, /protected
│
├── monitoring/
│   ├── prometheus.yml           # Prometheus scrape configuration
│   ├── alert_rules.yml          # Prometheus alert rules
│   ├── alertmanager.yml         # Active local Alertmanager configuration
│   └── alertmanager.yml.example # Template with SMTP and Slack credentials
│
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml   # Auto-provisioned Prometheus datasource
│       └── dashboards/
│           ├── dashboard.yml    # Auto-provisioned dashboard provider
│           └── api-monitoring-dashboard.json # Production 7-section dashboard definition
│
├── tests/
│   ├── __init__.py
│   ├── test_endpoints.py        # Endpoint and simulation tests
│   ├── test_auth.py             # Authentication failure tests (401)
│   └── test_metrics.py          # Metric increment & exposition tests
│
├── scripts/
│   ├── run_failure_demo.py      # Automated failure scenario burst generator
│   └── verify_monitoring.py     # Monitoring stack verification utility
│
├── docs/
│   └── root_cause_analysis.md   # Standardized RCA incident documentation
│
├── screenshots/
│   ├── README.md                # Guide for capturing submission screenshots
│   ├── dashboard.png            # (Target) Grafana dashboard capture
│   ├── prometheus-targets.png   # (Target) Prometheus target health capture
│   └── alert-proof.png          # (Target) Alert firing evidence capture
│
├── Dockerfile                   # Multi-stage, non-root Python 3.11 container
├── docker-compose.yml           # Multi-service stack definition
├── requirements.txt             # Pinned project dependencies
├── .env.example                 # Environment configuration template
├── .gitignore                   # Excludes secrets, caches, and metric data
└── README.md                    # Complete project guide
```

---

## 6. Prerequisites

- Python 3.11+ (for local development and testing)
- Docker & Docker Compose v2 (for containerized stack execution)
- Git & cURL

---

## 7. Python Environment Setup

Clone the repository and set up a Python virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Activate on Linux/macOS:
source venv/bin/activate
```

---

## 8. Installing Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. Running FastAPI Locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 10. Running the Monitoring Stack with Docker Compose

Start the full stack (FastAPI, Prometheus, Grafana, Alertmanager) with persistent volumes:

```bash
docker compose up -d --build
```

To view running containers:
```bash
docker compose ps
```

To shut down the stack:
```bash
docker compose down
```

---

## 11. Accessing Swagger Documentation

Open your browser to:
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 12. Accessing Prometheus

- **Prometheus Dashboard**: `http://localhost:9090`
- **Scrape Targets**: `http://localhost:9090/targets` (Verify `fastapi` target is `UP`)
- **Active Alert Rules**: `http://localhost:9090/alerts`

---

## 13. Accessing Grafana

- **Grafana URL**: `http://localhost:3000`
- **Default Credentials**: Username `admin` / Password `admin`
- The **API Monitoring Dashboard** is auto-provisioned upon login under the **Observability** folder.

---

## 14. Accessing Alertmanager

- **Alertmanager Web UI**: `http://localhost:9093`
- Inspect alert routing, silences, and notification receivers.

---

## 15. Available API Endpoints

| `GET` | `/dashboard` | Interactive White & Black Frontend Monitoring & Alerts UI | 200 OK (HTML) |
| `GET` | `/api/alerts` | Real-time evaluated Prometheus Alert Rules API | 200 OK (JSON) |
| `GET` | `/` | Root endpoint displaying service metadata | 200 OK |
| `GET` | `/health` | Application health and readiness probe | 200 OK / 503 Unavailable |
| `POST`| `/health/toggle-state` | Admin toggle to simulate unhealthy state | 200 OK |
| `GET` | `/users` | Lists fictional sample users | 200 OK |
| `GET` | `/products` | Lists fictional sample catalog products | 200 OK |
| `GET` | `/protected` | Demonstrates API Key authentication (`X-API-Key`) | 200 OK / 401 Unauthorized |
| `GET` | `/simulate-error` | Deliberately triggers internal server error | 500 Internal Server Error |
| `GET` | `/simulate-timeout` | Simulates slow response (default 3.5s > 3s SLA) | 200 OK |
| `GET` | `/simulate-rate-limit`| Simulates rate-limit rejection with `Retry-After: 60` | 429 Too Many Requests |
| `GET` | `/metrics` | Exposes metrics in Prometheus exposition format | 200 OK |

---

## 16. Metrics Catalog and Definitions

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `fastapi_requests_total` | Counter | `method`, `endpoint`, `status_code` | Total completed HTTP requests |
| `fastapi_request_duration_seconds` | Histogram | `method`, `endpoint` | Latency distribution with buckets: [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0] |
| `fastapi_active_requests` | Gauge | None | Number of concurrent in-flight requests |
| `fastapi_auth_failures_total` | Counter | `endpoint`, `reason` | Count of rejected 401 authentication attempts |
| `fastapi_rate_limit_exceeded_total`| Counter | `endpoint` | Count of HTTP 429 rate limit responses |
| `fastapi_slow_requests_total` | Counter | `endpoint` | Requests whose duration exceeded 3.0s SLA |
| `fastapi_app_health_status` | Gauge | None | Health state: `1` for healthy, `0` for unhealthy |
| `fastapi_app_start_time_seconds` | Gauge | None | Unix epoch timestamp of application startup |
| `fastapi_process_cpu_percent` | Gauge | None | FastAPI worker CPU utilization percentage |
| `fastapi_process_memory_bytes` | Gauge | None | Worker process Resident Set Size (RSS) memory |
| `fastapi_system_cpu_percent` | Gauge | None | Total host CPU utilization percentage |
| `fastapi_system_memory_percent` | Gauge | None | Total host memory utilization percentage |

---

## 17. PromQL Query Reference

1. **Total Request Rate (RPS)**:
   ```promql
   sum(rate(fastapi_requests_total[1m]))
   ```
2. **Request Rate by Endpoint**:
   ```promql
   sum(rate(fastapi_requests_total[1m])) by (endpoint)
   ```
3. **Average Response Duration (seconds)**:
   ```promql
   sum(rate(fastapi_request_duration_seconds_sum[1m])) / sum(rate(fastapi_request_duration_seconds_count[1m]))
   ```
4. **95th-Percentile Latency**:
   ```promql
   histogram_quantile(0.95, sum(rate(fastapi_request_duration_seconds_bucket[1m])) by (le))
   ```
5. **HTTP 4xx Client Error Rate**:
   ```promql
   sum(rate(fastapi_requests_total{status_code=~"4.."}[1m]))
   ```
6. **HTTP 5xx Server Error Rate**:
   ```promql
   sum(rate(fastapi_requests_total{status_code=~"5.."}[1m]))
   ```
7. **Overall Failure Percentage (%)**:
   ```promql
   (sum(rate(fastapi_requests_total{status_code=~"[45].."}[1m])) / (sum(rate(fastapi_requests_total[1m])) > 0)) * 100
   ```
8. **Requests Exceeding 3.0 Seconds (Rate/min)**:
   ```promql
   sum(increase(fastapi_slow_requests_total[1m]))
   ```
9. **Authentication Failures Rate**:
   ```promql
   sum(rate(fastapi_auth_failures_total[1m]))
   ```
10. **Rate Limit Events Rate**:
    ```promql
    sum(rate(fastapi_rate_limit_exceeded_total[1m]))
    ```
11. **Active Concurrent Requests**:
    ```promql
    fastapi_active_requests
    ```
12. **API Uptime Percentage (Last 30 Minutes)**:
    ```promql
    avg_over_time(up{job="fastapi"}[30m]) * 100
    ```

---

## 18. Grafana Dashboard Panels

The auto-provisioned **API Monitoring Dashboard** contains 7 visual sections:

- **Section A: Service Overview**: Stat cards for Target Status, Application Health, 30m Uptime %, Total Requests, Successful (2xx), Failures (4xx/5xx), Error %, and Avg Latency.
- **Section B: API Performance**: Request Rate by Endpoint, Latency (Avg vs p95), and Slow Requests (> 3s) vs Active In-Flight Requests.
- **Section C: HTTP Status Codes**: Stacked graph of 2xx/4xx/5xx traffic and dedicated 401/429 tracking.
- **Section D: Error Trends**: 500 Server Error spike analysis and overall error ratio %.
- **Section E: Endpoint-Level Analysis**: Tabular breakdown of requests and failures per route.
- **Section F: System & Process Health**: Process CPU %, RSS Memory bytes, and Host Memory utilization %.
- **Section G: Active Alerts**: Live Prometheus alert list panel displaying alert state, severity, and active duration.

---

## 19. Alert Rules & Thresholds

Defined in `monitoring/alert_rules.yml`:

| Alert Name | Severity | Condition | For Duration | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`APIDown`** | `critical` | `up{job="fastapi"} == 0` | 15s | Triggers when Prometheus cannot scrape FastAPI |
| **`SlowAPIResponse`**| `warning` | `p95 Latency > 3.0s` OR `slow_requests > 0` | 10s | Enforces the 3.0-second latency SLA |
| **`HTTP500Error`** | `critical` | `rate(fastapi_requests_total{status_code="500"}) > 0` | 10s | Detects server crashes or 500 errors |
| **`HighFailureRate`**| `warning` | Overall failure rate `> 5%` | 15s | Detects elevated failure ratios with zero-protection |
| **`ServiceHealthFailure`**| `critical` | `fastapi_app_health_status == 0` | 10s | Detects degraded health check response |
| **`AuthenticationFailureSpike`**| `warning` | `rate(fastapi_auth_failures_total) > 0.1` | 10s | Detects unauthorized access attempts |
| **`RateLimitExceeded`**| `warning` | `rate(fastapi_rate_limit_exceeded_total) > 0.1` | 10s | Detects client quota breaches |
| **`HighCPUUsage`** | `warning` | `fastapi_process_cpu_percent > 85` | 30s | Detects abnormal CPU consumption |

---

## 20. Email, Slack, and Phone Call Notification Configuration

The system supports multi-channel incident notifications via Alertmanager, SMTP, Slack, and Voice Calls (as required by the assignment specification):

### A. Email Notifications (SMTP)
- Configured in `monitoring/alertmanager.yml` or triggered directly via the Web Dashboard at `/dashboard`.
- Uses TLS on `smtp.gmail.com:587` with an app password.
- Automatically delivers formatted HTML alert notifications on `FIRING` and `RESOLVED`.

### B. Optional Emergency Phone/Call Alerts (Twilio Voice API)
- Dispatches automated voice calls to an on-call engineer's phone when a `critical` outage (`APIDown`, `HTTP500Error`) occurs.
- Script: `python scripts/send_call_alert.py +1234567890`
- API Endpoint: `POST /api/alerts/send-test-call` with payload `{"to_phone": "+1234567890"}`
- Web Dashboard: Accessible directly from the **Live Alerts** tab at `http://localhost:8000/dashboard`.

---

## 21. Failure Simulation Instructions

Run the automated simulation script:
```bash
python scripts/run_failure_demo.py
```

Or trigger scenarios manually using cURL:

1. **Authentication Failure (401)**:
   ```bash
   curl -i http://localhost:8000/protected
   ```
2. **Slow Response (> 3s SLA Breach)**:
   ```bash
   curl -i "http://localhost:8000/simulate-timeout?delay=3.5"
   ```
3. **Internal Server Error (500)**:
   ```bash
   curl -i http://localhost:8000/simulate-error
   ```
4. **Rate Limit Exceeded (429)**:
   ```bash
   curl -i http://localhost:8000/simulate-rate-limit
   ```
5. **Simulate Service Unhealthy State**:
   ```bash
   curl -i -X POST "http://localhost:8000/health/toggle-state?unhealthy=true"
   ```

---

## 22. Root-Cause Analysis (RCA) Reports

Comprehensive, evidence-based post-incident evaluations for all four incidents are documented in [docs/root_cause_analysis.md](file:///c:/Users/sarin/Downloads/FastAPI%20API/docs/root_cause_analysis.md).

---

## 23. Running Automated Tests

Run the complete test suite:
```bash
pytest -v
```

Expected output:
```text
tests/test_endpoints.py::test_root_endpoint PASSED
tests/test_endpoints.py::test_health_endpoint_healthy PASSED
tests/test_endpoints.py::test_health_endpoint_unhealthy_simulation PASSED
tests/test_endpoints.py::test_users_endpoint PASSED
tests/test_endpoints.py::test_products_endpoint PASSED
tests/test_endpoints.py::test_simulate_error_endpoint PASSED
tests/test_endpoints.py::test_simulate_timeout_endpoint PASSED
tests/test_endpoints.py::test_simulate_rate_limit_endpoint PASSED
tests/test_auth.py::test_protected_missing_api_key PASSED
tests/test_auth.py::test_protected_invalid_api_key PASSED
tests/test_auth.py::test_protected_valid_api_key PASSED
tests/test_metrics.py::test_metrics_endpoint_exposition PASSED
tests/test_metrics.py::test_request_counter_increments PASSED
tests/test_metrics.py::test_auth_failure_metric_increments PASSED
tests/test_metrics.py::test_rate_limit_metric_increments PASSED
tests/test_metrics.py::test_active_requests_gauge_lifecycle PASSED
```

---

## 24. Running Monitoring Stack Verification

Run the verification utility to validate all Docker services, Prometheus targets, and alerting rules:

```bash
python scripts/verify_monitoring.py
```

---

## 25. Troubleshooting Common Issues

- **Prometheus target shows DOWN**: Ensure FastAPI is healthy (`curl http://localhost:8000/health`) and that both containers are on `monitoring-net`.
- **Grafana shows 'No Data'**: Ensure Prometheus datasource is reachable (`http://prometheus:9090`) and generate test traffic using `python scripts/run_failure_demo.py`.
- **Port conflicts (8000, 9090, 3000, 9093)**: Check if ports are already bound by other local processes (`netstat -ano`).

---

## 26. Security Considerations

- API Key values are never logged or reflected in responses.
- Stack traces and file paths are never exposed to clients on 500 errors.
- Low metric cardinality is enforced by normalizing URL templates.
- Non-root user execution in Docker container.

---

## 27. Monitoring Maintenance

- Scrape interval: 5s (development/demo) to 15s (production).
- TSDB retention: 15 days configured in Docker Compose.
- Alert rules evaluation: 5s.

---

## 28. Known Limitations

- External email and Slack notifications require valid third-party credentials.
- System metrics via `psutil` measure container resources when running in Docker.

---

## 29. Screenshot and Evidence Locations

Place captured validation artifacts in `screenshots/`:
- `screenshots/dashboard.png`
- `screenshots/prometheus-targets.png`
- `screenshots/alert-proof.png`

---

## 30. Final Submission Checklist

- [x] Sample FastAPI REST API created and running.
- [x] Instrumentation middleware collecting Rate, Errors, Duration (RED).
- [x] Prometheus metrics exposed at `/metrics`.
- [x] Docker Compose stack running FastAPI, Prometheus, Grafana, and Alertmanager.
- [x] Grafana dashboard pre-provisioned with 7 functional sections.
- [x] Alert rules configured for downtime, 3s SLA breaches, 500 errors, failure rate, and health checks.
- [x] All 4 failure scenarios reproducible and verified.
- [x] Root-cause analysis reports documented.
- [x] Automated pytest test suite passing.
- [x] Operations guide and technical documentation complete.
