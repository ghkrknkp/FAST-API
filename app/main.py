from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import logger
from app.metrics import get_metrics_payload
from app.middleware import PrometheusMiddleware
from app.routers import dashboard, health, products, simulations, users
from app.schemas import ErrorResponse, RootResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events: startup and shutdown."""
    logger.info(
        f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...",
        extra={"event_type": "app_startup"},
    )
    yield
    logger.info(
        f"Shutting down {settings.APP_NAME}...",
        extra={"event_type": "app_shutdown"},
    )


app = FastAPI(
    title="API Monitoring Dashboard Service",
    description=(
        "Production-ready FastAPI REST service instrumented with Prometheus metrics, "
        "comprehensive failure simulations, structured logging, and Grafana observability."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register high-reliability Prometheus instrumentation middleware
app.add_middleware(PrometheusMiddleware)


# -------------------------------------------------------------
# Global Exception Handlers (Clean JSON, No Leaked Stack Traces)
# -------------------------------------------------------------
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Error", "detail": exc.detail, "status_code": exc.status_code},
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception captured: {exc}",
        extra={"endpoint": request.url.path, "event_type": "unhandled_exception"},
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected server error occurred. Please contact the administrator.",
            "status_code": 500,
        },
    )


# -------------------------------------------------------------
# Core Root & Metrics Endpoints
# -------------------------------------------------------------
@app.get(
    "/",
    response_model=RootResponse,
    summary="Application root and metadata",
    tags=["Root"],
)
async def root() -> RootResponse:
    """Returns application status and useful discovery links."""
    return RootResponse(
        message="FastAPI Monitoring API is fully operational",
        service=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs",
        metrics_url="/metrics",
        dashboard_url="/dashboard",
    )


@app.get(
    "/metrics",
    summary="Prometheus Metrics Exposition Endpoint",
    tags=["Observability"],
)
async def metrics():
    """
    Exposes metrics in Prometheus text format (version 0.0.4).
    Scraped periodically by Prometheus.
    """
    payload, content_type = get_metrics_payload()
    return Response(content=payload, media_type=content_type)


# -------------------------------------------------------------
# Router Registrations
# -------------------------------------------------------------
app.include_router(health.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(simulations.router)
app.include_router(dashboard.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
