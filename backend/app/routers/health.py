import json
import logging
from typing import Literal
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


class HealthComponent(BaseModel):
    status: Literal["ok", "error"]


class HealthChecks(BaseModel):
    backend: HealthComponent
    database: HealthComponent
    auth0: HealthComponent


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: HealthChecks


def _check_database() -> HealthComponent:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return HealthComponent(status="error")
    return HealthComponent(status="ok")


def _check_auth0() -> HealthComponent:
    settings = get_settings()
    domain = (settings.auth0_domain or "").strip().removeprefix("https://").rstrip("/")
    if (
        not domain
        or "/" in domain
        or "://" in domain
        or not settings.auth0_client_id
        or not settings.auth0_audience
    ):
        return HealthComponent(status="error")

    request = Request(
        f"https://{domain}/.well-known/openid-configuration",
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=3) as response:
            metadata = json.load(response)
    except (OSError, URLError, ValueError):
        logger.exception("Auth0 health check failed")
        return HealthComponent(status="error")

    expected_issuer = f"https://{domain}/"
    if (
        not isinstance(metadata, dict)
        or metadata.get("issuer") != expected_issuer
        or not isinstance(metadata.get("jwks_uri"), str)
    ):
        logger.error("Auth0 returned invalid OpenID configuration metadata")
        return HealthComponent(status="error")
    return HealthComponent(status="ok")


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    checks = HealthChecks(
        backend=HealthComponent(status="ok"),
        database=_check_database(),
        auth0=_check_auth0(),
    )
    status: Literal["ok", "degraded"] = (
        "ok"
        if all(check.status == "ok" for check in (checks.backend, checks.database, checks.auth0))
        else "degraded"
    )
    return HealthResponse(status=status, checks=checks)
