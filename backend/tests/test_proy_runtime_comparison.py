"""Pure comparison tests, loaded without importing app or numerical packages."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "proy_runtime_verifier",
    Path(__file__).resolve().parents[2] / "deploy/verify-proy-svm-runtime.py",
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def fixture(runtime):
    result = copy.deepcopy(verifier.IDENTITY)
    result.update({"runtime": dict(runtime), "recorded_utc": "2026-11-26T00:00:00+00:00",
                   "learned_state_before_sha256": "a" * 64,
                   "learned_state_after_sha256": "a" * 64,
                   "internal_label_encoder_fit_calls": 2,
                   "scores": [{"loan_id": "dev-" + str(i), "features": list(verifier.ILLUSTRATIVE),
                               "proba": [0.8, 0.2], "predicted": 1} for i in range(534)],
                   "illustrative": {"loan_id": "illustrative-six-paid-one-late",
                                    "features": list(verifier.ILLUSTRATIVE),
                                    "proba": [0.8, 0.2], "predicted": 1}})
    return result


class RuntimeComparisonTests(unittest.TestCase):
    def setUp(self):
        self.reference = fixture(verifier.REFERENCE_RUNTIME)
        self.candidate = fixture(verifier.CANDIDATE_RUNTIME)

    def test_matching(self):
        result = verifier.compare_probes(self.reference, self.candidate)
        self.assertTrue(result["compatible"])
        self.assertEqual(result["max_absolute_delta"], 0)
        self.assertEqual(len(result["per_row_deltas"]), 535)

    def test_real_probe_evidence_is_recomputable_without_inference(self):
        root = Path(__file__).resolve().parents[2] / "docs"
        record_path = root / "PROY_SVM_COMPATIBILIDAD.json"
        if not record_path.is_file():
            self.skipTest("Read-only compatibility evidence not mounted")
        record = json.loads(record_path.read_bytes())
        probes = {}
        for name in ("reference", "candidate"):
            source = root / "PROY_SVM_EVIDENCIAS" / record["probes"][name]["name"]
            content = source.read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), record["probes"][name]["sha256"])
            probes[name] = json.loads(content)
        comparison = verifier.compare_probes(probes["reference"], probes["candidate"])
        for name, value in comparison.items():
            self.assertEqual(record[name], value, name)
        self.assertEqual(record["tested_runtime_whitelist"],
                         [verifier.REFERENCE_RUNTIME, verifier.CANDIDATE_RUNTIME])
        self.assertIs(record["learned_state_unchanged"], True)
        self.assertIs(record["scope"]["production_authorized"], False)
        self.assertIs(record["scope"]["final_contacted"], False)

    def test_untrusted_tampering(self):
        mutations = [
            lambda p: p.update(artifact_before="0" * 64),
            lambda p: p.update(csv_after="0" * 64),
            lambda p: p["scores"][0].update(proba=[float("inf"), 0.2]),
            lambda p: p["scores"][0].update(predicted=0),
            lambda p: p["scores"].reverse(),
            lambda p: p["runtime"].update(sklearn="1.10.0"),
            lambda p: p["runtime"].update(scipy="1.19.0"),
            lambda p: p["runtime"].update(threadpoolctl="3.8.0"),
            lambda p: p["runtime"].update(machine="x86_64"),
            lambda p: p["scores"][0].update(features=[0] * 11),
            lambda p: p.update(classes=[1, 0]),
            lambda p: p.update(warnings=["version warning"]),
            lambda p: p["scores"].pop(),
            lambda p: p["scores"][0].update(proba=[0.2]),
            lambda p: p["scores"][0].update(loan_id=p["scores"][1]["loan_id"]),
            lambda p: p.pop("learned_state_unchanged"),
            lambda p: p.pop("learned_state_before_sha256"),
            lambda p: p.update(learned_state_after_sha256="b" * 64),
            lambda p: p.update(internal_label_encoder_fit_allowance=False),
            lambda p: p.update(internal_label_encoder_fit_calls=3),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                candidate = copy.deepcopy(self.candidate)
                mutation(candidate)
                with self.assertRaises(ValueError):
                    verifier.compare_probes(self.reference, candidate)

    def test_outside_tolerance(self):
        self.candidate["scores"][0]["proba"] = [0.8 - 2e-12, 0.2 + 2e-12]
        self.assertFalse(verifier.compare_probes(self.reference, self.candidate)["compatible"])

    def test_failed_probe_cannot_be_compared(self):
        with self.assertRaises(ValueError):
            verifier.compare_probes(
                {"compatible": False, "blocker": "fit forbidden"}, self.candidate
            )

    def test_within_tolerance(self):
        self.candidate["scores"][0]["proba"] = [0.8 - 1e-13, 0.2 + 1e-13]
        self.assertTrue(verifier.compare_probes(self.reference, self.candidate)["compatible"])

    def test_near_threshold_class_change_is_not_accepted(self):
        self.reference["scores"][0].update(proba=[0.9 + 1e-14, 0.1 - 1e-14], predicted=0)
        self.candidate["scores"][0].update(proba=[0.9 - 1e-14, 0.1 + 1e-14], predicted=1)
        with self.assertRaisesRegex(ValueError, "Predicted class changed"):
            verifier.compare_probes(self.reference, self.candidate)

    def test_no_numerical_or_application_imports(self):
        # Other backend tests import app/NumPy during collection: inspect a fresh process.
        code = (
            "import importlib.util,sys; "
            f"s=importlib.util.spec_from_file_location('verifier', {str(SPEC.origin)!r}); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "assert not any(n in sys.modules for n in ('numpy','sklearn','joblib','app'))"
        )
        subprocess.run([sys.executable, "-B", "-c", code], check=True, capture_output=True)

    def test_guard_allowance_is_narrow(self):
        # Numerical imports stay in a separate process; comparison tests remain pure.
        code = r'''
import importlib.util
import sys
from types import SimpleNamespace as Frame
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.svm import SVC
spec = importlib.util.spec_from_file_location("verifier", sys.argv[1])
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
model = CalibratedClassifierCV()
model.classes_ = np.array([0, 1])
state = {"model": model, "internal_label_encoder_fit_calls": 0}
guard = v.make_profile_guard(LabelEncoder, state)
def prediction_frame(owner, parent=None):
    return Frame(f_globals={"__name__": "sklearn.calibration"},
                 f_code=Frame(co_name="predict_proba"), f_locals={"self": owner}, f_back=parent)
outer = prediction_frame(model)
inner = prediction_frame(object(), outer)
def fit_frame(encoder=None, labels=None, parent=inner, code=LabelEncoder.fit.__code__):
    return Frame(f_code=code, f_globals={"__name__": "sklearn.preprocessing._label"},
                 f_locals={"self": LabelEncoder() if encoder is None else encoder,
                           "y": model.classes_ if labels is None else labels}, f_back=parent)
guard(fit_frame(), "call", None)
assert state["internal_label_encoder_fit_calls"] == 1
class SubEncoder(LabelEncoder):
    pass
bad_frames = [fit_frame(parent=None), fit_frame(labels=np.array([0, 2])),
              fit_frame(labels=[0, 1]), fit_frame(encoder=SubEncoder()),
              fit_frame(code=LabelEncoder.fit_transform.__code__),
              fit_frame(parent=prediction_frame(object()))]
for frame in bad_frames:
    try:
        guard(frame, "call", None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Invalid allowance")
# Real calls must be stopped before any method body can fit anything.
for estimator, method in [(LabelEncoder(), "fit"), (SVC(), "fit"),
                           (StandardScaler(), "fit_transform"), (model, "fit")]:
    try:
        sys.setprofile(guard)
        if type(estimator) is LabelEncoder:
            estimator.fit(np.array([0, 1]))
        else:
            getattr(estimator, method)(np.array([[0], [1]]), np.array([0, 1]))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Fitting was not blocked")
    finally:
        sys.setprofile(None)
assert state["internal_label_encoder_fit_calls"] == 1
'''
        result = subprocess.run([sys.executable, "-B", "-c", code, str(SPEC.origin)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
