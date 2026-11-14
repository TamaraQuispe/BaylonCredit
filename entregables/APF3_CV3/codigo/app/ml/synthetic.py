"""Fictional transaction simulator for academic experiments, never production."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from random import Random

from app.ml.features import FEATURE_NAMES, CreditFeatures
from app.ml.outcomes import TARGET_NAME, classify_credit_outcome

PROFILES = ("puntual", "mixto", "atrasos_frecuentes", "abonos", "dificultad_temporal", "nuevo")
SCENARIOS = (
    "anticipado",
    "puntual",
    "abonos_puntuales",
    "atraso_corto",
    "atraso_largo",
    "abonos_tardios",
    "sin_pago",
    "abono_incompleto",
)
OBSERVED_ON = date(2026, 10, 31)


def money(value: float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def remaining(loan: dict, at: datetime) -> Decimal:
    return money(loan["amount"]) - sum(
        (
            money(payment["amount"])
            for payment in loan["payments"]
            if datetime.fromisoformat(payment["at"]) <= at
        ),
        Decimal("0"),
    )


def snapshot(
    client: dict, loans: list[dict], sales: list[dict], at: datetime, amount: Decimal
) -> dict:
    previous = [
        loan
        for loan in loans
        if loan["client_id"] == client["client_id"]
        and datetime.fromisoformat(loan["evaluated_at"]) < at
    ]
    paid = [loan for loan in previous if remaining(loan, at) == 0]
    active = [loan for loan in previous if remaining(loan, at) > 0]
    late = sum(
        any(
            date.fromisoformat(p["at"][:10]) > date.fromisoformat(loan["due_date"])
            and datetime.fromisoformat(p["at"]) <= at
            for p in loan["payments"]
        )
        for loan in paid
    )
    overdue = sum(date.fromisoformat(loan["due_date"]) < at.date() for loan in active)
    features = CreditFeatures(
        completed_sales=sum(
            s["client_id"] == client["client_id"] and datetime.fromisoformat(s["at"]) < at
            for s in sales
        ),
        paid_credits=len(paid),
        paid_late=late,
        pending_overdue=overdue,
        pending_current=len(active) - overdue,
        outstanding=sum((remaining(loan, at) for loan in active), Decimal("0")),
        requested_amount=amount,
        max_credit_amount=Decimal(client["credit_cap"]),
        tenure_days=(at.date() - date.fromisoformat(client["registered_on"])).days,
    )
    return dict(zip(FEATURE_NAMES, features.vector(), strict=True))


def generate_academic_dataset(n_clients: int = 180, seed: int = 20261028) -> dict:
    if n_clients < 30:
        raise ValueError("Use at least 30 fictional clients for a three-way grouped split")
    rng = Random(seed)
    split_ids = list(range(n_clients))
    rng.shuffle(split_ids)
    train_end, validation_end = int(n_clients * 0.6), int(n_clients * 0.8)
    split = {
        index: "train" if rank < train_end else "validation" if rank < validation_end else "test"
        for rank, index in enumerate(split_ids)
    }
    clients, loans, sales, rows = [], [], [], []
    cutoff = datetime.combine(OBSERVED_ON, time.max)
    for index in range(n_clients):
        profile = PROFILES[index % len(PROFILES)]
        at = datetime(2026, 9, 1, 9) + timedelta(days=rng.randint(0, 12))
        if profile == "nuevo":
            at = datetime.combine(OBSERVED_ON, time(9))
        client = {
            "client_id": f"SYN-C{index + 1:04}",
            "data_source": "synthetic",
            "profile": profile,
            "split": split[index],
            "registered_on": (
                at.date() - timedelta(days=0 if profile == "nuevo" else rng.randint(0, 120))
            ).isoformat(),
            "credit_cap": "200.00",
        }
        clients.append(client)
        for offset in range(0 if profile == "nuevo" else rng.randint(0, 8)):
            sale_at = max(
                at - timedelta(days=offset + 1),
                datetime.combine(date.fromisoformat(client["registered_on"]), time(8)),
            )
            sales.append(
                {"client_id": client["client_id"], "at": sale_at.isoformat(), "kind": "cash"}
            )
        # Hidden simulated behaviour influences payment schedules, not a score-derived label.
        propensity = (
            rng.uniform(0.02, 0.12)
            if profile == "puntual"
            else rng.uniform(0.55, 0.8)
            if profile == "atrasos_frecuentes"
            else rng.uniform(0.12, 0.4)
        )
        count = 1 if profile == "nuevo" else rng.randint(8, 13)
        for number in range(count):
            if at > cutoff:
                break
            amount = money(min(200, max(10, rng.lognormvariate(3.85, 0.55))))
            features = snapshot(client, loans, sales, at, amount)
            if features["paid_credits"] == 0:
                amount = min(amount, Decimal("50"))
            available = Decimal(client["credit_cap"]) - money(features["outstanding"])
            if available < Decimal("10"):
                at += timedelta(days=rng.randint(1, 5))
                continue
            amount = min(amount, available)
            features = snapshot(client, loans, sales, at, amount)
            stress = profile == "dificultad_temporal" and number in {3, 4, 5}
            probability = min(
                0.88,
                propensity
                + (0.3 if stress else 0)
                + min(0.18, features["utilization"] * 0.06)
                + (0.08 if amount > 120 else 0),
            )
            if rng.random() < probability:
                scenario = rng.choices(SCENARIOS[3:], weights=[40, 20, 25, 8, 7])[0]
            else:
                scenario = (
                    "abonos_puntuales"
                    if profile == "abonos" and rng.random() < 0.8
                    else rng.choices(SCENARIOS[:3], weights=[15, 60, 25])[0]
                )
            due = at.date() + timedelta(days=1)
            due_at = datetime.combine(due, time(12))
            events = []

            def pay(when: datetime, value: Decimal, events: list = events) -> None:
                if when <= cutoff:
                    events.append({"at": when.isoformat(), "amount": str(value)})

            half = money(amount / 2)
            if scenario == "anticipado":
                pay(at + timedelta(hours=3), amount)
            elif scenario == "puntual":
                pay(due_at, amount)
            elif scenario == "abonos_puntuales":
                pay(at + timedelta(hours=3), half)
                pay(due_at, amount - half)
            elif scenario in {"atraso_corto", "atraso_largo"}:
                pay(
                    due_at
                    + timedelta(
                        days=rng.randint(1, 3) if scenario == "atraso_corto" else rng.randint(4, 12)
                    ),
                    amount,
                )
            elif scenario == "abonos_tardios":
                pay(due_at, half)
                pay(due_at + timedelta(days=rng.randint(1, 7)), amount - half)
            elif scenario == "abono_incompleto":
                pay(due_at, half)
            loan = {
                "loan_id": f"SYN-L{len(loans) + 1:05}",
                "client_id": client["client_id"],
                "data_source": "synthetic",
                "evaluated_at": at.isoformat(),
                "due_date": due.isoformat(),
                "amount": str(amount),
                "payments": events,
                "planned_scenario": scenario,
                "simulated_authorization": (
                    "owner_review"
                    if features["paid_credits"] == 0 or features["pending_overdue"] > 0
                    else "regular_grant"
                ),
                "split": client["split"],
            }
            balance = remaining(loan, cutoff)
            last_paid = max((date.fromisoformat(p["at"][:10]) for p in events), default=None)
            label = classify_credit_outcome(
                pending_amount=balance,
                due_date=due,
                last_payment_date=last_paid,
                observed_on=OBSERVED_ON,
            )
            loans.append(loan)
            rows.append(
                {
                    "loan_id": loan["loan_id"],
                    "client_id": client["client_id"],
                    "data_source": "synthetic",
                    "split": client["split"],
                    "evaluated_at": at.isoformat(),
                    "due_date": due.isoformat(),
                    "observed_on": OBSERVED_ON.isoformat(),
                    "requested_amount": str(amount),
                    "credit_cap": client["credit_cap"],
                    "pending_at_cutoff": str(balance),
                    "scenario": scenario if label is not None else "aun_sin_desenlace",
                    **features,
                    TARGET_NAME: label,
                }
            )
            sales.append(
                {
                    "client_id": client["client_id"],
                    "at": (at + timedelta(minutes=1)).isoformat(),
                    "kind": "credit",
                }
            )
            if rng.random() < 0.65:
                sales.append(
                    {
                        "client_id": client["client_id"],
                        "at": (at + timedelta(hours=2)).isoformat(),
                        "kind": "cash",
                    }
                )
            at += timedelta(days=rng.randint(1, 5))
    result = {
        "seed": seed,
        "observed_on": OBSERVED_ON.isoformat(),
        "clients": clients,
        "loans": loans,
        "sales": sales,
        "rows": rows,
    }
    validate_academic_dataset(result)
    return result


def validate_academic_dataset(dataset: dict) -> dict:
    clients = {client["client_id"]: client for client in dataset["clients"]}
    cutoff = datetime.combine(date.fromisoformat(dataset["observed_on"]), time.max)
    rows = {row["loan_id"]: row for row in dataset["rows"]}
    assert len(rows) == len(dataset["loans"])
    for sale in dataset["sales"]:
        assert date.fromisoformat(sale["at"][:10]) >= date.fromisoformat(
            clients[sale["client_id"]]["registered_on"]
        )
        assert datetime.fromisoformat(sale["at"]) <= cutoff
    for loan in dataset["loans"]:
        row, client = rows[loan["loan_id"]], clients[loan["client_id"]]
        at = datetime.fromisoformat(loan["evaluated_at"])
        assert loan["data_source"] == row["data_source"] == client["data_source"] == "synthetic"
        assert row["split"] == loan["split"] == client["split"]
        assert date.fromisoformat(loan["due_date"]) == at.date() + timedelta(days=1)
        assert Decimal("0") < money(loan["amount"]) <= Decimal(client["credit_cap"])
        for payment in loan["payments"]:
            assert at < datetime.fromisoformat(payment["at"]) <= cutoff
            assert money(payment["amount"]) > 0
        assert Decimal("0") <= remaining(loan, cutoff) <= money(loan["amount"])
        expected = snapshot(client, dataset["loans"], dataset["sales"], at, money(loan["amount"]))
        assert all(abs(row[name] - expected[name]) < 1e-9 for name in FEATURE_NAMES)
        assert (
            money(expected["outstanding"]) + money(loan["amount"])
            <= Decimal(client["credit_cap"])
        )
        label = classify_credit_outcome(
            pending_amount=remaining(loan, cutoff),
            due_date=date.fromisoformat(loan["due_date"]),
            last_payment_date=max(
                (date.fromisoformat(p["at"][:10]) for p in loan["payments"]), default=None
            ),
            observed_on=cutoff.date(),
        )
        assert row[TARGET_NAME] == label
    return {
        "clients": len(clients),
        "loans": len(rows),
        "payments": sum(len(loan["payments"]) for loan in dataset["loans"]),
        "scenarios": dict(Counter(row["scenario"] for row in dataset["rows"])),
        "labels": dict(Counter(str(row[TARGET_NAME]) for row in dataset["rows"])),
        "checks": [
            "amounts_positive_and_capped",
            "payments_never_exceed_debt",
            "one_day_terms",
            "payments_within_observation",
            "snapshots_recomputed_before_credit",
            "labels_recomputed_from_payments",
            "clients_do_not_cross_splits",
        ],
    }
