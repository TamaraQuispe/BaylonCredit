"""Seed only the disposable fault-test database; no real-person records."""

import asyncio

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionFactory, engine
from app.models.user import User, UserRole


async def main():
    settings = get_settings()
    if (
        settings.environment != "test"
        or make_url(settings.database_url).database != "credify_resilience"
    ):
        raise SystemExit("Refusing to seed outside the isolated resilience test database")
    async with SessionFactory() as db:
        existing = await db.scalar(select(User.id).where(User.email == "fault-test@example.com"))
        if existing is None:
            db.add(User(
                email="fault-test@example.com", full_name="Pruebas aisladas",
                hashed_password=hash_password("Resilience-Test-Only!"), role=UserRole.OPERATOR,
            ))
            await db.commit()
    await engine.dispose()
    print("Isolated resilience-test operator ready; no production data used.")


if __name__ == "__main__":
    asyncio.run(main())
