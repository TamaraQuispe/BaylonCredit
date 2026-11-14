from asyncio import CancelledError
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
import pytest_asyncio
from asyncpg import CannotConnectNowError, PostgresConnectionError
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_current_user
from app.db import session as session_module
from app.db.base import Base
from app.main import app
from app.models.client import Client
from app.models.user import User, UserRole

SECRET = "postgresql://private_user:secret_password@private_database:5432/private_db"
SQL = "SELECT confidential_column FROM private_clients"
UNAVAILABLE_MESSAGE = "Sistema no disponible temporalmente. Int\u00e9ntalo m\u00e1s tarde."
CLIENT_PAYLOAD = {
    "first_name": "Ana",
    "last_name": "Quispe",
    "document": "12345678",
    "phone": "987654321",
}
DATABASE_ERRORS = [
    pytest.param(OperationalError(SQL, {}, OSError(SECRET)), id="sqlalchemy-operational"),
    pytest.param(InterfaceError(SQL, {}, OSError(SECRET)), id="sqlalchemy-interface"),
    pytest.param(SQLAlchemyTimeoutError(SECRET), id="pool-timeout"),
    pytest.param(PostgresConnectionError(SECRET), id="postgres-connection"),
    pytest.param(CannotConnectNowError(SECRET), id="postgres-cannot-connect"),
    pytest.param(TimeoutError(SECRET), id="timeout"),
    pytest.param(OSError(SECRET), id="os-error"),
    pytest.param(ConnectionRefusedError(SECRET), id="connection-refused"),
]


@pytest.fixture
def admin_user() -> User:
    return User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="admin@baylon.com",
        full_name="Admin Baylon",
        hashed_password="unused-in-fault-tests",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest_asyncio.fixture
async def client(admin_user: User, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    async def current_user() -> User:
        return admin_user

    # Keep the real get_db dependency so its exception translation is exercised.
    monkeypatch.setitem(app.dependency_overrides, get_current_user, current_user)
    assert session_module.get_db not in app.dependency_overrides
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def fault_session(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, Mock, AsyncMock]:
    db = AsyncMock(spec=AsyncSession)
    db.scalars.return_value = []
    enter = AsyncMock(return_value=db)

    @asynccontextmanager
    async def session_context() -> AsyncIterator[AsyncSession]:
        session = await enter()
        try:
            yield session
        finally:
            await session.close()

    factory = Mock(side_effect=session_context)
    monkeypatch.setattr(session_module, "SessionFactory", factory)
    return db, factory, enter


def assert_database_unavailable(response: Response) -> None:
    assert response.status_code == 503, response.text
    assert response.json() == {
        "detail": UNAVAILABLE_MESSAGE,
        "code": "database_unavailable",
    }
    assert response.headers["Retry-After"] == "5"
    assert response.headers["X-Request-ID"]
    assert SECRET not in response.text
    assert SQL not in response.text


@pytest.mark.parametrize("error", [TimeoutError(SECRET), CancelledError()])
def test_timeout_listener_terminates_raw_driver_synchronously(error: BaseException) -> None:
    connection = Mock(closed=False, invalidated=False)
    driver = connection.connection.driver_connection
    driver.terminate = Mock(return_value=None)
    context = Mock(original_exception=error, connection=connection)

    assert session_module.terminate_timed_out_connection(context) is None

    driver.terminate.assert_called_once_with()


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ValueError(SECRET), id="unrelated"),
        pytest.param(OperationalError(SQL, {}, OSError(SECRET)), id="operational"),
        pytest.param(SQLAlchemyTimeoutError(SECRET), id="pool-timeout"),
    ],
)
def test_timeout_listener_ignores_unrelated_errors(error: Exception) -> None:
    context = Mock(spec=["original_exception"], original_exception=error)

    session_module.terminate_timed_out_connection(context)


@pytest.mark.parametrize("state", ["missing", "closed", "invalidated"])
def test_timeout_listener_skips_unusable_connections(state: str) -> None:
    connection = Mock(
        spec=["closed", "invalidated"], closed=state == "closed", invalidated=state == "invalidated"
    )
    context = Mock(
        original_exception=TimeoutError(SECRET),
        connection=None if state == "missing" else connection,
    )

    session_module.terminate_timed_out_connection(context)


