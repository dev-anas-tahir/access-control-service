from pathlib import Path

from pydantic import Field, PostgresDsn, RedisDsn
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
    app_name: str = "access-control-service"
    app_debug: bool = False

    # ──────────── DATABASE ──────────── #
    database_url: PostgresDsn = Field(default=...)
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
