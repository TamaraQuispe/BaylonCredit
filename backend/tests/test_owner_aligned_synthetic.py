import json
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.ml.features import FEATURE_NAMES
from app.ml.owner_aligned_synthetic import (
    DATA_KEYS,
    ROW_KEYS,
    _outcome,
    generate_owner_aligned_dataset,
    validate_owner_aligned_dataset,
)
from app.ml.synthetic import money, remaining, snapshot

FIXTURES = Path(__file__).parent / "fixtures"
AUDIT_KEYS = {
    "clients",
    "all_loans",
    "warmup_loans",
    "study_loans",
    "payments",
    "study_label_counts",
    "weekly_stats",
    "mean_weekly_study_grants",
    "mean_weekly_study_grant_clients",
    "grant_scale_pass",
    "hard_constraints_pass",
    "amount_summary",
    "visit_gaps",
    "source_vs_assumptions",
    "adequacy",
}


@pytest.mark.parametrize(
    ("due_date", "label", "scenario"),
    [
        ("2026-09-29", 1, "partial_late"),
        ("2026-10-01", None, "partial_unresolved"),
    ],
)
def test_single_observed_abono_is_partial_without_reading_future_plan(due_date, label, scenario):
    loan = {
        "amount": "20.00",
        "due_date": due_date,
        "payments": [{"at": "2026-09-30T12:00:00", "amount": "10.00"}],
    }
    balance, actual, kind = _outcome(loan, datetime(2026, 9, 30, 23, 59))
    assert balance == Decimal("10.00")
    assert actual == label and kind == scenario


@pytest.fixture(scope="module")
def anchors():
    return json.loads((FIXTURES / "APF3_OWNER_ANCHORS_V4.json").read_text())


@pytest.fixture(scope="module")
def simulation():
    return json.loads((FIXTURES / "APF3_ALIGNED_V4_PROTOCOL.json").read_text())["simulation"]


@pytest.fixture(scope="module", params=[77, 123])
def dataset(request, anchors, simulation):
    # Unit-test seeds only. Never generate a declared development/final replica.
    return generate_owner_aligned_dataset(
        anchors, simulation, request.param, f"UNIT-{request.param}"
    )


def test_determinism_and_contract(dataset, anchors, simulation):
    original_anchors, original_simulation = deepcopy(anchors), deepcopy(simulation)
    assert dataset == generate_owner_aligned_dataset(
        anchors, simulation, dataset["seed"], dataset["prefix"]
    )
    assert anchors == original_anchors and simulation == original_simulation
    assert set(dataset) == DATA_KEYS
    assert all(set(row) == ROW_KEYS for row in dataset["rows"])
    assert all(row["replica_id"] == dataset["prefix"] for row in dataset["rows"])
    assert all(row["origen"] == "simulado" for row in dataset["rows"])
    assert all(row["loan_id"].startswith(dataset["prefix"]) for row in dataset["rows"])
    assert all(row["client_id"].startswith(dataset["prefix"]) for row in dataset["rows"])
    assert not any("latent_lateness_probability" in row for row in dataset["rows"])
    audit = validate_owner_aligned_dataset(dataset, anchors, simulation)
    assert set(audit) == AUDIT_KEYS
    assert audit["clients"] == 12
    assert audit["all_loans"] == audit["warmup_loans"] + audit["study_loans"]
    assert audit["all_loans"] == len(dataset["rows"])
    assert audit["hard_constraints_pass"]
    assert sum(audit["study_label_counts"].values()) == audit["study_loans"]
    assert audit["source_vs_assumptions"]["owner_declared"] == anchors
    assert audit["source_vs_assumptions"]["simulation_assumptions"] == simulation
    assert audit["grant_scale_pass"] == (
        9 <= audit["mean_weekly_study_grants"] <= 15
        and 7 <= audit["mean_weekly_study_grant_clients"] <= 11
    )


