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


async def _new_client(client: AsyncClient, headers: dict, document: str) -> str:
    created = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Clave",
            "last_name": "Idempotente",
            "document": document,
            "phone": "987654321",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _credit_body(client_id: str, amount: str = "40.00") -> dict:
    return {
        "client_id": client_id,
        "amount": amount,
        "credit_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=10)).isoformat(),
    }


async def test_idempotency_key_replays_without_duplicating(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Idempotency-Key": "credito-0001",
    }
    client_id = await _new_client(client, headers, "90909090")

    first = await client.post("/api/v1/credits", headers=headers, json=_credit_body(client_id))
    assert first.status_code == 201, first.text
    replay = await client.post("/api/v1/credits", headers=headers, json=_credit_body(client_id))
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]

    listed = await client.get("/api/v1/credits", headers=headers)
    assert listed.status_code == 200, listed.text
    assert len([row for row in listed.json() if row["client_id"] == client_id]) == 1


async def test_idempotency_key_with_other_payload_conflicts(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Idempotency-Key": "credito-0002",
    }
    client_id = await _new_client(client, headers, "90909091")
    first = await client.post("/api/v1/credits", headers=headers, json=_credit_body(client_id))
    assert first.status_code == 201, first.text

    conflicting = await client.post(
        "/api/v1/credits", headers=headers, json=_credit_body(client_id, "41.00")
    )
    assert conflicting.status_code == 409, conflicting.text
    assert "otra solicitud" in conflicting.json()["detail"]


async def test_idempotency_key_is_scoped_per_operation(client: AsyncClient) -> None:
    session = await _login(client)
    auth = {"Authorization": f"Bearer {session['access_token']}"}
    headers = {**auth, "Idempotency-Key": "compartida-01"}
    client_id = await _new_client(client, auth, "90909092")
    credit = await client.post("/api/v1/credits", headers=headers, json=_credit_body(client_id))
    assert credit.status_code == 201, credit.text

    payment = await client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "client_id": client_id,
            "allocations": [{"credit_id": credit.json()["id"], "amount": "40.00"}],
            "payment_date": date.today().isoformat(),
            "method": "Efectivo",
        },
    )
    assert payment.status_code == 201, payment.text


async def test_idempotency_key_is_released_when_request_is_rejected(
    client: AsyncClient,
) -> None:
    session = await _login(client)
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Idempotency-Key": "credito-0004",
    }
    client_id = await _new_client(client, headers, "90909093")
    rejected = await client.post(
        "/api/v1/credits", headers=headers, json=_credit_body(client_id, "9999.00")
    )
    assert rejected.status_code == 422, rejected.text

    retry = await client.post(
        "/api/v1/credits", headers=headers, json=_credit_body(client_id, "9999.00")
    )
    assert retry.status_code == 422, retry.text
    assert "otra solicitud" not in retry.json()["detail"]