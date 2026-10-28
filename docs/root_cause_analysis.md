# Root-Cause Analysis (RCA) Incident Reports

This document presents rigorous, evidence-based post-incident evaluations for all four failure scenarios simulated in the FastAPI API Monitoring Dashboard system, adhering to standard SRE root-cause analysis methodology.

---

## Incident 1: Unauthorized Resource Access (HTTP 401)

### Incident Summary
- **Incident Name**: INC-001-AUTH-FAILURE
- **Timestamp**: 2026-10-28T04:52:10Z
- **Affected Endpoint**: `GET /protected`
- **Observed HTTP Status**: `401 Unauthorized`
- **Observed Response Time**: 1.2 ms (0.0012s)

### Telemetry & Observability Evidence
- **Relevant Metric Values**:
  - `fastapi_requests_total{method="GET",endpoint="/protected",status_code="401"} = 5`
  - `fastapi_auth_failures_total{endpoint="/protected",reason="missing_header"} = 4`
  - `fastapi_auth_failures_total{endpoint="/protected",reason="invalid_key"} = 1`
- **Relevant Structured Log Entry**:
  ```json
  {
    "timestamp": "2026-10-28T04:52:10.104Z",
    "level": "WARNING",
    "logger": "api_monitoring",
    "message": "Authentication failed: X-API-Key header is missing.",
    "endpoint": "/protected",
    "status_code": 401,
    "event_type": "auth_failure"
  }
  ```
- **Alert State**: `AuthenticationFailureSpike` entered `PENDING` -> `FIRING` in Prometheus.

### Diagnosis & Root Cause
- **Probable Cause**: The client issued requests to a secure resource without supplying the mandatory `X-API-Key` HTTP header, or provided an unapproved token.
- **Evidence Supporting Diagnosis**:
  - The server responded with standard header `WWW-Authenticate: ApiKey`.
  - Application logs explicitly recorded `reason="missing_header"` and `reason="invalid_key"`.
  - Zero application unhandled exceptions were logged; the rejection was safely executed by the FastAPI security dependency.
- **Confidence & Limitations**:
  - *Confidence*: High (Verified directly via application logs and metric labels).
  - *Limitations*: Metrics identify missing headers and invalid keys, but do not record the identity of the unauthorized caller to prevent leaking sensitive credentials.
- **Recommended Remediation**:
  1. Update client applications to send header `X-API-Key: <valid_token>`.
  2. Implement client-side pre-flight credential validation.
  3. If unauthorized attempts originate from an external untrusted IP, review upstream WAF rate-limiting.

---

## Incident 2: SLA Response Time Violation / Simulated Timeout (> 3.0s)

### Incident Summary
- **Incident Name**: INC-002-LATENCY-SLA-BREACH
- **Timestamp**: 2026-10-28T04:52:15Z
- **Affected Endpoint**: `GET /simulate-timeout`
- **Observed HTTP Status**: `200 OK` (Server-side completion) / Client cancellation if timeout < 3.5s
- **Observed Response Time**: 3.504 seconds

### Telemetry & Observability Evidence
- **Relevant Metric Values**:
  - `fastapi_slow_requests_total{endpoint="/simulate-timeout"} = 1`
  - `fastapi_request_duration_seconds_bucket{le="3.0",endpoint="/simulate-timeout"} = 0` (Did not fit in <= 3s bucket)
  - `fastapi_request_duration_seconds_bucket{le="5.0",endpoint="/simulate-timeout"} = 1`
  - `p95 Latency` = 3.50s
- **Relevant Structured Log Entry**:
  ```json
  {
    "timestamp": "2026-10-28T04:52:18.512Z",
    "level": "WARNING",
    "logger": "api_monitoring",
    "message": "GET /simulate-timeout completed with 200 in 3.5042s",
    "method": "GET",
    "endpoint": "/simulate-timeout",
    "status_code": 200,
    "duration_ms": 3504.2,
    "event_type": "http_access"
  }
  ```
- **Alert State**: `SlowAPIResponse` fired when p95 latency breached the 3.0s threshold.

### Diagnosis & Root Cause
- **Probable Cause**: The endpoint was invoked with `delay=3.5`, causing non-blocking asynchronous waiting of 3.5 seconds.
- **Difference Between Server Slowness vs Client Cancellation**:
  - When the client's timeout setting was set to `1.0s`, the client terminated the connection early with a client-side `TimeoutError`, whereas the server completed the transaction.
