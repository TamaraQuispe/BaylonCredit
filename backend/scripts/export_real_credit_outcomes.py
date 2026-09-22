"""Export anonymized, observed credit outcomes for model training."""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from app.db.session import SessionFactory
from app.ml.features import FEATURE_NAMES
from app.ml.outcomes import classify_credit_outcome
from app.models.commerce import Credit, CreditEvaluation, Payment, PaymentAllocation


async def export_dataset(output: Path) -> tuple[int, int]:
    async with SessionFactory() as db:
        rows = (
            await db.execute(
                select(
                    Credit,
                    CreditEvaluation.feature_snapshot,
                    func.max(Payment.payment_date).label("last_payment_date"),
                )
                .join(CreditEvaluation, CreditEvaluation.id == Credit.evaluation_id)
                .outerjoin(PaymentAllocation, PaymentAllocation.credit_id == Credit.id)
                .outerjoin(Payment, Payment.id == PaymentAllocation.payment_id)
                .group_by(Credit.id, CreditEvaluation.id)
            )
        ).all()

    exported: list[list[float | int]] = []
    unresolved = 0
    for credit, snapshot, last_payment_date in rows:
        outcome = classify_credit_outcome(
            pending_amount=credit.pending_amount,
            due_date=credit.due_date,
            last_payment_date=last_payment_date,
            observed_on=date.today(),
        )
        if outcome is None or not snapshot:
            unresolved += 1
            continue
        exported.append([*[float(snapshot[name]) for name in FEATURE_NAMES], outcome])

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([*FEATURE_NAMES, "defaulted"])
        writer.writerows(exported)
    return len(exported), unresolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    exported, unresolved = asyncio.run(export_dataset(args.output))
    print(f"Casos exportados: {exported}; aún no resueltos: {unresolved}")


if __name__ == "__main__":
    main()