def test_ranges_exposure_and_temporal_recomputation(dataset, anchors, simulation):
    clients = {client["client_id"]: client for client in dataset["clients"]}
    rows = {row["loan_id"]: row for row in dataset["rows"]}
    cutoff = datetime.combine(date.fromisoformat(dataset["observed_on"]), time.max)
    for loan in dataset["loans"]:
        row = rows[loan["loan_id"]]
        at = datetime.fromisoformat(loan["evaluated_at"])
        due = date.fromisoformat(loan["due_date"])
        amount = Decimal(loan["amount"])
        assert Decimal("5") <= amount <= Decimal("50")
        assert due == at.date() + timedelta(days=1)
        expected = snapshot(
            clients[loan["client_id"]], dataset["loans"], dataset["sales"], at, amount
        )
        assert all(row[name] == expected[name] for name in FEATURE_NAMES)
        assert amount + Decimal(str(expected["outstanding"])) <= Decimal("80")
        assert all(type(row[name]) in (float, int) for name in FEATURE_NAMES)
        visible = [p for p in loan["planned_payments"] if datetime.fromisoformat(p["at"]) <= cutoff]
        assert loan["payments"] == visible
        assert all(at < datetime.fromisoformat(p["at"]) <= cutoff for p in visible)
        assert sum((Decimal(p["amount"]) for p in loan["planned_payments"]), Decimal(0)) == amount
        balance = amount - sum((Decimal(p["amount"]) for p in visible), Decimal(0))
        assert Decimal(row["pending_at_cutoff"]) == balance
        label = (
            int(max(date.fromisoformat(p["at"][:10]) for p in visible) > due)
            if balance == 0
            else 1
            if cutoff.date() > due
            else None
        )
        assert row["late_payment"] == label
        # Removing all events after evaluation must leave every feature unchanged.
        past_loans = deepcopy(dataset["loans"])
        for past in past_loans:
            past["payments"] = [
                p for p in past["payments"] if datetime.fromisoformat(p["at"]) <= at
            ]
        past_sales = [s for s in dataset["sales"] if datetime.fromisoformat(s["at"]) < at]
        assert expected == snapshot(clients[loan["client_id"]], past_loans, past_sales, at, amount)
    assert validate_owner_aligned_dataset(dataset, anchors, simulation)["hard_constraints_pass"]


def test_schedule_full_warmup_study_and_partial_week(dataset, anchors, simulation):
    audit = validate_owner_aligned_dataset(dataset, anchors, simulation)
    assert len(audit["weekly_stats"]) == 24
    assert audit["weekly_stats"][0]["week_start"] == "2026-04-13"
    assert audit["weekly_stats"][-1]["week_start"] == "2026-09-21"
    assert all(
        w["opportunities"] == 12 and w["scheduled_clients"] == 9 for w in audit["weekly_stats"]
    )
    start = date.fromisoformat(simulation["study_start"])
    for offset in range(1, 5):
        monday = (start - timedelta(weeks=offset)).isoformat()
        week = [a for a in dataset["attempts"] if a["week_start"] == monday]
        assert len(week) == 12 and len({a["client_id"] for a in week}) == 9
        assert all(a["phase"] == "warmup" for a in week)
    trailing = [a for a in dataset["attempts"] if a["week_start"] == "2026-09-28"]
    assert len(trailing) < 12
    assert all(a["evaluated_at"][:10] <= "2026-09-30" for a in trailing)
    for client in dataset["clients"]:
        visits = [
            datetime.fromisoformat(a["evaluated_at"])
            for a in dataset["attempts"]
            if a["client_id"] == client["client_id"]
        ]
        assert len({at.date() for at in visits}) == len(visits)
        assert all(3 <= (b - a).days <= 14 for a, b in zip(visits, visits[1:], strict=False))
        age = (visits[0].date() - date.fromisoformat(client["registered_on"])).days
        assert 0 <= age <= 180


def test_refusals_are_metadata_not_labeled_and_sales_are_linked(dataset):
    refused = [a for a in dataset["attempts"] if not a["granted"]]
    assert refused
    assert all(a["loan_id"] is None and "late_payment" not in a for a in refused)
    assert {a["loan_id"] for a in dataset["attempts"] if a["granted"]} == {
        row["loan_id"] for row in dataset["rows"]
    }
    assert len(dataset["rows"]) + len(refused) == len(dataset["attempts"])
    assert len(dataset["sales"]) == len(dataset["loans"])
    assert all(sale["kind"] == "credit" for sale in dataset["sales"])
    assert {sale["loan_id"] for sale in dataset["sales"]} == {
        loan["loan_id"] for loan in dataset["loans"]
    }


