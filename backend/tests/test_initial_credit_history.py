from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.ml.model as credit_model
import app.services.ai_credit as ai_credit
import app.services.credit_scoring as scoring
import app.services.whatsapp as whatsapp
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.commerce import (
    Credit,
    CreditEvaluation,
    CreditStatus,
    InventoryMovement,
    PaymentAllocation,
    PaymentMode,
    Product,
    Sale,
)
from app.models.settings import SETTINGS_ID, BusinessSettings
from app.models.user import AuditLog, User, UserRole

MAX_CREDIT = Decimal("150.00")
OVERRIDE_REASON = "Owner reviewed and authorized a conservative first credit."


@pytest_asyncio.fixture
async def credit_env(monkeypatch):
    settings = Settings(
        _env_file=None,
        environment="test",
        require_paid_credit_history=True,
        credit_ml_enabled=False,
        openrouter_enabled=False,
        whatsapp_enabled=False,
    )
    # Patch module lookups, never the shared cached settings instance.
    for module in (scoring, credit_model, ai_credit, whatsapp):
        monkeypatch.setattr(module, "get_settings", lambda: settings)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        password = hash_password("secure-password")
        db.add_all(
            User(
                email=f"{role.value}@example.com",
                full_name=role.value,
                hashed_password=password,
                role=role,
            )
            for role in (UserRole.ADMIN, UserRole.OPERATOR)
        )
        customer = Client(
            first_name="Initial",
            last_name="Credit",
            document="12345678",
            phone="987654321",
        )
        product = Product(
            sku="HISTORY-TEST", name="Test product", category="Test", price=10, stock=20
        )
        db.add_all(
            [
                customer,
                product,
                BusinessSettings(
                    id=SETTINGS_ID,
                    business_name="History policy test",
                    business_phone="987654321",
                    business_address="Test address",
                    max_credit_amount=MAX_CREDIT,
                    scoring_low_min=80,
                    scoring_medium_min=60,
                    scoring_min_approved=60,
                    overdue_block_days=30,
                    max_exposure_percent=80,
                    new_client_blocked_days=0,
                ),
            ]
        )
        await db.commit()
        client_id, product_id = str(customer.id), str(product.id)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {}
            for role in ("admin", "operator"):
                login = await client.post(
                    "/api/v1/auth/login",
                    data={
                        "username": f"{role}@example.com",
                        "password": "secure-password",
                    },
                )
                assert login.status_code == 200, login.text
                headers[role] = {"Authorization": f"Bearer {login.json()['access_token']}"}
            yield client, session_factory, headers, client_id, product_id
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        await engine.dispose()


def _credit_payload(client_id: str, **overrides) -> dict:
    return {
        "client_id": client_id,
        "amount": "40.00",
        "credit_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=15)).isoformat(),
        "manual_override": True,
        "exception_reason": OVERRIDE_REASON,
        **overrides,
    }


