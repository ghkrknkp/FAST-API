from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.config import settings
from app.metrics import AUTH_FAILURES_TOTAL
from app.logging_config import logger

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Validates the X-API-Key header.
    Rejects missing or invalid credentials with HTTP 401 and tracks metrics.
    Never exposes key content in logs or response bodies.
    """
    if not api_key:
        AUTH_FAILURES_TOTAL.labels(endpoint="/protected", reason="missing_header").inc()
        logger.warning(
            "Authentication failed: X-API-Key header is missing.",
            extra={"endpoint": "/protected", "status_code": 401, "event_type": "auth_failure"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header 'X-API-Key'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != settings.API_KEY:
        AUTH_FAILURES_TOTAL.labels(endpoint="/protected", reason="invalid_key").inc()
        logger.warning(
            "Authentication failed: Provided API key is invalid.",
            extra={"endpoint": "/protected", "status_code": 401, "event_type": "auth_failure"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
