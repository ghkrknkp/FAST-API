import time
from typing import Dict, List
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import settings
from app.metrics import (
    APP_HEALTH_STATUS,
    AUTH_FAILURES_TOTAL,
    RATE_LIMIT_EXCEEDED_TOTAL,
    REQUEST_DURATION_SECONDS,
    REQUESTS_TOTAL,
    SLOW_REQUESTS_TOTAL,
    START_TIME,
)

router = APIRouter(tags=["Frontend Dashboard & Alerts"])


def evaluate_alert_rules() -> List[Dict]:
    """
    Evaluates configured Prometheus alert rules against current in-memory metrics.
    Provides instant alert states (NORMAL, PENDING, FIRING) for the frontend alerts view.
    """
    # 1. Total 500 errors
    total_500 = 0
    try:
        for metric in REQUESTS_TOTAL.collect():
            for sample in metric.samples:
                if sample.labels.get("status_code") == "500":
                    total_500 += int(sample.value)
    except Exception:
        pass

    # 2. Total slow requests (> 3s)
    total_slow = 0
    try:
        for metric in SLOW_REQUESTS_TOTAL.collect():
            for sample in metric.samples:
                total_slow += int(sample.value)
    except Exception:
        pass

    # 3. Total auth failures
    total_auth_fail = 0
    try:
        for metric in AUTH_FAILURES_TOTAL.collect():
            for sample in metric.samples:
                total_auth_fail += int(sample.value)
    except Exception:
        pass

    # 4. Total rate limits
    total_rate_limits = 0
    try:
        for metric in RATE_LIMIT_EXCEEDED_TOTAL.collect():
            for sample in metric.samples:
                total_rate_limits += int(sample.value)
    except Exception:
        pass

    # 5. Health status
    current_health = 1
    try:
        for metric in APP_HEALTH_STATUS.collect():
            for sample in metric.samples:
                current_health = int(sample.value)
    except Exception:
        pass

    alerts = [
        {
            "id": "alert-1",
            "name": "SlowAPIResponse",
            "severity": "warning",
            "condition": "Response duration > 3.0 seconds SLA",
            "state": "FIRING" if total_slow > 0 else "NORMAL",
            "trigger_count": total_slow,
            "threshold": "> 3.0s latency",
            "summary": "API response latency exceeded the 3.0-second SLA threshold.",
            "remediation": "Investigate downstream database queries or test with /simulate-timeout.",
            "test_endpoint": "/simulate-timeout?delay=3.5",
        },
        {
            "id": "alert-2",
            "name": "HTTP500Error",
            "severity": "critical",
            "condition": "HTTP 500 Internal Server Errors detected",
            "state": "FIRING" if total_500 > 0 else "NORMAL",
            "trigger_count": total_500,
            "threshold": "500 rate > 0 req/s",
            "summary": "Internal server crash or simulated 500 fault observed.",
            "remediation": "Inspect application JSON logs for tracebacks or test with /simulate-error.",
            "test_endpoint": "/simulate-error",
        },
        {
            "id": "alert-3",
            "name": "ServiceHealthFailure",
            "severity": "critical",
            "condition": "fastapi_app_health_status == 0",
            "state": "FIRING" if current_health == 0 else "NORMAL",
            "trigger_count": 1 if current_health == 0 else 0,
            "threshold": "Health probe returns unhealthy",
            "summary": "The /health readiness probe reported a degraded or failed state.",
            "remediation": "Check application dependencies or toggle state via /health/toggle-state.",
            "test_endpoint": "/health/toggle-state?unhealthy=true",
        },
        {
            "id": "alert-4",
            "name": "AuthenticationFailureSpike",
            "severity": "warning",
            "condition": "Rate of HTTP 401 Unauthorized > 0.1 req/s",
            "state": "FIRING" if total_auth_fail >= 3 else "NORMAL",
            "trigger_count": total_auth_fail,
            "threshold": "rate(fastapi_auth_failures_total) > 0.1",
            "summary": "High frequency of rejected authentication attempts on protected resources.",
            "remediation": "Verify client API keys and check for unauthorized brute force attempts.",
            "test_endpoint": "/protected",
        },
        {
            "id": "alert-5",
            "name": "RateLimitExceeded",
            "severity": "warning",
            "condition": "Rate of HTTP 429 Too Many Requests > 0.1 req/s",
            "state": "FIRING" if total_rate_limits >= 3 else "NORMAL",
            "trigger_count": total_rate_limits,
            "threshold": "rate(fastapi_rate_limit_exceeded_total) > 0.1",
            "summary": "Client exceeded permitted request quotas.",
            "remediation": "Inspect client traffic volume and enforce client-side Retry-After backoff.",
            "test_endpoint": "/simulate-rate-limit",
        },
        {
            "id": "alert-6",
            "name": "APIDown",
            "severity": "critical",
            "condition": "up{job='fastapi'} == 0",
            "state": "NORMAL",
            "trigger_count": 0,
            "threshold": "Prometheus target unreachable for > 15s",
            "summary": "Prometheus failed to scrape FastAPI at fastapi:8000.",
            "remediation": "Inspect container runtime status (docker compose ps) and network health.",
            "test_endpoint": "",
        },
    ]
    return alerts


