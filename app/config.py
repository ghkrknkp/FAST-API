import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "api-monitoring-dashboard"
    APP_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # Security: Demonstration API Key for GET /protected
    API_KEY: str = "secret-token-demo-key-12345"

    # Health Check toggle for testing failure states
    SIMULATE_UNHEALTHY: bool = False


settings = Settings()
