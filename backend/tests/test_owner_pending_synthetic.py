import hashlib
import json
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from random import Random

import pytest

from app.ml import owner_pending_synthetic as pending
from app.ml.owner_pending_synthetic import (
    PROTOCOL_SHA256,
    REVIEW_SHA256,
    _amount,
    _outcome,
    _payment_time,
    _pending_balance,
    _refusal,
    _snapshot,
    generate_owner_pending_dataset,
    validate_owner_pending_dataset,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def inputs():
    anchors, review, protocol = [
        json.loads((FIXTURES / name).read_bytes())
        for name in (
            "APF3_OWNER_ANCHORS_V4.json",
            "APF3_OWNER_REVIEW_V5.json",
            "APF3_PENDING_V6_DATA_PROTOCOL.json",
        )
    ]
    return anchors, protocol["simulation"], review, protocol


@pytest.fixture(scope="module", params=[77, 123])
def dataset(request, inputs):
    # Unit seeds only, never declared DEV histories or FINAL.
    return generate_owner_pending_dataset(*inputs, request.param, f"UNIT-PND6-{request.param}")


def test_source_identity(inputs):
    for name, expected in (
        ("APF3_OWNER_REVIEW_V5.json", REVIEW_SHA256),
        ("APF3_PENDING_V6_DATA_PROTOCOL.json", PROTOCOL_SHA256),
    ):
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == expected
    assert inputs[3]["client_pool_policy"]["real_fixed_population"] is False


def test_determinism_and_audit(dataset, inputs):
    original = deepcopy(inputs)
    assert dataset == generate_owner_pending_dataset(*inputs, dataset["seed"], dataset["prefix"])
    audit = validate_owner_pending_dataset(dataset, *inputs)
    assert inputs == original
    assert audit["pending_grants"] == 0 and audit["pending_policy_pass"]
    assert audit["hard_constraints_pass"] and not audit["coherence_accepted"]
    assert "owner_sample_review_pass" not in audit
    assert audit["source_review_completed_on_sample"]
    assert sum(audit["source_review_classifications"].values()) == 23
    assert audit["clients"] == 12
    assert len(audit["weekly_stats"]) == 24
    assert audit["request_return_intervals_days"]["min"] >= 3
    assert audit["request_return_intervals_days"]["max"] <= 14
    assert sum(audit["study_label_counts"].values()) == audit["study_loans"]
    assert set(audit["amount_precision_counts"]) == {"whole_or_half", "exact_cents"}
    assert len(audit["observed_payment_time_frequencies"]) > 30
    rosters = [
        {a["client_id"] for a in dataset["attempts"] if a["week_start"] == w["week_start"]}
        for w in audit["weekly_stats"]
    ]
    assert all(len(r) == 9 for r in rosters) and rosters[0] != rosters[1]
    audit["source_vs_assumptions"]["latest_review"]["not_business_model_approval"] = False
    assert inputs == original


@pytest.fixture
def controlled():
    client = {"client_id": "UNIT-C1", "credit_cap": "80.00", "registered_on": "2026-01-01"}
    loan = {
        "client_id": "UNIT-C1",
        "amount": "30.00",
        "evaluated_at": "2026-04-13T09:00:00",
        "due_date": "2026-04-17",
        "payments": [],
        "payment_agreement": True,
    }
    return client, loan, datetime(2026, 4, 15, 9)


@pytest.mark.parametrize("paid,balance", [(0, 30), (20, 10), (30, 0)])
def test_not_due_friday_request_wednesday_partial_and_full(controlled, paid, balance):
    client, loan, at = controlled
    if paid:
        loan["payments"] = [{"at": (at - timedelta(seconds=1)).isoformat(), "amount": str(paid)}]
    assert _pending_balance([loan], client["client_id"], at) == balance
    assert _refusal(client, [loan], [], at, Decimal(5)) == (
        "pending_balance_not_fully_settled" if balance else None
    )
    if not balance:
        assert _refusal(client, [loan], [], at, Decimal(81)) == "insufficient_available_exposure"


@pytest.mark.parametrize("offset", [0, 1, 86400])
def test_future_or_simultaneous_never_clears(controlled, offset):
    client, loan, at = controlled
    loan["payments"] = [{"at": (at + timedelta(seconds=offset)).isoformat(), "amount": "30.00"}]
    assert _pending_balance([loan], client["client_id"], at) == 30
    assert _refusal(client, [loan], [], at, Decimal(5)) == "pending_balance_not_fully_settled"
    assert _snapshot(client, [loan], [], at, Decimal(5))["outstanding"] == 30
    other = {**loan, "client_id": "OTHER"}
    assert _pending_balance([other], client["client_id"], at) == 0


@pytest.mark.parametrize(
    "hour,minute,label", [(19, 59, None), (20, 0, None), (20, 1, 1), (21, 0, 1)]
)
def test_pending_due_today_team_cutoff(hour, minute, label):
    loan = {"amount": "30.00", "due_date": "2026-04-17", "payments": [], "grace_days": 3}
    assert _outcome(loan, datetime(2026, 4, 17, hour, minute)) == (Decimal(30), label, "unresolved")


def test_late_after_due_grace_and_partial_suffix():
    loan = {
        "amount": "30.00",
        "due_date": "2026-04-17",
        "grace_days": 3,
        "payments": [
            {"at": "2026-04-17T10:00:00", "amount": "20.00"},
            {"at": "2026-04-18T08:00:00", "amount": "10.00"},
        ],
    }
    assert _outcome(loan, datetime(2026, 4, 18, 9)) == (Decimal(0), 1, "partial_late_before_due")
    loan["payments"][-1]["at"] = "2026-04-17T20:00:00"
    assert _outcome(loan, datetime(2026, 4, 18, 9))[1:] == (0, "partial_on_time_before_due")


def test_amounts_and_varied_times_reproducible(inputs):
    anchors, simulation, _, _ = inputs

    def draw():
        rng = Random(77)
        return [
            (_amount(rng, anchors, simulation), _payment_time(rng, date(2026, 4, 17)))
            for _ in range(300)
        ]

    draws = draw()
    assert draws == draw()
    assert all(5 <= amount <= 50 for amount, _ in draws)
    assert any(amount % Decimal("0.50") for amount, _ in draws)
    assert any(amount % Decimal("0.50") == 0 and amount % 5 != 0 for amount, _ in draws)
    assert len({at.time() for _, at in draws}) > 200
    assert all(
        time(8) <= at.time() <= time(12) or time(16) <= at.time() <= time(20) for _, at in draws
    )
    with pytest.raises(ValueError):
        _payment_time(Random(77), date(2026, 4, 17), datetime(2026, 4, 17, 20, 0, 1))


def test_future_plans_never_visible(dataset):
    clients = {c["client_id"]: c for c in dataset["clients"]}
    for loan in dataset["loans"]:
        at = datetime.fromisoformat(loan["evaluated_at"])
        client = clients[loan["client_id"]]
        clean = deepcopy(dataset["loans"])
        for prior in clean:
            prior["planned_payments"] = []
            prior["payments"] = [
                p for p in prior["payments"] if datetime.fromisoformat(p["at"]) < at
            ]
        assert _snapshot(client, dataset["loans"], dataset["sales"], at, Decimal(5)) == _snapshot(
            client, clean, dataset["sales"], at, Decimal(5)
        )
        assert _pending_balance(dataset["loans"], loan["client_id"], at) == 0


def test_validator_does_not_trust_generator_decisions(dataset, inputs, monkeypatch):
    def forbidden(*args, **kwargs):
        raise RuntimeError("Generator decision must not validate itself")

    monkeypatch.setattr(pending, "_refusal", forbidden)
    monkeypatch.setattr(pending, "_outcome", forbidden)
    assert validate_owner_pending_dataset(dataset, *inputs)["pending_policy_pass"]


@pytest.mark.parametrize("window,endpoint,hour", [(0, 0, 8), (0, 1, 12), (1, 0, 16), (1, 1, 20)])
def test_payment_window_endpoints(window, endpoint, hour):
    class BoundaryRandom:
        def random(self):
            return 0.25 if window == 0 else 0.75

        def randint(self, low, high):
            return high if endpoint else low

    assert _payment_time(BoundaryRandom(), date(2026, 4, 17)).time() == time(hour)


@pytest.mark.parametrize("change", ["approval", "window", "probability", "simulation", "anchors"])
def test_reject_modified_sources(inputs, change):
    anchors, simulation, review, protocol = deepcopy(inputs)
    if change == "approval":
        review["not_business_model_approval"] = False
    elif change == "window":
        protocol["payment_time_policy"]["windows"] = ["08:00-21:00"]
    elif change == "probability":
        protocol["simulation"]["exact_price_scenario_probability"] = 0.1
    elif change == "simulation":
        simulation = {**simulation, "amount_log_sigma": 0.8}
    else:
        anchors["client_cap_pen"] = 90
    with pytest.raises(ValueError):
        generate_owner_pending_dataset(anchors, simulation, review, protocol, 77, "UNIT")


@pytest.mark.parametrize(
    "change",
    [
        "amount",
        "payment",
        "payment_time",
        "visibility",
        "sale",
        "row",
        "label",
        "refusal",
        "client",
        "seed",
        "origin",
        "cutoff",
        "extra",
        "duplicate",
        "plan_order",
        "repeat",
    ],
)
def test_tampering_rejected(dataset, inputs, change):
    bad = deepcopy(dataset)
    if change == "amount":
        bad["attempts"][0]["requested_amount"] = "49.99"
    elif change == "payment":
        bad["loans"][0]["planned_payments"][0]["amount"] = "0.00"
    elif change == "payment_time":
        bad["loans"][0]["planned_payments"][0]["at"] = "2026-04-17T13:00:00"
    elif change == "visibility":
        bad["loans"][-1]["payments"] = []
        if not dataset["loans"][-1]["payments"]:
            bad["loans"][-1]["payments"] = deepcopy(bad["loans"][-1]["planned_payments"])
    elif change == "sale":
        bad["sales"][0]["amount"] = "5.01"
    elif change == "row":
        bad["rows"][0]["paid_credits"] += 1
    elif change == "label":
        bad["rows"][0]["late_payment"] = 1 - bad["rows"][0]["late_payment"]
    elif change == "refusal":
        a = next(a for a in bad["attempts"] if not a["granted"])
        a["granted"] = True
    elif change == "client":
        bad["clients"][0]["schedule_group"] = 9
    elif change == "seed":
        bad["seed"] = True
    elif change == "origin":
        bad["replica_id"] = "REAL"
    elif change == "cutoff":
        bad["observed_on"] = "2026-10-01"
    elif change == "extra":
        bad["loans"][0]["approval"] = True
    elif change == "duplicate":
        bad["sales"][1]["sale_id"] = bad["sales"][0]["sale_id"]
    elif change == "plan_order":
        loan = next(loan for loan in bad["loans"] if len(loan["planned_payments"]) == 2)
        loan["planned_payments"].reverse()
    else:
        bad["attempts"][0]["repeat_visit"] = True
    with pytest.raises(AssertionError):
        validate_owner_pending_dataset(bad, *inputs)
