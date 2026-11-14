from datetime import date
from decimal import Decimal

TARGET_NAME = "late_payment"
TARGET_DEFINITION = "Not fully paid by the end of the contractual due date"


def classify_credit_outcome(
    *,
    pending_amount: Decimal,
    due_date: date,
    last_payment_date: date | None,
    observed_on: date,
) -> int | None:
    """Return 1 for late payment, 0 for paid on time, None while unresolved."""
    if pending_amount == 0:
        if last_payment_date is None or last_payment_date > observed_on:
            return None
        return int(last_payment_date > due_date)
    if observed_on > due_date:
        return 1
    return None
