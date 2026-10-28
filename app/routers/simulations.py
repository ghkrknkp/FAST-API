import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.auth import verify_api_key
from app.logging_config import logger
from app.metrics import RATE_LIMIT_EXCEEDED_TOTAL
from app.schemas import ErrorResponse, ProtectedResponse, TimeoutSimulationResponse

router = APIRouter(tags=["Simulation & Testing"])


# -------------------------------------------------------------
# 1. Server Error Simulation (HTTP 500)
# -------------------------------------------------------------
@router.get(
    "/simulate-error",
    summary="Simulate Internal Server Error (HTTP 500)",
    response_model=ErrorResponse,
    responses={500: {"model": ErrorResponse, "description": "Deliberate internal server error"}},
)
async def simulate_error():
    """
    Intentionally generates an HTTP 500 Internal Server Error.
    Records failure in Prometheus metrics and structured access logs.
    Never exposes internal stack traces or secrets to the caller.
    """
    logger.error(
        "Simulated 500 error triggered at /simulate-error",
        extra={"endpoint": "/simulate-error", "status_code": 500, "event_type": "simulated_error"},
    )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Simulated internal server error for monitoring validation.",
    )


# -------------------------------------------------------------
# 2. Latency / Timeout Simulation (Delay > 3s)
# -------------------------------------------------------------
@router.get(
    "/simulate-timeout",
    summary="Simulate Slow API Latency / Timeout",
    response_model=TimeoutSimulationResponse,
)
async def simulate_timeout(
    delay: float = Query(
        default=3.5,
        ge=0.1,
        le=15.0,
        description="Artificial delay in seconds (default: 3.5s to breach the 3s SLA threshold)",
    )
) -> TimeoutSimulationResponse:
    """
    Simulates high latency using non-blocking asynchronous sleep.
    By default sleeps 3.5 seconds, which exceeds the 3.0-second SLA and
    triggers the SlowAPIResponse alert rule.
    """
    start_time = time.perf_counter()
    logger.warning(
        f"Simulating slow response with delay={delay}s",
        extra={"endpoint": "/simulate-timeout", "delay_seconds": delay, "event_type": "simulated_delay"},
    )

    # Non-blocking async sleep
    await asyncio.sleep(delay)

    actual_duration = time.perf_counter() - start_time
    return TimeoutSimulationResponse(
        status="completed",
        requested_delay_seconds=delay,
        actual_duration_seconds=round(actual_duration, 3),
        message="Completed delayed response successfully.",
    )


# -------------------------------------------------------------
# 3. Rate Limit Simulation (HTTP 429)
# -------------------------------------------------------------
@router.get(
    "/simulate-rate-limit",
    summary="Simulate Rate Limit Exceeded (HTTP 429)",
    response_model=ErrorResponse,
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded response"}},
)
async def simulate_rate_limit(response: Response):
    """
    Simulates an HTTP 429 Too Many Requests response with a Retry-After header.
    Increments the fastapi_rate_limit_exceeded_total counter.
    """
    RATE_LIMIT_EXCEEDED_TOTAL.labels(endpoint="/simulate-rate-limit").inc()
    logger.warning(
        "Rate limit quota exceeded on /simulate-rate-limit",
        extra={"endpoint": "/simulate-rate-limit", "status_code": 429, "event_type": "rate_limit_exceeded"},
    )
    response.headers["Retry-After"] = "60"
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Please wait 60 seconds before retrying.",
        headers={"Retry-After": "60"},
    )


# -------------------------------------------------------------
# 4. Protected Resource (Authentication Failure / Success Test)
# -------------------------------------------------------------
@router.get(
    "/protected",
    summary="Protected Resource (Requires X-API-Key)",
    response_model=ProtectedResponse,
    responses={
        200: {"description": "Authenticated successfully"},
        401: {"description": "Missing or invalid X-API-Key"},
    },
)
async def get_protected_resource(api_key: str = Depends(verify_api_key)) -> ProtectedResponse:
    """
    Demonstrates secure endpoint behavior.
    Requires header `X-API-Key`.
    Missing or wrong keys trigger HTTP 401 and increment `fastapi_auth_failures_total`.
    """
    return ProtectedResponse(
        status="success",
        message="Authenticated successfully via API Key.",
        accessed_at=datetime.now(timezone.utc).isoformat(),
    )
