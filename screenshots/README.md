# Monitoring Evidence & Screenshots

This directory contains visual validation artifacts for the FastAPI API Monitoring Dashboard stack.

## Required Artifacts Checklist

1. **`dashboard.png`**
   - High-resolution capture of the Grafana **API Monitoring Dashboard** under real test traffic.
   - Shows active panels across:
     - Section A: Service Overview (Target Status, Health Status, Uptime %, Total Requests, Failures, Error %, Latency)
     - Section B: API Performance (RPS, Avg & p95 Duration, Latency breakdown)
     - Section C: HTTP Status Codes (2xx, 4xx, 5xx, 401, 429)
     - Section D: Error Trends (500 error spikes, Error ratio %)
     - Section E: Endpoint Analysis table
     - Section F: Server & Process Health (CPU %, RSS Memory bytes, System Memory %)
     - Section G: Active Prometheus Alert List

2. **`prometheus-targets.png`**
   - Capture of `http://localhost:9090/targets` in Prometheus.
   - Confirms target `fastapi` at `http://fastapi:8000/metrics` is in **State: UP** with 100% scrape health.

3. **`alert-proof.png`**
   - Capture of `http://localhost:9090/alerts` or Alertmanager at `http://localhost:9093`.
   - Confirms alert rules (`HTTP500Error`, `SlowAPIResponse`, `APIDown`, `AuthenticationFailureSpike`, `RateLimitExceeded`) successfully transitioning between `PENDING` and `FIRING`.

---

## Capturing Evidence Locally

1. Launch stack:
   ```bash
   docker compose up -d
   ```
2. Run automated failure traffic generator:
   ```bash
   python scripts/run_failure_demo.py
   ```
3. Open Grafana at `http://localhost:3000` (User: `admin`, Password: `admin`), navigate to **API Monitoring Dashboard**, and save snapshot as `screenshots/dashboard.png`.
4. Open Prometheus at `http://localhost:9090/targets` and capture `screenshots/prometheus-targets.png`.
5. Open Prometheus at `http://localhost:9090/alerts` and capture `screenshots/alert-proof.png`.