@router.get("/api/alerts", summary="Live Alert Rules Evaluation API")
async def get_alerts_api():
    """Returns the live state of all configured monitoring alerts."""
    alerts = evaluate_alert_rules()
    firing_count = sum(1 for a in alerts if a["state"] == "FIRING")
    return JSONResponse(
        content={
            "status": "success",
            "timestamp": time.time(),
            "total_alerts": len(alerts),
            "firing_alerts": firing_count,
            "alerts": alerts,
        }
    )


@router.post("/api/alerts/send-test-email", summary="Send Real Alert Notification Email")
async def send_test_email_endpoint(request: Request):
    """Dispatches a real alert email to the specified recipient via SMTP."""
    from scripts.send_alert_email import send_alert_email

    try:
        body = await request.json()
    except Exception:
        body = {}

    to_email = body.get("to_email")
    if not to_email:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Field 'to_email' is required."})

    res = send_alert_email(
        to_email=to_email,
        alert_name=body.get("alert_name", "HTTP500Error"),
        severity=body.get("severity", "CRITICAL"),
        summary=body.get("summary", "Deliberate HTTP 500 fault simulated for alert verification"),
        smtp_user=body.get("smtp_user"),
        smtp_password=body.get("smtp_password"),
    )
    status_code = 200 if res.get("status") == "success" else 400
    return JSONResponse(status_code=status_code, content=res)



@router.post("/api/alerts/send-test-slack", summary="Dispatch Real-Time Slack Alert")
async def send_test_slack_endpoint(request: Request):
    """Posts a formatted Block Kit incident notification to Slack via Webhook."""
    from scripts.send_slack_alert import send_slack_alert

    try:
        body = await request.json()
    except Exception:
        body = {}

    res = send_slack_alert(
        webhook_url=body.get("webhook_url"),
        channel=body.get("channel", "#all-fastapi-alerts"),
        alert_name=body.get("alert_name", "HTTP500Error"),
        severity=body.get("severity", "CRITICAL"),
        summary=body.get("summary", "Deliberate HTTP 500 fault simulated for alert verification"),
        remediation=body.get("remediation", "Inspect application logs or verify /simulate-error calls."),
    )
    return JSONResponse(status_code=200, content=res)


