from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

OAUTH_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
)

AppEnv = Literal["development", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = "development"
    host: str = "127.0.0.1"
    port: int = 8001
    reload: bool = True
    log_level: str = "info"

    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://127.0.0.1:8001/auth/callback"
    session_secret: str = "dev-secret-change-in-production"
    # Session cookie lifetime in seconds (default 1 year). Cookie persists across
    # Vercel cold starts and browser restarts; cleared only on explicit logout.
    session_max_age: int = 365 * 24 * 60 * 60

    @property
    def is_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def get_settings() -> Settings:
    return Settings()
