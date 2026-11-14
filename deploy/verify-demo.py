"""Exercise the isolated local MVP; creates only fictional demonstration operations."""

import json
import os
from datetime import date
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.environ.get("DEMO_ORIGIN", "http://localhost:8081")
if BASE not in {"http://localhost:8081", "https://demo-credify.168-75-71-113.sslip.io"}:
    raise SystemExit("Verification refused outside the known demo environments")
TOKEN = ""


def request(path, payload=None, expected=200, form=False):
    headers = {"Content-Type": "application/x-www-form-urlencoded" if form else "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = None
    if payload is not None:
        data = (urlencode(payload) if form else json.dumps(payload)).encode()
    try:
        response = urlopen(Request(BASE + path, data=data, headers=headers), timeout=20)
    except HTTPError as error:
        if error.code == expected:
            return None
        raise
    with response:
        assert response.status == expected, (path, response.status)
        return json.load(response)


if __name__ == "__main__":
    assert request("/health/ready")["status"] == "ready"
    login = request("/api/v1/auth/login", {
        "username": "docente@example.com", "password": os.environ.get("DEMO_USER_PASSWORD", "DemoAPF2-2026!"),
    }, form=True)
    TOKEN = login["access_token"]
    client = request("/api/v1/clients")[0]
    assert "DEMO" in client["business_name"]
    request("/api/v1/credits/evaluate", {"client_id": client["id"], "amount": "0"}, expected=422)
    evaluation = request("/api/v1/credits/evaluate", {"client_id": client["id"], "amount": "50"})
    assert evaluation["model_version"] == "rules-v1"
    assert evaluation["ai_status"] == "disabled"
    credit = request("/api/v1/credits", {
        "client_id": client["id"], "amount": "50", "credit_date": date.today().isoformat(),
    }, expected=201)
    assert (date.fromisoformat(credit["due_date"]) - date.today()).days == 1
    request("/api/v1/payments", {
        "client_id": client["id"], "allocations": [{"credit_id": credit["id"], "amount": "20"}],
        "payment_date": date.today().isoformat(), "method": "efectivo", "reference": "DEMO - prueba APF2",
    }, expected=201)
    saved = request(f"/api/v1/credits/{credit['id']}")
    assert float(saved["pending_amount"]) == 30
    assert request(f"/api/v1/credits/evaluations?client_id={client['id']}")
    print("PASS: login, clients, invalid amount, rules evaluation, one-day credit, partial payment, persistence and history.")
