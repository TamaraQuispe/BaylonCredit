"""V5 fictional data revision only, not model approval or production policy.

The event loop and contract audit are intentionally independent of frozen V4:
its abono exception is historical evidence, not the later settlement rule.
Only pure calendar/distribution/outcome helpers are reused; no global mutation.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
from math import isfinite
from random import Random
from statistics import mean

from app.ml.features import FEATURE_NAMES
from app.ml.outcomes import TARGET_NAME
from app.ml.owner_aligned_synthetic import SOURCE_SHA256, _calendar, _outcome, _truncated
from app.ml.synthetic import money, snapshot

POLICY_VERSION = "academic-owner-settled-v5-data"
CLARIFICATION_SHA256 = "63e0e57052fa31a93de3710a8bba69fadef95f0cb97e9de452fe7d281082ad7f"
PROTOCOL_SHA256 = "5892958972ca96764d100d9833ab970f66c5214ad2f274f42b7b42c43ccf20c1"
SETTLED_POLICY = (
    "Reject new credit whenever any overdue principal remains; prior partial payments or "
    "agreements do not authorize another grant. Resume evaluation only after full settlement "
    "is observed. Never accelerate or invent payments to increase grants."
)
# Exact semantic source, including types and verbatim relay, independent of runtime files.
_CLARIFICATION = {
    "version": "owner-settlement-clarification-1",
    "source_status": "owner_response_relayed_by_user_in_current_conversation",
    "base_source_docx_sha256": SOURCE_SHA256,
    "declared_consultation_date": None,
    "user_messages_verbatim": [
        "que pague en el momento y hasta que pague no se vuelve a fiar, eso ha dicho",
        "los 30 completos dice",
    ],
    "scenario": {
        "initial_debt_pen": 40,
        "prior_payment_pen": 10,
        "overdue_remaining_pen": 30,
        "required_payment_before_new_credit_pen": 30,
    },
    "rule": {
        "applies_to": "overdue debt at the time of evaluating a new credit request",
        "new_credit_while_overdue_balance_positive": False,
        "partial_payment_restores_eligibility": False,
        "payment_agreement_alone_restores_eligibility": False,
        "required_condition": (
            "All overdue remaining principal must be fully settled and the payment observed "
            "before a subsequent credit evaluation"
        ),
        "after_settlement": (
            "The overdue-debt block is removed; other limits and owner review still apply, "
            "never automatic approval"
        ),
        "not_yet_due_debt": (
            "Not resolved by this overdue scenario; do not extend this clarification "
            "to all current debt"
        ),
        "target_and_grace": (
            "No change to contractual next-day lateness labels or separate commercial grace"
        ),
    },
    "precedence": (
        "For overdue eligibility, this later clarification supersedes the earlier "
        "abono-or-agreement alternative. Preserve the original declaration and frozen "
        "V4 bytes as historical evidence."
    ),
    "not_business_model_approval": True,
    "not_customer_consent": True,
    "not_a_training_dataset": True,
    "privacy": (
        "Aggregate fictional example and user-relayed rule only; no owner form, signatures "
        "or customer identities"
    ),
}
DATA_KEYS = set(
    (
        "seed prefix replica_id origen observed_on clients loans sales attempts rows "
        "policy_version calibration"
    ).split()
)
ROW_KEYS = (
    set(FEATURE_NAMES)
    | {TARGET_NAME}
    | set(
        (
            "phase replica_id origen requested_amount credit_cap client_id loan_id evaluated_at "
            "due_date observed_on pending_at_cutoff scenario"
        ).split()
    )
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
    "payment_id": "payment_id replica_id origen at amount",
    "sale_id": "sale_id loan_id client_id replica_id origen phase at kind amount",
}


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _calibration(anchors: dict, simulation: dict, clarification: dict) -> dict:
    if type(clarification) is not dict or _canonical(clarification) != _canonical(_CLARIFICATION):
        raise ValueError("Expected the exact user-relayed settlement clarification and types")
    return {
        "version": POLICY_VERSION,
        "base_source_docx_sha256": SOURCE_SHA256,
        "clarification_file_sha256": CLARIFICATION_SHA256,
        "clarification_semantic_sha256": sha256(_canonical(clarification).encode()).hexdigest(),
        "data_protocol_sha256": PROTOCOL_SHA256,
        "base_anchors": deepcopy(anchors),
        "base_simulation": deepcopy(simulation),
        "effective_overdue_policy": SETTLED_POLICY,
        "payment_visibility": "strictly_before_evaluation; cutoff_inclusive",
    }


def _overdue_balance(loans: list[dict], client_id: str, at: datetime) -> Decimal:
    # The shared snapshot includes payments at <= at. Eligibility is stricter:
    # simultaneous payments have no event ordering and cannot clear the block.
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
            if loan["client_id"] == client_id
            and datetime.fromisoformat(loan["evaluated_at"]) < at
            and date.fromisoformat(loan["due_date"]) < at.date()
        ),
        Decimal(0),
    )


def _refusal(
    client: dict, loans: list[dict], sales: list[dict], at: datetime, amount: Decimal
) -> str | None:
    if _overdue_balance(loans, client["client_id"], at) > 0:
        return "overdue_balance_not_fully_settled"
    features = snapshot(client, loans, sales, at, amount)
    if money(features["outstanding"]) + amount > money(client["credit_cap"]):
        return "insufficient_available_exposure"
    return None


def _authorization(features: dict) -> list[str]:
    if features["paid_credits"] == 0:
        return ["simulated_identity_reference", "simulated_owner_review"]
    return ["simulated_regular_grant"]


def generate_owner_settled_dataset(
    anchors: dict, simulation: dict, clarification: dict, seed: int, prefix: str
) -> dict:
    """Generate one fictional replica, without fitting, reseeding or saving cohorts."""
    first_day, study_start, cutoff = _calendar(anchors, simulation)
    calibration = _calibration(anchors, simulation, clarification)
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
        amount = money(
            _truncated(
                rng,
                anchors["typical_amount_estimate_pen"],
                simulation["amount_log_sigma"],
                low,
                high,
            )
        )
        features = snapshot(client, loans, sales, at, amount)
        available = cap - money(features["outstanding"])
        if available >= low:
            amount = min(amount, available)
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
        features = snapshot(client, loans, sales, at, amount)
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
        final_at = datetime.combine(due + timedelta(days=delay), time(14))
        plan = [(final_at, amount)]
        scenario = "late" if late else "on_time"
        if partial:
            before = (
                not late or rng.random() < simulation["partial_before_due_probability_when_late"]
            )
            before = before or delay == 1
            first_at = (
                at + timedelta(hours=3)
                if before
                else datetime.combine(due + timedelta(days=1), time(9))
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
    validate_owner_settled_dataset(dataset, anchors, simulation, clarification)
    return dataset


def validate_owner_settled_dataset(
    dataset: dict, anchors: dict, simulation: dict, clarification: dict
) -> dict:
    """Independently recompute events, eligibility, features and labels; never fit.

    Invalid source inputs raise ValueError; dataset violations raise AssertionError.
    Scale/adequacy are descriptive, never source-coherence acceptance.
    """
    first_day, study_start, cutoff = _calendar(anchors, simulation)
    calibration = _calibration(anchors, simulation, clarification)
    assert set(dataset) == DATA_KEYS
    assert dataset["policy_version"] == POLICY_VERSION
    assert _canonical(dataset["calibration"]) == _canonical(calibration)
    prefix = dataset["prefix"]
    assert isinstance(prefix, str) and prefix.strip() and type(dataset["seed"]) is int
    assert dataset["replica_id"] == prefix and dataset["origen"] == "simulado"
    assert dataset["observed_on"] == cutoff.date().isoformat()
    assert all(
        type(dataset[key]) is list for key in ("clients", "loans", "sales", "attempts", "rows")
    )
    clients = {c["client_id"]: c for c in dataset["clients"]}
    loans = {loan["loan_id"]: loan for loan in dataset["loans"]}
    rows = {r["loan_id"]: r for r in dataset["rows"]}
    assert len(clients) == len(dataset["clients"]) == 12
    assert len(loans) == len(dataset["loans"]) == len(rows) == len(dataset["rows"])
    assert loans.keys() == rows.keys()
    low, high = anchors["loan_amount_range_pen"]
    assert (low, high, anchors["client_cap_pen"], anchors["contract_term_days"]) == (5, 50, 80, 1)
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

    # Validate atomic observed payments before any eligibility reconstruction.
    for loan in dataset["loans"]:
        entity(loan, "loan_id")
        assert loan["client_id"] in clients
        at = datetime.fromisoformat(loan["evaluated_at"])
        due = date.fromisoformat(loan["due_date"])
        amount = currency(loan["amount"])
        assert low <= amount <= high and due == at.date() + timedelta(days=1)
        plan = loan["planned_payments"]
        assert type(plan) is list and len(plan) in (1, 2)
        assert type(loan["payments"]) is list
        total, previous = Decimal(0), at
        for payment in plan:
            entity(payment, "payment_id")
            when, value = datetime.fromisoformat(payment["at"]), currency(payment["amount"])
            assert when > previous and value > 0
            if when.date() <= due:
                assert when >= at + timedelta(hours=3) and when.time() <= time(20)
            total += value
            assert total <= amount
            previous = when
        assert total == amount
        assert _canonical(loan["payments"]) == _canonical(
            [p for p in plan if datetime.fromisoformat(p["at"]) <= cutoff]
        )
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
            assert before or first.date() == due + timedelta(days=1)
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
        sale_at = datetime.fromisoformat(sale["at"])
        assert datetime.fromisoformat(loan["evaluated_at"]) < sale_at <= cutoff
        assert sale_at.date() == date.fromisoformat(loan["evaluated_at"][:10])
    assert sold == loans.keys()

    visits = {client_id: [] for client_id in clients}
    attempts_by_week, granted = {}, {}
    previous_at = None
    for attempt in dataset["attempts"]:
        entity(attempt, "attempt_id")
        assert attempt["client_id"] in clients
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
        assert low <= amount <= high
        expected = snapshot(client, dataset["loans"], dataset["sales"], at, amount)
        # Reconstruct the stricter rule independently of the generator decision.
        blocked = any(
            prior["client_id"] == client["client_id"]
            and datetime.fromisoformat(prior["evaluated_at"]) < at
            and date.fromisoformat(prior["due_date"]) < at.date()
            and currency(prior["amount"])
            > sum(
                (
                    currency(p["amount"])
                    for p in prior["payments"]
                    if datetime.fromisoformat(p["at"]) < at
                ),
                Decimal(0),
            )
            for prior in dataset["loans"]
        )
        assert not (attempt["granted"] is True and blocked), "Overdue principal blocks every grant"
        refusal = (
            "overdue_balance_not_fully_settled"
            if blocked
            else "insufficient_available_exposure"
            if money(expected["outstanding"]) + amount > cap
            else None
        )
        assert type(attempt["granted"]) is bool and attempt["granted"] == (refusal is None)
        assert attempt["refusal_reason"] == refusal and type(attempt["repeat_visit"]) is bool
        if refusal:
            assert attempt["loan_id"] is None
            continue
        loan_id = attempt["loan_id"]
        assert loan_id in loans and loan_id not in granted
        granted[loan_id] = attempt
        loan, row = loans[loan_id], rows[loan_id]
        assert loan["client_id"] == client["client_id"]
        assert loan["evaluated_at"] == attempt["evaluated_at"]
        assert loan["phase"] == phase and currency(loan["amount"]) == amount
        assert loan["authorization_tags"] == _authorization(expected)
        assert set(row) == ROW_KEYS
        assert row["origen"] == "simulado" and row["replica_id"] == prefix
        for key in ("client_id", "loan_id", "evaluated_at", "due_date", "phase"):
            assert row[key] == loan[key]
        assert row["observed_on"] == dataset["observed_on"]
        assert row["requested_amount"] == loan["amount"] and row["credit_cap"] == str(cap)
        for name in FEATURE_NAMES:
            assert type(row[name]) in (int, float) and isfinite(row[name])
            assert abs(row[name] - expected[name]) < 1e-9
        balance, label, scenario = _outcome(loan, cutoff)
        assert currency(row["pending_at_cutoff"]) == balance
        assert row[TARGET_NAME] is None or type(row[TARGET_NAME]) is int
        assert row[TARGET_NAME] == label and row["scenario"] == scenario
    assert granted.keys() == loans.keys()

    request_gaps, grant_gaps = [], []
    for client_id, times in visits.items():
        if times:
            age = (times[0].date() - date.fromisoformat(clients[client_id]["registered_on"])).days
            assert (
                simulation["registration_age_range_days"][0]
                <= age
                <= simulation["registration_age_range_days"][1]
            )
        request_gaps.extend(
            (b.date() - a.date()).days for a, b in zip(times, times[1:], strict=False)
        )
        credit_times = sorted(
            datetime.fromisoformat(a["evaluated_at"])
            for a in granted.values()
            if a["client_id"] == client_id
        )
        grant_gaps.extend(
            (b.date() - a.date()).days for a, b in zip(credit_times, credit_times[1:], strict=False)
        )
    assert all(3 <= gap <= 14 for gap in request_gaps)
    weekly_stats = []
    for week in range((cutoff.date() - first_day).days // 7 + 1):
        monday = first_day + timedelta(weeks=week)
        attempts = attempts_by_week.get(monday, [])
        full_week = monday + timedelta(days=6) <= cutoff.date()
        for (group, member), client_id in groups.items():
            scheduled = [a for a in attempts if a["client_id"] == client_id]
            if group == week % 4:
                assert not scheduled
                continue
            repeat = group == (week + 1) % 4
            if full_week:
                assert len(scheduled) == (2 if repeat else 1)
            else:
                assert len(scheduled) <= (2 if repeat else 1)
                if (cutoff.date() - monday).days >= 3:
                    assert scheduled
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
        if full_week:
            assert len(attempts) == 12 and len({a["client_id"] for a in attempts}) == 9
        if full_week and monday >= study_start:
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
    study = [r for r in dataset["rows"] if r["phase"] == "study"]
    counts = Counter(str(r[TARGET_NAME]) for r in study)
    counts = {key: counts[key] for key in ("0", "1", "None")}
    known, minority = counts["0"] + counts["1"], min(counts["0"], counts["1"])
    avg_grants = mean(w["grants"] for w in weekly_stats) if weekly_stats else None
    avg_clients = mean(w["grant_clients"] for w in weekly_stats) if weekly_stats else None

    def summary(values: list) -> dict:
        return {
            "count": len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": mean(values) if values else None,
        }

    return {
        "policy_version": POLICY_VERSION,
        "settlement_policy_pass": True,
        "hard_constraints_pass": True,
        "coherence_accepted": False,
        "coherence_status": "Pending broader source-coherence audit; no model authorization",
        "clients": len(clients),
        "requests": len(dataset["attempts"]),
        "all_loans": len(loans),
        "warmup_loans": len(loans) - len(study),
        "study_loans": len(study),
        "payments": sum(len(loan["payments"]) for loan in dataset["loans"]),
        "study_label_counts": counts,
        "weekly_stats": weekly_stats,
        "mean_weekly_study_requests": mean(w["requests"] for w in weekly_stats)
        if weekly_stats
        else None,
        "mean_weekly_study_request_clients": mean(w["request_clients"] for w in weekly_stats)
        if weekly_stats
        else None,
        "mean_weekly_study_grants": avg_grants,
        "mean_weekly_study_grant_clients": avg_clients,
        "legacy_grant_scale_flag": bool(
            avg_grants is not None
            and anchors["approximate_loans_per_week"] * 0.75
            <= avg_grants
            <= anchors["approximate_loans_per_week"] * 1.25
            and abs(avg_clients - anchors["approximate_distinct_clients_per_week"]) <= 2
        ),
        "amount_summary": {
            "requested": summary(
                [float(currency(a["requested_amount"])) for a in dataset["attempts"]]
            ),
            "granted": summary([float(currency(loan["amount"])) for loan in dataset["loans"]]),
        },
        "request_return_intervals_days": summary(request_gaps),
        "granted_credit_intervals_days": summary(grant_gaps),
        "source_vs_assumptions": {
            "original_declaration": deepcopy(anchors),
            "latest_clarification": deepcopy(clarification),
            "calibration": calibration,
            "base_simulation_assumptions": deepcopy(simulation),
            "effective_overdue_policy": SETTLED_POLICY,
            "precedence_scope": (
                "Only overdue eligibility superseded; no customer consent or model approval"
            ),
            "source_units": {
                "weekly_loans": "granted credits",
                "weekly_clients": "distinct grant recipients",
                "return_days": "request returns",
                "schedule": "assumption, not measured requests",
            },
        },
        "adequacy": {
            "n_study": len(study),
            "known_study_labels": known,
            "minority_class_count": minority,
            "adequate": known >= 200 and minority >= 30,
            "policy": "Descriptive only; never reseed, force labels or approvals",
        },
    }
