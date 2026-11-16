"""Compare frozen transaction units to owner anchors; never import or execute ML."""

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(values):
    return {
        "n": len(values), "min": min(values) if values else None,
        "median": statistics.median(values) if values else None,
        "mean": statistics.mean(values) if values else None,
        "max": max(values) if values else None,
    }


def gaps(events, start, low, high):
    by_client = defaultdict(list)
    for event in events:
        by_client[event["client_id"]].append(event)
    values, outside = [], []
    for client, items in by_client.items():
        items.sort(key=lambda item: item["evaluated_at"])
        for previous, current in zip(items, items[1:], strict=False):
            # Include a predecessor in warmup; the later event must be in study.
            later = date.fromisoformat(current["evaluated_at"][:10])
            if later < start:
                continue
            delta = (later - date.fromisoformat(previous["evaluated_at"][:10])).days
            values.append(delta)
            if not low <= delta <= high:
                outside.append({"client_id": client, "days": delta,
                                "previous_at": previous["evaluated_at"],
                                "current_at": current["evaluated_at"]})
    return {**summarize(values), "outside_source_range": len(outside), "examples": outside[:5]}


def audit(source, output):
    assert source.is_dir() and output.parent.is_dir() and not output.exists()
    assert not output.resolve().is_relative_to(source.resolve())
    assert not source.resolve().is_relative_to(output.resolve())
    experiment = source / "experimento"
    frozen = json.loads((source / "manifest-paquete.json").read_text())["experiment_sha256"]
    before = {name: sha(experiment / name) for name in frozen}
    assert before == frozen
    anchors = json.loads((experiment / "calibration.json").read_text())
    protocol = json.loads((experiment / "protocol.json").read_text())
    worlds = json.loads((experiment / "development_transactions.json").read_text())["replicas"]
    worlds.append(json.loads((experiment / "final_transactions.json").read_text()))
    start = date.fromisoformat(protocol["simulation"]["study_start"])
    low, high = anchors["return_days_range"]
    results = []
    for world in worlds:
        rows = [r for r in world["rows"] if r["phase"] == "study"]
        loans = [loan for loan in world["loans"] if loan["phase"] == "study"]
        loan_by_id = {loan["loan_id"]: loan for loan in loans}
        weeks = []
        for index in range(protocol["simulation"]["study_full_weeks"]):
            first = start + timedelta(weeks=index)
            last = first + timedelta(days=7)
            attempts = [a for a in world["attempts"]
                        if first <= date.fromisoformat(a["evaluated_at"][:10]) < last]
            granted = [loan for loan in loans
                       if first <= date.fromisoformat(loan["evaluated_at"][:10]) < last]
            weeks.append({"week_start": first.isoformat(), "attempts": len(attempts),
                          "grants": len(granted),
                          "granted_clients": len({loan["client_id"] for loan in granted})})
        amounts = [float(loan["amount"]) for loan in loans]
        exposures = [float(r["outstanding"]) + float(r["requested_amount"]) for r in rows]
        partial, late_delays = 0, []
        for row in rows:
            loan = loan_by_id[row["loan_id"]]
            total = sum((Decimal(p["amount"]) for p in loan["payments"]), Decimal(0))
            # Count observed abonos; never read future payment plans.
            partial += bool(loan["payments"]) and (
                len(loan["payments"]) > 1 or total < Decimal(loan["amount"]))
            if row["late_payment"] == 1 and Decimal(row["pending_at_cutoff"]) == 0:
                last_payment = max(date.fromisoformat(p["at"][:10]) for p in loan["payments"])
                late_delays.append((last_payment - date.fromisoformat(loan["due_date"])).days)
        known = [r for r in rows if r["late_payment"] is not None]
        results.append({
            "replica_id": world["replica_id"], "study_rows": len(rows),
            "known": len(known), "unknown": len(rows) - len(known),
            "late": sum(r["late_payment"] for r in known),
            "late_rate": sum(r["late_payment"] for r in known) / len(known),
            "weeks": weeks,
            "weekly_grants": summarize([w["grants"] for w in weeks]),
            "weekly_granted_clients": summarize([w["granted_clients"] for w in weeks]),
            "weekly_attempts": summarize([w["attempts"] for w in weeks]),
            "scheduled_return_days": gaps(world["attempts"], start, low, high),
            "granted_loan_return_days": gaps(world["loans"], start, low, high),
            "amounts_pen": summarize(amounts),
            "amount_range_violations": sum(not 5 <= value <= 50 for value in amounts),
            "new_exposure_over_80": sum(value > 80 + 1e-9 for value in exposures),
            "observed_partial_loans": partial,
            "partial_rate_per_study_loan": partial / len(rows),
            "late_settled_delay_days": summarize(late_delays),
            "late_settled_delay_outside_1_15": sum(not 1 <= d <= 15 for d in late_delays),
        })
    assert before == {name: sha(experiment / name) for name in frozen}
    result = {
        "status": "SOURCE_ALIGNMENT_NOT_CLOSED",
        "scope": "Business aggregates and observed transactions only; no model prediction",
        "anchors": anchors, "results": results, "frozen_unchanged": True,
        "source_sha256": before, "script_sha256": sha(Path(__file__)),
        "new_training": False, "new_predictions": False,
        "findings": [
            "12 granted loans/week was translated to 12 scheduled opportunities/week",
            "The verified source says return to request credit: scheduled attempts match this unit; grant gaps are not that constraint",
            "Source prior abono was narrowed to post-due abono on every overdue loan",
            "The verified source explicitly counts fiados and lateness at contractual due date, separately from grace",
        ],
        "verified_source_reading": {
            "docx_sha256": anchors["source_docx_sha256"],
            "request_return_paragraphs": [6, 8],
            "granted_weekly_volume_paragraphs": [6, 7, 9],
            "contractual_lateness_paragraphs": [15, 16, 17, 24, 25],
            "partial_credit_unit_paragraphs": [36, 37, 38],
            "overdue_rule_paragraphs": [44, 46, 48],
            "overdue_rule_quote": "no se otorga un nuevo fiado si tiene saldo vencido; primero debe abonar o acordar fecha de pago",
            "note": "Focused private source inspection; no owner form, contacts or signatures are copied",
        },
        "decision": "Do not certify full coherence or change the consulted V4 test. Review the narrower overdue policy before a new protocol.",
    }
    output.mkdir()
    (output / "auditoria-coherencia.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Revision De Coherencia Con Rildo",
        "", "**Estado: coherencia con la fuente NO cerrada.** No usar este diagnostico para retocar FINAL.",
        "", "Se comparan magnitudes del negocio, no resultados del modelo. Las tres historias son alternativas.",
        "", "| Historia | Fiados/semana | Clientes/semana | Retorno entre fiados, dias | Intervalos fuera 3-14 |",
        "| --- | ---: | ---: | --- | ---: |",
    ]
    for item in results:
        g = item["granted_loan_return_days"]
        lines.append(f"| {item['replica_id']} | {item['weekly_grants']['mean']:.4f} | "
                     f"{item['weekly_granted_clients']['mean']:.4f} | {g['min']}-{g['max']} | "
                     f"{g['outside_source_range']} de {g['n']} |")
    lines += [
        "", "Los margenes del protocolo fueron elegidos por el equipo: no son tolerancias confirmadas por Rildo.",
        "", "## Brechas Que Deben Resolverse", "",
        "1. Diferenciar visitas, solicitudes y fiados otorgados; 12 oportunidades no garantizan 12 fiados.",
        "2. La ficha original P6/P8 dice volver a pedir fiado: 3-14 dias se contrasta con solicitudes. Los intervalos entre otorgamientos se muestran solo para distinguir unidades, no como incumplimientos de ese ancla.",
        "3. La ficha P24/P25 cuenta fiados atrasados al vencimiento contractual; la gracia se trata aparte en P15-P17. P38 cuenta fiados con abonos. La aclaracion de usuario fija 45 evaluables, ocho atrasos y tres desconocidos incluidos en 48.",
        "4. Precisar el abono y la revision: la regla post-vencimiento por cada deuda es una restriccion del equipo, no de la fuente agregada.",
        "", "## Lo Que Si Se Comprueba", "",
        "Importes y exposicion, plazo y pagos se contrastan en el JSON. Abonos observados por fiado no equivalen automaticamente a anotaciones del cuaderno.",
        "Las tasas de atraso no se fuerzan. Su diferencia no valida ni invalida por si sola el significado del target fuente.",
        "", "## Accion", "",
        "Conservar V4 y sus entregables sin alterar. Resolver las aclaraciones de fuente y predeclarar una nueva especificacion antes de generar otra cohorte.",
        "No presentar el dataset como plenamente coherente con Rildo mientras estas traducciones sigan abiertas.",
    ]
    (output / "Revision_Coherencia_Rildo.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": result["status"], "output": str(output), "results": [
        {k: item[k] for k in ("replica_id", "weekly_grants", "granted_loan_return_days")}
        for item in results
    ]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.source, args.output)
