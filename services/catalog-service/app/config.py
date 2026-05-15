from pathlib import Path

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ──────────── APPLICATION ──────────── #
    app_env: str = "development"
    app_name: str = "catalog-service"
    app_debug: bool = False
    log_level: str = "INFO"

    # ──────────── DATABASE ──────────── #
    database_url: PostgresDsn = Field(default=...)
    test_database_url: PostgresDsn | None = None
    pool_size: int = 10
    max_overflow: int = 20

    # ──────────── IAM / JWT ──────────── #
    iam_jwks_url: str = Field(default=...)

    # ──────────── GCP ──────────── #
    gcp_project_id: str = Field(default=...)
    pubsub_topic_id: str = Field(default=...)


settings = Settings()
