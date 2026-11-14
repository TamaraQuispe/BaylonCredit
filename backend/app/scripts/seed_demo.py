"""Create fictional records only in the explicitly isolated demo database."""

import asyncio
import os
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.client import Client
from app.models.settings import SETTINGS_ID, BusinessSettings
from app.models.user import User, UserRole


async def seed_demo() -> None:
    settings = get_settings()
    if (
        os.environ.get("DEMO_MODE") != "true"
        or make_url(settings.database_url).database != "credify_demo"
        or settings.environment != "staging"
    ):
        raise SystemExit("Demo seed refused: staging and credify_demo are required.")

    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "docente@example.com"))
        if user is None:
            db.add(User(
                email="docente@example.com",
                full_name="Docente - DEMOSTRACION",
                hashed_password=hash_password(
                    os.environ.get("DEMO_USER_PASSWORD", "DemoAPF2-2026!")
                ),
                role=UserRole.OPERATOR,
            ))
        for index in range(1, 4):
            document = f"9000000{index}"
            exists = await db.scalar(select(Client.id).where(Client.document == document))
            if exists is None:
                db.add(Client(
                    first_name=f"Cliente demo {index}",
                    last_name="Ficticio",
                    business_name=f"DEMO - Cliente de prueba {index}",
                    document=document,
                    phone="000000000",
                    address="Registro ficticio para sustentacion",
                ))
        policy = await db.get(BusinessSettings, SETTINGS_ID)
        if policy is None:
            db.add(BusinessSettings(
                id=SETTINGS_ID,
                business_name="Cerveceria Baylon - DEMOSTRACION",
                business_phone="000000000",
                business_address="Entorno local de demostracion",
                default_credit_term_days=1,
                max_credit_amount=Decimal("200"),
            ))
        else:
            policy.business_name = "Cerveceria Baylon - DEMOSTRACION"
            policy.default_credit_term_days = 1
        await db.commit()
    print("Demo ready: fictional clients, operator account, one-day credit policy.")


if __name__ == "__main__":
    asyncio.run(seed_demo())
