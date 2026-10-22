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
from app.services.scheduler import is_scheduler_healthy

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


class HealthComponent(BaseModel):
    status: Literal["ok", "error"]


class DatabaseHealthComponent(HealthComponent):
    provider: Literal["postgresql", "prisma_postgres", "other"]


class BackgroundTasksHealth(BaseModel):
    status: Literal["ok", "error"]
    scheduler: HealthComponent


class HealthChecks(BaseModel):
    backend: HealthComponent
    database: DatabaseHealthComponent
    auth0: HealthComponent
    background_tasks: BackgroundTasksHealth


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: HealthChecks


def _check_database() -> DatabaseHealthComponent:
    host = (engine.url.host or "").lower()
    is_postgres = engine.url.drivername.startswith("postgres")
    provider: Literal["postgresql", "prisma_postgres", "other"] = (
        "prisma_postgres"
        if host == "db.prisma.io" or host.endswith(".db.prisma.io")
        else "postgresql" if is_postgres else "other"
    )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return DatabaseHealthComponent(status="error", provider=provider)
    return DatabaseHealthComponent(status="ok", provider=provider)


def _check_background_tasks() -> BackgroundTasksHealth:
    scheduler = HealthComponent(status="ok" if is_scheduler_healthy() else "error")
    status: Literal["ok", "error"] = scheduler.status
    return BackgroundTasksHealth(
        status=status,
        scheduler=scheduler,
    )


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
        background_tasks=_check_background_tasks(),
    )
    status: Literal["ok", "degraded"] = (
        "ok"
        if all(
            check.status == "ok"
            for check in (
                checks.backend,
                checks.database,
                checks.auth0,
                checks.background_tasks,
            )
        )
        else "degraded"
    )
    return HealthResponse(status=status, checks=checks)