def test_only_past_positive_post_due_abonos_authorize_overdue_grants(dataset):
    for loan in dataset["loans"]:
        at = datetime.fromisoformat(loan["evaluated_at"])
        overdue = [
            prior
            for prior in dataset["loans"]
            if prior["client_id"] == loan["client_id"]
            and prior["evaluated_at"] < loan["evaluated_at"]
            and date.fromisoformat(prior["due_date"]) < at.date()
            and remaining(prior, at) > 0
        ]
        if overdue:
            assert "simulated_owner_review" in loan["authorization_tags"]
            assert all(
                any(
                    Decimal(p["amount"]) > 0
                    and prior["due_date"] < p["at"][:10]
                    and datetime.fromisoformat(p["at"]) < at
                    for p in prior["payments"]
                )
                for prior in overdue
            )
    for row in dataset["rows"]:
        if row["paid_credits"] == 0:
            loan = next(loan for loan in dataset["loans"] if loan["loan_id"] == row["loan_id"])
            assert loan["authorization_tags"] == [
                "simulated_identity_reference",
                "simulated_owner_review",
            ]


def test_controlled_abono_history_requires_post_due_payment_before_evaluation(
    dataset, anchors, simulation
):
    controlled = deepcopy(dataset)
    # A controlled event fixture, not a regenerated or outcome-tuned replica:
    # replace one punctual loan followed three days later by another grant.
    loans = controlled["loans"]
    prior, following = next(
        (a, b)
        for a in loans
        for b in loans
        if a["client_id"] == b["client_id"]
        and a["planned_scenario"] == "on_time"
        and datetime.fromisoformat(b["evaluated_at"]) - datetime.fromisoformat(a["evaluated_at"])
        == timedelta(days=3)
        and a["evaluated_at"][:10] < "2026-08-01"
    )
    due = date.fromisoformat(prior["due_date"])
    half = money(Decimal(prior["amount"]) / 2)
    prior["planned_payments"] = [
        {
            "payment_id": f"{prior['loan_id']}-P{number}",
            "replica_id": dataset["prefix"],
            "origen": "simulado",
            "at": datetime.combine(due + timedelta(days=days), hour).isoformat(),
            "amount": str(value),
        }
        for number, (days, hour, value) in enumerate(
            [(1, time(9), half), (4, time(14), Decimal(prior["amount"]) - half)], 1
        )
    ]
    prior["payments"] = deepcopy(prior["planned_payments"])
    prior["planned_scenario"] = "partial_late_after_due"
    clients = {client["client_id"]: client for client in controlled["clients"]}
    rows = {row["loan_id"]: row for row in controlled["rows"]}
    for loan in loans:
        if loan["client_id"] != prior["client_id"]:
            continue
        row = rows[loan["loan_id"]]
        features = snapshot(
            clients[loan["client_id"]],
            loans,
            controlled["sales"],
            datetime.fromisoformat(loan["evaluated_at"]),
            Decimal(loan["amount"]),
        )
        row.update(features)
        loan["authorization_tags"] = (
            ["simulated_identity_reference", "simulated_owner_review"]
            if not features["paid_credits"]
            else ["simulated_owner_review"]
            if features["pending_overdue"]
            else ["simulated_regular_grant"]
        )
    rows[prior["loan_id"]].update(late_payment=1, scenario="partial_late")
    assert rows[following["loan_id"]]["pending_overdue"] > 0
    assert "simulated_owner_review" in following["authorization_tags"]
    assert validate_owner_aligned_dataset(controlled, anchors, simulation)["hard_constraints_pass"]
    for invalid_at in (
        datetime.fromisoformat(prior["evaluated_at"]) + timedelta(hours=3),
        datetime.fromisoformat(following["evaluated_at"]),
        datetime.fromisoformat(following["evaluated_at"]) + timedelta(hours=1),
    ):
        invalid = deepcopy(controlled)
        changed = next(loan for loan in invalid["loans"] if loan["loan_id"] == prior["loan_id"])
        changed["payments"][0]["at"] = invalid_at.isoformat()
        changed["planned_payments"][0]["at"] = invalid_at.isoformat()
        with pytest.raises(AssertionError):
            validate_owner_aligned_dataset(invalid, anchors, simulation)


