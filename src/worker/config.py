# src/worker/config.py
"""Configuration settings for the worker service."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Worker application settings."""

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND"
    )

    # Task Processing Configuration
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    max_task_age: int = Field(default=7200, env="MAX_TASK_AGE")  # 2 hours
    default_retry_ratio: float = Field(default=0.3, env="DEFAULT_RETRY_RATIO")

    # Queue Pressure Thresholds
    retry_queue_warning: int = Field(default=1000, env="RETRY_QUEUE_WARNING")
    retry_queue_critical: int = Field(default=5000, env="RETRY_QUEUE_CRITICAL")

    # Rate Limiting Configuration
    default_rate_limit_requests: int = Field(
        default=100, env="DEFAULT_RATE_LIMIT_REQUESTS"
    )
    default_rate_limit_interval: int = Field(
        default=60, env="DEFAULT_RATE_LIMIT_INTERVAL"
    )

    # Circuit Breaker Configuration
    circuit_breaker_fail_max: int = Field(
        default=10, env="CIRCUIT_BREAKER_FAIL_MAX"
    )
    circuit_breaker_reset_timeout: int = Field(
        default=120, env="CIRCUIT_BREAKER_RESET_TIMEOUT"
    )

    # Development Configuration
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Worker Configuration
    worker_concurrency: int = Field(default=2, env="CELERY_WORKER_CONCURRENCY")
    worker_prefetch_multiplier: int = Field(
        default=1, env="WORKER_PREFETCH_MULTIPLIER"
    )
    task_soft_time_limit: int = Field(
        default=600, env="CELERY_TASK_SOFT_TIME_LIMIT"
    )  # 10 minutes
    task_time_limit: int = Field(
        default=900, env="CELERY_TASK_TIME_LIMIT"
    )  # 15 minutes

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }


# Global settings instance
settings = Settings()
