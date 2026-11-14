"""Read-only release check against production; does not create clients or credits."""

import asyncio
from dataclasses import replace
from decimal import Decimal

from sqlalchemy import exists, select, text

from app.core.config import get_settings
from app.db.session import SessionFactory, engine
from app.models.client import Client
from app.models.commerce import Credit
from app.services.credit_scoring import build_recommendation, evaluate_credit
from app.services import credit_scoring


async def main() -> None:
    assert get_settings().require_paid_credit_history, "Paid-history policy is disabled"
    async with SessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        no_paid_history = ~exists().where(
            Credit.client_id == Client.id, Credit.pending_amount == 0
        )
        client = await db.scalar(select(Client).where(Client.is_active.is_(True), no_paid_history).limit(1))
        mode = "existing no-history client"
        collector = credit_scoring.collect_credit_features
        if client is None:
            client = await db.scalar(select(Client).where(Client.is_active.is_(True)).limit(1))
            if client is None:
                raise RuntimeError("No active client available for verification")
            mode = "controlled no-paid-history vector; existing clients all have paid history"

            async def no_history_features(*args, **kwargs):
                features = await collector(*args, **kwargs)
                return replace(features, paid_credits=0, paid_late=0)

            credit_scoring.collect_credit_features = no_history_features
        try:
            result = await evaluate_credit(db, client.id, Decimal("50"))
        finally:
            credit_scoring.collect_credit_features = collector
        assert not result.approved
        assert result.recommended_limit == 0
        assert result.confidence == 0
        assert any(factor.key == "payment_history_review" for factor in result.factors)
        assert build_recommendation(result, Decimal("50"))
        await db.rollback()
    print(f"PASS: policy enabled; {mode} requires review; limit/confidence zero. Read-only transaction, no client identifiers printed.")


if __name__ == "__main__":
    async def verify_and_close() -> None:
        try:
            await main()
        finally:
            await engine.dispose()

    asyncio.run(verify_and_close())
