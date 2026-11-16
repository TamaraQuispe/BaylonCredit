import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.ml.features import FEATURE_NAMES
from app.ml.owner_aligned_synthetic import generate_owner_aligned_dataset
from app.ml.owner_settled_synthetic import (
    CLARIFICATION_SHA256,
    DATA_KEYS,
    POLICY_VERSION,
    PROTOCOL_SHA256,
    ROW_KEYS,
    _authorization,
    _overdue_balance,
    _refusal,
    generate_owner_settled_dataset,
    validate_owner_settled_dataset,
)
from app.ml.synthetic import money, snapshot

FIXTURES = Path(__file__).parent / "fixtures"
BACKEND = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def inputs():
    return (
        json.loads((FIXTURES / "APF3_OWNER_ANCHORS_V4.json").read_text()),
        json.loads((FIXTURES / "APF3_ALIGNED_V4_PROTOCOL.json").read_text())["simulation"],
        json.loads((FIXTURES / "APF3_OWNER_SETTLEMENT_CLARIFICATION.json").read_text()),
    )


@pytest.fixture(scope="module", params=[77, 123])
def dataset(request, inputs):
    # Only unit seeds; never generate declared DEV or FINAL cohorts here.
    return generate_owner_settled_dataset(*inputs, request.param, f"UNIT-SET5-{request.param}")


def test_determinism_schema_provenance_and_audit(dataset, inputs):
    original = deepcopy(inputs)
    assert dataset == generate_owner_settled_dataset(*inputs, dataset["seed"], dataset["prefix"])
    assert inputs == original
    assert set(dataset) == DATA_KEYS and dataset["policy_version"] == POLICY_VERSION
    assert all(set(row) == ROW_KEYS for row in dataset["rows"])
    audit = validate_owner_settled_dataset(dataset, *inputs)
    assert audit["settlement_policy_pass"] and audit["hard_constraints_pass"]
    assert audit["coherence_accepted"] is False
    assert "grant_scale_pass" not in audit
    assert type(audit["legacy_grant_scale_flag"]) is bool
    assert audit["requests"] == len(dataset["attempts"])
    assert audit["all_loans"] == len(dataset["loans"]) == len(dataset["rows"])
    assert audit["amount_summary"]["requested"]["count"] == audit["requests"]
    assert audit["amount_summary"]["granted"]["count"] == audit["all_loans"]
    assert audit["mean_weekly_study_requests"] == 12
    assert audit["mean_weekly_study_request_clients"] == 9
    assert len(audit["weekly_stats"]) == 24
    assert sum(audit["study_label_counts"].values()) == audit["study_loans"]
    assert audit["request_return_intervals_days"]["min"] >= 3
    assert audit["request_return_intervals_days"]["max"] <= 14
    assert (
        audit["granted_credit_intervals_days"]["count"]
        < audit["request_return_intervals_days"]["count"]
    )
    source = audit["source_vs_assumptions"]
    assert source["original_declaration"] == inputs[0]
    assert source["latest_clarification"] == inputs[2]
    assert source["base_simulation_assumptions"] == inputs[1]
    assert dataset["calibration"]["clarification_file_sha256"] == CLARIFICATION_SHA256
    # Returned audits and dataset metadata must not alias caller-owned source dictionaries.
    source["latest_clarification"]["scenario"]["initial_debt_pen"] = 999
    assert inputs == original


def test_observed_only_snapshots_strict_settlement_and_unknowns(dataset):
    clients = {c["client_id"]: c for c in dataset["clients"]}
    rows = {r["loan_id"]: r for r in dataset["rows"]}
    for loan in dataset["loans"]:
        at = datetime.fromisoformat(loan["evaluated_at"])
        assert _overdue_balance(dataset["loans"], loan["client_id"], at) == 0
        expected = snapshot(
            clients[loan["client_id"]],
            dataset["loans"],
            dataset["sales"],
            at,
            money(loan["amount"]),
        )
        assert all(rows[loan["loan_id"]][name] == expected[name] for name in FEATURE_NAMES)
        assert expected["pending_overdue"] == 0
        assert money(expected["outstanding"]) + money(loan["amount"]) <= 80
        past = deepcopy(dataset["loans"])
        for prior in past:
            prior["payments"] = [
                p for p in prior["payments"] if datetime.fromisoformat(p["at"]) <= at
            ]
            prior["planned_payments"] = []
        assert expected == snapshot(
            clients[loan["client_id"]], past, dataset["sales"], at, money(loan["amount"])
        )
    assert any(r["late_payment"] is None for r in dataset["rows"])
    refused = [a for a in dataset["attempts"] if not a["granted"]]
    assert refused and all(a["loan_id"] is None and "late_payment" not in a for a in refused)
    assert len(dataset["sales"]) == len(dataset["loans"])


