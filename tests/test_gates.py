from copy import deepcopy
from pathlib import Path

import yaml

from engine.claim_lint import lint_ledger
from engine.gates import gate_claim, gate_path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return yaml.safe_load((ROOT / "evidence" / "claims" / name).read_text(encoding="utf-8"))


def test_seed_claims_pass_all_gates():
    for path, packet in lint_ledger():
        assert packet.verdict == "PASS", path
        report = gate_path(path)
        assert report.verdict == "PASS", (path.name, report.verdict, report.reason)
        assert report.host_effect["naming_status"] == "UNNAMED"
        assert report.host_effect["knowledge_status"] == "UNKNOWN"
        assert "L5B_organ_function" in report.unmodeled_layers
        assert report.receipt["engine_version"].startswith("0.3")
        assert len(report.receipt["state_registry_hash"]) == 64


def test_g0_generic_cancer():
    claim = _load("C-0001.yaml")
    claim["context"]["disease"] = "ovarian cancer"
    report = gate_claim(claim)
    assert report.verdict == "CONTEXT_MISMATCH"


def test_g1_treated_specimen():
    claim = _load("C-0001.yaml")
    claim["context"]["treatment"] = "post-NACT"
    report = gate_claim(claim)
    assert report.verdict == "OUT_OF_FROZEN_SLICE"


def test_g2_hrd_is_not_functional_hr():
    claim = deepcopy(_load("C-0002.yaml"))
    claim["relation"] = {"type": "increases_likelihood_of"}
    claim["knowledge_status"] = "SUPPORTED_IN_MODEL"
    report = gate_claim(claim)
    assert report.verdict == "UNKNOWN"


def test_g4_scale_jump():
    claim = _load("C-0001.yaml")
    claim["target_layer"] = "L6"
    claim["object"] = {"state_id": "HOST_OBSERVATION_ASCITES"}
    report = gate_claim(claim)
    assert report.verdict == "SCALE_JUMP_REJECTED"


def test_g4_organ_function_unmodeled():
    claim = _load("C-0001.yaml")
    claim["target_layer"] = "L5B"
    report = gate_claim(claim)
    assert report.verdict == "UNMODELED"


def test_g4_outcome_out_of_scope():
    claim = _load("C-0001.yaml")
    claim["target_layer"] = "L7"
    report = gate_claim(claim)
    assert report.verdict == "OUT_OF_SCOPE"


def test_g5_conflicted_not_averaged():
    claim = _load("C-0002.yaml")
    claim["knowledge_status"] = "CONFLICTED"
    report = gate_claim(claim)
    assert report.verdict == "CONFLICTED"


def test_g7_host_observation_keeps_effect_unknown():
    claim = _load("C-0001.yaml")
    claim["object"] = {"state_id": "HOST_OBSERVATION_ASCITES"}
    claim["source_layer"] = "L5A"
    claim["target_layer"] = "L6"
    claim["subject"] = {"state_id": "ASCITIC_TUMOR_CELLS_PRESENT"}
    report = gate_claim(claim)
    assert report.verdict == "PASS"
    assert report.host_effect == {
        "naming_status": "UNNAMED",
        "knowledge_status": "UNKNOWN",
        "coverage_status": "GATE_ONLY",
    }
