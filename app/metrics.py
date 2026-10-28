import time
import psutil
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Application start timestamp
START_TIME = time.time()

# -------------------------------------------------------------
# 1. HTTP Request Metrics (RED Method: Rate, Errors, Duration)
# -------------------------------------------------------------

REQUESTS_TOTAL = Counter(
    "fastapi_requests_total",
    "Total count of HTTP requests completed by the application.",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "fastapi_request_duration_seconds",
    "Histogram of request duration in seconds across critical latency thresholds.",
    ["method", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
)

ACTIVE_REQUESTS = Gauge(
    "fastapi_active_requests",
    "Number of currently active HTTP requests being processed.",
)

# -------------------------------------------------------------
# 2. Failure & Anomaly Metrics
# -------------------------------------------------------------

AUTH_FAILURES_TOTAL = Counter(
    "fastapi_auth_failures_total",
    "Total count of rejected authentication attempts.",
    ["endpoint", "reason"],
)

RATE_LIMIT_EXCEEDED_TOTAL = Counter(
    "fastapi_rate_limit_exceeded_total",
    "Total count of HTTP 429 Rate Limit responses generated.",
    ["endpoint"],
)

SLOW_REQUESTS_TOTAL = Counter(
    "fastapi_slow_requests_total",
    "Total count of requests whose duration exceeded 3.0 seconds.",
    ["endpoint"],
)

# -------------------------------------------------------------
# 3. Application Health & System Metrics
# -------------------------------------------------------------

APP_HEALTH_STATUS = Gauge(
    "fastapi_app_health_status",
    "Reported health state of the application: 1 for healthy, 0 for unhealthy.",
)
APP_HEALTH_STATUS.set(1)

APP_START_TIME_SECONDS = Gauge(
    "fastapi_app_start_time_seconds",
    "Unix timestamp representing when the application was launched.",
)
APP_START_TIME_SECONDS.set(START_TIME)

# psutil system & process gauges
PROCESS_CPU_PERCENT = Gauge(
    "fastapi_process_cpu_percent",
    "Current CPU utilization percentage for the FastAPI worker process.",
)

PROCESS_MEMORY_BYTES = Gauge(
    "fastapi_process_memory_bytes",
    "Current process resident set size (RSS) memory consumption in bytes.",
)

SYSTEM_CPU_PERCENT = Gauge(
    "fastapi_system_cpu_percent",
    "Total system CPU utilization percentage.",
)

SYSTEM_MEMORY_PERCENT = Gauge(
    "fastapi_system_memory_percent",
    "Total system memory utilization percentage.",
)


def update_system_metrics() -> None:
    """Safely updates process and host system metrics using psutil."""
    try:
        proc = psutil.Process()
        # Process metrics
        PROCESS_CPU_PERCENT.set(proc.cpu_percent(interval=None))
        PROCESS_MEMORY_BYTES.set(proc.memory_info().rss)

        # Host system metrics
        SYSTEM_CPU_PERCENT.set(psutil.cpu_percent(interval=None))
        SYSTEM_MEMORY_PERCENT.set(psutil.virtual_memory().percent)
    except Exception:
        # Do not allow metric scraping to fail if psutil encounters OS permission quirks
        pass


def get_metrics_payload() -> tuple[bytes, str]:
    """Updates dynamic collectors and returns the Prometheus exposition format payload."""
    update_system_metrics()
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
