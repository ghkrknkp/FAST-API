from typing import List, Optional
from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    message: str = Field(..., example="FastAPI Monitoring API is operational")
    service: str = Field(..., example="api-monitoring-dashboard")
    version: str = Field(..., example="1.0.0")
    docs_url: str = Field(..., example="/docs")
    metrics_url: str = Field(..., example="/metrics")
    dashboard_url: str = Field(default="/dashboard", example="/dashboard")


class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    service: str = Field(..., example="api-monitoring-dashboard")
    uptime_seconds: float = Field(..., example=120.45)
    timestamp: str = Field(..., example="2026-10-28T04:49:15Z")
    version: str = Field(..., example="1.0.0")
    details: Optional[dict] = None


class User(BaseModel):
    id: int = Field(..., example=1)
    username: str = Field(..., example="alex_dev")
    email: str = Field(..., example="alex@example.com")
    role: str = Field(..., example="Platform Engineer")
    is_active: bool = Field(default=True, example=True)


class Product(BaseModel):
    id: int = Field(..., example=101)
    name: str = Field(..., example="Cloud Observability Suite")
    category: str = Field(..., example="DevOps")
    price: float = Field(..., example=299.99)
    in_stock: bool = Field(default=True, example=True)


class ProtectedResponse(BaseModel):
    status: str = Field(..., example="success")
    message: str = Field(..., example="Authenticated successfully via API Key")
    accessed_at: str = Field(..., example="2026-10-28T04:49:15Z")


class TimeoutSimulationResponse(BaseModel):
    status: str = Field(..., example="completed")
    requested_delay_seconds: float = Field(..., example=3.5)
    actual_duration_seconds: float = Field(..., example=3.504)
    message: str = Field(..., example="Completed delayed response")


class ErrorResponse(BaseModel):
    error: str = Field(..., example="Internal Server Error")
    detail: str = Field(..., example="An unexpected error occurred during processing.")
    status_code: int = Field(..., example=500)
