import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx

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

    monkeypatch.setattr(health, "_check_database", lambda: health.HealthComponent(status="ok"))
    monkeypatch.setattr(health, "_check_auth0", lambda: health.HealthComponent(status="ok"))

    response = get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "backend": {"status": "ok"},
            "database": {"status": "ok"},
            "auth0": {"status": "ok"},
        },
    }


def test_health_check_reports_degraded_dependencies(monkeypatch) -> None:
    from app.routers import health

    monkeypatch.setattr(health, "_check_database", lambda: health.HealthComponent(status="error"))
    monkeypatch.setattr(health, "_check_auth0", lambda: health.HealthComponent(status="ok"))

    response = get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["database"] == {"status": "error"}


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
