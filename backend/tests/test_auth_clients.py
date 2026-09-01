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


async def test_login_and_create_client(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    assert login.status_code == 200
    assert login.headers["X-Request-ID"]
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Ana",
            "last_name": "Quispe",
            "business_name": "Bodega Ana",
            "document": "12345678",
            "phone": "987654321",
        },
    )
    assert created.status_code == 201
    assert created.json()["document"] == "12345678"

    listed = await client.get("/api/v1/clients", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_rejects_invalid_credentials(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
