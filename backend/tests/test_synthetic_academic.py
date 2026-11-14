from copy import deepcopy
from datetime import datetime
from decimal import Decimal

import pytest

from app.ml.features import FEATURE_NAMES
from app.ml.synthetic import generate_academic_dataset, validate_academic_dataset


@pytest.fixture(scope="module")
def dataset():
    return generate_academic_dataset(30, seed=42)


def test_academic_simulation_reproducible_and_varied(dataset):
    assert dataset == generate_academic_dataset(30, seed=42)
    assert dataset != generate_academic_dataset(30, seed=43)
    summary = validate_academic_dataset(dataset)
    assert len(summary["scenarios"]) >= 7
    assert set(summary["labels"]) == {"0", "1", "None"}
    assert len({row["requested_amount"] for row in dataset["rows"]}) > 20
    assert all(len({row[feature] for row in dataset["rows"]}) > 1 for feature in FEATURE_NAMES)


def test_clients_do_not_cross_partitions_and_first_loan_has_no_paid_history(dataset):
    for client in dataset["clients"]:
        records = [row for row in dataset["rows"] if row["client_id"] == client["client_id"]]
        assert {row["split"] for row in records} == {client["split"]}
        assert min(records, key=lambda row: row["evaluated_at"])["paid_credits"] == 0
        assert all(row["data_source"] == "synthetic" for row in records)
    assert {c["split"] for c in dataset["clients"]} == {"train", "validation", "test"}


def test_transaction_snapshots_and_outcomes_are_consistent(dataset):
    assert validate_academic_dataset(dataset)["loans"] == len(dataset["rows"])
    for row in dataset["rows"]:
        assert all(name in row for name in FEATURE_NAMES)
        assert row["paid_late"] <= row["paid_credits"]
        assert 0 <= row["punctuality_rate"] <= 1
        assert 0 <= row["overdue_rate"] <= 1
        assert Decimal(row["pending_at_cutoff"]) >= 0
    assert not any(
        "first_name" in row or "document" in row or "phone" in row for row in dataset["rows"]
    )


def test_validation_catches_overpayment(dataset):
    invalid = deepcopy(dataset)
    loan = next(loan for loan in invalid["loans"] if loan["payments"])
    loan["payments"][0]["amount"] = str(Decimal(loan["amount"]) + Decimal("1"))
    with pytest.raises(AssertionError):
        validate_academic_dataset(invalid)


def test_validation_catches_snapshot_leakage(dataset):
    invalid = deepcopy(dataset)
    invalid["rows"][0]["paid_credits"] += 1
    with pytest.raises(AssertionError):
        validate_academic_dataset(invalid)


def test_no_payment_before_credit_or_after_observation(dataset):
    for loan in dataset["loans"]:
        for payment in loan["payments"]:
            assert datetime.fromisoformat(payment["at"]) > datetime.fromisoformat(
                loan["evaluated_at"]
            )
            assert payment["at"][:10] <= dataset["observed_on"]


def test_validation_catches_cross_partition_client(dataset):
    invalid = deepcopy(dataset)
    invalid["rows"][0]["split"] = "other"
    with pytest.raises(AssertionError):
        validate_academic_dataset(invalid)