@pytest.fixture
def controlled():
    client = {"client_id": "UNIT-C1", "credit_cap": "80.00", "registered_on": "2026-01-01"}
    loan = {
        "client_id": client["client_id"],
        "amount": "40.00",
        "evaluated_at": "2026-04-13T09:00:00",
        "due_date": "2026-04-14",
        "payments": [{"at": "2026-04-13T12:00:00", "amount": "10.00"}],
        "payment_agreement": "owner review and partial payment accepted",
        "authorization_tags": ["simulated_owner_review"],
        "grace_days": 3,
    }
    return client, loan, datetime(2026, 4, 15, 14)


@pytest.mark.parametrize("additional,remaining", [(0, 30), (20, 10)])
def test_40_minus_10_requires_all_remaining_not_agreement_or_grace(
    controlled, additional, remaining
):
    client, loan, at = controlled
    if additional:
        loan["payments"].append(
            {"at": (at - timedelta(seconds=1)).isoformat(), "amount": str(additional)}
        )
    assert _overdue_balance([loan], client["client_id"], at) == remaining
    assert _refusal(client, [loan], [], at, Decimal(5)) == "overdue_balance_not_fully_settled"


@pytest.mark.parametrize("offset,blocked", [(-1, False), (0, True), (1, True)])
def test_full_observed_30_requires_strictly_previous_event(controlled, offset, blocked):
    client, loan, at = controlled
    loan["payments"].append({"at": (at + timedelta(seconds=offset)).isoformat(), "amount": "30.00"})
    assert (_refusal(client, [loan], [], at, Decimal(5)) is not None) == blocked
    if not blocked:
        assert _refusal(client, [loan], [], at, Decimal(81)) == "insufficient_available_exposure"
        fresh = snapshot(client, [], [], at, Decimal(5))
        assert _authorization(fresh) == ["simulated_identity_reference", "simulated_owner_review"]


def test_another_overdue_blocks_and_client_isolation_and_not_due_scope(controlled):
    client, loan, at = controlled
    other = deepcopy(loan)
    loan["payments"].append({"at": (at - timedelta(seconds=1)).isoformat(), "amount": "30.00"})
    assert (
        _refusal(client, [loan, other], [], at, Decimal(5)) == "overdue_balance_not_fully_settled"
    )
    other["client_id"] = "UNIT-OTHER"
    assert _refusal(client, [loan, other], [], at, Decimal(5)) is None
    expected = snapshot(client, [loan], [], at, Decimal(5))
    assert expected == snapshot(client, [loan, other], [], at, Decimal(5))
    other["client_id"] = client["client_id"]
    other["due_date"] = at.date().isoformat()
    assert _refusal(client, [other], [], at, Decimal(5)) is None
    assert _refusal(client, [other], [], at, Decimal(51)) == "insufficient_available_exposure"


