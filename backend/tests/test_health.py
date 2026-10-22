import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
from sqlalchemy.engine import make_url

from app.core import dependencies
from app.main import app
from app.models.health import WaterLog


def get(path: str) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(request())


def post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)

    return asyncio.run(request())


def test_health_check_reports_all_components(monkeypatch) -> None:
    from app.routers import health

    monkeypatch.setattr(
        health,
        "_check_database",
        lambda: health.DatabaseHealthComponent(status="ok", provider="prisma_postgres"),
    )
    monkeypatch.setattr(health, "_check_auth0", lambda: health.HealthComponent(status="ok"))
    monkeypatch.setattr(
        health,
        "_check_background_tasks",
        lambda: health.BackgroundTasksHealth(
            status="ok",
            scheduler=health.HealthComponent(status="ok"),
        ),
    )

    response = get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "backend": {"status": "ok"},
            "database": {"status": "ok", "provider": "prisma_postgres"},
            "auth0": {"status": "ok"},
            "background_tasks": {
                "status": "ok",
                "scheduler": {"status": "ok"},
            },
        },
    }


def test_health_check_reports_degraded_dependencies(monkeypatch) -> None:
    from app.routers import health

    monkeypatch.setattr(
        health,
        "_check_database",
        lambda: health.DatabaseHealthComponent(status="error", provider="prisma_postgres"),
    )
    monkeypatch.setattr(health, "_check_auth0", lambda: health.HealthComponent(status="ok"))
    monkeypatch.setattr(
        health,
        "_check_background_tasks",
        lambda: health.BackgroundTasksHealth(
            status="ok",
            scheduler=health.HealthComponent(status="ok"),
        ),
    )

    response = get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["database"] == {
        "status": "error",
        "provider": "prisma_postgres",
    }


def test_database_health_refuses_non_prisma_host(monkeypatch) -> None:
    from app.routers import health

    monkeypatch.setattr(
        health,
        "engine",
        SimpleNamespace(url=make_url("postgresql+pg8000://user:password@localhost/lifeos")),
    )

    result = health._check_database()

    assert result == health.DatabaseHealthComponent(status="error", provider="other")


def test_database_health_checks_prisma_host(monkeypatch) -> None:
    from app.routers import health

    calls: list[str] = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            calls.append(str(statement))

    monkeypatch.setattr(
        health,
        "engine",
        SimpleNamespace(
            url=make_url("postgresql+pg8000://user:password@pooled.db.prisma.io/postgres"),
            connect=Connection,
        ),
    )

    result = health._check_database()

    assert result == health.DatabaseHealthComponent(status="ok", provider="prisma_postgres")
    assert calls == ["SELECT 1"]


def test_background_task_health_checks_recent_scheduler_cycle(monkeypatch) -> None:
    from app.routers import health

    monkeypatch.setattr(health, "is_scheduler_healthy", lambda: True)

    result = health._check_background_tasks()

    assert result.status == "ok"
    assert result.scheduler.status == "ok"


def test_background_task_health_fails_when_scheduler_is_stale(monkeypatch) -> None:
    from app.routers import health

    monkeypatch.setattr(health, "is_scheduler_healthy", lambda: False)

    result = health._check_background_tasks()

    assert result.status == "error"
    assert result.scheduler.status == "error"


def test_health_check_has_no_other_api_prefix() -> None:
    response = get("/health")

    assert response.status_code == 404


def test_mood_history_accepts_seven_days(monkeypatch) -> None:
    from app.services import health as health_service

    user = SimpleNamespace(
        id=uuid4(),
        timezone="Asia/Kolkata",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_current_user, lambda: user)
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_db, lambda: object())
    monkeypatch.setattr(health_service, "list_moods", lambda session, current_user, days: [])

    response = get("/api/v1/health/mood/history?days=7")

    assert response.status_code == 200
    assert response.json() == {"items": [], "days": 7}


def test_mood_history_rejects_unsupported_day_count(monkeypatch) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        timezone="Asia/Kolkata",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_current_user, lambda: user)
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_db, lambda: object())

    response = get("/api/v1/health/mood/history?days=8")

    assert response.status_code == 422
    assert response.json()["detail"] == "Input should be 7 or 30."


def test_water_endpoints_serialize_orm_logs(monkeypatch) -> None:
    from app.services import health as health_service

    user = SimpleNamespace(
        id=uuid4(),
        timezone="Asia/Kolkata",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    logged_at = datetime.now(UTC)
    water_log = WaterLog(
        id=uuid4(),
        user_id=user.id,
        amount_ml=375,
        logged_at=logged_at,
        log_date=date.today(),
    )
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_current_user, lambda: user)
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_db, lambda: object())
    monkeypatch.setattr(
        health_service,
        "get_water_today",
        lambda session, current_user: (date.today(), 375, 2000, [water_log]),
    )
    monkeypatch.setattr(
        health_service,
        "add_water",
        lambda session, current_user, payload: water_log,
    )

    today_response = get("/api/v1/health/water/today")
    add_response = post("/api/v1/health/water", {"amount_ml": 375})

    assert today_response.status_code == 200
    assert today_response.json()["items"] == [
        {
            "id": str(water_log.id),
            "amount_ml": 375,
            "logged_at": logged_at.isoformat().replace("+00:00", "Z"),
        }
    ]
    assert add_response.status_code == 201
    assert add_response.json() == {
        "id": str(water_log.id),
        "amount_ml": 375,
        "logged_at": logged_at.isoformat().replace("+00:00", "Z"),
    }
