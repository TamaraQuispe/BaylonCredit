"""Pruebas de concurrencia de P0-03 contra PostgreSQL real.

SQLite no demuestra la semantica de bloqueos de PostgreSQL, asi que estas pruebas
se saltan salvo que exista ``PROY_POSTGRES_URL``. Ejemplo local:

    PROY_POSTGRES_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/credify_proy_test \\
        python -m pytest tests/test_proy_concurrency_postgres.py
"""

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal

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
from app.models.commerce import Credit, Payment, PaymentAllocation, Product
from app.models.settings import SETTINGS_ID, BusinessSettings
from app.models.user import User, UserRole

POSTGRES_URL = os.getenv("PROY_POSTGRES_URL")
REASON = "Owner reviewed and authorized a conservative first credit."

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="Requiere PostgreSQL real (define PROY_POSTGRES_URL).",
)


@pytest_asyncio.fixture
async def pg_env(monkeypatch) -> AsyncIterator[tuple]:
    settings = Settings(
        _env_file=None,
        environment="test",
        require_paid_credit_history=True,
        credit_ml_enabled=False,
        openrouter_enabled=False,
        whatsapp_enabled=False,
    )
    for module in (scoring, credit_model, ai_credit, whatsapp):
        monkeypatch.setattr(module, "get_settings", lambda: settings)

    engine = create_async_engine(POSTGRES_URL, pool_size=10, max_overflow=10)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
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
            first_name="Concurrente",
            last_name="Prueba",
            document="87654321",
            phone="987654321",
        )
        product = Product(
            sku="PG-TEST", name="Producto PG", category="Test", price=10, stock=50
        )
        db.add_all(
            [
                customer,
                product,
                BusinessSettings(
                    id=SETTINGS_ID,
                    business_name="Postgres concurrency test",
                    business_phone="987654321",
                    business_address="Test address",
                    max_credit_amount=Decimal("150.00"),
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

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            headers = {}
            for role in ("admin", "operator"):
                login = await client.post(
                    "/api/v1/auth/login",
                    data={"username": f"{role}@example.com", "password": "secure-password"},
                )
                assert login.status_code == 200, login.text
                headers[role] = {"Authorization": f"Bearer {login.json()['access_token']}"}
            yield client, session_factory, headers, client_id, product_id
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


def _credit_body(client_id: str, key: str | None = None) -> tuple[dict, dict]:
    payload = {
        "client_id": client_id,
        "amount": "40.00",
        "credit_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=15)).isoformat(),
        "manual_override": True,
        "exception_reason": REASON,
    }
    headers = {"Idempotency-Key": key} if key else {}
    return payload, headers


async def test_concurrent_credits_leave_only_one_pending_loan(pg_env) -> None:
    client, session_factory, headers, client_id, _ = pg_env
    payload, _ = _credit_body(client_id)
    first, second = await asyncio.gather(
        client.post("/api/v1/credits", headers=headers["admin"], json=payload),
        client.post("/api/v1/credits", headers=headers["operator"], json=payload),
    )
    codes = sorted([first.status_code, second.status_code])
    assert codes == [201, 422], (first.text, second.text)
    blocked = next(r for r in (first, second) if r.status_code == 422)
    assert "saldo pendiente" in blocked.json()["detail"]

    async with session_factory() as db:
        assert await db.scalar(select(func.count(Credit.id))) == 1
        pending = await db.scalar(
            select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
                Credit.client_id == client_id
            )
        )
        assert Decimal(pending) == Decimal("40.00")


async def test_concurrent_retry_with_same_key_does_not_duplicate(pg_env) -> None:
    client, session_factory, headers, client_id, _ = pg_env
    payload, extra = _credit_body(client_id, key="pg-credito-1")
    auth = {**headers["admin"], **extra}
    first, second = await asyncio.gather(
        client.post("/api/v1/credits", headers=auth, json=payload),
        client.post("/api/v1/credits", headers=auth, json=payload),
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    async with session_factory() as db:
        assert await db.scalar(select(func.count(Credit.id))) == 1


async def test_concurrent_payments_never_overpay(pg_env) -> None:
    client, session_factory, headers, client_id, _ = pg_env
    payload, _ = _credit_body(client_id)
    created = await client.post("/api/v1/credits", headers=headers["admin"], json=payload)
    assert created.status_code == 201, created.text
    credit_id = created.json()["id"]

    body = {
        "client_id": client_id,
        "allocations": [{"credit_id": credit_id, "amount": "40.00"}],
        "payment_date": date.today().isoformat(),
        "method": "Efectivo",
    }
    first, second = await asyncio.gather(
        client.post("/api/v1/payments", headers=headers["admin"], json=body),
        client.post("/api/v1/payments", headers=headers["operator"], json=body),
    )
    assert sorted([first.status_code, second.status_code]) == [201, 409], (
        first.text,
        second.text,
    )

    async with session_factory() as db:
        credit = await db.get(Credit, credit_id)
        assert credit.pending_amount == 0
        paid = await db.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                PaymentAllocation.credit_id == credit.id
            )
        )
        assert Decimal(paid) == Decimal("40.00")
        assert await db.scalar(select(func.count(Payment.id))) == 1


async def test_credit_and_credit_sale_do_not_both_leave_debt(pg_env) -> None:
    client, session_factory, headers, client_id, product_id = pg_env
    payload, _ = _credit_body(client_id)
    credit_call = client.post("/api/v1/credits", headers=headers["admin"], json=payload)
    sale_call = client.post(
        "/api/v1/sales",
        headers=headers["operator"],
        json={
            "payment_mode": "credito",
            "client_id": client_id,
            "due_date": (date.today() + timedelta(days=15)).isoformat(),
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    )
    credit_response, sale_response = await asyncio.gather(credit_call, sale_call)
    statuses = sorted([credit_response.status_code, sale_response.status_code])
    assert statuses == [201, 422], (credit_response.text, sale_response.text)

    async with session_factory() as db:
        assert await db.scalar(select(func.count(Credit.id))) == 1
        assert (await db.get(Product, product_id)).stock == 50
