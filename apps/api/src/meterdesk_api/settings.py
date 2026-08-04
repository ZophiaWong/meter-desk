from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DEMO_AUTH_SIGNING_KEY = "meterdesk-demo-only-signing-key-change-me-before-sharing"


class Settings(BaseSettings):
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://meterdesk:meterdesk@localhost:5432/meterdesk"
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=5, ge=0)
    database_pool_timeout_seconds: float = Field(default=5, gt=0)
    database_connect_timeout_seconds: int = Field(default=3, gt=0)
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    demo_auth_signing_key: str = Field(
        default=DEFAULT_DEMO_AUTH_SIGNING_KEY,
        min_length=32,
    )
    demo_auth_token_ttl_seconds: int = Field(default=8 * 60 * 60, gt=0)

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def reject_demo_auth_in_production(self) -> "Settings":
        if self.environment.strip().lower() in {"production", "prod"}:
            raise ValueError("Demo authentication cannot run in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
