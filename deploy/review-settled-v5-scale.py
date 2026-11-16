"""Review weekly grant units against the later source clarification; no ML imports."""

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weekly_summary(weeks):
    assert len(weeks) == 24
    assert len({week["week_start"] for week in weeks}) == 24
    for week in weeks:
        assert all(type(week[key]) is int and week[key] >= 0 for key in (
            "requests", "request_clients", "grants", "grant_clients",
        ))
        assert week["grant_clients"] <= week["grants"] <= week["requests"]
        assert week["grant_clients"] <= week["request_clients"]
    return {
        "full_weeks": len(weeks),
        "mean_requests": statistics.mean(w["requests"] for w in weeks),
        "mean_grants": statistics.mean(w["grants"] for w in weeks),
        "mean_grant_recipients": statistics.mean(w["grant_clients"] for w in weeks),
        "grants_frequency": dict(sorted(Counter(w["grants"] for w in weeks).items())),
        "recipients_frequency": dict(sorted(Counter(w["grant_clients"] for w in weeks).items())),
        "joint_frequency": [
            {"grants": grants, "recipients": recipients, "weeks": count}
            for (grants, recipients), count in sorted(Counter(
                (w["grants"], w["grant_clients"]) for w in weeks
            ).items())
        ],
        "weeks": weeks,
    }


def review(source, clarification_path, output):
    assert source.is_dir() and output.parent.is_dir() and not output.exists()
    assert not output.resolve().is_relative_to(source.resolve())
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text())["files"]
    assert all(sha(source / name) == digest for name, digest in manifest.items())
    before = {name: sha(source / name) for name in manifest}
    clarification_bytes = clarification_path.read_bytes()
    clarification = json.loads(clarification_bytes)
    assert clarification["version"] == "owner-weekly-scale-clarification-1"
    assert clarification["confirmed_yes"] is True
    assert clarification["confirmed_scope"] == {
        "usual_approximate_granted_loans_per_week": 12,
        "usual_approximate_distinct_grant_recipients_per_week": 9,
        "lower_activity_examples_granted_loans_per_week": [10, 11],
        "lower_activity_examples_distinct_grant_recipients_per_week": [8, 9],
        "reason_in_question": (
            "Some customers still owe overdue debt and are not granted new credit "
            "until full settlement"
        ),
    }
    prepared = json.loads((source / "data_revision_report.json").read_text())
    audits = json.loads((source / "development_audits.json").read_text())
    assert not prepared["models_trained"] and not prepared["final_generated"]
    results = []
    for audit in audits:
        result = {"replica_id": audit["replica_id"], **weekly_summary(audit["weekly_stats"])}
        assert result["mean_grants"] == audit["mean_weekly_study_grants"]
        assert result["mean_grant_recipients"] == audit["mean_weekly_study_grant_clients"]
        results.append(result)
    report = {
        "status": "WEEKLY_VARIATION_CORROBORATED_BY_OWNER_RELAY",
        "scope": "Later qualitative source confirmation of lower activity, not complete dataset acceptance",
        "clarification": clarification,
        "replicas": results,
        "weekly_hard_bounds_established": False,
        "all_weeks_confirmed_by_owner": False,
        "old_team_tolerance_confirmed": False,
        "global_coherence_accepted": False,
        "models_trained": False,
        "final_generated": False,
        "data_regenerated": False,
        "input_manifest_sha256": sha(manifest_path),
        "input_sha256_before": before,
        "input_sha256_after": {name: sha(source / name) for name in manifest},
        "clarification_sha256": hashlib.sha256(clarification_bytes).hexdigest(),
        "tool_sha256": sha(Path(__file__)),
        "remaining_scope": (
            "Population, distribution shape, warmup, stationarity and cash-sale coverage "
            "remain explicit assumptions. Define a separate model protocol before fitting."
        ),
    }
    assert report["input_sha256_before"] == report["input_sha256_after"]
    assert clarification_bytes == clarification_path.read_bytes()
    output.mkdir()
    (output / "confirmacion-escala.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# V5: Confirmacion De Variacion Semanal", "",
        "Rildo confirma, segun la respuesta transmitida por la usuaria, que hay semanas de 10 u 11 fiados a ocho o nueve clientes por la deuda pendiente.",
        "La referencia habitual sigue siendo aproximadamente 12 fiados a nueve clientes. Se confirma la posibilidad de menor actividad, no una distribucion ni limites absolutos.",
        "", "| Historia sintetica | Fiados otorgados/semana | Clientes con fiado/semana |",
        "| --- | ---: | ---: |",
    ]
    for result in results:
        lines.append(f"| {result['replica_id']} | {result['mean_grants']:.4f} | "
                     f"{result['mean_grant_recipients']:.4f} |")
    lines.extend([
        "", "Los promedios son compatibles descriptivamente con actividad habitual cercana a 12/9 y semanas de menor actividad. No se cambiaron los datos para hacerlos coincidir.",
        "La frecuencia completa de cada conteo semanal se conserva en el JSON, incluidos los valores no mencionados en la pregunta. No se afirma que cada semana haya sido validada por Rildo.",
        "", "## Alcance", "",
        "Confirmacion posterior a la preparacion DEV, no umbral prospectivo. No confirma la tolerancia antigua del equipo, no autoriza modelos ni sustituye revision global de supuestos.",
        "No se genero FINAL, no se entrenaron modelos, no se modificaron datasets ni se actualizaron los entregables V4.",
    ])
    (output / "Revision_Escala_V5.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": report["status"], "replicas": [
        {key: r[key] for key in ("replica_id", "mean_grants", "mean_grant_recipients",
                                "grants_frequency", "recipients_frequency")}
        for r in results
    ], "global_coherence_accepted": False, "data_regenerated": False}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--clarification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review(args.source, args.clarification, args.output)
