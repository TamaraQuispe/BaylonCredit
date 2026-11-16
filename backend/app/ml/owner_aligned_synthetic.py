"""Owner-aligned V4 fictional histories, not training or business approval.

Inputs are the current Rildo anchors and the saved protocol's ``simulation``
object. Planned payments are simulation metadata; only observed events enter
snapshots and outcomes. No model, service, or experiment runner is called here.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from math import isfinite, log
from random import Random
from statistics import mean

from app.ml.features import FEATURE_NAMES
from app.ml.outcomes import TARGET_NAME, classify_credit_outcome
from app.ml.synthetic import money, remaining, snapshot

SOURCE_SHA256 = "45bc22a10ad5dccf323708b8aeabb780d8de4629ff5087cca2582c7dd055819f"
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
}
ROW_KEYS = {
    *FEATURE_NAMES,
    TARGET_NAME,
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


def _calendar(anchors: dict, simulation: dict) -> tuple[date, date, datetime]:
    if anchors.get("source_docx_sha256") != SOURCE_SHA256:
        raise ValueError("Only the current Rildo declaration is an allowed source")
    if anchors.get("version") != "owner-anchors-v4":
        raise ValueError("Expected owner-anchors-v4")
    if simulation["population_clients_per_replica"] != 12:
        raise ValueError("The rotating schedule requires the declared 12-client assumption")
    warmup = simulation["warmup_weeks"]
    full = simulation["study_full_weeks"]
    trailing = simulation["study_trailing_days"]
    if not all(type(n) is int for n in (warmup, full, trailing)):
        raise ValueError("Calendar lengths must be integers")
    if warmup < 0 or full < 0 or not 0 <= trailing < 7 or full * 7 + trailing == 0:
        raise ValueError("Invalid warmup/study length")
    start = date.fromisoformat(simulation["study_start"])
    end = date.fromisoformat(simulation["observed_on"])
    if start.weekday() != 0 or end != start + timedelta(days=7 * full + trailing - 1):
        raise ValueError("Study must start Monday and end at the configured observation date")
    return start - timedelta(weeks=warmup), start, datetime.combine(end, time.max)


def _truncated(rng: Random, location: float, sigma: float, low: float, high: float) -> float:
    while True:
        value = rng.lognormvariate(log(location), sigma)
        if low <= value <= high:
            return value


def _overdue(loans: list[dict], client_id: str, at: datetime) -> list[dict]:
    return [
        loan
        for loan in loans
        if loan["client_id"] == client_id
        and datetime.fromisoformat(loan["evaluated_at"]) < at
        and date.fromisoformat(loan["due_date"]) < at.date()
        and remaining(loan, at) > 0
    ]


def _has_abono(loan: dict, at: datetime) -> bool:
    return any(
        money(payment["amount"]) > 0
        and date.fromisoformat(loan["due_date"]) < date.fromisoformat(payment["at"][:10])
        and datetime.fromisoformat(payment["at"]) < at
        for payment in loan["payments"]
    )


def _authorization(features: dict) -> list[str]:
    if features["paid_credits"] == 0:
        return ["simulated_identity_reference", "simulated_owner_review"]
    if features["pending_overdue"]:
        return ["simulated_owner_review"]
    return ["simulated_regular_grant"]


def _outcome(loan: dict, cutoff: datetime) -> tuple[Decimal, int | None, str]:
    # Ignore plans, propensity, scenario and any scoring system when deriving labels.
    balance = remaining(loan, cutoff)
    label = classify_credit_outcome(
        pending_amount=balance,
        due_date=date.fromisoformat(loan["due_date"]),
        last_payment_date=max(
            (date.fromisoformat(p["at"][:10]) for p in loan["payments"]), default=None
        ),
        observed_on=cutoff.date(),
    )
    scenario = "unresolved" if label is None else "late" if label else "on_time"
    if len(loan["payments"]) == 2 or (loan["payments"] and balance > 0):
        scenario = "partial_" + scenario
    return balance, label, scenario


def generate_owner_aligned_dataset(anchors: dict, simulation: dict, seed: int, prefix: str) -> dict:
    """Generate one independent fictional replica; never retry for scale/adequacy."""
    first_day, study_start, cutoff = _calendar(anchors, simulation)
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
        first_visit = min(
            (at.date() for at, number, _, _ in schedule if number == index),
            default=first_day,
        )
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
        overdue = _overdue(loans, client["client_id"], at)
        refusal = (
            "insufficient_available_exposure"
            if available < low
            else "overdue_without_visible_post_due_abono"
            if not all(_has_abono(loan, at) for loan in overdue)
            else None
        )
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
        partial = rng.random() < (
            anchors["partial_payment_annotations"] / anchors["partial_payment_denominator"]
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
                not late or rng.random() < (simulation["partial_before_due_probability_when_late"])
            )
            # With a one-day delay, the before-due branch avoids a zero-length interval.
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
                "payment_id": f"{loan_id}-P{number}",
                "replica_id": prefix,
                "origen": "simulado",
                "at": when.isoformat(),
                "amount": str(value),
            }
            for number, (when, value) in enumerate(plan, 1)
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
            "payments": [
                dict(payment) for payment in planned if payment["at"] <= cutoff.isoformat()
            ],
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
    }
    validate_owner_aligned_dataset(dataset, anchors, simulation)
    return dataset


def validate_owner_aligned_dataset(dataset: dict, anchors: dict, simulation: dict) -> dict:
    """Raise AssertionError on event/contract violations; return a descriptive audit.

    Grant-scale and sample-adequacy failures are reported, not generation failures.
    The validator does not regenerate histories or consult any planned score.
    """
    first_day, study_start, cutoff = _calendar(anchors, simulation)
    prefix = dataset["prefix"]
    assert set(dataset) == DATA_KEYS
    assert isinstance(prefix, str) and prefix.strip() and type(dataset["seed"]) is int
    assert dataset["replica_id"] == prefix and dataset["origen"] == "simulado"
    assert dataset["observed_on"] == cutoff.date().isoformat()
    clients = {client["client_id"]: client for client in dataset["clients"]}
    loans = {loan["loan_id"]: loan for loan in dataset["loans"]}
    rows = {row["loan_id"]: row for row in dataset["rows"]}
    assert len(clients) == len(dataset["clients"]) == 12
    assert len(loans) == len(dataset["loans"]) == len(rows) == len(dataset["rows"])
    assert loans.keys() == rows.keys()
    low, high = anchors["loan_amount_range_pen"]
    assert (low, high, anchors["client_cap_pen"], anchors["contract_term_days"]) == (5, 50, 80, 1)
    cap = money(anchors["client_cap_pen"])
    ids = set()

    def entity(record: dict, key: str) -> None:
        identifier = record[key]
        assert isinstance(identifier, str) and identifier.startswith(prefix + "-")
        assert identifier not in ids
        ids.add(identifier)
        assert record["origen"] == "simulado" and record["replica_id"] == prefix

    groups = {}
    for client in dataset["clients"]:
        entity(client, "client_id")
        assert client["credit_cap"] == str(cap)
        group, member = client["schedule_group"], client["schedule_member"]
        assert type(group) is int and 0 <= group < 4
        assert type(member) is int and 0 <= member < 3
        assert (group, member) not in groups
        groups[group, member] = client["client_id"]
        assert 0 <= client["latent_lateness_probability"] <= 1

    attempts_by_week = {}
    visits = {client_id: [] for client_id in clients}
    granted = {}
    previous_at = None
    for attempt in dataset["attempts"]:
        entity(attempt, "attempt_id")
        client = clients[attempt["client_id"]]
        at = datetime.fromisoformat(attempt["evaluated_at"])
        assert datetime.combine(first_day, time.min) <= at <= cutoff
        assert at.time() in (time(9), time(14))
        assert previous_at is None or previous_at <= at
        previous_at = at
        times = visits[client["client_id"]]
        assert not times or times[-1].date() != at.date()
        visits[client["client_id"]].append(at)
        assert date.fromisoformat(client["registered_on"]) <= at.date()
        phase = "warmup" if at.date() < study_start else "study"
        assert attempt["phase"] == phase
        monday = at.date() - timedelta(days=at.weekday())
        assert attempt["week_start"] == monday.isoformat()
        attempts_by_week.setdefault(monday, []).append(attempt)
        assert isinstance(attempt["requested_amount"], str)
        amount = money(attempt["requested_amount"])
        assert low <= amount <= high
        expected = snapshot(client, dataset["loans"], dataset["sales"], at, amount)
        available = cap - money(expected["outstanding"])
        overdue = _overdue(dataset["loans"], client["client_id"], at)
        refusal = (
            "insufficient_available_exposure"
            if available < low
            else "overdue_without_visible_post_due_abono"
            if not all(_has_abono(loan, at) for loan in overdue)
            else None
        )
        assert type(attempt["granted"]) is bool and attempt["granted"] == (refusal is None)
        assert attempt["refusal_reason"] == refusal
        assert type(attempt["repeat_visit"]) is bool
        if refusal:
            assert attempt["loan_id"] is None
        else:
            assert amount <= available
            loan_id = attempt["loan_id"]
            assert loan_id not in granted and loan_id in loans
            granted[loan_id] = attempt
            loan = loans[loan_id]
            assert loan["client_id"] == client["client_id"]
            assert loan["evaluated_at"] == attempt["evaluated_at"]
            assert loan["phase"] == phase and money(loan["amount"]) == amount
            assert loan["authorization_tags"] == _authorization(expected)
    assert granted.keys() == loans.keys()

    gaps = []
    for client_id, times in visits.items():
        if times:
            age = (times[0].date() - date.fromisoformat(clients[client_id]["registered_on"])).days
            assert (
                simulation["registration_age_range_days"][0]
                <= age
                <= (simulation["registration_age_range_days"][1])
            )
        gaps.extend((b.date() - a.date()).days for a, b in zip(times, times[1:], strict=False))
    assert all(3 <= gap <= 14 for gap in gaps)

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
                # Even a truncated week includes every primary visit whose entire
                # permissible day window is visible by the cutoff.
                if (cutoff.date() - monday).days >= 3:
                    assert scheduled
            if scheduled:
                primary = scheduled[0]
                day = (date.fromisoformat(primary["evaluated_at"][:10]) - monday).days
                assert member <= day <= 3 and not primary["repeat_visit"]
                if len(scheduled) == 2:
                    assert repeat and scheduled[1]["repeat_visit"]
                    assert (
                        date.fromisoformat(scheduled[1]["evaluated_at"][:10]) - monday
                    ).days == day + 3
                elif repeat and monday + timedelta(days=day + 3) <= cutoff.date():
                    raise AssertionError("Missing scheduled repeat visit")
        if full_week:
            assert len(attempts) == 12
            assert len({a["client_id"] for a in attempts}) == 9
        if full_week and monday >= study_start:
            approved = [a for a in attempts if a["granted"]]
            weekly_stats.append(
                {
                    "week_start": monday.isoformat(),
                    "opportunities": len(attempts),
                    "scheduled_clients": len({a["client_id"] for a in attempts}),
                    "grants": len(approved),
                    "grant_clients": len({a["client_id"] for a in approved}),
                }
            )
    assert len(weekly_stats) == simulation["study_full_weeks"]

    for loan in dataset["loans"]:
        entity(loan, "loan_id")
        client, row = clients[loan["client_id"]], rows[loan["loan_id"]]
        at = datetime.fromisoformat(loan["evaluated_at"])
        due = date.fromisoformat(loan["due_date"])
        amount = money(loan["amount"])
        assert isinstance(loan["amount"], str) and low <= amount <= high
        assert due == at.date() + timedelta(days=1)
        plan = loan["planned_payments"]
        assert len(plan) in (1, 2)
        total, previous = Decimal("0"), at
        for payment in plan:
            entity(payment, "payment_id")
            when, value = datetime.fromisoformat(payment["at"]), money(payment["amount"])
            assert when > at and when >= previous and value > 0
            if when.date() <= due:
                assert when >= at + timedelta(hours=3) and when.time() <= time(20)
            total += value
            assert total <= amount
            previous = when
        assert total == amount
        assert loan["payments"] == [p for p in plan if datetime.fromisoformat(p["at"]) <= cutoff]
        final = datetime.fromisoformat(plan[-1]["at"])
        delay = (final.date() - due).days
        assert (
            delay == 0
            or anchors["late_delay_range_days"][0] <= delay <= (anchors["late_delay_range_days"][1])
        )
        scenario = "late" if delay else "on_time"
        if len(plan) == 2:
            assert money(plan[0]["amount"]) == money(amount / 2)
            first = datetime.fromisoformat(plan[0]["at"])
            before = first.date() <= due
            assert before or first.date() == due + timedelta(days=1)
            assert delay != 1 or before
            scenario = "partial_" + scenario + ("_before_due" if before else "_after_due")
        assert loan["planned_scenario"] == scenario
        assert set(row) == ROW_KEYS
        assert row["origen"] == "simulado" and row["replica_id"] == prefix
        for key in ("client_id", "loan_id", "evaluated_at", "due_date", "phase"):
            assert row[key] == loan[key]
        assert row["observed_on"] == dataset["observed_on"]
        assert row["requested_amount"] == loan["amount"] and row["credit_cap"] == str(cap)
        expected = snapshot(client, dataset["loans"], dataset["sales"], at, amount)
        for name in FEATURE_NAMES:
            assert type(row[name]) in (int, float) and isfinite(row[name])
            assert abs(row[name] - expected[name]) < 1e-9
        assert money(expected["outstanding"]) + amount <= cap
        balance, label, scenario = _outcome(loan, cutoff)
        assert isinstance(row["pending_at_cutoff"], str)
        assert money(row["pending_at_cutoff"]) == balance
        assert row[TARGET_NAME] is None or type(row[TARGET_NAME]) is int
        assert row[TARGET_NAME] == label and row["scenario"] == scenario

    sold = set()
    for sale in dataset["sales"]:
        entity(sale, "sale_id")
        loan = loans[sale["loan_id"]]
        assert sale["loan_id"] not in sold
        sold.add(sale["loan_id"])
        assert sale["kind"] == "credit" and sale["client_id"] == loan["client_id"]
        assert sale["phase"] == loan["phase"] and sale["amount"] == loan["amount"]
        sale_at = datetime.fromisoformat(sale["at"])
        assert datetime.fromisoformat(loan["evaluated_at"]) < sale_at <= cutoff
        assert sale["at"][:10] == loan["evaluated_at"][:10]
        assert date.fromisoformat(sale["at"][:10]) >= date.fromisoformat(
            clients[sale["client_id"]]["registered_on"]
        )
    assert sold == loans.keys()

    study = [row for row in dataset["rows"] if row["phase"] == "study"]
    counts = Counter(str(row[TARGET_NAME]) for row in study)
    counts = {key: counts[key] for key in ("0", "1", "None")}
    known = counts["0"] + counts["1"]
    minority = min(counts["0"], counts["1"])
    avg_grants = mean(w["grants"] for w in weekly_stats) if weekly_stats else None
    avg_clients = mean(w["grant_clients"] for w in weekly_stats) if weekly_stats else None

    def amount_summary(records: list[dict], key: str) -> dict:
        values = [float(money(record[key])) for record in records]
        return {
            "count": len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": mean(values) if values else None,
        }

    return {
        "clients": len(clients),
        "all_loans": len(loans),
        "warmup_loans": len(rows) - len(study),
        "study_loans": len(study),
        "payments": sum(len(loan["payments"]) for loan in dataset["loans"]),
        "study_label_counts": counts,
        "weekly_stats": weekly_stats,
        "mean_weekly_study_grants": avg_grants,
        "mean_weekly_study_grant_clients": avg_clients,
        "grant_scale_pass": bool(
            avg_grants is not None
            and anchors["approximate_loans_per_week"] * 0.75
            <= avg_grants
            <= (anchors["approximate_loans_per_week"] * 1.25)
            and abs(avg_clients - anchors["approximate_distinct_clients_per_week"]) <= 2
        ),
        "hard_constraints_pass": True,
        "amount_summary": {
            "requested": amount_summary(dataset["attempts"], "requested_amount"),
            "granted": amount_summary(dataset["loans"], "amount"),
        },
        "visit_gaps": {
            "count": len(gaps),
            "min_days": min(gaps) if gaps else None,
            "max_days": max(gaps) if gaps else None,
            "mean_days": mean(gaps) if gaps else None,
            "within_3_14": True,
        },
        "source_vs_assumptions": {
            "source_docx_sha256": SOURCE_SHA256,
            "owner_declared": dict(anchors),
            "simulation_assumptions": dict(simulation),
            "excluded_source": "Earlier wholly hypothetical owner form",
            "scope": "Alternative fictional history, not real validation or business approval",
        },
        "adequacy": {
            "n_study": len(study),
            "known_study_labels": known,
            "minority_class_count": minority,
            "n_study_below_200": len(study) < 200,
            "known_study_labels_below_200": known < 200,
            "minority_below_30": minority < 30,
            "adequate": known >= 200 and minority >= 30,
            "policy": "Report only; never reseed, force labels or force approvals",
        },
    }
