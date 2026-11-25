from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.services.ai_credit as ai_credit
import app.services.credit_scoring as scoring
import app.services.whatsapp as whatsapp
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def client(monkeypatch) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        _env_file=None,
        environment="test",
        require_paid_credit_history=True,
        credit_ml_enabled=False,
        openrouter_enabled=False,
        whatsapp_enabled=False,
    )
    for module in (scoring, ai_credit, whatsapp):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
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


async def _new_client(client: AsyncClient, headers: dict, document: str) -> str:
    created = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Sin",
            "last_name": "Historial",
            "document": document,
            "phone": "987654321",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def test_evaluate_enqueues_review_for_client_without_history(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    client_id = await _new_client(client, headers, "77770001")

    evaluation = await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "50.00"},
    )
    assert evaluation.status_code == 200, evaluation.text
    assert evaluation.json()["requires_manual_review"] is True

    reviews = await client.get("/api/v1/credits/reviews?status=pendiente", headers=headers)
    assert reviews.status_code == 200, reviews.text
    body = reviews.json()
    assert len(body) == 1
    assert body[0]["client_id"] == client_id
    assert body[0]["decision"] == "REQUIRES_OWNER_REVIEW"


async def test_distinct_evaluations_create_distinct_reviews(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    client_id = await _new_client(client, headers, "77770002")

    await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "50.00"},
    )
    await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "50.00"},
    )

    reviews = await client.get("/api/v1/credits/reviews", headers=headers)
    assert reviews.status_code == 200
    assert len(reviews.json()) == 2


async def test_assign_and_resolve_review(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    client_id = await _new_client(client, headers, "77770003")

    await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "50.00"},
    )
    reviews = await client.get("/api/v1/credits/reviews?status=pendiente", headers=headers)
    review_id = reviews.json()[0]["id"]

    assigned = await client.post(f"/api/v1/credits/reviews/{review_id}/assign", headers=headers)
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "asignada"

    resolved = await client.post(
        f"/api/v1/credits/reviews/{review_id}/resolve?resolution=aprobada&note=OK",
        headers=headers,
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["status"] == "resuelta"
    assert body["resolution"] == "aprobada"
    assert body["resolution_note"] == "OK"


async def test_resolve_already_resolved_returns_conflict(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    client_id = await _new_client(client, headers, "77770004")

    await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "50.00"},
    )
    reviews = await client.get("/api/v1/credits/reviews?status=pendiente", headers=headers)
    review_id = reviews.json()[0]["id"]

    first = await client.post(
        f"/api/v1/credits/reviews/{review_id}/resolve?resolution=rechazada",
        headers=headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/credits/reviews/{review_id}/resolve?resolution=aprobada",
        headers=headers,
    )
    assert second.status_code == 409


async def test_resolve_unknown_returns_404(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    import uuid

    response = await client.post(
        f"/api/v1/credits/reviews/{uuid.uuid4()}/resolve?resolution=aprobada",
        headers=headers,
    )
    assert response.status_code == 404


async def test_review_enqueued_on_direct_credit_without_history(client: AsyncClient) -> None:
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    client_id = await _new_client(client, headers, "77770005")

    # direct credit without history requires manual override; should still enqueue review
    credit = await client.post(
        "/api/v1/credits",
        headers=headers,
        json={
            "client_id": client_id,
            "amount": "40.00",
            "credit_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
            "manual_override": True,
            "exception_reason": "Revision obligatoria por falta de historial.",
        },
    )
    assert credit.status_code == 201, credit.text

    reviews = await client.get("/api/v1/credits/reviews", headers=headers)
    assert reviews.status_code == 200
    assert len(reviews.json()) >= 1