"""
Configuration settings for the access control service.

This module defines the application settings using Pydantic's BaseSettings,
loading values from environment variables and .env files. It includes
configuration for database connections, JWT authentication, and cloud services.

Example:
    ```python
    from app.config import settings

    # Access database URL
    db_url = settings.database_url

    # Access JWT settings
    jwt_expire_minutes = settings.jwt_access_token_expire_minutes
    ```
"""

from pathlib import Path

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class defines all configurable parameters for the access control service,
    including application settings, database configuration, JWT settings, and
    cloud service configurations.

    Attributes:
        app_env: The application environment (e.g., development, staging, production).
        app_name: The name of the application.
        app_debug: Flag to enable/disable debug mode.
        database_url: PostgreSQL database connection URL.
        pool_size: Size of the database connection pool.
        max_overflow: Maximum number of overflow connections in the pool.
        redis_url: Redis connection URL.
        jwt_algorithm: Algorithm used for JWT signing (default: RS256).
        jwt_issuer: Issuer claim for JWT tokens.
        jwt_access_token_expire_minutes: Access token expiration time in minutes.
        jwt_refresh_token_expire_days: Refresh token expiration time in days.
        private_key_path: Path to the private key for JWT signing.
        public_key_path: Path to the public key for JWT verification.
        gcp_project_id: Google Cloud Platform project ID.
        pubsub_topic_id: Pub/Sub topic ID for event publishing.
    """

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ──────────── APPLICATION ──────────── #
    app_env: str = "development"
    app_name: str = "access-control-service"
    app_debug: bool = False
    log_level: str = "INFO"

    # ──────────── DATABASE ──────────── #
    database_url: PostgresDsn = Field(default=...)
    test_database_url: PostgresDsn | None = None
    pool_size: int = 10
    max_overflow: int = 20
    redis_url: RedisDsn = Field(default=...)

    # ──────────── JWT ──────────── #
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "access-control-service"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    private_key_path: Path = Path("keys/private_key.pem")
    public_key_path: Path = Path("keys/public_key.pem")

    # ──────────── GCP ──────────── #
    gcp_project_id: str = Field(default=...)
    pubsub_topic_id: str = Field(default=...)


settings = Settings()
