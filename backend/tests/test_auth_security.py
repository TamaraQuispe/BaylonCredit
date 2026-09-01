from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        db.add(
            User(
                email="admin@baylon.com",
                full_name="Admin Baylon",
                hashed_password=hash_password("secure-password"),
                role=UserRole.ADMIN,
            )
        )
        db.add(
            User(
                email="vendedor@baylon.com",
                full_name="Vendedor Baylon",
                hashed_password=hash_password("secure-password"),
                role=UserRole.OPERATOR,
            )
        )
        await db.commit()

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


async def login(client: AsyncClient, email: str = "admin@baylon.com") -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "secure-password"},
    )
    assert response.status_code == 200
    return response.json()


async def test_login_returns_refresh_token_and_rotation(client: AsyncClient) -> None:
    first = await login(client)
    assert first["access_token"]
    assert first["refresh_token"]

    rotated = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != first["refresh_token"]

    reused = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert reused.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    session = await login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}

    logged_out = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": session["refresh_token"]},
    )
    assert logged_out.status_code == 204

    reused = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": session["refresh_token"]},
    )
    assert reused.status_code == 401


async def test_profile_update_and_password_change(client: AsyncClient) -> None:
    session = await login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}

    updated = await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"full_name": "Admin Actualizado", "position": "Gerente", "phone": "999888777"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Admin Actualizado"
    assert updated.json()["position"] == "Gerente"

    changed = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "secure-password", "new_password": "nueva-password-larga"},
    )
    assert changed.status_code == 204

    refused = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "incorrecta", "new_password": "nueva-password-larga"},
    )
    assert refused.status_code == 400

    rotated = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": session["refresh_token"]},
    )
    assert rotated.status_code == 401


async def test_invalid_refresh_token_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "token-inexistente-de-al-menos-treinta-y-dos-caracteres"},
    )
    assert response.status_code == 401


async def test_login_rate_limiting_after_repeated_failures(client: AsyncClient) -> None:
    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@baylon.com", "password": "incorrecta"},
        )
        assert response.status_code == 401

    blocked = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    assert blocked.status_code == 429


async def test_users_crud_and_audit_require_admin(client: AsyncClient) -> None:
    operator_session = await login(client, "vendedor@baylon.com")
    operator_headers = {"Authorization": f"Bearer {operator_session['access_token']}"}

    forbidden = await client.post(
        "/api/v1/users",
        headers=operator_headers,
        json={
            "email": "nuevo@baylon.com",
            "full_name": "Nuevo Usuario",
            "password": "secure-password",
            "role": "viewer",
        },
    )
    assert forbidden.status_code == 403

    admin_session = await login(client)
    admin_headers = {"Authorization": f"Bearer {admin_session['access_token']}"}

    created = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "nuevo@baylon.com",
            "full_name": "Nuevo Usuario",
            "password": "secure-password",
            "role": "viewer",
            "position": "Supervisor",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"role": "operator", "phone": "111222333"},
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "operator"

    disabled = await client.patch(
        f"/api/v1/users/{user_id}/status?active=false",
        headers=admin_headers,
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    audit = await client.get("/api/v1/users/audit", headers=admin_headers)
    assert audit.status_code == 200
    entries = audit.json()
    actions = [entry["action"] for entry in entries]
    assert "user_created" in actions
    assert "user_updated" in actions
    assert "user_deactivated" in actions
    user_actions = [entry for entry in entries if entry["action"].startswith("user_")]
    assert user_actions
    assert all(entry["actor_email"] == "admin@baylon.com" for entry in user_actions)

    forbidden_audit = await client.get("/api/v1/users/audit", headers=operator_headers)
    assert forbidden_audit.status_code == 403


async def test_admin_cannot_disable_own_account(client: AsyncClient) -> None:
    admin_session = await login(client)
    admin_headers = {"Authorization": f"Bearer {admin_session['access_token']}"}
    admin_id = admin_session["user"]["id"]

    response = await client.patch(
        f"/api/v1/users/{admin_id}/status?active=false",
        headers=admin_headers,
    )
    assert response.status_code == 400