from datetime import date, timedelta
from decimal import Decimal


def classify_credit_outcome(
    *,
    pending_amount: Decimal,
    due_date: date,
    last_payment_date: date | None,
    observed_on: date,
    default_grace_days: int = 30,
) -> int | None:
    """Return 1 for default, 0 for paid within grace, or None while unresolved."""
    default_date = due_date + timedelta(days=default_grace_days)
    if pending_amount == 0:
        if last_payment_date is None:
            return None
        return int(last_payment_date > default_date)
    if observed_on > default_date:
        return 1
    return None
