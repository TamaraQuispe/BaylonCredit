import asyncio
import os

from pydantic import ValidationError
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


async def create_admin() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    full_name = os.environ.get("ADMIN_FULL_NAME", "Administrador")
    try:
        payload = UserCreate(
            email=email,
            full_name=full_name.strip(),
            password=password,
            role=UserRole.ADMIN,
        )
    except ValidationError as error:
        raise SystemExit(f"Invalid administrator data: {error}") from None

    async with SessionFactory() as db:
        normalized_email = str(payload.email).lower()
        existing = await db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            print(f"Admin user {normalized_email} already exists")
            return
        db.add(
            User(
                email=normalized_email,
                full_name=payload.full_name,
                hashed_password=hash_password(payload.password),
                role=UserRole.ADMIN,
            )
        )
        await db.commit()
        print(f"Admin user {normalized_email} created")


if __name__ == "__main__":
    asyncio.run(create_admin())
