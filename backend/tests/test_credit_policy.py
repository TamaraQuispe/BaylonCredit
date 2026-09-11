from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.credit_scoring import risk_from_score


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        db.add(
            User(
                email="admin@credify.com",
                full_name="Admin Credify",
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


async def _login(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@credify.com", "password": "secure-password"},
    )
    assert response.status_code == 200
    return response.json()


def test_risk_bands_are_configurable() -> None:
    assert risk_from_score(100) == risk_from_score(80)
    assert risk_from_score(80).value == "bajo"
    assert risk_from_score(79).value == "medio"
    assert risk_from_score(60).value == "medio"
    assert risk_from_score(59).value == "alto"
    assert risk_from_score(0).value == "alto"
    lowered_low = risk_from_score(72, low_min=70, medium_min=55)
    assert lowered_low.value == "bajo"
    assert risk_from_score(54, low_min=70, medium_min=55).value == "alto"


async def test_exception_requires_motivo(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    new_client = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Rosa",
            "last_name": "Luna",
            "document": "33334444",
            "phone": "987654321",
        },
    )
    assert new_client.status_code == 201, new_client.text
    client_id = new_client.json()["id"]

    without_reason = await client.post(
        "/api/v1/credits",
        headers=headers,
        json={
            "client_id": client_id,
            "amount": "9999.00",
            "credit_date": date.today().isoformat(),
            "manual_override": True,
        },
    )
    assert without_reason.status_code == 422, without_reason.text
    assert "motivo" in without_reason.json()["detail"]

    with_reason = await client.post(
        "/api/v1/credits",
        headers=headers,
        json={
            "client_id": client_id,
            "amount": "85.00",
            "credit_date": date.today().isoformat(),
            "manual_override": True,
            "exception_reason": "Commitment de pago confirmado por el dueño.",
        },
    )
    assert with_reason.status_code == 201, with_reason.text
    assert with_reason.json()["pending_amount"] == "85.00"


async def test_credit_profile_reflects_line_usage(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    new_client = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Jorge",
            "last_name": "Palacios",
            "document": "77778888",
            "phone": "987654321",
        },
    )
    client_id = new_client.json()["id"]

    credit = await client.post(
        "/api/v1/credits",
        headers=headers,
        json={
            "client_id": client_id,
            "amount": "40.00",
            "credit_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
        },
    )
    assert credit.status_code == 201, credit.text

    profile = await client.get(f"/api/v1/clients/{client_id}/credit-profile", headers=headers)
    assert profile.status_code == 200, profile.text
    body = profile.json()
    assert body["client_name"] == "Jorge Palacios"
    assert body["used"] == "40.00"
    assert Decimal(body["assigned_line"]) > 0
    assert float(body["available"]) >= 0
    assert body["active_credits"] == 1
    assert body["overdue_credits"] == 0
    assert body["last_score"] is not None


async def test_risk_report_lists_clients_with_score(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    new_client = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Ana",
            "last_name": "Flores",
            "document": "44445555",
            "phone": "987654321",
        },
    )
    client_id = new_client.json()["id"]
    evaluation = await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "30.00"},
    )
    assert evaluation.status_code == 200, evaluation.text

    report = await client.get("/api/v1/reports/risk", headers=headers)
    assert report.status_code == 200, report.text
    entries = [entry for entry in report.json()["clients"] if entry["client_id"] == client_id]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["score"] == evaluation.json()["score"]
    assert entry["risk"] == evaluation.json()["risk"]
    assert entry["recommendation"]
    assert entry["utilization_percent"] >= 0