async def _evaluate(client: AsyncClient, headers: dict, client_id: str) -> dict:
    response = await client.post(
        "/api/v1/credits/evaluate",
        headers=headers,
        json={"client_id": client_id, "amount": "40.00"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _assert_review(evaluation: dict) -> None:
    assert evaluation["approved"] is False
    assert evaluation["requires_manual_review"] is True
    assert Decimal(evaluation["recommended_limit"]) == 0
    assert evaluation["confidence"] == 0
    assert "payment_history_review" in {factor["key"] for factor in evaluation["factors"]}


async def _pay(client: AsyncClient, headers: dict, client_id: str, credit_id: str, amount: str):
    response = await client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "client_id": client_id,
            "allocations": [{"credit_id": credit_id, "amount": amount}],
            "payment_date": date.today().isoformat(),
            "method": "cash",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_paid_history_policy_is_opt_in() -> None:
    assert Settings.model_fields["require_paid_credit_history"].default is False


async def test_high_score_without_paid_history_requires_review_and_is_persisted(credit_env):
    client, session_factory, headers, client_id, _ = credit_env
    evaluation = await _evaluate(client, headers["admin"], client_id)
    assert evaluation["score"] >= 80
    assert evaluation["risk"] == "bajo"
    assert evaluation["model_version"] == scoring.RULES_VERSION
    _assert_review(evaluation)

    history = await client.get(
        "/api/v1/credits/evaluations", headers=headers["admin"], params={"client_id": client_id}
    )
    assert history.status_code == 200, history.text
    assert len(history.json()) == 1
    entry = history.json()[0]
    _assert_review(entry)
    assert entry["source"] == "manual"
    async with session_factory() as db:
        stored = await db.get(CreditEvaluation, UUID(entry["id"]))
        assert stored.approved is False
        assert stored.recommended_limit == 0
        assert stored.confidence == 0
        assert stored.factors == evaluation["factors"]
        assert stored.feature_snapshot["paid_credits"] == 0


async def test_disabling_opt_in_preserves_existing_approval(credit_env, monkeypatch):
    client, _, headers, client_id, _ = credit_env
    settings = scoring.get_settings().model_copy(update={"require_paid_credit_history": False})
    monkeypatch.setattr(scoring, "get_settings", lambda: settings)
    evaluation = await _evaluate(client, headers["admin"], client_id)
    assert evaluation["approved"] is True
    assert evaluation["requires_manual_review"] is False
    assert Decimal(evaluation["recommended_limit"]) > 0
    assert evaluation["confidence"] > 0
    assert "payment_history_review" not in {factor["key"] for factor in evaluation["factors"]}


@pytest.mark.parametrize("history_kind", ["evaluations", "sales", "tenure"])
async def test_non_payment_history_never_unlocks_credit(credit_env, history_kind):
    client, session_factory, headers, client_id, _ = credit_env
    async with session_factory() as db:
        customer = await db.get(Client, UUID(client_id))
        if history_kind == "tenure":
            customer.created_at = datetime.now(UTC) - timedelta(days=3650)
        elif history_kind == "sales":
            admin = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
            db.add_all(
                Sale(
                    code=f"HISTORY-{index}",
                    payment_mode=PaymentMode.CASH,
                    client_id=customer.id,
                    created_by_id=admin.id,
                    subtotal=10,
                    tax=Decimal("1.80"),
                    total=Decimal("11.80"),
                )
                for index in range(5)
            )
        await db.commit()

    for _ in range(3):
        evaluation = await _evaluate(client, headers["admin"], client_id)
        assert evaluation["score"] >= 80
        _assert_review(evaluation)
    async with session_factory() as db:
        stored = (await db.scalars(select(CreditEvaluation))).all()
        assert len(stored) == 3
        assert all(row.feature_snapshot["paid_credits"] == 0 for row in stored)
        if history_kind == "sales":
            assert all(row.feature_snapshot["completed_sales"] == 5 for row in stored)
        elif history_kind == "tenure":
            assert all(row.feature_snapshot["tenure_days"] >= 3650 for row in stored)


@pytest.mark.parametrize("role", ["admin", "operator"])
async def test_direct_credit_without_explicit_override_is_rejected(credit_env, role):
    client, session_factory, headers, client_id, _ = credit_env
    payload = _credit_payload(client_id)
    del payload["manual_override"]
    response = await client.post("/api/v1/credits", headers=headers[role], json=payload)
    assert response.status_code == 422, response.text
    async with session_factory() as db:
        assert await db.scalar(select(func.count(Credit.id))) == 0
        evaluation = (await db.scalars(select(CreditEvaluation))).one()
        assert evaluation.approved is False
        assert evaluation.source == "direct_credit"


async def test_operator_cannot_override_initial_credit(credit_env):
    client, session_factory, headers, client_id, _ = credit_env
    response = await client.post(
        "/api/v1/credits", headers=headers["operator"], json=_credit_payload(client_id)
    )
    assert response.status_code == 403, response.text
    async with session_factory() as db:
        assert await db.scalar(select(func.count(Credit.id))) == 0
        assert await db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == "credit_overridden")
        ) == 0


