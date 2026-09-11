from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.services.whatsapp as whatsapp_service
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Credit, User, UserRole
from app.models.client import Client
from app.models.commerce import CreditStatus, RiskLevel
from app.models.whatsapp import NotificationStatus, WhatsappNotification


def _settings(**overrides) -> Settings:
    base = {
        "whatsapp_enabled": False,
        "whatsapp_token": "test-token",
        "whatsapp_phone_number_id": "123456789",
        "whatsapp_verify_token": "verify-token",
        "whatsapp_app_secret": "app-secret",
        "whatsapp_default_country_code": "51",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_normalize_phone_local_short() -> None:
    assert whatsapp_service.normalize_phone("999 123 456") == "+51999123456"


def test_normalize_phone_international_plain() -> None:
    assert whatsapp_service.normalize_phone("51999123456") == "+51999123456"


def test_normalize_phone_international_plus() -> None:
    assert whatsapp_service.normalize_phone("+51-999-123-456") == "+51999123456"


def test_signature_verifies_only_exact_body() -> None:
    signed = whatsapp_service.compute_signature("secret", b'{"a":1}')
    assert whatsapp_service.verify_signature("secret", signed, b'{"a":1}')
    assert not whatsapp_service.verify_signature("secret", signed, b'{"a":2}')
    assert not whatsapp_service.verify_signature("secret", None, b'{"a":1}')


def test_build_template_payload() -> None:
    payload = whatsapp_service.build_template_payload(
        "+51999123456", "credit_evaluation_result", ["Tamara", "aprobada", "200.00"]
    )
    assert payload["to"] == "+51999123456"
    assert payload["template"]["name"] == "credit_evaluation_result"
    assert payload["template"]["language"]["code"] == "es"
    assert payload["template"]["components"][0]["parameters"][0] == {
        "type": "text",
        "text": "Tamara",
    }


class _FakeResponse:
    def __init__(self, status_code: int = 200, json_body: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_body or {"messages": [{"id": "wamid.TEST123"}]}
        self.text = "ok"

    def json(self) -> dict:
        return self._json


class _FakeAsyncClient:
    captured: tuple[str, dict, dict] | None = None

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
        type(self).captured = (url, json, headers)
        return _FakeResponse()


async def test_send_template_message_hits_graph_api(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.whatsapp.get_settings",
        lambda: _settings(whatsapp_enabled=True),
    )
    monkeypatch.setattr("app.services.whatsapp.httpx.AsyncClient", _FakeAsyncClient)
    message_id = await whatsapp_service.send_template_message(
        "999123456", "credit_evaluation_result", ["Tamara", "aprobada", "200.00"]
    )
    assert message_id == "wamid.TEST123"
    url, payload, headers = _FakeAsyncClient.captured
    assert "123456789/messages" in url
    assert headers["Authorization"] == "Bearer test-token"
    assert payload["to"] == "+51999123456"


async def test_send_template_message_disabled_is_noop(monkeypatch) -> None:
    called = False

    class _NeverCalled(_FakeAsyncClient):
        def __init__(self, timeout: float) -> None:
            super().__init__(timeout)
            nonlocal called
            called = True

    monkeypatch.setattr("app.services.whatsapp.httpx.AsyncClient", _NeverCalled)
    message_id = await whatsapp_service.send_template_message(
        "999123456", "credit_evaluation_result", ["Tamara", "aprobada", "200.00"]
    )
    assert message_id == "mock"
    assert not called


async def test_send_template_message_raises_on_api_error(monkeypatch) -> None:
    class _ErrorClient(_FakeAsyncClient):
        async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
            return _FakeResponse(status_code=401, json_body={"error": {"message": "denied"}})

    monkeypatch.setattr(
        "app.services.whatsapp.get_settings",
        lambda: _settings(whatsapp_enabled=True),
    )
    monkeypatch.setattr("app.services.whatsapp.httpx.AsyncClient", _ErrorClient)
    with pytest.raises(whatsapp_service.WhatsAppError):
        await whatsapp_service.send_template_message(
            "999123456", "credit_evaluation_result", ["Tamara", "aprobada", "200.00"]
        )


async def test_webhook_get_verifies_and_returns_challenge(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.whatsapp.get_settings", lambda: _settings(whatsapp_verify_token="vt")
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ok = await client.get(
            "/api/v1/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "12345"},
        )
        bad = await client.get(
            "/api/v1/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
        )
    assert ok.status_code == 200
    assert ok.text == "12345"
    assert bad.status_code == 403


@pytest_asyncio.fixture
async def sqlite_client() -> AsyncIterator[AsyncClient]:
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


async def test_webhook_post_rejects_bad_signature(sqlite_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.whatsapp.get_settings",
        lambda: _settings(whatsapp_app_secret="secret"),
    )
    response = await sqlite_client.post(
        "/api/v1/whatsapp/webhook", content=b'{"entry":[]}', headers={"x-hub-signature-256": "nope"}
    )
    assert response.status_code == 403


async def test_webhook_post_accepts_good_signature_and_records_status(
    sqlite_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.api.routes.whatsapp.get_settings",
        lambda: _settings(whatsapp_app_secret="secret"),
    )
    body = b'{"entry":[{"changes":[{"value":{"statuses":[' \
        b'{"id":"wamid.1","status":"delivered"}]}}]}]}'
    signed = whatsapp_service.compute_signature("secret", body)
    response = await sqlite_client.post(
        "/api/v1/whatsapp/webhook",
        content=body,
        headers={"x-hub-signature-256": signed},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_due_reminders_send_and_dedupe() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        user = User(
            email="admin@baylon.com",
            full_name="Admin Baylon",
            hashed_password=hash_password("secure-password"),
            role=UserRole.ADMIN,
        )
        db.add(user)
        await db.flush()
        client = Client(
            first_name="Tamara",
            last_name="Quispe",
            document="99999999",
            phone="999123456",
            is_active=True,
        )
        db.add(client)
        await db.flush()
        reminder = Credit(
            code="F-REMINDER",
            client_id=client.id,
            created_by_id=user.id,
            original_amount=Decimal("100"),
            pending_amount=Decimal("100"),
            credit_date=date.today() - timedelta(days=30),
            due_date=date.today() - timedelta(days=1),
            status=CreditStatus.CURRENT,
            risk=RiskLevel.LOW,
            score=80,
            recommended_limit=Decimal("200"),
        )
        db.add(reminder)
        reminded = Credit(
            code="F-REMINDED",
            client_id=client.id,
            created_by_id=user.id,
            original_amount=Decimal("80"),
            pending_amount=Decimal("30"),
            credit_date=date.today() - timedelta(days=10),
            due_date=date.today() - timedelta(days=1),
            status=CreditStatus.CURRENT,
            risk=RiskLevel.LOW,
            score=80,
            recommended_limit=Decimal("200"),
        )
        db.add(reminded)
        await db.flush()
        db.add(
            WhatsappNotification(
                phone="+51999123456",
                template_name="credit_payment_reminder",
                credit_id=reminded.id,
                message_id="wamid.previous",
                status=NotificationStatus.SENT,
            )
        )
        await db.commit()

    result = await whatsapp_service.send_due_reminders(session_factory)
    assert result == {"sent": 1, "skipped": 1, "failed": 0}

    async with session_factory() as db:
        rows = list(await db.scalars(select(WhatsappNotification)))
        assert len(rows) == 2
    await engine.dispose()