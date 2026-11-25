"""Pruebas del protocolo PROY P0-05, de la grilla y de la puerta FINAL cerrada."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts import proy_credit_experiment_v1 as p05

REPO = Path(__file__).resolve().parents[2]
PROTOCOL = REPO / "docs/PROY_P0-05_MODEL_PROTOCOL.json"
DEVELOPMENT = REPO / "entregables/PROY_Grupo2/materiales/development"


@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL.read_bytes())


def test_protocol_declares_the_requested_grid(protocol):
    p05.validate_protocol(protocol)
    candidates = p05.build_candidates(protocol)
    by_family = {name: [c for c in candidates if c["family"] == name] for name in p05.MODEL_FAMILIES}
    assert len(by_family["svm"]) == 6
    assert len(by_family["knn"]) == 5
    assert len(by_family["tree"]) == 12
    assert len(by_family["adaboost"]) == 2
    assert [c["n_neighbors"] for c in by_family["knn"]] == [1, 3, 5, 7, 9]
    assert [c["n_estimators"] for c in by_family["adaboost"]] == [50, 400]
    assert len(candidates) == protocol["candidate_count"]["trained_models"] == 25


def test_protocol_keeps_both_dummies_and_no_inherited_winner(protocol):
    assert tuple(protocol["baselines"]) == p05.BASELINES
    assert protocol["selection"]["minimum_precision"] is None
    assert "no_inherited_winner" in protocol["selection"]
    assert "Ni SVM ni arbol" in protocol["selection"]["no_inherited_winner"]


def test_protocol_hashes_match_the_development_package(protocol):
    found = p05.verify_inputs(DEVELOPMENT, protocol)
    assert found == protocol["frozen_inputs"]


def test_feature_order_matches_application_contract(protocol):
    from app.ml import proy_contract
    from app.ml.features import FEATURE_NAMES

    assert protocol["feature_names"] == list(FEATURE_NAMES) == list(proy_contract.FEATURE_NAMES_PROY)


def test_final_test_is_closed_without_a_freeze(tmp_path):
    status = p05.final_test_status(tmp_path)
    assert status["status"] == "closed"
    assert "congelada" in status["reason"]


def test_final_test_rejects_tampered_artifacts(tmp_path):
    (tmp_path / "freeze_before_final.json").write_text(json.dumps({
        "version": p05.VERSION,
        "frozen_utc": "2026-11-25T00:00:00+00:00",
        "files": {},
        "final_generation_calls": 0,
        "final_prediction_calls": 0,
    }))
    (tmp_path / "artifact_manifest.json").write_text(json.dumps({"selected_model.joblib": "0" * 64}))
    (tmp_path / "selected_model.joblib").write_bytes(b"not-the-artifact")
    with pytest.raises(ValueError, match="cambio despues del freeze"):
        p05.final_test_status(tmp_path)


def test_final_test_rejects_prior_final_contact(tmp_path):
    (tmp_path / "freeze_before_final.json").write_text(json.dumps({
        "version": p05.VERSION,
        "frozen_utc": "2026-11-25T00:00:00+00:00",
        "files": {},
        "final_generation_calls": 1,
        "final_prediction_calls": 0,
    }))
    with pytest.raises(ValueError, match="contacto previo con FINAL"):
        p05.final_test_status(tmp_path)


def test_protocol_rejects_an_altered_knn_grid(protocol):
    altered = json.loads(json.dumps(protocol))
    altered["candidate_grid"]["knn"]["n_neighbors"] = [1, 3, 5]
    with pytest.raises(ValueError, match="k = 1, 3, 5, 7, 9"):
        p05.validate_protocol(altered)


def test_protocol_rejects_a_precision_floor(protocol):
    altered = json.loads(json.dumps(protocol))
    altered["selection"]["minimum_precision"] = 0.5
    with pytest.raises(ValueError, match="piso de precision"):
        p05.validate_protocol(altered)


def test_development_rows_keep_the_frozen_fold_order(tmp_path, protocol):
    folds = json.loads((DEVELOPMENT / "planned_folds.json").read_bytes())
    rows, x, y = p05.read_development(DEVELOPMENT, folds)
    assert len(rows) == 534 and x.shape == (534, 11) and len(set(y.tolist())) == 2
    assert len({row["client_id"] for row in rows}) == 24

    shuffled = tmp_path / "dev"
    shutil.copytree(DEVELOPMENT, shuffled)
    lines = (shuffled / "development_known.csv").read_text().splitlines()
    lines[1], lines[2] = lines[2], lines[1]
    (shuffled / "development_known.csv").write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="orden de known_row_ids"):
        p05.read_development(shuffled, folds)