@pytest.mark.parametrize("error", DATABASE_ERRORS)
@pytest.mark.parametrize("phase", ["acquire", "query"])
async def test_database_failures_return_safe_503(
    client: AsyncClient,
    fault_session: tuple[AsyncMock, Mock, AsyncMock],
    error: Exception,
    phase: str,
) -> None:
    db, factory, enter = fault_session
    if phase == "acquire":
        enter.side_effect = error
    else:
        db.scalars.side_effect = error

    response = await client.get(
        "/api/v1/clients", headers={"X-Request-ID": "database-failure-request"}
    )

    assert_database_unavailable(response)
    assert response.headers["X-Request-ID"] == "database-failure-request"
    factory.assert_called_once_with()
    enter.assert_awaited_once_with()
    db.commit.assert_not_awaited()
    if phase == "acquire":
        db.scalars.assert_not_awaited()
    else:
        db.scalars.assert_awaited_once()
        db.close.assert_awaited_once_with()
    if phase == "query" and isinstance(error, (TimeoutError, SQLAlchemyTimeoutError)):
        db.invalidate.assert_awaited_once_with()
    else:
        db.invalidate.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(OperationalError(SQL, {}, OSError(SECRET)), id="connection-lost"),
        pytest.param(SQLAlchemyTimeoutError(SECRET), id="pool-timeout"),
    ],
)
async def test_failed_write_closes_session_without_retrying(
    client: AsyncClient,
    fault_session: tuple[AsyncMock, Mock, AsyncMock],
    error: Exception,
) -> None:
    db, factory, enter = fault_session
    db.commit.side_effect = error

    response = await client.post("/api/v1/clients", json=CLIENT_PAYLOAD)

    assert_database_unavailable(response)
    factory.assert_called_once_with()
    enter.assert_awaited_once_with()
    db.add.assert_called_once()
    db.commit.assert_awaited_once_with()
    db.refresh.assert_not_awaited()
    db.close.assert_awaited_once_with()


async def test_failed_commit_rolls_back_flushed_client(
    client: AsyncClient, admin_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as setup:
            setup.add(admin_user)
            await setup.commit()

        db = sessions()
        close = AsyncMock(wraps=db.close)
        monkeypatch.setattr(db, "close", close)

        async def failed_commit() -> None:
            await db.flush()
            assert await db.scalar(select(func.count()).select_from(Client)) == 1
            raise OperationalError(SQL, {}, OSError(SECRET))

        commit = AsyncMock(side_effect=failed_commit)
        monkeypatch.setattr(db, "commit", commit)
        factory = Mock(return_value=db)
        monkeypatch.setattr(session_module, "SessionFactory", factory)

        response = await client.post("/api/v1/clients", json=CLIENT_PAYLOAD)

        assert_database_unavailable(response)
        factory.assert_called_once_with()
        commit.assert_awaited_once_with()
        close.assert_awaited_once_with()
        async with sessions() as verification:
            assert await verification.scalar(select(func.count()).select_from(Client)) == 0
            assert await verification.get(User, admin_user.id) is not None
    finally:
        await engine.dispose()


@pytest.mark.parametrize("phase", ["acquire", "query"])
async def test_liveness_survives_database_outage_but_readiness_fails(
    client: AsyncClient, fault_session: tuple[AsyncMock, Mock, AsyncMock], phase: str
) -> None:
    db, factory, enter = fault_session
    if phase == "acquire":
        enter.side_effect = ConnectionRefusedError(SECRET)
    else:
        db.execute.side_effect = OperationalError(SQL, {}, OSError(SECRET))

    live = await client.get("/health/live")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    factory.assert_not_called()

    ready = await client.get("/health/ready")

    assert ready.status_code == 503
    assert ready.headers["X-Request-ID"]
    assert SECRET not in ready.text
    assert SQL not in ready.text
    factory.assert_called_once_with()
    if phase == "query":
        db.execute.assert_awaited_once()
        db.close.assert_awaited_once_with()


async def test_next_request_recovers_after_database_becomes_available(
    client: AsyncClient, fault_session: tuple[AsyncMock, Mock, AsyncMock]
) -> None:
    db, factory, enter = fault_session
    enter.side_effect = [ConnectionRefusedError(SECRET), db]

    failed = await client.get("/api/v1/clients")
    assert_database_unavailable(failed)
    assert factory.call_count == 1

    recovered = await client.get("/api/v1/clients")

    assert recovered.status_code == 200, recovered.text
    assert recovered.json() == []
    assert "Retry-After" not in recovered.headers
    assert recovered.headers["X-Request-ID"]
    assert recovered.headers["X-Request-ID"] != failed.headers["X-Request-ID"]
    assert factory.call_count == 2
    assert enter.await_count == 2
    db.scalars.assert_awaited_once()
    db.close.assert_awaited_once_with()
