"""Unit and frozen-source integration checks, without model imports."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "data_audit", Path(__file__).with_name("audit-aligned-v4-data.py")
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class DataAuditTests(unittest.TestCase):
    def test_second_relation_is_not_replaced_when_nonmonotonic(self):
        rows = [
            {
                "paid_late": 0,
                "late_payment": 0,
                "client_id": "same",
                "tenure_days": t,
                "completed_sales": s,
            }
            for t, s in ((30, 8), (119, 8), (120, 20), (239, 20), (240, 10))
        ]
        result = AUDIT.relationships(rows)
        self.assertEqual([b["n"] for b in result["second"]], [2, 2, 1])
        self.assertEqual([b["median_sales"] for b in result["second"]], [8, 20, 10])
        self.assertFalse(result["monotonic_medians"])
        self.assertIn("NO", result["conclusion"])

    @unittest.skipUnless(
        AUDIT.DEFAULT_SOURCE.is_dir(), "Local frozen V4 package not installed"
    )
    def test_quality_detects_invalid_values_and_preserves_coincidences(self):
        experiment = AUDIT.DEFAULT_SOURCE / "experimento"
        worlds = AUDIT.load(experiment / "development_transactions.json")["replicas"]
        original = AUDIT.load(experiment / "development_rows.json")[0]
        features = AUDIT.feature_names(AUDIT.REPO / "backend/app/ml/features.py")
        duplicate = AUDIT.quality([original, dict(original)], features, worlds)
        self.assertEqual(duplicate["n"], 2)
        self.assertEqual(duplicate["duplicate_loan_id_excess"], 1)
        self.assertEqual(duplicate["duplicate_feature_vector_groups"], 1)
        self.assertEqual(duplicate["duplicate_feature_vector_rows"], 2)
        corrupted = dict(original)
        corrupted.update(
            paid_late=original["paid_credits"] + 1,
            utilization=None,
            outstanding=float("nan"),
            overdue_rate="invalid",
            requested_ratio=-1,
        )
        quality = AUDIT.quality([corrupted], features, worlds)["features"]
        self.assertEqual(quality["paid_late"]["invalid_range"], 1)
        self.assertEqual(quality["paid_late"]["snapshot_mismatch"], 1)
        self.assertEqual(quality["utilization"]["null"], 1)
        self.assertEqual(quality["outstanding"]["nonfinite"], 1)
        self.assertEqual(quality["overdue_rate"]["invalid_type"], 1)
        self.assertEqual(quality["requested_ratio"]["invalid_range"], 1)

    @unittest.skipUnless(
        AUDIT.DEFAULT_SOURCE.is_dir(), "Local frozen V4 package not installed"
    )
    def test_frozen_dev_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            result = AUDIT.run(AUDIT.DEFAULT_SOURCE, Path(folder))
            self.assertTrue(result["frozen_unchanged"])
            self.assertEqual(
                result["source_sha256_before"], result["source_sha256_after"]
            )
            self.assertEqual(len(result["csv"]["final.csv"]["header"]), 24)
            self.assertEqual(len(result["unknowns"]), 7)
            self.assertTrue(
                all(
                    r["excluded_supervised"] and r["verified_unresolved"]
                    for r in result["unknowns"]
                )
            )
            self.assertEqual(
                result["quality_all_study"]["nulls_by_column"]["late_payment"], 7
            )
            for scope in ("quality_supervised", "quality_all_study"):
                for stats in result[scope]["features"].values():
                    self.assertEqual(
                        sum(
                            stats[k]
                            for k in (
                                "null",
                                "nonfinite",
                                "invalid_type",
                                "invalid_range",
                                "snapshot_mismatch",
                            )
                        ),
                        0,
                    )
            self.assertEqual(
                [(g["late"], g["n"]) for g in result["relationships"]["first"]],
                [(8, 218), (60, 334)],
            )
            self.assertEqual(
                [item["criterion"] for item in result["coherence_criteria"]],
                [
                    "Escala del negocio",
                    "Rangos/unidades",
                    "Consistencia l\u00f3gica/temporal",
                    "Relaciones plausibles",
                    "Se\u00f1al ni nula ni perfecta",
                    "Coherencia con APF2",
                    "Mezcla real+simulado",
                ],
            )
            self.assertEqual(len(result["calibration_constraints"]), 7)
            self.assertEqual(result["dev_signal_saved"]["metrics"]["n"], 552)
            self.assertAlmostEqual(
                result["dev_signal_saved"]["metrics"]["f2"], 0.5592105263157895
            )
            self.assertEqual(
                result["dev_signal_saved"]["metrics"]["confusion_matrix"],
                [[351, 133], [17, 51]],
            )
            self.assertNotIn("final", result["dev_signal_saved"])
            self.assertIn(
                "100% sintetico", result["coherence_criteria"][6]["assessment"]
            )
            output = Path(folder) / "anexos/datos"
            markdown = (output / "coherencia-datos.md").read_text(encoding="utf-8")
            self.assertIn("## Ficha Principal: Consigna 4.2", markdown)
            self.assertIn("## Restricciones de calibraci\u00f3n", markdown)
            self.assertNotIn("## Siete Criterios De Coherencia", markdown)
            self.assertEqual(
                AUDIT.sha(output / "diccionario-datos.csv"),
                "39d16b28262441d12338af8d88f4a709955cbb37acad81320127716a312c8625",
            )
            self.assertEqual(
                {p.name for p in (Path(folder) / "anexos/datos").iterdir()},
                {
                    "calidad-dev-v4.json",
                    "diccionario-datos.csv",
                    "diccionario-datos.md",
                    "coherencia-datos.md",
                    "eda_relaciones_entrega.png",
                },
            )


if __name__ == "__main__":
    unittest.main()
