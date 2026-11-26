import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.services.ai_credit as ai_credit
import app.services.credit_scoring as scoring
import app.services.whatsapp as whatsapp
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.commerce import CreditReview, CreditReviewStatus
from app.models.settings import DEFAULT_ORGANIZATION_ID, Organization
from app.models.user import User, UserRole
from app.services import credit_review as review_service


@pytest_asyncio.fixture
async def app_context(
    monkeypatch,
) -> AsyncIterator[tuple[AsyncClient, async_sessionmaker[AsyncSession]]]:
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
    # SQLite no distingue zonas horarias; TEST_DATABASE_URL permite correr estos
    # tests contra Postgres real en CI (job backend-postgres).
    database_url = os.environ.get("TEST_DATABASE_URL")
    engine = create_async_engine(database_url or "sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        if database_url:
            await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        # La migracion 0013 siembra esta organizacion; SQLite no aplica la FK
        # de clients.organization_id y sin ella Postgres rechaza el insert.
        db.add(Organization(id=DEFAULT_ORGANIZATION_ID, name="Credify"))
        db.add(
            User(
                email="admin@credify.com",
                full_name="Admin Credify",
                hashed_password=hash_password("secure-password"),
                role=UserRole.ADMIN,
            )
        )
        db.add(
            User(
                email="viewer@credify.com",
                full_name="Consulta Credify",
                hashed_password=hash_password("secure-password"),
                role=UserRole.VIEWER,
            )
        )
        await db.commit()

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app_context) -> AsyncClient:
    return app_context[0]


async def _login(client: AsyncClient, email: str = "admin@credify.com") -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "secure-password"},
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


async def test_review_actions_denied_for_viewer_role(client: AsyncClient) -> None:
    admin = await _login(client)
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    client_id = await _new_client(client, admin_headers, "77770006")

    evaluation = await client.post(
        "/api/v1/credits/evaluate",
        headers=admin_headers,
        json={"client_id": client_id, "amount": "50.00"},
    )
    assert evaluation.status_code == 200, evaluation.text

    reviews = await client.get(
        "/api/v1/credits/reviews?status=pendiente", headers=admin_headers
    )
    assert reviews.status_code == 200, reviews.text
    review_id = reviews.json()[0]["id"]

    viewer = await _login(client, "viewer@credify.com")
    viewer_headers = {"Authorization": f"Bearer {viewer['access_token']}"}

    assigned = await client.post(
        f"/api/v1/credits/reviews/{review_id}/assign", headers=viewer_headers
    )
    assert assigned.status_code == 403, assigned.text

    resolved = await client.post(
        f"/api/v1/credits/reviews/{review_id}/resolve?resolution=aprobada",
        headers=viewer_headers,
    )
    assert resolved.status_code == 403, resolved.text


async def _pending_review_id(
    client: AsyncClient, headers: dict, document: str
) -> str:
    client_id = await _new_client(client, headers, document)
    evaluation = await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "50.00"},
    )
    assert evaluation.status_code == 200, evaluation.text
    reviews = await client.get(
        "/api/v1/credits/reviews?status=pendiente", headers=headers
    )
    assert reviews.status_code == 200, reviews.text
    return reviews.json()[0]["id"]


async def _set_deadline(session_factory, review_id: str, **values) -> None:
    async with session_factory() as db:
        review = await db.get(CreditReview, UUID(review_id))
        assert review is not None
        for field, value in values.items():
            setattr(review, field, value)
        await db.commit()


async def test_enqueue_sets_expiry_deadline(app_context) -> None:
    client, session_factory = app_context
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    review_id = await _pending_review_id(client, headers, "77770007")

    async with session_factory() as db:
        review = await db.get(CreditReview, UUID(review_id))
        assert review is not None
        assert review.expires_at is not None
        assert review.expires_at > review.created_at


