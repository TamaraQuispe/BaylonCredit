from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.commerce import Product
from app.models.user import User, UserRole

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")


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
            Product(
                id=PRODUCT_ID,
                sku="TEST-001",
                name="Producto de prueba",
                category="Otros",
                icon="category",
                price=Decimal("10.00"),
                unit_cost=Decimal("7.00"),
                stock=5,
                minimum_stock=1,
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


async def test_product_image_url_can_be_created_and_removed(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "sku": "IMG-001",
            "name": "Producto con imagen",
            "category": "Otros",
            "icon": "category",
            "image_url": "https://example.com/producto.jpg",
            "price": "12.50",
            "stock": 3,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["image_url"] == "https://example.com/producto.jpg"

    product_id = created.json()["id"]
    updated = await client.patch(
        f"/api/v1/products/{product_id}", headers=headers, json={"image_url": None}
    )
    assert updated.status_code == 200
    assert updated.json()["image_url"] is None

    invalid = await client.patch(
        f"/api/v1/products/{product_id}",
        headers=headers,
        json={"image_url": "file:///tmp/producto.jpg"},
    )
    assert invalid.status_code == 422


async def test_sale_updates_stock_and_creates_credit_atomically(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created_client = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Mario",
            "last_name": "Rojas",
            "document": "12345678",
            "phone": "987654321",
        },
    )

    sale = await client.post(
        "/api/v1/sales",
        headers=headers,
        json={
            "payment_mode": "fiado",
            "client_id": created_client.json()["id"],
            "due_date": "2030-01-15",
            "items": [{"product_id": str(PRODUCT_ID), "quantity": 2}],
        },
    )
    assert sale.status_code == 201, sale.text
    assert sale.json()["total"] == "23.60"
    assert sale.json()["credit"]["pending_amount"] == "23.60"

    products = await client.get("/api/v1/products", headers=headers)
    assert products.json()[0]["stock"] == 3

    rejected = await client.post(
        "/api/v1/sales",
        headers=headers,
        json={
            "payment_mode": "contado",
            "items": [{"product_id": str(PRODUCT_ID), "quantity": 4}],
        },
    )
    assert rejected.status_code == 409
    products_after_rejection = await client.get("/api/v1/products", headers=headers)
    assert products_after_rejection.json()[0]["stock"] == 3


async def test_fiado_sale_uses_default_term_from_settings(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"default_credit_term_days": 30},
    )
    created_client = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Lucia",
            "last_name": "Torres",
            "document": "88776655",
            "phone": "987654321",
        },
    )

    sale = await client.post(
        "/api/v1/sales",
        headers=headers,
        json={
            "payment_mode": "fiado",
            "client_id": created_client.json()["id"],
            "items": [{"product_id": str(PRODUCT_ID), "quantity": 1}],
        },
    )
    assert sale.status_code == 201, sale.text
    expected_due = (date.today() + timedelta(days=30)).isoformat()
    assert sale.json()["credit"]["due_date"] == expected_due


async def test_direct_credit_and_partial_payment_are_consistent(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created_client = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Rosa",
            "last_name": "Flores",
            "document": "87654321",
            "phone": "987654321",
        },
    )
    client_id = created_client.json()["id"]

    credit = await client.post(
        "/api/v1/credits",
        headers=headers,
        json={
            "client_id": client_id,
            "amount": "100.00",
            "credit_date": date.today().isoformat(),
            "due_date": "2030-01-15",
        },
    )
    assert credit.status_code == 201, credit.text
    credit_id = credit.json()["id"]

    payment = await client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "client_id": client_id,
            "allocations": [{"credit_id": credit_id, "amount": "40.00"}],
            "payment_date": date.today().isoformat(),
            "method": "Transferencia",
            "reference": "TEST-001",
        },
    )
    assert payment.status_code == 201, payment.text
    assert payment.json()["amount"] == "40.00"
    assert payment.json()["remaining_balance"] == "60.00"

    updated = await client.get(f"/api/v1/credits/{credit_id}", headers=headers)
    assert updated.json()["pending_amount"] == "60.00"
    assert updated.json()["paid_percent"] == 40.0
    assert len(updated.json()["payments"]) == 1


async def test_portfolio_report_reflects_active_and_overdue_fiados(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@baylon.com", "password": "secure-password"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created_client = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Pedro",
            "last_name": "Ramírez",
            "document": "55667788",
            "phone": "987654321",
        },
    )
    client_id = created_client.json()["id"]

    active = await client.post(
        "/api/v1/credits",
        headers=headers,
        json={
            "client_id": client_id,
            "amount": "120.00",
            "credit_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
        },
    )
    assert active.status_code == 201, active.text

    overdue = await client.post(
        "/api/v1/credits",
        headers=headers,
        json={
            "client_id": client_id,
            "amount": "80.00",
            "credit_date": "2026-01-01",
            "due_date": "2026-01-10",
            "manual_override": True,
        },
    )
    assert overdue.status_code == 201, overdue.text

    report = await client.get("/api/v1/reports/portfolio", headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["summary"]["active_credits"] == 2
    assert body["summary"]["total_pending"] == "200.00"
    assert body["summary"]["overdue_credits"] == 1
    assert len(body["clients"]) == 1
    client_entry = body["clients"][0]
    assert client_entry["client_id"] == client_id
    assert client_entry["total_pending"] == "200.00"
    assert client_entry["total_overdue"] == "80.00"
    assert client_entry["overdue_credits"] == 1

    no_auth = await client.get("/api/v1/reports/portfolio")
    assert no_auth.status_code == 401
