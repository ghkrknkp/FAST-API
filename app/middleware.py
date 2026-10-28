import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.metrics import (
    REQUESTS_TOTAL,
    REQUEST_DURATION_SECONDS,
    ACTIVE_REQUESTS,
    SLOW_REQUESTS_TOTAL,
)
from app.logging_config import logger


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    High-reliability ASGI middleware that records Prometheus metrics and structured
    diagnostic logs for every HTTP transaction.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Ignore Prometheus scrape requests to avoid feedback loops and metric distortion
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        raw_path = request.url.path

        # Determine normalized route template to maintain low metric cardinality
        endpoint = raw_path
        # Starlette stores matched route in scope after routing, fallback to raw path
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match.value == 2:  # Match.FULL
                endpoint = getattr(route, "path", raw_path)
                break

        start_time = time.perf_counter()
        ACTIVE_REQUESTS.inc()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            # Catch unhandled exceptions to record metrics before re-raising
            logger.error(
                f"Unhandled exception during {method} {endpoint}: {exc}",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": 500,
                    "event_type": "request_exception",
                },
                exc_info=True,
            )
            status_code = 500
            raise exc
        finally:
            duration = time.perf_counter() - start_time
            ACTIVE_REQUESTS.dec()

            # Record metrics
            REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
            REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()

            # Track slow requests exceeding 3 seconds SLA
            if duration >= 3.0:
                SLOW_REQUESTS_TOTAL.labels(endpoint=endpoint).inc()

            # Structured access logging
            log_level = logger.warning if status_code >= 400 else logger.info
            log_level(
                f"{method} {endpoint} completed with {status_code} in {duration:.4f}s",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                    "event_type": "http_access",
                },
            )
