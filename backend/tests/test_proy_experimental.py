"""Contratos del endpoint experimental PROY: apagado, staging y sin efectos de negocio."""

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routes import proy_experimental as route
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.ml import proy_model
from app.ml.proy_contract import CONTRACT_VERSION, FEATURE_NAMES_PROY
from app.ml.proy_model import MODEL_VERSION, ProyModelUnavailable
from app.models.commerce import (
    Credit,
    CreditEvaluation,
    CreditReview,
    CreditStatus,
    PaymentMode,
    RiskLevel,
    Sale,
)
from app.models.proy_experimental import ProyExperimentalEvaluation
from app.models.settings import DEFAULT_ORGANIZATION_ID, Organization
from app.models.user import User, UserRole
from app.services import proy_experimental as service


def _staging_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "staging",
        "proy_experimental_enabled": True,
        "jwt_secret_key": "staging-only-secret-with-enough-length",
    }
    values.update(overrides)
    return Settings(**values)


@pytest_asyncio.fixture
async def app_context(monkeypatch) -> AsyncIterator[tuple[AsyncClient, async_sessionmaker]]:
    monkeypatch.setattr(route, "get_settings", lambda: _staging_settings())
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_factory
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
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _new_client(client: AsyncClient, headers: dict, document: str) -> str:
    created = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Demo",
            "last_name": "Proy",
            "document": document,
            "phone": "987654321",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def _seed_credit(
    session_factory, client_id: str, *, amount: str, pending: str
) -> None:
    """Historial directo en la base: una venta y su fiado."""
    async with session_factory() as db:
        admin = await db.scalar(select(User).where(User.email == "admin@credify.com"))
        sale = Sale(
            code=f"S-{uuid4().hex[:8].upper()}",
            payment_mode=PaymentMode.CREDIT,
            client_id=UUID(client_id),
            created_by_id=admin.id,
            subtotal=Decimal(amount),
            tax=Decimal("0"),
            total=Decimal(amount),
        )
        db.add(sale)
        await db.flush()
        db.add(
            Credit(
                code=f"F-{uuid4().hex[:8].upper()}",
                client_id=UUID(client_id),
                sale_id=sale.id,
                created_by_id=admin.id,
                original_amount=Decimal(amount),
                pending_amount=Decimal(pending),
                credit_date=date.today(),
                due_date=date.today(),
                status=CreditStatus.PAID if Decimal(pending) == 0 else CreditStatus.CURRENT,
                risk=RiskLevel.LOW,
                score=80,
                recommended_limit=Decimal("200"),
            )
        )
        await db.commit()


async def _count(session_factory, model) -> int:
    async with session_factory() as db:
        return int(await db.scalar(select(func.count(model.id))) or 0)


async def test_disabled_by_default_and_never_enabled_outside_staging() -> None:
    assert Settings(_env_file=None).proy_experimental_enabled is False
    with pytest.raises(ValueError, match="restricted to staging"):
        Settings(
            _env_file=None,
            environment="production",
            proy_experimental_enabled=True,
            jwt_secret_key="production-secret-with-enough-length",
        )


async def test_disabled_flag_returns_404(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(
        route, "get_settings", lambda: _staging_settings(proy_experimental_enabled=False)
    )
    headers = await _login(client)

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": str(uuid4()), "amount": "40.00"},
    )

    assert response.status_code == 404, response.text


async def test_flag_is_ignored_outside_staging(client: AsyncClient, monkeypatch) -> None:
    # El validador de Settings ya impide arrancar asi; el endpoint vuelve a comprobarlo.
    monkeypatch.setattr(
        route,
        "get_settings",
        lambda: SimpleNamespace(environment="test", proy_experimental_enabled=True),
    )
    headers = await _login(client)

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": str(uuid4()), "amount": "40.00"},
    )

    assert response.status_code == 404, response.text


async def test_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        json={"client_id": str(uuid4()), "amount": "40.00"},
    )

    assert response.status_code == 401, response.text


async def test_viewer_cannot_trigger_inference(client: AsyncClient) -> None:
    headers = await _login(client, "viewer@credify.com")

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": str(uuid4()), "amount": "40.00"},
    )

    assert response.status_code == 403, response.text