@pytest.mark.parametrize("reason", [None, "too short", "          x"])
async def test_admin_override_requires_meaningful_reason(credit_env, reason):
    client, session_factory, headers, client_id, _ = credit_env
    payload = _credit_payload(client_id, exception_reason=reason)
    if reason is None:
        del payload["exception_reason"]
    response = await client.post("/api/v1/credits", headers=headers["admin"], json=payload)
    assert response.status_code == 422, response.text
    async with session_factory() as db:
        assert await db.scalar(select(func.count(Credit.id))) == 0
        assert await db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == "credit_overridden")
        ) == 0


@pytest.mark.parametrize("amount", ["40.00", "150.00"])
async def test_admin_override_within_business_cap_succeeds_and_is_audited(credit_env, amount):
    client, session_factory, headers, client_id, _ = credit_env
    response = await client.post(
        "/api/v1/credits",
        headers=headers["admin"],
        json=_credit_payload(client_id, amount=amount),
    )
    assert response.status_code == 201, response.text
    assert Decimal(response.json()["pending_amount"]) == Decimal(amount)
    async with session_factory() as db:
        credit = await db.get(Credit, UUID(response.json()["id"]))
        evaluation = await db.get(CreditEvaluation, credit.evaluation_id)
        assert evaluation.approved is False
        assert credit.recommended_limit == 0
        audit = (
            await db.scalars(select(AuditLog).where(AuditLog.action == "credit_overridden"))
        ).one()
        assert audit.actor_user_id == credit.created_by_id
        assert (await db.get(User, audit.actor_user_id)).role == UserRole.ADMIN
        assert audit.entity_type == "credit"
        assert audit.entity_id == str(credit.id)
        assert audit.details["reason"] == OVERRIDE_REASON
        assert Decimal(audit.details["amount"]) == Decimal(amount)
        assert Decimal(audit.details["recommended_limit"]) == 0
        assert audit.details["evaluation_id"] == str(evaluation.id)
    _assert_review(await _evaluate(client, headers["admin"], client_id))


async def test_admin_override_cannot_exceed_configured_business_cap(credit_env):
    client, session_factory, headers, client_id, _ = credit_env
    response = await client.post(
        "/api/v1/credits",
        headers=headers["admin"],
        json=_credit_payload(client_id, amount=str(MAX_CREDIT + Decimal("0.01"))),
    )
    assert response.status_code == 422, response.text
    async with session_factory() as db:
        assert await db.scalar(select(func.count(Credit.id))) == 0
        assert await db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == "credit_overridden")
        ) == 0


@pytest.mark.parametrize("role", ["admin", "operator"])
async def test_credit_sales_cannot_bypass_review_even_with_override_fields(credit_env, role):
    client, session_factory, headers, client_id, product_id = credit_env
    for _ in range(2):
        response = await client.post(
            "/api/v1/sales",
            headers=headers[role],
            json={
                "payment_mode": "credito",
                "client_id": client_id,
                "due_date": (date.today() + timedelta(days=15)).isoformat(),
                "items": [{"product_id": product_id, "quantity": 1}],
                "manual_override": True,
                "exception_reason": OVERRIDE_REASON,
            },
        )
        assert response.status_code == 422, response.text
    history = await client.get(
        "/api/v1/credits/evaluations", headers=headers[role], params={"client_id": client_id}
    )
    assert history.status_code == 200, history.text
    assert len(history.json()) == 2
    for evaluation in history.json():
        assert evaluation["source"] == "credit_sale"
        _assert_review(evaluation)
    async with session_factory() as db:
        assert await db.scalar(select(func.count(Sale.id))) == 0
        assert await db.scalar(select(func.count(Credit.id))) == 0
        assert await db.scalar(select(func.count(InventoryMovement.id))) == 0
        assert (await db.get(Product, UUID(product_id))).stock == 20
    _assert_review(await _evaluate(client, headers[role], client_id))