@pytest.mark.parametrize(
    "corruption",
    [
        "policy",
        "calibration",
        "calibration_bool",
        "row",
        "target",
        "unknown_target",
        "feature_bool",
        "extra_schema",
        "duplicate",
        "payment",
        "future",
        "subcent",
        "authorization",
        "schedule",
        "decision",
        "latent",
        "sale",
        "observed_bool",
    ],
)
def test_independent_validator_rejects_corruption(dataset, inputs, corruption):
    invalid = deepcopy(dataset)
    if corruption == "policy":
        invalid["policy_version"] = "academic-owner-aligned-v4"
    elif corruption == "calibration":
        invalid["calibration"]["clarification_file_sha256"] = "unknown"
    elif corruption == "calibration_bool":
        invalid["calibration"]["base_anchors"]["not_a_training_dataset"] = 1
    elif corruption == "row":
        invalid["rows"][0]["outstanding"] += 1
    elif corruption == "target":
        invalid["rows"][0]["late_payment"] = 1 - invalid["rows"][0]["late_payment"]
    elif corruption == "unknown_target":
        next(r for r in invalid["rows"] if r["late_payment"] is None)["late_payment"] = 0
    elif corruption == "feature_bool":
        invalid["rows"][0]["pending_overdue"] = False
    elif corruption == "extra_schema":
        invalid["loans"][0]["payment_agreement"] = True
    elif corruption == "duplicate":
        invalid["clients"][1]["client_id"] = invalid["clients"][0]["client_id"]
    elif corruption == "payment":
        invalid["loans"][0]["payments"][0]["amount"] = "999.00"
    elif corruption == "future":
        invalid["loans"][0]["payments"][0]["at"] = "2027-01-01T14:00:00"
    elif corruption == "subcent":
        invalid["loans"][0]["planned_payments"][0]["amount"] = "0.001"
    elif corruption == "authorization":
        invalid["loans"][0]["authorization_tags"] = ["real_owner_approved"]
    elif corruption == "schedule":
        invalid["attempts"].pop(0)
    elif corruption == "decision":
        next(a for a in invalid["attempts"] if not a["granted"])["granted"] = True
    elif corruption == "latent":
        invalid["rows"][0]["latent_lateness_probability"] = 0.2
    elif corruption == "observed_bool":
        invalid["loans"][0]["payments"][0]["amount"] = True
    else:
        invalid["sales"][0]["client_id"] = invalid["clients"][-1]["client_id"]
    with pytest.raises(AssertionError):
        validate_owner_settled_dataset(invalid, *inputs)


def test_validator_does_not_delegate_settlement_to_generator(dataset, inputs, monkeypatch):
    import app.ml.owner_settled_synthetic as settled

    invalid = deepcopy(dataset)
    prior, following = next(
        (a, b)
        for a in invalid["loans"]
        for b in invalid["loans"]
        if a["client_id"] == b["client_id"]
        and datetime.fromisoformat(b["evaluated_at"]) - datetime.fromisoformat(a["evaluated_at"])
        == timedelta(days=3)
        and a["planned_scenario"] == "on_time"
    )
    # Valid atomic partial-late plan, with a residual balance when the next grant occurs.
    first = datetime.fromisoformat(prior["evaluated_at"]) + timedelta(hours=3)
    final = datetime.fromisoformat(following["evaluated_at"]) + timedelta(days=1, hours=5)
    half = money(Decimal(prior["amount"]) / 2)
    prior["planned_payments"] = [
        {
            "payment_id": f"{prior['loan_id']}-P{n}",
            "replica_id": invalid["prefix"],
            "origen": "simulado",
            "at": when.isoformat(),
            "amount": str(value),
        }
        for n, (when, value) in enumerate(
            [(first, half), (final, Decimal(prior["amount"]) - half)], 1
        )
    ]
    prior["payments"] = deepcopy(prior["planned_payments"])
    prior["planned_scenario"] = "partial_late_before_due"
    clients = {c["client_id"]: c for c in invalid["clients"]}
    rows = {r["loan_id"]: r for r in invalid["rows"]}
    for loan in invalid["loans"]:
        features = snapshot(
            clients[loan["client_id"]],
            invalid["loans"],
            invalid["sales"],
            datetime.fromisoformat(loan["evaluated_at"]),
            money(loan["amount"]),
        )
        balance, label, scenario = settled._outcome(
            loan, datetime.fromisoformat(invalid["observed_on"] + "T23:59:59.999999")
        )
        rows[loan["loan_id"]].update(
            **features, pending_at_cutoff=str(balance), late_payment=label, scenario=scenario
        )
        loan["authorization_tags"] = _authorization(features)
    monkeypatch.setattr(settled, "_refusal", lambda *args: None)
    monkeypatch.setattr(settled, "_overdue_balance", lambda *args: Decimal(0))
    with pytest.raises(AssertionError, match="Overdue principal blocks every grant"):
        validate_owner_settled_dataset(invalid, *inputs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("new_credit_while_overdue_balance_positive", True),
        ("partial_payment_restores_eligibility", 0),
        ("payment_agreement_alone_restores_eligibility", True),
        ("not_yet_due_debt", "all current debt blocks credit"),
    ],
)
def test_unknown_or_mistyped_semantics_rejected(inputs, field, value):
    anchors, simulation, clarification = deepcopy(inputs)
    clarification["rule"][field] = value
    with pytest.raises(ValueError, match="exact user-relayed"):
        generate_owner_settled_dataset(anchors, simulation, clarification, 77, "UNIT")


