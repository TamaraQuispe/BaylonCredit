from datetime import date
from decimal import Decimal

import pytest

from app.ml.outcomes import classify_credit_outcome
from app.ml.training import load_real_dataset


def test_paid_on_due_date_is_on_time() -> None:
    assert (
        classify_credit_outcome(
            pending_amount=Decimal("0"),
            due_date=date(2026, 1, 1),
            last_payment_date=date(2026, 1, 1),
            observed_on=date(2026, 2, 1),
        )
        == 0
    )


def test_unpaid_day_after_due_date_is_late() -> None:
    assert (
        classify_credit_outcome(
            pending_amount=Decimal("25"),
            due_date=date(2026, 1, 1),
            last_payment_date=None,
            observed_on=date(2026, 1, 2),
        )
        == 1
    )


def test_current_credit_has_no_outcome() -> None:
    assert (
        classify_credit_outcome(
            pending_amount=Decimal("25"),
            due_date=date(2026, 1, 15),
            last_payment_date=None,
            observed_on=date(2026, 1, 15),
        )
        is None
    )


def test_training_rejects_too_few_real_outcomes(tmp_path) -> None:
    dataset = tmp_path / "outcomes.csv"
    dataset.write_text(
        "completed_sales,paid_credits,paid_late,pending_overdue,pending_current,"
        "outstanding,utilization,requested_ratio,tenure_days,punctuality_rate,"
        "overdue_rate,late_payment\n1,0,0,0,0,0,0,0.5,30,0,0,0\n"
    )
    with pytest.raises(ValueError, match="al menos 30"):
        load_real_dataset(dataset)


def test_paid_one_day_late_stays_late() -> None:
    assert classify_credit_outcome(
        pending_amount=Decimal("0"), due_date=date(2026, 1, 1),
        last_payment_date=date(2026, 1, 2), observed_on=date(2026, 1, 3),
    ) == 1


def test_partial_payment_does_not_resolve_before_due_date() -> None:
    assert classify_credit_outcome(
        pending_amount=Decimal("10"), due_date=date(2026, 1, 2),
        last_payment_date=date(2026, 1, 1), observed_on=date(2026, 1, 1),
    ) is None


def test_old_30_day_csv_is_not_accepted(tmp_path) -> None:
    dataset = tmp_path / "old.csv"
    dataset.write_text("defaulted\n0\n")
    with pytest.raises(ValueError, match="late_payment"):
        load_real_dataset(dataset)