async def test_only_full_payment_unlocks_automatic_credit_and_sales(credit_env):
    client, session_factory, headers, client_id, product_id = credit_env
    response = await client.post(
        "/api/v1/credits", headers=headers["admin"], json=_credit_payload(client_id)
    )
    assert response.status_code == 201, response.text
    credit_id = response.json()["id"]
    await _pay(client, headers["operator"], client_id, credit_id, "10.00")
    _assert_review(await _evaluate(client, headers["admin"], client_id))

    payment = await _pay(client, headers["operator"], client_id, credit_id, "30.00")
    assert Decimal(payment["remaining_balance"]) == 0
    async with session_factory() as db:
        credit = await db.get(Credit, UUID(credit_id))
        assert credit.pending_amount == 0
        assert credit.status == CreditStatus.PAID
        assert await db.scalar(
            select(func.sum(PaymentAllocation.amount)).where(
                PaymentAllocation.credit_id == credit.id
            )
        ) == credit.original_amount

    evaluation = await _evaluate(client, headers["admin"], client_id)
    assert evaluation["approved"] is True
    assert evaluation["requires_manual_review"] is False
    assert Decimal(evaluation["recommended_limit"]) >= 40
    assert evaluation["confidence"] > 0
    assert "payment_history_review" not in {factor["key"] for factor in evaluation["factors"]}
    history = await client.get(
        "/api/v1/credits/evaluations", headers=headers["admin"], params={"client_id": client_id}
    )
    assert history.status_code == 200, history.text
    assert sum(entry["requires_manual_review"] for entry in history.json()) == 2

    direct = await client.post(
        "/api/v1/credits",
        headers=headers["operator"],
        json=_credit_payload(client_id, manual_override=False, exception_reason=None),
    )
    assert direct.status_code == 201, direct.text
    sale = await client.post(
        "/api/v1/sales",
        headers=headers["operator"],
        json={
            "payment_mode": "credito",
            "client_id": client_id,
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    )
    assert sale.status_code == 201, sale.text
    assert sale.json()["credit"] is not None


@pytest.mark.parametrize("block", ["overdue", "exposure"])
async def test_paid_history_does_not_bypass_other_risk_blocks(credit_env, block):
    client, session_factory, headers, client_id, _ = credit_env
    first = await client.post(
        "/api/v1/credits", headers=headers["admin"], json=_credit_payload(client_id)
    )
    assert first.status_code == 201, first.text
    await _pay(client, headers["admin"], client_id, first.json()["id"], "40.00")
    assert (await _evaluate(client, headers["admin"], client_id))["approved"] is True

    outstanding = await client.post(
        "/api/v1/credits",
        headers=headers["admin"],
        json=_credit_payload(client_id, amount="120.00" if block == "exposure" else "40.00"),
    )
    assert outstanding.status_code == 201, outstanding.text
    if block == "overdue":
        async with session_factory() as db:
            credit = await db.get(Credit, UUID(outstanding.json()["id"]))
            credit.credit_date = date.today() - timedelta(days=60)
            credit.due_date = date.today() - timedelta(days=31)
            credit.status = CreditStatus.OVERDUE
            await db.commit()

    evaluation = await _evaluate(client, headers["admin"], client_id)
    assert evaluation["approved"] is False
    assert evaluation["requires_manual_review"] is False
    assert "payment_history_review" not in {factor["key"] for factor in evaluation["factors"]}
    assert ("vencidos" if block == "overdue" else "80.0%") in evaluation["recommendation"]
    response = await client.post(
        "/api/v1/credits",
        headers=headers["admin"],
        json=_credit_payload(client_id, manual_override=False),
    )
    assert response.status_code == 422, response.text
