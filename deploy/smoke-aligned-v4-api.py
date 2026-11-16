"""Real V4 ASGI smoke; run inside the isolated, read-only training-test image."""

import argparse
import asyncio
import fcntl
import hashlib
import io
import json
import logging
import os
import resource
import secrets
import socket
import struct
import sys
import traceback
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


class SmokeFailure(Exception):
    """Only constant, non-secret diagnostic labels may be exposed."""


def check(condition, label):
    if not condition:
        raise SmokeFailure(label)


def snapshot(root):
    paths = sorted(root.rglob("*"))
    check(not any(path.is_symlink() for path in paths), "bundle symlink")
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


async def smoke(args, result):
    bundle = args.bundle.resolve(strict=True)
    evidence = args.evidence_dir.resolve(strict=True)
    check(os.geteuid() != 0, "root user forbidden")
    for path in (Path("/"), Path("/app"), bundle, evidence, Path(__file__).parent):
        check(os.statvfs(path).f_flag & os.ST_RDONLY, "writable input mount")
    # No writable persistent mounts, including mounts not named by this CLI.
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        fields = line.split()
        filesystem = fields[fields.index("-") + 1]
        if "rw" in fields[5].split(","):
            check(filesystem in {"tmpfs", "proc", "devpts", "mqueue"},
                  "writable persistent mount")
    check(Path("/proc/self/status").read_text().split("CapEff:\t")[1].split()[0]
          == "0000000000000000", "capabilities present")
    # Some Docker kernels expose inactive tunnel devices even with --network none.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        for _, name in socket.if_nameindex():
            flags = fcntl.ioctl(probe.fileno(), 0x8913, struct.pack("256s", name.encode()))
            check(name == "lo" or not struct.unpack_from("H", flags, 16)[0] & 1,
                  "active non-loopback network interface")
    before = snapshot(bundle)
    result["bundle_sha256_before"] = before
    os.environ.update({
        "ENVIRONMENT": "staging", "ACADEMIC_ML_V4_ENABLED": "true",
        "ACADEMIC_ML_V4_DIR": str(bundle), "JWT_SECRET_KEY": secrets.token_urlsafe(64),
        "DATABASE_URL": "postgresql+asyncpg://fixture:fixture@127.0.0.1:1/fixture",
        "ACADEMIC_ML_LAB_ENABLED": "false", "WHATSAPP_ENABLED": "false",
        "OPENROUTER_ENABLED": "false", "CREDIT_ML_ENABLED": "false",
    })
    check(not Path("/app/.env").exists(), "dotenv file forbidden")
    logging.disable(logging.CRITICAL)
    # Prefer the read-only workspace backend over any package baked into the image.
    sys.path.insert(0, "/app")

    import joblib
    import numpy as np
    from httpx import ASGITransport, AsyncClient
    from sklearn.pipeline import Pipeline
    from sklearn.svm import SVC
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.core.security import create_access_token
    from app.db.session import get_db
    from app.main import app
    from app.models.user import User, UserRole
    from app.services import academic_lab_v4 as lab
    from app.services import ai_credit, audit, credit_scoring, whatsapp

    check(not app.dependency_overrides, "preexisting dependency overrides")
    check(Path(lab.__file__).is_relative_to("/app/app"), "wrong backend imported")
    check(lab.runtime_versions() == lab.RUNTIME, "actual runtime mismatch")
    result["runtime"] = lab.runtime_versions()
    result["isolation"] = {"uid": os.geteuid(), "inputs_read_only": True,
                           "network": "no_active_non_loopback", "capabilities": "none"}
    counts = {"identity_get": 0, "forbidden_actions": 0, "joblib_load": 0,
              "predict_proba": 0}
    result["counts"] = counts

    def forbidden(*_args, **_kwargs):
        counts["forbidden_actions"] += 1
        raise AssertionError("Forbidden SQL, business, training or inference operation")

    user_id = uuid4()
    user = User(id=user_id, email="smoke@example.invalid", full_name="Smoke fixture",
                role=UserRole.OPERATOR, is_active=True)

    class IdentityDB:
        async def get(self, model, key):
            check(model is User and key == user_id, "unexpected identity lookup")
            counts["identity_get"] += 1
            return user

        add = execute = commit = flush = delete = add_all = forbidden

        def __getattr__(self, _name):
            return forbidden

    async def identity_db():
        yield IdentityDB()

    expected_input = json.loads((bundle / "illustrative_input.json").read_bytes())
    features = expected_input.get("features", expected_input)
    expected_vector = np.asarray([[np.nan if features[name] is None else float(features[name])
                                   for name in lab.FEATURE_NAMES]])
    expected_output = json.loads((evidence / "illustrative_output.json").read_bytes())
    result["frozen_illustrative_output_sha256"] = hashlib.sha256(
        (evidence / "illustrative_output.json").read_bytes()).hexdigest()
    original_load = joblib.load

    def load(stream, *a, **kw):
        counts["joblib_load"] += 1
        check(isinstance(stream, io.BytesIO), "model not loaded from verified bytes")
        check(hashlib.sha256(stream.getvalue()).hexdigest()
              == before["selected_model.joblib"], "wrong model bytes")
        model = original_load(stream, *a, **kw)
        predict_proba = model.predict_proba

        def predict(vector, *a, **kw):
            counts["predict_proba"] += 1
            check(counts["predict_proba"] == 1, "multiple inference calls")
            check(vector.shape == (1, len(lab.FEATURE_NAMES)), "cohort inference")
            np.testing.assert_array_equal(vector, expected_vector)
            return predict_proba(vector, *a, **kw)

        model.predict_proba = predict
        model.predict = forbidden
        return model

    base = get_settings().api_v1_prefix + "/academic-ml/v4"
    endpoints = [("GET", "/summary"), ("GET", "/cases"),
                 ("POST", "/evaluate/illustrative-v4")]
    result["requests"] = []
    lab.validated_bundle.cache_clear()
    lab.load_model.cache_clear()
    app.dependency_overrides[get_db] = identity_db
    event.listen(Engine, "before_execute", forbidden)
    event.listen(Engine, "before_cursor_execute", forbidden)
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(joblib, "load", side_effect=load))
            for cls, names in ((Pipeline, ("fit", "fit_transform", "fit_predict")),
                               (SVC, ("fit",)),
                               (AsyncSession, ("add", "add_all", "execute", "commit",
                                               "flush", "delete", "get"))):
                for name in names:
                    stack.enter_context(patch.object(cls, name, forbidden))
            for module, names in (
                (credit_scoring, ("evaluate_credit", "evaluate_and_record")),
                (audit, ("add_audit_log",)),
                (ai_credit, ("enqueue_ai_explanation", "dispatch_ai_explanation")),
                (whatsapp, ("enqueue_evaluation_notification", "dispatch_evaluation_notification",
                            "send_template_message", "enqueue_payment_confirmation")),
            ):
                for name in names:
                    stack.enter_context(patch.object(module, name, forbidden))
            token, _ = create_access_token(user_id, UserRole.OPERATOR)
            headers = {"Authorization": f"Bearer {token}"}
            check(get_current_user not in app.dependency_overrides, "JWT guard overridden")
            async with AsyncClient(transport=ASGITransport(app=app),
                                   base_url="http://smoke.invalid") as client:
                async def request(method, path, expected, **kwargs):
                    response = await client.request(method, base + path, **kwargs)
                    result["requests"].append({"method": method, "path": path,
                                               "status": response.status_code})
                    check(response.status_code == expected, "HTTP contract mismatch")
                    return response.json()

                # These gates must not even read a bundle file.
                with patch.object(Path, "read_bytes", side_effect=forbidden):
                    for method, path in endpoints:
                        await request(method, path, 401)
                        await request(method, path, 401,
                                      headers={"Authorization": "Bearer invalid"})
                    check(counts["identity_get"] == 0, "invalid JWT read identity")
                    user.is_active = False
                    await request("GET", "/summary", 401, headers=headers)
                    user.is_active = True
                    await request("POST", "/evaluate/unknown", 404, headers=headers)
                    await request("POST", "/evaluate/FINAL-L1", 404, headers=headers)
                    for kwargs in ({"json": {}}, {"json": {"features": {}}},
                                   {"content": b"not-json"}, {"params": {"x": "1"}},
                                   {"files": {"upload": ("input.json", b"{}")}}):
                        await request("POST", "/evaluate/illustrative-v4", 422,
                                      headers=headers, **kwargs)
                    settings = get_settings()
                    with patch.object(settings, "academic_ml_v4_enabled", False):
                        for method, path in endpoints:
                            await request(method, path, 404, headers=headers)
                summary = await request("GET", "/summary", 200, headers=headers)
                cases = await request("GET", "/cases", 200, headers=headers)
                check(counts["joblib_load"] == counts["predict_proba"] == 0,
                      "summary/cases deserialized or inferred")
                result["summary_cases_counts"] = {
                    "joblib_load": counts["joblib_load"],
                    "predict_proba": counts["predict_proba"],
                }
                check(cases == [lab.CASE], "case contract")
                check(summary["final_labeled_rows"] == 259, "known FINAL count")
                comparison = {row["family"]: row for row in summary["comparison"]}
                check(comparison["svm"]["raw"]["confusion_matrix"] == [[80, 114], [4, 61]],
                      "raw SVM matrix")
                policy = comparison["constant_1"]["policy"]
                check(policy["metrics"]["f2"] == 0.622568093385214,
                      "constant-1 policy F2")
                check(policy["reviews"] == 255, "constant-1 reviews")
                # Exercise fail-closed trust/runtime checks without mutating frozen files.
                original_read = Path.read_bytes

                def corrupted_read(path):
                    data = original_read(path)
                    return data + b" " if path == bundle / "selected_model.joblib" else data

                with patch.object(Path, "read_bytes", corrupted_read):
                    await request("GET", "/summary", 503, headers=headers)
                with patch.object(lab.platform, "python_version", return_value="unsupported"):
                    await request("GET", "/summary", 503, headers=headers)
                check(counts["joblib_load"] == 0, "trust failure deserialized")
                evaluated = await request("POST", "/evaluate/illustrative-v4", 200,
                                          headers=headers)
                check(evaluated["estimated_late_probability"] == 0.11922453881690649,
                      "illustrative score")
                check(evaluated["threshold"] == 0.1
                      and evaluated["predicted_late_payment"] == 1
                      and evaluated["actual_late_payment"] is None
                      and evaluated["review_policy_applied"] is False, "illustrative contract")
                check(evaluated["features"] == features, "frozen features changed")
                check(expected_output["features"] == evaluated["features"]
                      and expected_output["feature_names"] == lab.FEATURE_NAMES
                      and expected_output["probability"] == evaluated["estimated_late_probability"]
                      and expected_output["threshold"] == evaluated["threshold"]
                      and expected_output["predicted"] == evaluated["predicted_late_payment"]
                      and expected_output["known_label"] is None,
                      "original illustrative output mismatch")
                check(evaluated["research_only"] is True
                      and evaluated["business_approval"] is False, "research restrictions")
                result["frozen_illustrative_output"] = expected_output
                result["evaluation"] = evaluated
                result["summary"] = summary
                result["cases"] = cases
                check(counts["joblib_load"] == counts["predict_proba"] == 1,
                      "expected exactly one real load and probability call")
                check(counts["identity_get"] > 0 and counts["forbidden_actions"] == 0,
                      "unexpected DB or side effect")
                check(not any(name.startswith("scripts.academic_credit") for name in sys.modules),
                      "training runner imported")
    finally:
        app.dependency_overrides.pop(get_db, None)
        event.remove(Engine, "before_execute", forbidden)
        event.remove(Engine, "before_cursor_execute", forbidden)
        result["bundle_sha256_after"] = snapshot(bundle)
        check(result["bundle_sha256_after"] == before, "bundle modified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True,
                        help="Read-only original experimento directory")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {"status": "failed", "scope": "real ASGI/JWT/model; identity fixture, no real DB",
              "human_e2e": False, "final_inference": False}
    output = None
    try:
        if args.output:
            check(args.output.resolve().is_relative_to(Path("/tmp")), "output outside tmp")
            output = args.output
        asyncio.run(smoke(args, result))
        result["status"] = "passed"
    except Exception as error:
        # Never serialize exception text: third-party errors can contain credentials.
        result["error_type"] = type(error).__name__
        result["error_locations"] = [
            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
            for frame in traceback.extract_tb(error.__traceback__)
        ]
        if isinstance(error, SmokeFailure):
            result["failed_check"] = str(error)
    result["process_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if output:
        output.write_text(encoded)
    print(encoded, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
