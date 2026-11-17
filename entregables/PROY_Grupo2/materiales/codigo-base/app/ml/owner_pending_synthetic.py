"""Fictional owner-pending V6 histories, not business validation or approval."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256
from math import isfinite
from random import Random
from statistics import mean

from app.ml.features import FEATURE_NAMES
from app.ml.outcomes import TARGET_NAME
from app.ml.owner_aligned_synthetic import _calendar, _truncated
from app.ml.synthetic import money, remaining, snapshot

POLICY_VERSION = "academic-owner-pending-v6-data"
REVIEW_SHA256 = "a72ea574fa2997d3477b0522c0044d590638957f0b5e553c31d97764df1a89a3"
PROTOCOL_SHA256 = "5f3cea3798b73d31cf8aea54dc6bc45341777871988f7ef68686d34287811431"
REVIEW_SEMANTIC_SHA256 = "ce8d1268758197c188334c0e4397cb2cd5f616ad503cd5513773110608b68528"
PROTOCOL_SEMANTIC_SHA256 = "ec69b3822ee3347695eca2ad996586356e328d6dcaef89715064a5bfc9911a5b"
ANCHORS_SEMANTIC_SHA256 = "4b45c46aeae8f22000972f167d814d66b98bf8a45bc06d55fd2e2798ba40c881"
PENDING_POLICY = (
    "Reject evaluation for new credit whenever any remaining principal is positive, "
    "including debt not yet due. Partial payments and agreements do not restore eligibility. "
    "Full settlement must be observed strictly before evaluation; it resumes eligibility only."
)
DATA_KEYS = {
    "seed",
    "prefix",
    "replica_id",
    "origen",
    "observed_on",
    "clients",
    "loans",
    "sales",
    "attempts",
    "rows",
    "policy_version",
    "calibration",
}
ROW_KEYS = (
    set(FEATURE_NAMES)
    | {TARGET_NAME}
    | {
        "phase",
        "replica_id",
        "origen",
        "requested_amount",
        "credit_cap",
        "client_id",
        "loan_id",
        "evaluated_at",
        "due_date",
        "observed_on",
        "pending_at_cutoff",
        "scenario",
    }
)
PAYMENT_WINDOWS = (
    (time(8, 0), time(12, 0)),
    (time(16, 0), time(20, 0)),
)
_SCHEMAS = {
    "client_id": (
        "client_id replica_id origen registered_on credit_cap schedule_group schedule_member "
        "latent_lateness_probability"
    ),
    "attempt_id": (
        "attempt_id client_id replica_id origen phase week_start repeat_visit evaluated_at "
        "requested_amount granted refusal_reason loan_id"
    ),
    "loan_id": (
        "loan_id client_id replica_id origen phase evaluated_at due_date amount "
        "planned_payments planned_scenario payments authorization_tags"
    ),
    "sale_id": "sale_id loan_id client_id replica_id origen phase at kind amount",
    "payment_id": "payment_id replica_id origen at amount",
}


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _calibration(anchors: dict, simulation: dict, review: dict, protocol: dict) -> dict:
    if protocol.get("latest_source_review") != "APF3_OWNER_REVIEW_V5.json":
        raise ValueError("Protocol must identify the latest owner review")
    if protocol.get("base_anchors") != "APF3_OWNER_ANCHORS_V4.json":
        raise ValueError("Protocol must preserve the base anchors")
    return {
        "version": POLICY_VERSION,
        "base_source_docx_sha256": anchors["source_docx_sha256"],
        "review_file_sha256": REVIEW_SHA256,
        "review_semantic_sha256": sha256(_canonical(review).encode()).hexdigest(),
        "data_protocol_sha256": PROTOCOL_SHA256,
        "base_anchors": deepcopy(anchors),
        "base_simulation": deepcopy(simulation),
        "amount_policy": deepcopy(protocol["amount_policy"]),
        "payment_time_policy": deepcopy(protocol["payment_time_policy"]),
        "client_pool_policy": deepcopy(protocol["client_pool_policy"]),
        "effective_pending_balance_policy": PENDING_POLICY,
        "payment_visibility": "strictly_before_evaluation; cutoff_inclusive",
    }


def _validate_inputs(anchors: dict, simulation: dict, review: dict, protocol: dict) -> None:
    for value, expected in (
        (anchors, ANCHORS_SEMANTIC_SHA256),
        (review, REVIEW_SEMANTIC_SHA256),
        (protocol, PROTOCOL_SEMANTIC_SHA256),
    ):
        if sha256(_canonical(value).encode()).hexdigest() != expected:
            raise ValueError("Source semantics differ from the frozen V6 inputs")
    if _canonical(simulation) != _canonical(protocol["simulation"]):
        raise ValueError("Simulation must equal the predeclared V6 scenario")
    if protocol.get("version") != POLICY_VERSION:
        raise ValueError("Expected pending V6 protocol")
    if protocol.get("selection_protocol") is not None or protocol.get("final_seed") is not None:
        raise ValueError("Data revision does not authorize a final model protocol")
    if protocol.get("models_authorized") is not False:
        raise ValueError("This protocol never authorizes model fitting")
    if review.get("version") != "owner-review-v5-1":
        raise ValueError("Expected the latest owner review")
    if review.get("review_date") != "2026-11-15":
        raise ValueError("Owner review date mismatch")
    if review.get("confirmed_rules", {}).get("pending_balance") != (
        "Any positive remaining balance blocks a new credit evaluation, including debt not yet due"
    ):
        raise ValueError("Pending-balance rule missing")
    if (
        anchors.get("source_docx_sha256")
        != "45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f"
    ):
        raise ValueError("Owner anchors do not identify the original declaration")


def _pending_balance(loans: list[dict], client_id: str, at: datetime) -> Decimal:
    return sum(
        (
            money(loan["amount"])
            - sum(
                (
                    money(p["amount"])
                    for p in loan["payments"]
                    if datetime.fromisoformat(p["at"]) < at
                ),
                Decimal(0),
            )
            for loan in loans
            if loan["client_id"] == client_id and datetime.fromisoformat(loan["evaluated_at"]) < at
        ),
        Decimal(0),
    )


def _snapshot(
    client: dict, loans: list[dict], sales: list[dict], at: datetime, amount: Decimal
) -> dict:
    observed = [
        {**loan, "payments": [p for p in loan["payments"] if datetime.fromisoformat(p["at"]) < at]}
        for loan in loans
    ]
    return snapshot(client, observed, sales, at, amount)


def _refusal(
    client: dict, loans: list[dict], sales: list[dict], at: datetime, amount: Decimal
) -> str | None:
    if _pending_balance(loans, client["client_id"], at) > 0:
        return "pending_balance_not_fully_settled"
    features = _snapshot(client, loans, sales, at, amount)
    if money(features["outstanding"]) + amount > money(client["credit_cap"]):
        return "insufficient_available_exposure"
    return None


def _authorization(features: dict) -> list[str]:
    if features["paid_credits"] == 0:
        return ["simulated_identity_reference", "simulated_owner_review"]
    return ["simulated_regular_grant"]


def _amount(rng: Random, anchors: dict, simulation: dict) -> Decimal:
    low, high = anchors["loan_amount_range_pen"]
    for _ in range(1000):
        raw = _truncated(
            rng, anchors["typical_amount_estimate_pen"], simulation["amount_log_sigma"], low, high
        )
        if rng.random() < simulation["exact_price_scenario_probability"]:
            value = money(raw)
        else:
            value = (Decimal(str(raw)) * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2
            value = money(value)
        if Decimal(str(low)) <= value <= Decimal(str(high)):
            return value
    raise ValueError("Unable to generate an amount in range")


def _payment_time(rng: Random, day: date, earliest: datetime | None = None) -> datetime:
    for _ in range(1000):
        start, end = PAYMENT_WINDOWS[0] if rng.random() < 0.5 else PAYMENT_WINDOWS[1]
        seconds = (datetime.combine(day, end) - datetime.combine(day, start)).total_seconds()
        when = datetime.combine(day, start) + timedelta(seconds=rng.randint(0, int(seconds)))
        if earliest is None or when >= earliest:
            return when
    raise ValueError("No payment time is available after the requested earliest bound")


def _outcome(loan: dict, cutoff: datetime) -> tuple[Decimal, int | None, str]:
    balance = remaining(loan, cutoff)
    due = date.fromisoformat(loan["due_date"])
    payments = loan["payments"]
    if balance == 0:
        last = max(payments, key=lambda p: p["at"])
        last_at = datetime.fromisoformat(last["at"])
        late = last_at.date() > due or (last_at.date() == due and last_at.time() > time(20))
        scenario = "late" if late else "on_time"
        if len(payments) == 2:
            before = datetime.fromisoformat(payments[0]["at"]).date() <= due
            scenario = "partial_" + scenario + ("_before_due" if before else "_after_due")
        return balance, int(late), scenario
    due_passed = cutoff.date() > due or (cutoff.date() == due and cutoff.time() > time(20))
    if due_passed:
        scenario = "unresolved" if balance == money(loan["amount"]) else "partial_unresolved"
        return balance, 1, scenario
    scenario = "unresolved" if balance == money(loan["amount"]) else "partial_unresolved"
    return balance, None, scenario


def generate_owner_pending_dataset(
    anchors: dict, simulation: dict, review: dict, protocol: dict, seed: int, prefix: str
) -> dict:
    """Generate one fictional example roster without saving or training."""
    _validate_inputs(anchors, simulation, review, protocol)
    first_day, study_start, cutoff = _calendar(anchors, simulation)
    calibration = _calibration(anchors, simulation, review, protocol)
    if type(seed) is not int or not isinstance(prefix, str) or not prefix.strip():
        raise ValueError("An integer seed and nonempty fictional prefix are required")
    rng = Random(seed)
    low, high = anchors["loan_amount_range_pen"]
    cap = money(anchors["client_cap_pen"])
    schedule = []
    for week in range((cutoff.date() - first_day).days // 7 + 1):
        monday = first_day + timedelta(weeks=week)
        for group in range(4):
            if group == week % 4:
                continue
            for member in range(3):
                day = member + rng.randint(0, 3 - member)
                days = [day, day + 3] if group == (week + 1) % 4 else [day]
                for visit, offset in enumerate(days):
                    at = datetime.combine(monday + timedelta(days=offset), time(9))
                    if at <= cutoff:
                        schedule.append((at, group * 3 + member, monday, bool(visit)))
    schedule.sort()
    clients = []
    p = anchors["late"] / anchors["evaluable"]
    concentration = simulation["latent_beta_concentration"]
    for index in range(12):
        first_visit = min((at.date() for at, n, _, _ in schedule if n == index), default=first_day)
        clients.append(
            {
                "client_id": f"{prefix}-C{index + 1:03}",
                "replica_id": prefix,
                "origen": "simulado",
                "registered_on": (
                    first_visit
                    - timedelta(days=rng.randint(*simulation["registration_age_range_days"]))
                ).isoformat(),
                "credit_cap": str(cap),
                "schedule_group": index // 3,
                "schedule_member": index % 3,
                "latent_lateness_probability": rng.betavariate(
                    p * concentration, (1 - p) * concentration
                ),
            }
        )
    loans, sales, attempts, rows = [], [], [], []
    for at, index, monday, repeat in schedule:
        client = clients[index]
        phase = "warmup" if at.date() < study_start else "study"
        amount = _amount(rng, anchors, simulation)
        refusal = _refusal(client, loans, sales, at, amount)
        attempt = {
            "attempt_id": f"{prefix}-A{len(attempts) + 1:05}",
            "client_id": client["client_id"],
            "replica_id": prefix,
            "origen": "simulado",
            "phase": phase,
            "week_start": monday.isoformat(),
            "repeat_visit": repeat,
            "evaluated_at": at.isoformat(),
            "requested_amount": str(amount),
            "granted": refusal is None,
            "refusal_reason": refusal,
            "loan_id": None,
        }
        attempts.append(attempt)
        if refusal:
            continue
        features = _snapshot(client, loans, sales, at, amount)
        due = at.date() + timedelta(days=anchors["contract_term_days"])
        late = rng.random() < client["latent_lateness_probability"]
        partial = (
            rng.random()
            < anchors["partial_payment_annotations"] / anchors["partial_payment_denominator"]
        )
        delay = (
            int(
                round(
                    _truncated(
                        rng,
                        anchors["usual_late_delay_days"],
                        simulation["late_delay_log_sigma"],
                        *anchors["late_delay_range_days"],
                    )
                )
            )
            if late
            else 0
        )
        final_at = _payment_time(rng, due + timedelta(days=delay))
        plan = [(final_at, amount)]
        scenario = "late" if delay else "on_time"
        if partial:
            before = (
                not late or rng.random() < simulation["partial_before_due_probability_when_late"]
            ) or delay == 1
            earliest = at + timedelta(hours=3)
            first_at = (
                _payment_time(rng, at.date(), earliest)
                if before
                else datetime.combine(due + timedelta(days=1), time(9))
            )
            if not before:
                first_at = _payment_time(
                    rng, due + timedelta(days=1), datetime.combine(due + timedelta(days=1), time(8))
                )
            half = money(amount * Decimal(str(simulation["partial_payment_fraction"])))
            plan = [(first_at, half), (final_at, amount - half)]
            scenario = "partial_" + scenario + ("_before_due" if before else "_after_due")
        loan_id = f"{prefix}-L{len(loans) + 1:05}"
        planned = [
            {
                "payment_id": f"{loan_id}-P{n}",
                "replica_id": prefix,
                "origen": "simulado",
                "at": when.isoformat(),
                "amount": str(value),
            }
            for n, (when, value) in enumerate(plan, 1)
        ]
        loan = {
            "loan_id": loan_id,
            "client_id": client["client_id"],
            "replica_id": prefix,
            "origen": "simulado",
            "phase": phase,
            "evaluated_at": at.isoformat(),
            "due_date": due.isoformat(),
            "amount": str(amount),
            "planned_payments": planned,
            "planned_scenario": scenario,
            "payments": [dict(p) for p in planned if datetime.fromisoformat(p["at"]) <= cutoff],
            "authorization_tags": _authorization(features),
        }
        loans.append(loan)
        attempt["loan_id"] = loan_id
        balance, label, observed_scenario = _outcome(loan, cutoff)
        rows.append(
            {
                "loan_id": loan_id,
                "client_id": client["client_id"],
                "replica_id": prefix,
                "origen": "simulado",
                "phase": phase,
                "evaluated_at": at.isoformat(),
                "due_date": due.isoformat(),
                "observed_on": cutoff.date().isoformat(),
                "requested_amount": str(amount),
                "credit_cap": str(cap),
                "pending_at_cutoff": str(balance),
                "scenario": observed_scenario,
                **features,
                TARGET_NAME: label,
            }
        )
        sales.append(
            {
                "sale_id": f"{prefix}-S{len(sales) + 1:05}",
                "loan_id": loan_id,
                "client_id": client["client_id"],
                "replica_id": prefix,
                "origen": "simulado",
                "phase": phase,
                "at": (at + timedelta(minutes=1)).isoformat(),
                "kind": "credit",
                "amount": str(amount),
            }
        )
    dataset = {
        "seed": seed,
        "prefix": prefix,
        "replica_id": prefix,
        "origen": "simulado",
        "observed_on": cutoff.date().isoformat(),
        "clients": clients,
        "loans": loans,
        "sales": sales,
        "attempts": attempts,
        "rows": rows,
        "policy_version": POLICY_VERSION,
        "calibration": calibration,
    }
    validate_owner_pending_dataset(dataset, anchors, simulation, review, protocol)
    return dataset


def validate_owner_pending_dataset(
    dataset: dict, anchors: dict, simulation: dict, review: dict, protocol: dict
) -> dict:
    """Independently recompute events, eligibility, features and labels; never fit."""
    _validate_inputs(anchors, simulation, review, protocol)
    first_day, study_start, cutoff = _calendar(anchors, simulation)
    calibration = _calibration(anchors, simulation, review, protocol)
    assert set(dataset) == DATA_KEYS and dataset["policy_version"] == POLICY_VERSION
    assert _canonical(dataset["calibration"]) == _canonical(calibration)
    prefix = dataset["prefix"]
    assert isinstance(prefix, str) and prefix.strip() and type(dataset["seed"]) is int
    assert dataset["replica_id"] == prefix and dataset["origen"] == "simulado"
    assert dataset["observed_on"] == cutoff.date().isoformat()
    assert all(type(dataset[k]) is list for k in ("clients", "loans", "sales", "attempts", "rows"))
    clients = {c["client_id"]: c for c in dataset["clients"]}
    loans = {loan["loan_id"]: loan for loan in dataset["loans"]}
    rows = {row["loan_id"]: row for row in dataset["rows"]}
    assert len(clients) == len(dataset["clients"]) == 12
    assert len(loans) == len(dataset["loans"]) == len(rows) == len(dataset["rows"])
    assert loans.keys() == rows.keys()
    cap = money(anchors["client_cap_pen"])
    ids = set()

    def entity(record: dict, key: str) -> None:
        assert set(record) == set(_SCHEMAS[key].split())
        identifier = record[key]
        assert isinstance(identifier, str) and identifier.startswith(prefix + "-")
        assert identifier not in ids
        ids.add(identifier)
        assert record["origen"] == "simulado" and record["replica_id"] == prefix

    def currency(value: str) -> Decimal:
        assert isinstance(value, str)
        number = Decimal(value)
        assert number.is_finite() and number == money(value)
        return number

    groups = {}
    for client in dataset["clients"]:
        entity(client, "client_id")
        assert client["credit_cap"] == str(cap)
        group, member = client["schedule_group"], client["schedule_member"]
        assert type(group) is int and 0 <= group < 4
        assert type(member) is int and 0 <= member < 3
        assert (group, member) not in groups
        groups[group, member] = client["client_id"]
        assert type(client["latent_lateness_probability"]) in (int, float)
        assert 0 <= client["latent_lateness_probability"] <= 1

    # Check atomic events before reconstructing balances or features.
    for loan in dataset["loans"]:
        entity(loan, "loan_id")
        assert loan["client_id"] in clients
        at = datetime.fromisoformat(loan["evaluated_at"])
        due = date.fromisoformat(loan["due_date"])
        amount = currency(loan["amount"])
        assert 5 <= amount <= 50 and due == at.date() + timedelta(days=1)
        plan = loan["planned_payments"]
        assert type(plan) is list and len(plan) in (1, 2)
        assert type(loan["payments"]) is list
        total, previous = Decimal(0), at
        for n, payment in enumerate(plan, 1):
            entity(payment, "payment_id")
            assert payment["payment_id"] == f"{loan['loan_id']}-P{n}"
            when, value = datetime.fromisoformat(payment["at"]), currency(payment["amount"])
            assert when > previous and value > 0
            assert any(start <= when.time() <= end for start, end in PAYMENT_WINDOWS)
            if when.date() <= due:
                assert when >= at + timedelta(hours=3)
            total += value
            assert total <= amount
            previous = when
        assert total == amount
        assert loan["payments"] == [p for p in plan if datetime.fromisoformat(p["at"]) <= cutoff]
        delay = (datetime.fromisoformat(plan[-1]["at"]).date() - due).days
        assert (
            delay == 0
            or anchors["late_delay_range_days"][0] <= delay <= anchors["late_delay_range_days"][1]
        )
        scenario = "late" if delay else "on_time"
        if len(plan) == 2:
            assert currency(plan[0]["amount"]) == money(
                amount * Decimal(str(simulation["partial_payment_fraction"]))
            )
            first = datetime.fromisoformat(plan[0]["at"])
            before = first.date() <= due
            assert first.date() == (at.date() if before else due + timedelta(days=1))
            assert delay != 1 or before
            scenario = "partial_" + scenario + ("_before_due" if before else "_after_due")
        assert loan["planned_scenario"] == scenario

    sold = set()
    for sale in dataset["sales"]:
        entity(sale, "sale_id")
        assert sale["loan_id"] in loans and sale["loan_id"] not in sold
        sold.add(sale["loan_id"])
        loan = loans[sale["loan_id"]]
        assert sale["kind"] == "credit" and sale["client_id"] == loan["client_id"]
        assert sale["phase"] == loan["phase"] and sale["amount"] == loan["amount"]
        assert datetime.fromisoformat(sale["at"]) == datetime.fromisoformat(
            loan["evaluated_at"]
        ) + timedelta(minutes=1)
        assert datetime.fromisoformat(sale["at"]) <= cutoff
    assert sold == loans.keys()

    visits = {client_id: [] for client_id in clients}
    attempts_by_week = {}
    granted = {}
    previous_at = None
    for attempt in dataset["attempts"]:
        entity(attempt, "attempt_id")
        client = clients[attempt["client_id"]]
        at = datetime.fromisoformat(attempt["evaluated_at"])
        assert datetime.combine(first_day, time.min) <= at <= cutoff
        assert at.time() == time(9)
        assert previous_at is None or previous_at <= at
        previous_at = at
        times = visits[client["client_id"]]
        assert not times or times[-1].date() != at.date()
        times.append(at)
        assert date.fromisoformat(client["registered_on"]) <= at.date()
        phase = "warmup" if at.date() < study_start else "study"
        assert attempt["phase"] == phase
        monday = at.date() - timedelta(days=at.weekday())
        assert attempt["week_start"] == monday.isoformat()
        attempts_by_week.setdefault(monday, []).append(attempt)
        amount = currency(attempt["requested_amount"])
        assert Decimal("5") <= amount <= Decimal("50")
        pending = sum(
            (
                currency(prior["amount"])
                - sum(
                    (
                        currency(p["amount"])
                        for p in prior["payments"]
                        if datetime.fromisoformat(p["at"]) < at
                    ),
                    Decimal(0),
                )
                for prior in dataset["loans"]
                if prior["client_id"] == client["client_id"]
                and datetime.fromisoformat(prior["evaluated_at"]) < at
            ),
            Decimal(0),
        )
        features = _snapshot(client, dataset["loans"], dataset["sales"], at, amount)
        available = cap - money(features["outstanding"])
        expected = (
            "pending_balance_not_fully_settled"
            if pending > 0
            else "insufficient_available_exposure"
            if amount > available
            else None
        )
        assert type(attempt["granted"]) is bool and type(attempt["repeat_visit"]) is bool
        assert attempt["granted"] == (expected is None)
        assert attempt["refusal_reason"] == expected
        assert pending == 0 or not attempt["granted"]
        if expected:
            assert attempt["loan_id"] is None
        else:
            assert amount <= available
            loan = loans[attempt["loan_id"]]
            assert attempt["loan_id"] not in granted
            granted[attempt["loan_id"]] = attempt
            assert loan["client_id"] == client["client_id"]
            assert loan["evaluated_at"] == attempt["evaluated_at"]
            assert loan["phase"] == phase
            assert currency(loan["amount"]) == amount
            assert loan["authorization_tags"] == _authorization(features)
    assert granted.keys() == loans.keys()

    request_gaps = []
    for client_id, times in visits.items():
        assert times
        age = (times[0].date() - date.fromisoformat(clients[client_id]["registered_on"])).days
        assert (
            simulation["registration_age_range_days"][0]
            <= age
            <= simulation["registration_age_range_days"][1]
        )
        request_gaps.extend(
            (b.date() - a.date()).days for a, b in zip(times, times[1:], strict=False)
        )
    assert all(3 <= gap <= 14 for gap in request_gaps)
    weekly_stats = []
    for week in range((cutoff.date() - first_day).days // 7 + 1):
        monday = first_day + timedelta(weeks=week)
        attempts = attempts_by_week.get(monday, [])
        full = monday + timedelta(days=6) <= cutoff.date()
        for (group, member), client_id in groups.items():
            scheduled = [a for a in attempts if a["client_id"] == client_id]
            if group == week % 4:
                assert not scheduled
                continue
            repeat = group == (week + 1) % 4
            assert len(scheduled) <= (2 if repeat else 1)
            if full:
                assert len(scheduled) == (2 if repeat else 1)
            if scheduled:
                day = (date.fromisoformat(scheduled[0]["evaluated_at"][:10]) - monday).days
                assert member <= day <= 3 and not scheduled[0]["repeat_visit"]
                if len(scheduled) == 2:
                    assert repeat and scheduled[1]["repeat_visit"]
                    assert (
                        date.fromisoformat(scheduled[1]["evaluated_at"][:10]) - monday
                    ).days == day + 3
                elif repeat and monday + timedelta(days=day + 3) <= cutoff.date():
                    raise AssertionError("Missing scheduled repeat visit")
            elif monday + timedelta(days=3) <= cutoff.date():
                raise AssertionError("Missing scheduled visit")
        if full:
            assert len(attempts) == 12 and len({a["client_id"] for a in attempts}) == 9
        if full and monday >= study_start:
            approved = [a for a in attempts if a["granted"]]
            weekly_stats.append(
                {
                    "week_start": monday.isoformat(),
                    "requests": len(attempts),
                    "request_clients": len({a["client_id"] for a in attempts}),
                    "grants": len(approved),
                    "grant_clients": len({a["client_id"] for a in approved}),
                }
            )
    assert len(weekly_stats) == simulation["study_full_weeks"]

    pending_violations = 0
    for loan in dataset["loans"]:
        row, client = rows[loan["loan_id"]], clients[loan["client_id"]]
        assert set(row) == ROW_KEYS
        assert row["origen"] == "simulado" and row["replica_id"] == prefix
        for key in ("client_id", "loan_id", "evaluated_at", "due_date", "phase"):
            assert row[key] == loan[key]
        assert row["observed_on"] == dataset["observed_on"]
        assert row["requested_amount"] == loan["amount"] and row["credit_cap"] == str(cap)
        at = datetime.fromisoformat(loan["evaluated_at"])
        due = date.fromisoformat(loan["due_date"])
        if _pending_balance(dataset["loans"], loan["client_id"], at) > 0:
            pending_violations += 1
        assert due == at.date() + timedelta(days=1)
        for payment in loan["planned_payments"]:
            when = datetime.fromisoformat(payment["at"])
            assert any(start <= when.time() <= end for start, end in PAYMENT_WINDOWS)
        visible_loans = [
            {
                **prior,
                "payments": [p for p in prior["payments"] if datetime.fromisoformat(p["at"]) < at],
            }
            for prior in dataset["loans"]
        ]
        expected = snapshot(client, visible_loans, dataset["sales"], at, money(loan["amount"]))
        for name in FEATURE_NAMES:
            assert type(row[name]) in (int, float) and isfinite(row[name])
            assert abs(row[name] - expected[name]) < 1e-9
        # Labels use only observed events, independently of planned scenarios and _outcome.
        balance = currency(loan["amount"]) - sum(
            (currency(p["amount"]) for p in loan["payments"]), Decimal(0)
        )
        label = None
        scenario = "unresolved" if balance == currency(loan["amount"]) else "partial_unresolved"
        if balance == 0:
            last_at = max(datetime.fromisoformat(p["at"]) for p in loan["payments"])
            label = int(last_at > datetime.combine(due, time(20)))
            scenario = "late" if label else "on_time"
            if len(loan["payments"]) == 2:
                before = datetime.fromisoformat(loan["payments"][0]["at"]).date() <= due
                scenario = "partial_" + scenario + ("_before_due" if before else "_after_due")
        elif cutoff > datetime.combine(due, time(20)):
            label = 1
        assert currency(row["pending_at_cutoff"]) == balance
        assert row[TARGET_NAME] is None or type(row[TARGET_NAME]) is int
        assert row[TARGET_NAME] == label and row["scenario"] == scenario
    assert pending_violations == 0

    study = [r for r in dataset["rows"] if r["phase"] == "study"]
    counts = Counter(str(r[TARGET_NAME]) for r in study)
    counts = {key: counts[key] for key in ("0", "1", "None")}
    known, minority = counts["0"] + counts["1"], min(counts["0"], counts["1"])
    avg_grants = mean(w["grants"] for w in weekly_stats)
    avg_clients = mean(w["grant_clients"] for w in weekly_stats)

    def summary(values: list) -> dict:
        return {
            "count": len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": mean(values) if values else None,
        }

    return {
        "policy_version": POLICY_VERSION,
        "pending_policy_pass": True,
        "source_review_completed_on_sample": True,
        "source_review_scope": "23 intentional V5 sample classifications; not approval of V6 rows",
        "source_review_classifications": dict(
            Counter(
                item["response"]
                for section in ("fiados", "rejections", "weeks", "assumptions")
                for item in review["sample"][section]
            )
        ),
        "source_review_file_sha256": REVIEW_SHA256,
        "pending_grants": pending_violations,
        "hard_constraints_pass": True,
        "coherence_accepted": False,
        "coherence_status": (
            "Owner reviewed an intentional sample; global synthetic validation remains bounded"
        ),
        "clients": 12,
        "requests": len(dataset["attempts"]),
        "all_loans": len(loans),
        "warmup_loans": len(loans) - len(study),
        "study_loans": len(study),
        "study_label_counts": counts,
        "weekly_stats": weekly_stats,
        "mean_weekly_study_requests": mean(w["requests"] for w in weekly_stats),
        "mean_weekly_study_request_clients": mean(w["request_clients"] for w in weekly_stats),
        "mean_weekly_study_grants": avg_grants,
        "mean_weekly_study_grant_clients": avg_clients,
        "legacy_grant_scale_flag": bool(
            anchors["approximate_loans_per_week"] * 0.75
            <= avg_grants
            <= anchors["approximate_loans_per_week"] * 1.25
            and abs(avg_clients - anchors["approximate_distinct_clients_per_week"]) <= 2
        ),
        "amount_summary": {
            "requested": summary(
                [float(money(a["requested_amount"])) for a in dataset["attempts"]]
            ),
            "granted": summary([float(money(loan["amount"])) for loan in dataset["loans"]]),
        },
        "amount_precision_counts": dict(
            Counter(
                "whole_or_half" if money(loan["amount"]) % Decimal("0.50") == 0 else "exact_cents"
                for loan in dataset["loans"]
            )
        ),
        "observed_payment_time_frequencies": dict(
            sorted(
                Counter(p["at"][11:] for loan in dataset["loans"] for p in loan["payments"]).items()
            )
        ),
        "request_return_intervals_days": summary(request_gaps),
        "source_vs_assumptions": {
            "original_declaration": deepcopy(anchors),
            "latest_review": deepcopy(review),
            "base_simulation_assumptions": deepcopy(simulation),
            "calibration": calibration,
            "client_pool_interpretation": "12-client example roster, not a real fixed population",
            "weekly_variation": "12/9 is a usual approximate reference; lower activity is possible",
            "amount_precision": "Rildo permits whole/.50 amounts and exact product-price totals",
            "pending_balance_policy": PENDING_POLICY,
            "due_cutoff": (
                "TEAM ASSUMPTION: 20:00 America/Lima; exact hard cutoff not owner-confirmed"
            ),
            "amount_probability": (
                "TEAM ASSUMPTION: 0.75 rounded / 0.25 exact-price scenario; "
                "not measured frequencies"
            ),
        },
        "adequacy": {
            "n_study": len(study),
            "known_study_labels": known,
            "minority_class_count": minority,
            "adequate": known >= 200 and minority >= 30,
            "policy": "Descriptive only; never reseed, force labels or approvals",
        },
    }
