from asyncio import CancelledError
from collections.abc import AsyncIterator

import asyncpg
from sqlalchemy import event
from sqlalchemy.engine import ExceptionContext
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
SERVICE_UNAVAILABLE_MESSAGE = "Sistema no disponible temporalmente. Inténtalo más tarde."


class DatabaseUnavailable(Exception):
    """A transient database dependency failure, without exposing connection details."""


connection_options = {}
if settings.database_url.startswith("postgresql+asyncpg:"):
    connection_options = {
        "pool_timeout": settings.database_pool_timeout_seconds,
        "connect_args": {
            "timeout": settings.database_connect_timeout_seconds,
            "command_timeout": settings.database_command_timeout_seconds,
        },
    }
engine = create_async_engine(settings.database_url, **connection_options)

if settings.database_url.startswith("postgresql+asyncpg:"):

    @event.listens_for(engine.sync_engine, "handle_error")
    def terminate_timed_out_connection(context: ExceptionContext) -> None:
        if not isinstance(context.original_exception, (TimeoutError, CancelledError)):
            return
        connection = context.connection
        if connection is not None and not connection.closed and not connection.invalidated:
            # asyncpg's graceful close can wait indefinitely for cancellation from
            # an unresponsive server. Abort before SQLAlchemy starts that cleanup.
            connection.connection.driver_connection.terminate()

SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    try:
        async with SessionFactory() as session:
            try:
                yield session
            except (TimeoutError, PoolTimeoutError):
                # A stalled server may not acknowledge rollback/cancellation. Discard
                # that connection before context cleanup rather than waiting on it.
                await session.invalidate()
                raise
    except (
        OperationalError,
        InterfaceError,
        PoolTimeoutError,
        asyncpg.PostgresConnectionError,
        asyncpg.CannotConnectNowError,
        TimeoutError,
        OSError,
    ) as error:
        # Closing the session rolls back uncommitted work. Never retry a write here:
        # a disconnected commit can have an unknown outcome to the caller.
        raise DatabaseUnavailable() from error
