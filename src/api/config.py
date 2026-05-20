# src/api/config.py
"""Configuration settings for the API service."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")

    # Task Processing Configuration
    max_retries: int = Field(default=3)
    max_task_age: int = Field(default=7200)  # 2 hours
    default_retry_ratio: float = Field(default=0.3)

    # Queue Pressure Thresholds
    retry_queue_warning: int = Field(default=1000)
    retry_queue_critical: int = Field(default=5000)

    # Rate Limiting Configuration
    default_rate_limit_requests: int = Field(default=100)
    default_rate_limit_interval: int = Field(default=60)

    # Circuit Breaker Configuration
    circuit_breaker_fail_max: int = Field(default=10)
    circuit_breaker_reset_timeout: int = Field(default=120)

    # Development Configuration
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # API Configuration
    api_title: str = "AsyncTaskFlow API"
    api_description: str = "Production-ready distributed API task gateway"
    api_version: str = "1.0.0"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    # Content Size Limits
    max_content_size: int = Field(default=1_048_576)  # 1 MB

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "",
    }


# Global settings instance
settings = Settings()
