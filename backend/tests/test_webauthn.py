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
        await db.commit()

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


async def login(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    assert response.status_code == 200
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_webauthn_registration_begin_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/webauthn/registration/begin", json={})
    assert response.status_code == 401


async def test_webauthn_registration_begin_returns_options(client: AsyncClient) -> None:
    token = (await login(client))["access_token"]
    response = await client.post(
        "/api/v1/auth/webauthn/registration/begin",
        headers=auth_headers(token),
        json={"name": "Mi llave"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert "challenge" in body["options"]
    assert "rp" in body["options"]
    assert "user" in body["options"]
    assert body["options"]["user"]["name"] == "admin@baylon.com"


async def test_webauthn_list_and_delete_credentials(client: AsyncClient) -> None:
    token = (await login(client))["access_token"]
    headers = auth_headers(token)

    empty = await client.get("/api/v1/auth/webauthn/credentials", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == []

    missing = await client.delete(
        "/api/v1/auth/webauthn/credentials/not-a-real-id", headers=headers
    )
    assert missing.status_code == 404

    bad_finish = await client.post(
        "/api/v1/auth/webauthn/registration/finish",
        headers=headers,
        json={
            "session_id": "bogus-session",
            "challenge": "AAAAAA",
            "credential": {},
        },
    )
    assert bad_finish.status_code == 400


async def test_webauthn_authentication_begin_is_public(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/webauthn/authentication/begin", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert "challenge" in body["options"]

    with_user = await client.post(
        "/api/v1/auth/webauthn/authentication/begin",
        json={"user_handle": "00000000-0000-0000-0000-000000000000"},
    )
    assert with_user.status_code == 404