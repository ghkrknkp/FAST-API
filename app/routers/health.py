import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Response, status

from app.config import settings
from app.metrics import APP_HEALTH_STATUS, START_TIME
from app.schemas import HealthResponse

router = APIRouter(tags=["Health & Status"])

# State toggle for live failure simulation
_forced_unhealthy_state: Optional[bool] = None


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health & Readiness Probe",
    responses={
        200: {"description": "Service is healthy and ready to accept traffic"},
        503: {"description": "Service is unhealthy or in a degraded state"},
    },
)
async def get_health(
    response: Response,
    simulate_fail: Optional[bool] = None,
) -> HealthResponse:
    """
    Evaluates application readiness and health.
    Supports query parameter `simulate_fail=true` for on-demand failure testing.
    Updates the Prometheus gauge `fastapi_app_health_status`.
    """
    global _forced_unhealthy_state

    # Check query override or environment setting
    is_unhealthy = (
        simulate_fail
        if simulate_fail is not None
        else (_forced_unhealthy_state if _forced_unhealthy_state is not None else settings.SIMULATE_UNHEALTHY)
    )

    uptime = time.time() - START_TIME
    now_iso = datetime.now(timezone.utc).isoformat()

    if is_unhealthy:
        APP_HEALTH_STATUS.set(0)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="unhealthy",
            service=settings.APP_NAME,
            uptime_seconds=round(uptime, 2),
            timestamp=now_iso,
            version="1.0.0",
            details={"error": "Deliberately simulated unhealthy health-check condition."},
        )

    APP_HEALTH_STATUS.set(1)
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        uptime_seconds=round(uptime, 2),
        timestamp=now_iso,
        version="1.0.0",
        details={"checks": {"memory": "ok", "process": "running"}},
    )


@router.post(
    "/health/toggle-state",
    summary="Toggle service health state for alert verification",
    include_in_schema=True,
)
async def toggle_health_state(unhealthy: bool):
    """Admin utility to switch application health state between healthy and unhealthy."""
    global _forced_unhealthy_state
    _forced_unhealthy_state = unhealthy
    APP_HEALTH_STATUS.set(0 if unhealthy else 1)
    return {"message": f"Service health set to {'unhealthy' if unhealthy else 'healthy'}"}