def test_payment_plan_branches_and_cutoff_unknowns(dataset):
    rows = {row["loan_id"]: row for row in dataset["rows"]}
    future = []
    for loan in dataset["loans"]:
        at = datetime.fromisoformat(loan["evaluated_at"])
        due = date.fromisoformat(loan["due_date"])
        plan = loan["planned_payments"]
        final = datetime.fromisoformat(plan[-1]["at"])
        delay = (final.date() - due).days
        assert delay == 0 or 1 <= delay <= 15
        if delay == 0:
            assert final.time() <= time(20)
        if len(plan) == 2:
            first = datetime.fromisoformat(plan[0]["at"])
            assert Decimal(plan[0]["amount"]) == money(Decimal(loan["amount"]) / 2)
            assert at + timedelta(hours=3) <= first < final
            if delay == 1:
                assert first.date() <= due
            if "after_due" in loan["planned_scenario"]:
                assert first.date() == due + timedelta(days=1)
        if len(plan) > len(loan["payments"]):
            future.append(loan)
            row = rows[loan["loan_id"]]
            assert row["late_payment"] == (1 if due < date(2026, 9, 30) else None)
    assert future


@pytest.mark.parametrize("field", ["paid_credits", "outstanding", "late_payment", "phase"])
def test_validator_rejects_corrupted_rows(dataset, anchors, simulation, field):
    invalid = deepcopy(dataset)
    row = invalid["rows"][0]
    row[field] = (
        "study"
        if field == "phase"
        else 1 - row[field]
        if field == "late_payment"
        else row[field] + 1
    )
    with pytest.raises(AssertionError):
        validate_owner_aligned_dataset(invalid, anchors, simulation)


@pytest.mark.parametrize(
    "corruption",
    [
        "overpayment",
        "future_observed",
        "duplicate_id",
        "schedule",
        "authorization",
        "latent_feature",
    ],
)
def test_validator_rejects_event_and_metadata_corruption(dataset, anchors, simulation, corruption):
    invalid = deepcopy(dataset)
    if corruption == "overpayment":
        invalid["loans"][0]["payments"][0]["amount"] = "999.00"
    elif corruption == "future_observed":
        invalid["loans"][0]["payments"][0]["at"] = "2026-10-01T09:00:00"
    elif corruption == "duplicate_id":
        invalid["clients"][1]["client_id"] = invalid["clients"][0]["client_id"]
    elif corruption == "schedule":
        invalid["attempts"].pop(0)
    elif corruption == "authorization":
        invalid["loans"][0]["authorization_tags"] = ["real_owner_approved"]
    else:
        invalid["rows"][0]["latent_lateness_probability"] = 0.5
    with pytest.raises(AssertionError):
        validate_owner_aligned_dataset(invalid, anchors, simulation)


def test_short_simulation_reports_adequacy_without_enforcing_200(anchors, simulation):
    short = {
        **simulation,
        "warmup_weeks": 0,
        "study_full_weeks": 1,
        "study_trailing_days": 3,
        "observed_on": "2026-04-22",
    }
    dataset = generate_owner_aligned_dataset(anchors, short, 77, "UNIT-SHORT")
    audit = validate_owner_aligned_dataset(dataset, anchors, short)
    assert audit["warmup_loans"] == 0
    assert audit["adequacy"]["n_study_below_200"]
    assert audit["adequacy"]["minority_below_30"]
    assert not audit["adequacy"]["adequate"]
    assert audit["hard_constraints_pass"]
    assert len(audit["weekly_stats"]) == 1
    assert any(row["late_payment"] is None for row in dataset["rows"])


def test_wrong_source_or_inconsistent_calendar_rejected(anchors, simulation):
    with pytest.raises(ValueError, match="current Rildo"):
        generate_owner_aligned_dataset(
            {**anchors, "source_docx_sha256": "hypothetical"}, simulation, 77, "UNIT"
        )
    with pytest.raises(ValueError, match="observation date"):
        generate_owner_aligned_dataset(
            anchors, {**simulation, "observed_on": "2026-10-01"}, 77, "UNIT"
        )
