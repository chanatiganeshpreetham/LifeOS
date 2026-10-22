import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_production_rejects_development_defaults() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY must be explicitly configured"):
        Settings(_env_file=None, environment="production")


def test_production_accepts_explicit_configuration() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://user:password@db.example.com/lifeos",
        secret_key=SecretStr("a-production-secret-value-that-is-long-enough"),
        frontend_url="https://lifeos.example.com",
        auth0_domain="tenant.example.com",
        auth0_client_id="client-id",
        auth0_audience="https://api.example.com",
        mail_host="smtp.example.com",
    )

    assert settings.environment == "production"
