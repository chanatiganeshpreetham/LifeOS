import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx

from app.core import dependencies
from app.main import app
from app.repositories import auth as auth_repository


def request(path: str, method: str = "GET") -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path)

    return asyncio.run(send_request())


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        avatar_url=None,
        timezone="Asia/Kolkata",
        is_verified=True,
        created_at=datetime.now(UTC),
        is_active=True,
    )


def test_initialize_session_returns_rate_limit_headers(monkeypatch) -> None:
    user = _user()
    monkeypatch.setitem(
        app.dependency_overrides,
        dependencies.get_auth0_access_claims,
        lambda: {"sub": "auth0|test-user"},
    )
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_db, lambda: object())
    monkeypatch.setattr(
        auth_repository,
        "get_user_by_auth0_subject",
        lambda session, subject: user,
    )

    response = request("/api/v1/auth/session", method="POST")

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.headers["x-ratelimit-limit"] == "60"


def test_get_profile_returns_rate_limit_headers(monkeypatch) -> None:
    user = _user()
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_current_user, lambda: user)

    response = request("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.headers["x-ratelimit-limit"] == "60"
