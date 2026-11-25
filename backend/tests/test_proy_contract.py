from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.ml.features import FEATURE_NAMES
from app.ml.outcomes import classify_credit_outcome
from app.ml.proy_contract import (
    CONTRACT_VERSION,
    FEATURE_NAMES_PROY,
    TARGET_GRACE_DAYS,
    describe_contract,
    outstanding_is_blocking,
    snapshot_is_valid,
    target_cutoff,
    validate_feature_snapshot,
)


def _snapshot(**overrides) -> dict[str, float]:
    values = {
        "completed_sales": 12.0,
        "paid_credits": 12.0,
        "paid_late": 2.0,
        "pending_overdue": 0.0,
        "pending_current": 0.0,
        "outstanding": 0.0,
        "utilization": 0.0,
        "requested_ratio": 0.25,
        "tenure_days": 120.0,
        "punctuality_rate": 0.8333,
        "overdue_rate": 0.0,
    }
    values.update(overrides)
    return values


def test_contract_matches_historical_feature_order() -> None:
    assert FEATURE_NAMES_PROY == tuple(FEATURE_NAMES)
    assert len(FEATURE_NAMES_PROY) == 11


def test_versioned_contract_is_serializable() -> None:
    described = describe_contract()
    assert described["contract_version"] == CONTRACT_VERSION
    assert len(described["features"]) == 11
    assert described["target"]["timezone"] == "America/Lima"


def test_valid_snapshot_has_no_problems() -> None:
    assert validate_feature_snapshot(_snapshot()) == []
    assert snapshot_is_valid(_snapshot())


def test_missing_and_unknown_features_are_reported() -> None:
    incomplete = _snapshot()
    del incomplete["overdue_rate"]
    incomplete["score"] = 91.0
    problems = validate_feature_snapshot(incomplete)
    assert any("overdue_rate" in problem for problem in problems)
    assert any("score" in problem for problem in problems)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_non_finite_and_negative_counts_are_rejected(bad: float) -> None:
    problems = validate_feature_snapshot(_snapshot(completed_sales=bad))
    assert problems


@pytest.mark.parametrize("ratio", [1.2, -0.1])
def test_ratios_must_stay_in_range(ratio: float) -> None:
    assert validate_feature_snapshot(_snapshot(utilization=ratio))
    assert validate_feature_snapshot(_snapshot(punctuality_rate=ratio))
    assert validate_feature_snapshot(_snapshot(overdue_rate=ratio))


def test_counts_must_be_integers() -> None:
    assert validate_feature_snapshot(_snapshot(paid_late=1.5))


def test_target_contract_matches_labeling_function() -> None:
    due = date(2026, 11, 10)
    observed = due + timedelta(days=TARGET_GRACE_DAYS)
    assert target_cutoff(due) > due
    # Liquidado dentro del plazo: puntual.
    assert classify_credit_outcome(
        pending_amount=Decimal("0"),
        due_date=due,
        last_payment_date=due,
        observed_on=observed,
    ) == 0
    # Liquidado despues del plazo: atraso, nunca desconocido.
    assert classify_credit_outcome(
        pending_amount=Decimal("0"),
        due_date=due,
        last_payment_date=due + timedelta(days=1),
        observed_on=observed,
    ) == 1
    # Saldo pendiente con el plazo vencido: atraso.
    assert classify_credit_outcome(
        pending_amount=Decimal("12.00"),
        due_date=due,
        last_payment_date=None,
        observed_on=observed,
    ) == 1
    # Saldo pendiente aun dentro del plazo: desconocido, no clase 0.
    assert classify_credit_outcome(
        pending_amount=Decimal("12.00"),
        due_date=observed + timedelta(days=5),
        last_payment_date=None,
        observed_on=observed,
    ) is None
    # Sin fecha de liquidacion confiable: no se fabrica etiqueta.
    assert classify_credit_outcome(
        pending_amount=Decimal("0"),
        due_date=due,
        last_payment_date=None,
        observed_on=observed,
    ) is None


@pytest.mark.parametrize("pending,blocked", [("0.00", False), ("0.01", True), ("80.00", True)])
def test_any_pending_balance_blocks(pending: str, blocked: bool) -> None:
    assert outstanding_is_blocking(Decimal(pending)) is blocked