async def test_unknown_client_returns_404(client: AsyncClient) -> None:
    headers = await _login(client)

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": str(uuid4()), "amount": "40.00"},
    )

    assert response.status_code == 404, response.text


async def test_pending_balance_blocks_without_loading_artifact(
    app_context, monkeypatch
) -> None:
    client, session_factory = app_context
    headers = await _login(client)
    client_id = await _new_client(client, headers, "88880001")
    await _seed_credit(session_factory, client_id, amount="30.00", pending="30.00")
    # Se usa el predict_proy real: la compuerta debe cortar antes del loader.
    monkeypatch.setattr(
        proy_model,
        "_load",
        lambda *_: pytest.fail("el artefacto no debe cargarse con saldo pendiente"),
    )

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": client_id, "amount": "40.00"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["decision"] == "BLOCKED_PENDING_BALANCE"
    assert body["reason"] == "pending_debt"
    assert body["model_called"] is False
    assert body["probability"] is None and body["predicted"] is None
    assert body["business_approval"] is False and body["research_only"] is True
    assert Decimal(body["pending_amount"]) == Decimal("30.00")
    assert await _count(session_factory, ProyExperimentalEvaluation) == 1
    assert await _count(session_factory, CreditEvaluation) == 0
    assert await _count(session_factory, CreditReview) == 0
    assert await _count(session_factory, Credit) == 1


async def test_snapshot_comes_from_database_and_is_persisted(
    app_context, monkeypatch
) -> None:
    client, session_factory = app_context
    headers = await _login(client)
    client_id = await _new_client(client, headers, "88880002")
    await _seed_credit(session_factory, client_id, amount="80.00", pending="0.00")
    captured: dict = {}

    def fake_predict(snapshot):
        captured.update(snapshot)
        return {
            "decision": "MODEL_REVIEW_CANDIDATE",
            "reason": "human_decision_required",
            "probability": 0.42,
            "threshold": 0.1,
            "predicted": 1,
            "model_called": True,
            "model_version": MODEL_VERSION,
            "schema_version": CONTRACT_VERSION,
        }

    monkeypatch.setattr(service, "predict_proy", fake_predict)

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": client_id, "amount": "40.00"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(captured) == set(FEATURE_NAMES_PROY)
    assert captured["completed_sales"] == 1 and captured["paid_credits"] == 1
    assert captured["outstanding"] == Decimal("0")
    # S/ 40 sobre el cupo de referencia S/ 80, no sobre el tope vivo (S/ 200).
    assert captured["requested_ratio"] == pytest.approx(0.5)
    assert body["decision"] == "MODEL_REVIEW_CANDIDATE"
    assert body["probability"] == pytest.approx(0.42)
    assert Decimal(body["threshold"]) == Decimal("0.1000")
    assert body["predicted"] == 1 and body["model_called"] is True
    assert body["schema_version"] == CONTRACT_VERSION
    assert body["requires_human_decision"] is True
    assert body["feature_snapshot"] == {name: float(value) for name, value in captured.items()}
    assert await _count(session_factory, ProyExperimentalEvaluation) == 1
    assert await _count(session_factory, CreditEvaluation) == 0
    assert await _count(session_factory, CreditReview) == 0
    assert await _count(session_factory, Credit) == 1


async def test_unavailable_model_fails_closed_without_trace(
    app_context, monkeypatch
) -> None:
    client, session_factory = app_context
    headers = await _login(client)
    client_id = await _new_client(client, headers, "88880003")
    await _seed_credit(session_factory, client_id, amount="80.00", pending="0.00")

    def unavailable(*_):
        raise ProyModelUnavailable("Artifact SHA256 mismatch")

    monkeypatch.setattr(service, "predict_proy", unavailable)

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": client_id, "amount": "40.00"},
    )

    assert response.status_code == 503, response.text
    assert "SHA256" not in response.text
    assert await _count(session_factory, ProyExperimentalEvaluation) == 0


async def test_rejects_non_positive_amount(client: AsyncClient) -> None:
    headers = await _login(client)

    response = await client.post(
        "/api/v1/proy-experimental/evaluations",
        headers=headers,
        json={"client_id": str(uuid4()), "amount": "0"},
    )

    assert response.status_code == 422, response.text