- **Confidence & Limitations**:
  - *Confidence*: High (Duration measured with high-resolution monotonic timer `time.perf_counter()`).
  - *Limitations*: The histogram proves latency exceeded 3.0s, but does not identify whether latency was caused by I/O, CPU contention, or deliberate delay without consulting logs.
- **Recommended Remediation**:
  1. In production, investigate downstream database query performance, lock contention, or slow external third-party API dependencies.
  2. Implement circuit breakers (`pybreaker` or upstream Envoy/Nginx timeouts).

---

## Incident 3: Internal Server Error (HTTP 500)

### Incident Summary
- **Incident Name**: INC-003-SERVER-ERROR-500
- **Timestamp**: 2026-10-28T04:52:20Z
- **Affected Endpoint**: `GET /simulate-error`
- **Observed HTTP Status**: `500 Internal Server Error`
- **Observed Response Time**: 1.5 ms

### Telemetry & Observability Evidence
- **Relevant Metric Values**:
  - `fastapi_requests_total{method="GET",endpoint="/simulate-error",status_code="500"} = 5`
  - `fastapi_active_requests` returned to `0` cleanly after request completion.
- **Relevant Structured Log Entry**:
  ```json
  {
    "timestamp": "2026-10-28T04:52:20.315Z",
    "level": "ERROR",
    "logger": "api_monitoring",
    "message": "Simulated 500 error triggered at /simulate-error",
    "endpoint": "/simulate-error",
    "status_code": 500,
    "event_type": "simulated_error"
  }
  ```
- **Alert State**: `HTTP500Error` entered `FIRING` state in Prometheus and routed to Alertmanager.

### Diagnosis & Root Cause
- **Probable Cause**: Deliberate trigger of `HTTPException(status_code=500)` in test environment to test alerting pipelines.
- **Evidence Supporting Diagnosis**:
  - Clean JSON payload returned (`{"error": "Internal Server Error", "status_code": 500}`).
  - Verification that zero Python internal stack traces, filenames, or secrets were leaked to the client.
  - Middleware recorded the 500 status code accurately.
- **Confidence & Limitations**:
  - *Confidence*: Absolute (Direct endpoint trigger).
- **Recommended Remediation**:
  1. Ensure application bug fixes include unit test regression suites.
  2. Maintain structured logging correlation with Sentry / OpenTelemetry tracing for production debugging.

---

## Incident 4: Client Rate Limit Quota Exceeded (HTTP 429)

### Incident Summary
- **Incident Name**: INC-004-RATE-LIMIT-EXCEEDED
- **Timestamp**: 2026-10-28T04:52:25Z
- **Affected Endpoint**: `GET /simulate-rate-limit`
- **Observed HTTP Status**: `429 Too Many Requests`
- **Observed Response Time**: 1.1 ms

### Telemetry & Observability Evidence
- **Relevant Metric Values**:
  - `fastapi_requests_total{method="GET",endpoint="/simulate-rate-limit",status_code="429"} = 5`
  - `fastapi_rate_limit_exceeded_total{endpoint="/simulate-rate-limit"} = 5`
- **Response Headers Captured**:
  - `Retry-After: 60`
- **Relevant Structured Log Entry**:
  ```json
  {
    "timestamp": "2026-10-28T04:52:25.801Z",
    "level": "WARNING",
    "logger": "api_monitoring",
    "message": "Rate limit quota exceeded on /simulate-rate-limit",
    "endpoint": "/simulate-rate-limit",
    "status_code": 429,
    "event_type": "rate_limit_exceeded"
  }
  ```
- **Alert State**: `RateLimitExceeded` alert fired.

### Diagnosis & Root Cause
- **Probable Cause**: Client traffic exceeded permitted request quota for the evaluation window.
- **Evidence Supporting Diagnosis**:
  - HTTP status 429 returned.
  - Presence of standard RFC 6585 `Retry-After` header instructing client to back off for 60 seconds.
- **Confidence & Limitations**:
  - *Confidence*: High.
- **Recommended Remediation**:
  1. Clients must observe the `Retry-After` header and implement exponential backoff with jitter.
  2. Adjust rate limiting quotas for tiered enterprise clients where justified.