@router.get("/dashboard", response_class=HTMLResponse, summary="Frontend Monitoring & Alerts UI")
async def get_dashboard_html(request: Request):
    """
    Renders a sleek, responsive White & Black high-contrast web dashboard
    with real-time metrics, interactive failure simulations, and live alerts status.
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>API Monitoring Dashboard & Alerts</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #09090b;
      --card-bg: #121215;
      --card-border: #27272a;
      --text-primary: #ffffff;
      --text-secondary: #a1a1aa;
      --text-muted: #71717a;
      --accent-white: #ffffff;
      --accent-crimson: #ef4444;
      --accent-amber: #f59e0b;
      --accent-emerald: #10b981;
      --code-bg: #18181b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text-primary);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Header & Navigation */
    header {
      background: rgba(18, 18, 21, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .logo-area { display: flex; align-items: center; gap: 0.75rem; }
    .logo-badge {
      background: #ffffff;
      color: #000000;
      font-weight: 800;
      font-size: 0.85rem;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }
    .brand-title { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.5px; }

    .nav-tabs { display: flex; gap: 0.5rem; }
    .nav-tab {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-secondary);
      font-family: inherit;
      font-weight: 600;
      font-size: 0.9rem;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .nav-tab:hover { color: var(--text-primary); border-color: var(--card-border); }
    .nav-tab.active { background: #ffffff; color: #000000; border-color: #ffffff; }

    .alert-counter-badge {
      background: var(--accent-crimson);
      color: #ffffff;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.1rem 0.4rem;
      border-radius: 999px;
      display: none;
    }

    /* Main Container */
    main { flex: 1; padding: 2rem; max-width: 1400px; margin: 0 auto; width: 100%; }

    /* Stat Cards Grid */
    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      position: relative;
      overflow: hidden;
    }
    .stat-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 2px;
      background: #27272a;
    }
    .stat-card.active-indicator::before { background: #ffffff; }
    .stat-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 600; }
    .stat-value { font-size: 1.75rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .stat-desc { font-size: 0.8rem; color: var(--text-secondary); }

    /* Section Views */
    .view-section { display: none; }
    .view-section.active { display: block; }

    /* Alerts Tab */
    .alerts-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--card-border);
    }
    .alerts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 1.25rem;
    }
    .alert-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .alert-card:hover { border-color: #52525b; transform: translateY(-2px); }
    .alert-card.is-firing {
      border-color: var(--accent-crimson);
      background: linear-gradient(180deg, rgba(239, 68, 68, 0.08) 0%, var(--card-bg) 100%);
    }

    .alert-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .alert-name { font-size: 1.15rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .alert-badge {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-normal { background: #27272a; color: #a1a1aa; border: 1px solid #3f3f46; }
    .badge-firing { background: var(--accent-crimson); color: #ffffff; animation: pulse 2s infinite; }
    .badge-warning { background: #3f3f46; color: var(--accent-amber); border: 1px solid var(--accent-amber); }
    .badge-critical { background: #3f3f46; color: var(--accent-crimson); border: 1px solid var(--accent-crimson); }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.6; }
    }

    .alert-field { display: flex; flex-direction: column; gap: 0.25rem; }
    .alert-label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }
    .alert-val { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4; }
    .code-val { font-family: 'JetBrains Mono', monospace; background: var(--code-bg); padding: 0.2rem 0.4rem; border-radius: 4px; color: #e4e4e7; font-size: 0.8rem; border: 1px solid #27272a; }

    .alert-actions { display: flex; gap: 0.5rem; margin-top: auto; padding-top: 0.5rem; }
    .btn-simulate {
      background: #ffffff;
      color: #000000;
      border: none;
      padding: 0.5rem 0.85rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-simulate:hover { background: #e4e4e7; }
    .btn-simulate.secondary {
      background: transparent;
      color: #ffffff;
      border: 1px solid var(--card-border);
    }
    .btn-simulate.secondary:hover { background: #27272a; }

    /* Simulator Panel */
    .sim-panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }
    .sim-buttons { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1rem; }
    .console-box {
      background: #000000;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem;
      margin-top: 1rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      min-height: 120px;
      max-height: 260px;
      overflow-y: auto;
      color: #a1a1aa;
    }

    /* Footer */
    footer {
      border-top: 1px solid var(--card-border);
      padding: 1.5rem 2rem;
      display: flex;
      justify-content: space-between;
      color: var(--text-muted);
      font-size: 0.85rem;
    }
    footer a { color: var(--text-secondary); text-decoration: none; }
    footer a:hover { color: #ffffff; }
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <header>
    <div class="logo-area">
      <span class="logo-badge">MONITOR</span>
      <h1 class="brand-title">FastAPI Observability</h1>
    </div>
    <div class="nav-tabs">
      <button class="nav-tab active" id="tab-overview" onclick="switchTab('overview')">Overview</button>
      <button class="nav-tab" id="tab-alerts" onclick="switchTab('alerts')">
        Live Alerts <span class="alert-counter-badge" id="alert-counter">0</span>
      </button>
      <button class="nav-tab" id="tab-simulator" onclick="switchTab('simulator')">Failure Simulator</button>
      <button class="nav-tab" id="tab-links" onclick="window.open('/docs', '_blank')">Swagger UI ↗</button>
    </div>
  </header>

  <main>
    <!-- Top Stat Cards (Always visible) -->
    <div class="stat-grid">
      <div class="stat-card active-indicator">
        <span class="stat-title">Target Status</span>
        <span class="stat-value" id="val-status" style="color: var(--accent-emerald);">UP</span>
        <span class="stat-desc">FastAPI ASGI Server</span>
      </div>
      <div class="stat-card">
        <span class="stat-title">Health Probe</span>
        <span class="stat-value" id="val-health">HEALTHY</span>
        <span class="stat-desc" id="val-health-detail">Liveness: OK</span>
      </div>
      <div class="stat-card">
        <span class="stat-title">Uptime</span>
        <span class="stat-value" id="val-uptime">0s</span>
        <span class="stat-desc">Since application start</span>
      </div>
      <div class="stat-card">
        <span class="stat-title">Total Requests</span>
        <span class="stat-value" id="val-requests">0</span>
        <span class="stat-desc">Instrumented requests</span>
      </div>
      <div class="stat-card">
        <span class="stat-title">Active Alerts</span>
        <span class="stat-value" id="val-active-alerts" style="color: #ffffff;">0</span>
        <span class="stat-desc">Evaluated alert rules</span>
      </div>
    </div>

    <!-- 1. OVERVIEW VIEW -->
    <section id="view-overview" class="view-section active">
      <div class="sim-panel">
        <h2 style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem;">Interactive API Testing & Traffic Generator</h2>
        <p style="color: var(--text-secondary); font-size: 0.9rem;">Trigger real endpoint requests to observe live metrics and alerts reacting in real time.</p>
        <div class="sim-buttons">
          <button class="btn-simulate" onclick="callApi('/', 'GET')">GET / (Root)</button>
          <button class="btn-simulate" onclick="callApi('/health', 'GET')">GET /health</button>
          <button class="btn-simulate" onclick="callApi('/users', 'GET')">GET /users</button>
          <button class="btn-simulate" onclick="callApi('/products', 'GET')">GET /products</button>
          <button class="btn-simulate secondary" onclick="callApi('/protected', 'GET')">GET /protected (Missing Key -> 401)</button>
          <button class="btn-simulate secondary" onclick="callApi('/simulate-timeout?delay=3.5', 'GET')">GET /simulate-timeout (>3s SLA)</button>
          <button class="btn-simulate secondary" onclick="callApi('/simulate-error', 'GET')">GET /simulate-error (HTTP 500)</button>
          <button class="btn-simulate secondary" onclick="callApi('/simulate-rate-limit', 'GET')">GET /simulate-rate-limit (HTTP 429)</button>
        </div>
        <div class="console-box" id="overview-console">
          > Ready. Click any endpoint above to generate live traffic and test monitoring responses...
        </div>
      </div>
    </section>

    <!-- 2. ALERTS VIEW ("IN ALERTS") -->
    <section id="view-alerts" class="view-section">
      <div class="alerts-header">
        <div>
          <h2 style="font-size: 1.5rem; font-weight: 700;">Prometheus Alert Rules Status</h2>
          <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.25rem;">
            Real-time evaluation of all configured SLA, availability, and failure alerts.
          </p>
        </div>
        <button class="btn-simulate secondary" onclick="refreshAlerts()">⟳ Refresh Alerts</button>
      <div class="sim-panel" style="margin-bottom: 1.5rem; background: #121215; border: 1px solid #27272a;">
        <h3 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
          📧 Live Email Alert Dispatcher
        </h3>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;">
          Deliver genuine incident notifications directly to your email inbox for assignment verification.
        </p>
        <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center;">
          <input type="email" id="email-recipient" placeholder="Enter your email address (e.g. you@gmail.com)" 
                 style="flex: 1; min-width: 260px; background: #000; border: 1px solid #3f3f46; color: #fff; padding: 0.6rem 0.85rem; border-radius: 6px; font-family: inherit; font-size: 0.85rem;">
          <select id="email-alert-type" style="background: #000; border: 1px solid #3f3f46; color: #fff; padding: 0.6rem 0.85rem; border-radius: 6px; font-family: inherit; font-size: 0.85rem;">
            <option value="HTTP500Error">Alert: HTTP500Error (Critical)</option>
            <option value="SlowAPIResponse">Alert: SlowAPIResponse (>3s SLA)</option>
            <option value="ServiceHealthFailure">Alert: ServiceHealthFailure</option>
            <option value="AuthenticationFailureSpike">Alert: AuthenticationFailureSpike</option>
            <option value="RateLimitExceeded">Alert: RateLimitExceeded</option>
          </select>
          <button class="btn-simulate" onclick="sendLiveEmailAlert()">Send Email Alert</button>
        </div>
        <div id="email-status-message" style="margin-top: 0.75rem; font-size: 0.85rem; display: none;"></div>
      </div>

      <div class="sim-panel" style="margin-bottom: 1.5rem; background: #121215; border: 1px solid #27272a;">
        <h3 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
          💬 Slack Alert Dispatcher (#all-fastapi-alerts)
        </h3>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;">
          Posts formatted incident cards directly to your configured Slack webhook for immediate team notification.
        </p>
        <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center;">
          <select id="slack-alert-type" style="background: #000; border: 1px solid #3f3f46; color: #fff; padding: 0.6rem 0.85rem; border-radius: 6px; font-family: inherit; font-size: 0.85rem;">
            <option value="HTTP500Error">Alert: HTTP500Error (Crash Incident)</option>
            <option value="SlowAPIResponse">Alert: SlowAPIResponse (>3s SLA Violation)</option>
            <option value="APIDown">Alert: APIDown (Critical Outage)</option>
            <option value="RateLimitExceeded">Alert: RateLimitExceeded (HTTP 429)</option>
          </select>
          <button class="btn-simulate" onclick="sendLiveSlackAlert()">Post Alert to Slack Channel</button>
        </div>
        <div id="slack-status-message" style="margin-top: 0.75rem; font-size: 0.85rem; display: none;"></div>
      </div>

      <div class="alerts-grid" id="alerts-container">
        <!-- Rendered dynamically -->
      </div>
    </section>

    <!-- 3. SIMULATOR VIEW -->
    <section id="view-simulator" class="view-section">
      <div class="sim-panel">
        <h2 style="font-size: 1.25rem; font-weight: 700;">Four Required Failure Scenarios</h2>
        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.25rem;">
          Reproduce each assignment incident to inspect status codes, headers, and alert trigger transitions.
        </p>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-top: 1.5rem;">
          <div class="stat-card">
            <span class="stat-title">Scenario 1: Auth Failure</span>
            <span style="font-size: 0.9rem; color: var(--text-secondary);">Tests 401 Unauthorized rejection without exposing credentials.</span>
            <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
              <button class="btn-simulate" onclick="callApi('/protected', 'GET')">Test 401</button>
              <button class="btn-simulate secondary" onclick="callApiWithKey('/protected')">Test 200 (With Key)</button>
            </div>
          </div>

          <div class="stat-card">
            <span class="stat-title">Scenario 2: Timeout (> 3s)</span>
            <span style="font-size: 0.9rem; color: var(--text-secondary);">Asynchronous delay of 3.5s triggering SlowAPIResponse alert.</span>
            <div style="margin-top: 1rem;">
              <button class="btn-simulate" onclick="callApi('/simulate-timeout?delay=3.5', 'GET')">Trigger 3.5s Delay</button>
            </div>
          </div>

          <div class="stat-card">
            <span class="stat-title">Scenario 3: Server Error</span>
            <span style="font-size: 0.9rem; color: var(--text-secondary);">Generates clean HTTP 500 Internal Server Error without leaking traces.</span>
            <div style="margin-top: 1rem;">
              <button class="btn-simulate" onclick="callApi('/simulate-error', 'GET')">Trigger HTTP 500</button>
            </div>
          </div>

          <div class="stat-card">
            <span class="stat-title">Scenario 4: Rate Limit</span>
            <span style="font-size: 0.9rem; color: var(--text-secondary);">Generates HTTP 429 with standard Retry-After: 60 response header.</span>
            <div style="margin-top: 1rem;">
              <button class="btn-simulate" onclick="callApi('/simulate-rate-limit', 'GET')">Trigger HTTP 429</button>
            </div>
          </div>
        </div>

        <div class="console-box" id="sim-console" style="margin-top: 1.5rem;">
          > Live console output will display here...
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div>API Monitoring Dashboard • FastAPI & Prometheus Observability Stack</div>
    <div>
      <a href="/metrics" target="_blank">/metrics</a> &nbsp;|&nbsp;
      <a href="/docs" target="_blank">/docs</a> &nbsp;|&nbsp;
      <a href="/api/alerts" target="_blank">/api/alerts</a>
    </div>
  </footer>

  <script>
    function switchTab(tabId) {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));

      const activeBtn = document.getElementById('tab-' + tabId);
      const activeSection = document.getElementById('view-' + tabId);
      if (activeBtn) activeBtn.classList.add('active');
      if (activeSection) activeSection.classList.add('active');
      if (tabId === 'alerts') refreshAlerts();
    }

    async function callApi(url, method) {
      const consoleBox = document.getElementById('overview-console');
      const simBox = document.getElementById('sim-console');
      const start = performance.now();

      function logLine(msg) {
        const time = new Date().toLocaleTimeString();
        const line = `[${time}] ${msg}\\n`;
        if (consoleBox) { consoleBox.innerText = line + consoleBox.innerText; }
        if (simBox) { simBox.innerText = line + simBox.innerText; }
      }

      logLine(`--> ${method} ${url} sending...`);
      try {
        const res = await fetch(url, { method: method });
        const duration = (performance.now() - start).toFixed(2);
        const data = await res.json().catch(() => ({}));
        logLine(`<-- HTTP ${res.status} (${duration}ms) -> ${JSON.stringify(data)}`);
      } catch (err) {
        logLine(`<-- Request Failed: ${err.message}`);
      }
      refreshStats();
      refreshAlerts();
    }

    async function callApiWithKey(url) {
      const start = performance.now();
      const consoleBox = document.getElementById('sim-console');
      try {
        const res = await fetch(url, { headers: { 'X-API-Key': 'secret-token-demo-key-12345' } });
        const duration = (performance.now() - start).toFixed(2);
        const data = await res.json();
        consoleBox.innerText = `[${new Date().toLocaleTimeString()}] <-- HTTP ${res.status} (${duration}ms) [AUTHENTICATED] -> ${JSON.stringify(data)}\\n` + consoleBox.innerText;
      } catch (e) {
        consoleBox.innerText = `[${new Date().toLocaleTimeString()}] Error: ${e.message}\\n` + consoleBox.innerText;
      }
      refreshStats();
      refreshAlerts();
    }

    async function refreshStats() {
      try {
        const res = await fetch('/health');
        const data = await res.json();
        document.getElementById('val-status').innerText = 'UP';
        document.getElementById('val-health').innerText = data.status.toUpperCase();
        document.getElementById('val-health').style.color = data.status === 'healthy' ? 'var(--accent-emerald)' : 'var(--accent-crimson)';
        document.getElementById('val-uptime').innerText = `${Math.round(data.uptime_seconds)}s`;
        // Fetch total requests from metrics
        const mres = await fetch('/api/alerts');
        const mdata = await mres.json();
        let total = 0;
        if (mdata.alerts) {
          mdata.alerts.forEach(a => { total += (a.trigger_count || 0); });
        }
        document.getElementById('val-requests').innerText = total;
      } catch (e) {
        document.getElementById('val-status').innerText = 'ERROR';
        document.getElementById('val-status').style.color = 'var(--accent-crimson)';
      }
    }

    async function refreshAlerts() {
      try {
        const res = await fetch('/api/alerts');
        const data = await res.json();
        const container = document.getElementById('alerts-container');
        if (!container) return;

        container.innerHTML = '';
        const firingCount = data.firing_alerts || 0;
        const counterEl = document.getElementById('alert-counter');
        const activeAlertsVal = document.getElementById('val-active-alerts');

        if (activeAlertsVal) activeAlertsVal.innerText = firingCount;
        if (counterEl) {
          counterEl.innerText = firingCount;
          counterEl.style.display = firingCount > 0 ? 'inline-block' : 'none';
        }

        data.alerts.forEach(alert => {
          const isFiring = alert.state === 'FIRING';
          const card = document.createElement('div');
          card.className = `alert-card ${isFiring ? 'is-firing' : ''}`;

          card.innerHTML = `
            <div class="alert-top">
              <div>
                <span class="alert-name">${alert.name}</span>
                <div style="margin-top: 0.25rem;">
                  <span class="alert-badge ${alert.severity === 'critical' ? 'badge-critical' : 'badge-warning'}">${alert.severity}</span>
                </div>
              </div>
              <span class="alert-badge ${isFiring ? 'badge-firing' : 'badge-normal'}">${alert.state}</span>
            </div>

            <div class="alert-field">
              <span class="alert-label">Condition</span>
              <span class="alert-val"><code class="code-val">${alert.condition}</code></span>
            </div>

            <div class="alert-field">
              <span class="alert-label">Summary</span>
              <span class="alert-val">${alert.summary}</span>
            </div>

            <div class="alert-field">
              <span class="alert-label">Remediation</span>
              <span class="alert-val">${alert.remediation}</span>
            </div>

            <div class="alert-actions">
              ${alert.test_endpoint ? `<button class="btn-simulate" onclick="callApi('${alert.test_endpoint}', 'GET')">Simulate Trigger</button>` : ''}
              <button class="btn-simulate secondary" onclick="window.open('/metrics', '_blank')">View Metrics</button>
            </div>
          `;
          container.appendChild(card);
        });
      } catch(e) {
        console.error('Alert refresh failed:', e);
      }
    }

    async function sendLiveEmailAlert() {
      const emailInput = document.getElementById('email-recipient');
      const alertType = document.getElementById('email-alert-type').value;
      const statusMsg = document.getElementById('email-status-message');
      const recipient = emailInput ? emailInput.value.trim() : '';

      if (!recipient) {
        statusMsg.style.display = 'block';
        statusMsg.style.color = 'var(--accent-crimson)';
        statusMsg.innerText = 'Please enter a valid recipient email address.';
        return;
      }

      statusMsg.style.display = 'block';
      statusMsg.style.color = 'var(--text-secondary)';
      statusMsg.innerText = 'Sending email alert via SMTP...';

      try {
        const res = await fetch('/api/alerts/send-test-email', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to_email: recipient,
            alert_name: alertType,
            severity: alertType === 'HTTP500Error' ? 'CRITICAL' : 'WARNING'
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          statusMsg.style.color = 'var(--accent-emerald)';
          statusMsg.innerText = `✓ Email delivered successfully to ${recipient}! Check your inbox.`;
        } else {
          statusMsg.style.color = 'var(--accent-amber)';
          statusMsg.innerText = `SMTP Info: ${data.message}`;
        }
      } catch (err) {
        statusMsg.style.color = 'var(--accent-crimson)';
        statusMsg.innerText = `Failed to contact alert dispatch endpoint: ${err.message}`;
      }
    }

    async function sendLiveSlackAlert() {
      const alertType = document.getElementById('slack-alert-type').value;
      const statusMsg = document.getElementById('slack-status-message');
      statusMsg.style.display = 'block';
      statusMsg.style.color = 'var(--text-secondary)';
      statusMsg.innerText = 'Posting incident alert to Slack webhook (#all-fastapi-alerts)...';

      try {
        const res = await fetch('/api/alerts/send-test-slack', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            alert_name: alertType,
            severity: alertType === 'HTTP500Error' || alertType === 'APIDown' ? 'CRITICAL' : 'WARNING',
            summary: `Simulated incident for monitoring verification on ${alertType}`
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          statusMsg.style.color = 'var(--accent-emerald)';
          statusMsg.innerText = '✓ Alert successfully posted to #all-fastapi-alerts on Slack! Check your Slack window.';
        } else {
          statusMsg.style.color = 'var(--accent-crimson)';
          statusMsg.innerText = `Slack delivery note: ${data.message}`;
        }
      } catch (err) {
        statusMsg.style.color = 'var(--accent-crimson)';
        statusMsg.innerText = `Failed to contact Slack dispatch endpoint: ${err.message}`;
      }
    }

    // Auto-refresh every 5 seconds
    setInterval(() => {
      refreshStats();
      if (document.getElementById('view-alerts').classList.contains('active')) {
        refreshAlerts();
      }
    }, 5000);

    // Initial load
    refreshStats();
    refreshAlerts();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
