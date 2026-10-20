from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEVELOPMENT_SECRET = "development-only-secret-key-change-before-deployment"
_DEVELOPMENT_DATABASE_URL = "postgresql+pg8000://lifeos:lifeos@localhost:5432/lifeos"
_DEVELOPMENT_REDIS_URL = "redis://localhost:6379/0"
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = _DEVELOPMENT_DATABASE_URL
    redis_url: str = _DEVELOPMENT_REDIS_URL
    secret_key: SecretStr = SecretStr(_DEVELOPMENT_SECRET)
    frontend_url: str = "http://localhost:5173"
    auth0_domain: str | None = None
    auth0_client_id: str | None = None
    auth0_audience: str | None = None
    mail_host: str | None = None
    mail_port: int = 1025
    mail_username: str | None = None
    mail_password: SecretStr | None = None
    mail_from: str = "noreply@lifeos.local"
    mail_starttls: bool = False
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None
    vapid_claims_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key.get_secret_value() == _DEVELOPMENT_SECRET:
                raise ValueError("SECRET_KEY must be explicitly configured for production")
            if len(self.secret_key.get_secret_value()) < 32:
                raise ValueError("SECRET_KEY must contain at least 32 characters in production")
            if self.database_url == _DEVELOPMENT_DATABASE_URL:
                raise ValueError("DATABASE_URL must point to a production database")
            if self.redis_url == _DEVELOPMENT_REDIS_URL:
                raise ValueError("REDIS_URL must point to a production Redis instance")
            if self.frontend_url == "http://localhost:5173":
                raise ValueError("FRONTEND_URL must be configured for production")
            if not self.auth0_domain or not self.auth0_client_id or not self.auth0_audience:
                raise ValueError(
                    "AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_AUDIENCE must be configured"
                )
            if not self.mail_host:
                raise ValueError("MAIL_HOST must be configured for production")
            if (self.mail_username is None) != (self.mail_password is None):
                raise ValueError("MAIL_USERNAME and MAIL_PASSWORD must be configured together")
            vapid_settings = (
                self.vapid_public_key,
                self.vapid_private_key,
                self.vapid_claims_email,
            )
            if any(vapid_settings) and not all(vapid_settings):
                raise ValueError(
                    "VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, and VAPID_CLAIMS_EMAIL "
                    "must be configured together"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