async def test_expire_endpoint_closes_overdue_reviews(app_context) -> None:
    client, session_factory = app_context
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    review_id = await _pending_review_id(client, headers, "77770008")
    await _set_deadline(
        session_factory,
        review_id,
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )

    first = await client.post("/api/v1/credits/reviews/expire", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json() == {"expired": 1}

    second = await client.post("/api/v1/credits/reviews/expire", headers=headers)
    assert second.status_code == 200, second.text
    assert second.json() == {"expired": 0}

    pending = await client.get(
        "/api/v1/credits/reviews?status=pendiente", headers=headers
    )
    assert pending.status_code == 200, pending.text
    assert pending.json() == []

    expired = await client.get(
        "/api/v1/credits/reviews?status=expirada", headers=headers
    )
    assert expired.status_code == 200, expired.text
    body = expired.json()
    assert len(body) == 1
    assert body[0]["status"] == "expirada"
    assert body[0]["resolution"] == "expirada"
    assert body[0]["resolved_at"] is not None


async def test_expire_endpoint_requires_admin(client: AsyncClient) -> None:
    viewer = await _login(client, "viewer@credify.com")
    headers = {"Authorization": f"Bearer {viewer['access_token']}"}

    response = await client.post("/api/v1/credits/reviews/expire", headers=headers)

    assert response.status_code == 403, response.text


async def test_overdue_reviews_without_deadline_use_created_at(app_context) -> None:
    client, session_factory = app_context
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    review_id = await _pending_review_id(client, headers, "77770009")
    ttl = get_settings().credit_review_ttl_hours
    await _set_deadline(
        session_factory,
        review_id,
        expires_at=None,
        created_at=datetime.now(UTC) - timedelta(hours=ttl + 1),
    )

    response = await client.post("/api/v1/credits/reviews/expire", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"expired": 1}


async def test_overdue_review_cannot_be_assigned_or_resolved(app_context) -> None:
    client, session_factory = app_context
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    review_id = await _pending_review_id(client, headers, "77770010")
    await _set_deadline(
        session_factory,
        review_id,
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )

    assigned = await client.post(
        f"/api/v1/credits/reviews/{review_id}/assign", headers=headers
    )
    assert assigned.status_code == 409, assigned.text
    assert "expiro" in assigned.json()["detail"]

    resolved = await client.post(
        f"/api/v1/credits/reviews/{review_id}/resolve?resolution=aprobada",
        headers=headers,
    )
    assert resolved.status_code == 409, resolved.text


async def test_list_hides_overdue_reviews_before_the_job_runs(app_context) -> None:
    client, session_factory = app_context
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    review_id = await _pending_review_id(client, headers, "77770011")
    await _set_deadline(
        session_factory,
        review_id,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    pending = await client.get(
        "/api/v1/credits/reviews?status=pendiente", headers=headers
    )
    assert pending.status_code == 200, pending.text
    assert pending.json() == []

    expired = await client.get(
        "/api/v1/credits/reviews?status=expirada", headers=headers
    )
    assert expired.status_code == 200, expired.text
    assert len(expired.json()) == 1


async def test_expire_reviews_once_closes_overdue_reviews(app_context) -> None:
    client, session_factory = app_context
    session = await _login(client)
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    review_id = await _pending_review_id(client, headers, "77770012")
    await _set_deadline(
        session_factory,
        review_id,
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )

    expired = await review_service.expire_reviews_once(session_factory)

    assert expired == 1
    async with session_factory() as db:
        review = await db.get(CreditReview, UUID(review_id))
        assert review is not None
        assert review.status is CreditReviewStatus.EXPIRED
        assert review.resolved_at is not None


async def test_review_expiry_loop_runs_a_cycle_then_sleeps(monkeypatch) -> None:
    cycles: list[int] = []

    async def fake_once(session_factory=None) -> int:
        cycles.append(1)
        return 0

    async def stop(_seconds: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(review_service, "expire_reviews_once", fake_once)
    monkeypatch.setattr(review_service.asyncio, "sleep", stop)

    with pytest.raises(asyncio.CancelledError):
        await review_service.review_expiry_loop(60)

    assert cycles == [1]


def test_expiry_interval_setting_allows_disabling_and_rejects_negatives() -> None:
    disabled = Settings(_env_file=None, credit_review_expiry_interval_minutes=0)
    assert disabled.credit_review_expiry_interval_minutes == 0

    with pytest.raises(ValueError):
        Settings(_env_file=None, credit_review_expiry_interval_minutes=-1)


def test_credit_review_timestamps_match_postgres_timestamptz() -> None:
    # SQLite acepta cualquier datetime, pero asyncpg rechaza un datetime UTC
    # contra una columna timestamp without time zone y rompe la expiracion.
    assert CreditReview.__table__.c.expires_at.type.timezone is True
    assert CreditReview.__table__.c.resolved_at.type.timezone is True
