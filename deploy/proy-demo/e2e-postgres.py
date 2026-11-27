"""E2E real del endpoint PROY sobre PostgreSQL y la imagen de staging.

Comprueba, contra la API en ejecucion y la base real: inicio de sesion, snapshot
calculado en el servidor, inferencia del SVM, traza persistida y ausencia de
efectos de negocio (ni fiado, ni evaluacion, ni revision). No usa mocks ni
sqlite; pensado para el job ``e2e-postgres`` del workflow PROY SVM x86_64.

Solo stdlib. La base se consulta con ``docker exec ... psql`` para no duplicar
el cliente SQL en la imagen de la API.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

CLIENT_DOCUMENT = "90000001"
REQUESTED_AMOUNT = "40.00"
# La tupla x86_64 difiere de la referencia en ~2.6e-14; 1e-9 deja margen.
EXPECTED_PROBABILITY = 0.1065748513407444
PROBABILITY_TOLERANCE = 1e-9
EXPECTED_SNAPSHOT = {
    "completed_sales": 1.0,
    "paid_credits": 1.0,
    "paid_late": 0.0,
    "pending_overdue": 0.0,
    "pending_current": 0.0,
    "outstanding": 0.0,
    "utilization": 0.0,
    "requested_ratio": 0.2,
    "tenure_days": 0.0,
    "punctuality_rate": 1.0,
    "overdue_rate": 0.0,
}
COUNT_SQL = (
    "SELECT (SELECT count(*) FROM credits), "
    "(SELECT count(*) FROM credit_evaluations), "
    "(SELECT count(*) FROM credit_reviews), "
    "(SELECT count(*) FROM proy_experimental_evaluations)"
)


def psql(container: str, user: str, database: str, sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", container, "psql", "-U", user, "-d", database, "-tAc", sql],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("psql fallo; salida retenida para no filtrar credenciales")
    return result.stdout.strip()


def http(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
    form: bool = False,
) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        if form:
            body = urllib.parse.urlencode(payload).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return error.code, {}


def wait_ready(base_url: str, timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, _ = http(f"{base_url}/health/ready")
            if status == 200:
                return
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError("la API no respondio /health/ready dentro del plazo")


def counts(container: str, user: str, database: str) -> dict[str, int]:
    credits, evaluations, reviews, traces = psql(container, user, database, COUNT_SQL).split("|")
    return {
        "credits": int(credits),
        "credit_evaluations": int(evaluations),
        "credit_reviews": int(reviews),
        "proy_experimental_evaluations": int(traces),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--pg-container", required=True)
    parser.add_argument("--pg-user", default="demo")
    parser.add_argument("--pg-database", default="credify_demo")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--expected-probability", type=float, default=EXPECTED_PROBABILITY)
    args = parser.parse_args()

    password = os.environ.get("DEMO_USER_PASSWORD")
    if not password:
        print("E2E_FALLIDO: falta DEMO_USER_PASSWORD", file=sys.stderr)
        return 1

    evidence: dict = {
        "schema": "proy-e2e-x86_64-v1",
        "status": "failed",
        "started_utc": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "database": f"{args.pg_database}@{args.pg_container}",
        "client_document": CLIENT_DOCUMENT,
        "requested_amount": REQUESTED_AMOUNT,
        "expected_probability": args.expected_probability,
        "checks": [],
    }
    try:
        wait_ready(args.base_url)
        status, login = http(
            f"{args.base_url}/api/v1/auth/login",
            method="POST",
            payload={"username": "docente@example.com", "password": password},
            form=True,
        )
        assert status == 200, f"login devolvio {status}"
        assert login["user"]["role"] == "operator", "rol semilla inesperado"
        token = login["access_token"]
        evidence["checks"].append("login_real")

        client_id = psql(
            args.pg_container,
            args.pg_user,
            args.pg_database,
            f"SELECT id FROM clients WHERE document = '{CLIENT_DOCUMENT}' AND is_active LIMIT 1",
        )
        assert client_id, "cliente de control ausente en la base"
        evidence["client_id"] = client_id

        before = counts(args.pg_container, args.pg_user, args.pg_database)
        evidence["counts_before"] = before

        status, body = http(
            f"{args.base_url}/api/v1/proy-experimental/evaluations",
            method="POST",
            token=token,
            payload={"client_id": client_id, "amount": REQUESTED_AMOUNT},
        )
        assert status == 201, f"evaluacion devolvio {status}"
        evidence["response"] = body
        assert body["decision"] == "MODEL_REVIEW_CANDIDATE", body["decision"]
        assert body["reason"] == "human_decision_required", body["reason"]
        assert body["model_called"] is True
        assert body["predicted"] == 1
        assert float(body["threshold"]) == 0.1
        assert body["model_version"] == "credit-proy-svm-v1"
        assert body["schema_version"] == "proy-credit-contract-v1"
        assert body["policy_version"] == "proy-pending-balance-v1"
        assert body["research_only"] is True and body["business_approval"] is False
        assert body["requires_human_decision"] is True
        assert abs(body["probability"] - args.expected_probability) <= PROBABILITY_TOLERANCE, (
            f"probabilidad {body['probability']} fuera de tolerancia"
        )
        assert body["feature_snapshot"] == EXPECTED_SNAPSHOT, body["feature_snapshot"]
        assert float(body["pending_amount"]) == 0.0
        evidence["checks"].append("snapshot_e_inferencia_reales")

        row = psql(
            args.pg_container,
            args.pg_user,
            args.pg_database,
            "SELECT decision, model_called, probability, requested_amount::text, "
            "pending_amount::text, feature_snapshot::text, created_by_id IS NOT NULL "
            f"FROM proy_experimental_evaluations WHERE id = '{body['id']}'",
        )
        assert row, "la traza no se persistio"
        decision, model_called, probability, requested, pending, snapshot, author = row.split("|", 6)
        assert decision == body["decision"]
        assert model_called == "t"
        assert abs(float(probability) - body["probability"]) <= PROBABILITY_TOLERANCE
        assert requested == REQUESTED_AMOUNT and float(pending) == 0.0
        assert json.loads(snapshot) == body["feature_snapshot"]
        assert author == "t", "la traza no registra autor"
        evidence["trace"] = {
            "decision": decision,
            "model_called": True,
            "probability": float(probability),
            "requested_amount": requested,
            "feature_snapshot": json.loads(snapshot),
            "has_author": True,
        }
        evidence["checks"].append("traza_persistida")

        after = counts(args.pg_container, args.pg_user, args.pg_database)
        evidence["counts_after"] = after
        assert after["credits"] == before["credits"], "se creo un fiado"
        assert after["credit_evaluations"] == before["credit_evaluations"], "se creo una evaluacion"
        assert after["credit_reviews"] == before["credit_reviews"], "se creo una revision"
        assert after["proy_experimental_evaluations"] == before["proy_experimental_evaluations"] + 1
        evidence["checks"].append("sin_efectos_de_negocio")

        evidence["status"] = "passed"
        print(
            f"E2E_OK proy_experimental decision={body['decision']} "
            f"probability={body['probability']:.16f} credits={before['credits']}->{after['credits']} "
            f"traces={before['proy_experimental_evaluations']}->{after['proy_experimental_evaluations']}"
        )
        return 0
    except (AssertionError, RuntimeError, KeyError) as error:
        evidence["failed_check"] = str(error)[:300]
        print(f"E2E_FALLIDO: {error}", file=sys.stderr)
        return 1
    finally:
        evidence["finished_utc"] = datetime.now(UTC).isoformat()
        path = Path(args.evidence)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print(f"EVIDENCIA {path}")


if __name__ == "__main__":
    sys.exit(main())