@pytest.mark.parametrize(
    "corruption", ["missing", "source", "scenario_type", "verbatim", "approval"]
)
def test_unknown_clarification_source_rejected(inputs, corruption):
    anchors, simulation, clarification = deepcopy(inputs)
    if corruption == "missing":
        clarification = {}
    elif corruption == "source":
        clarification["base_source_docx_sha256"] = "unknown"
    elif corruption == "scenario_type":
        clarification["scenario"]["initial_debt_pen"] = 40.0
    elif corruption == "verbatim":
        clarification["user_messages_verbatim"][-1] = "un abono basta"
    else:
        clarification["not_business_model_approval"] = False
    with pytest.raises(ValueError):
        generate_owner_settled_dataset(anchors, simulation, clarification, 77, "UNIT")


def test_short_sample_does_not_force_adequacy(inputs):
    anchors, simulation, clarification = inputs
    short = {
        **simulation,
        "warmup_weeks": 0,
        "study_full_weeks": 1,
        "study_trailing_days": 3,
        "observed_on": "2026-04-22",
    }
    data = generate_owner_settled_dataset(anchors, short, clarification, 77, "UNIT-SHORT")
    audit = validate_owner_settled_dataset(data, anchors, short, clarification)
    assert not audit["adequacy"]["adequate"] and not audit["coherence_accepted"]
    assert audit["settlement_policy_pass"]
    assert any(r["late_payment"] is None for r in data["rows"])


@pytest.mark.parametrize(
    "relative,digest",
    [
        (
            "app/ml/owner_aligned_synthetic.py",
            "9fdb39dbcf33d507dc42876e53496841f79ec8c71a309ffbc8cc3b3224560a92",
        ),
        (
            "scripts/academic_credit_aligned_v4.py",
            "517290f1ce71fd1b6ac0dad93c604e0cabede4839b9bc40373b51f67f47afffb",
        ),
        (
            "tests/test_owner_aligned_synthetic.py",
            "7bd90d3ccc8ac122293f8ab2a42e4d16875b6d59a2628a9d09665fc0667327f9",
        ),
        (
            "tests/fixtures/APF3_OWNER_ANCHORS_V4.json",
            "81f858bc8827c88e41352745f65345a72d2b9d06361046bc86d3f07540806064",
        ),
        (
            "tests/fixtures/APF3_ALIGNED_V4_PROTOCOL.json",
            "b9a6c49c2e2cb3b0e036fb9e5ce37f69421c31e6d98ccb096b7ba37b8760345c",
        ),
        ("tests/fixtures/APF3_OWNER_SETTLEMENT_CLARIFICATION.json", CLARIFICATION_SHA256),
        ("tests/fixtures/APF3_SETTLED_V5_DATA_PROTOCOL.json", PROTOCOL_SHA256),
    ],
)
def test_frozen_and_verbatim_fixture_hashes(relative, digest):
    assert hashlib.sha256((BACKEND / relative).read_bytes()).hexdigest() == digest
    if "fixtures" in relative:
        doc = BACKEND.parent / "docs" / Path(relative).name
        if doc.exists():
            assert doc.read_bytes() == (BACKEND / relative).read_bytes()


def test_v4_deterministic_and_unaffected_by_v5(inputs):
    anchors, simulation, _ = inputs
    before = generate_owner_aligned_dataset(anchors, simulation, 77, "UNIT-V4-FROZEN")
    generate_owner_settled_dataset(*inputs, 77, "UNIT-SET5-ISOLATED")
    after = generate_owner_aligned_dataset(anchors, simulation, 77, "UNIT-V4-FROZEN")
    assert before == after
