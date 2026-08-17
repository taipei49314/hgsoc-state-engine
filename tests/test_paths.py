from pathlib import Path

import yaml

from engine.paths import run_query, run_query_path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "evidence" / "claims"
QUERIES = ROOT / "fixtures" / "queries"
EXTRA = ROOT / "fixtures" / "paths"


def _load_query(name: str) -> dict:
    return yaml.safe_load((QUERIES / name).read_text(encoding="utf-8"))


def test_brca1_has_primary_and_no_invented_second():
    report = run_query_path(QUERIES / "brca1.yaml", claim_dirs=[LEDGER])
    assert report.verdict == "PASS"
    assert report.primary_path is not None
    assert report.primary_path["edges"][0]["claim_id"] == "C-0001"
    assert report.second_path == "NO_SECOND_ADMISSIBLE_PATH"
    assert report.divergence_point is None
    assert report.deepest_reached_layer == "L2"
    assert report.deepest_named_layer is None
    assert report.why_stopped["code"] == "NO_ADMITTED_CONTINUATION"
    assert report.why_stopped["next_layer"] == "L3"
    assert report.host_effect == {
        "naming_status": "UNNAMED",
        "knowledge_status": "UNKNOWN",
        "coverage_status": "GATE_ONLY",
    }
    assert "L5B_organ_function" in report.unmodeled_layers
    assert report.unknown["organ_function"] == "UNMODELED"
    assert report.weakest_link["weakest_evidence_fit"] == "FIT_1"
    assert report.receipt["engine_version"].startswith("0.5")
    assert report.primary_path["edges"][0]["evidence"][0]["PMID"] == "25400221"
    assert report.primary_path["edges"][0]["falsify"]["observable"]


def test_t11_two_mechanisms_from_extra_claim():
    report = run_query(_load_query("brca1.yaml"), claim_dirs=[LEDGER, EXTRA])
    assert report.verdict == "PASS"
    assert report.primary_path["edges"][0]["claim_id"] == "C-0001"
    assert isinstance(report.second_path, dict)
    assert report.second_path["edges"][0]["claim_id"] == "C-T11-B"
    assert report.divergence_point == "BRCA1_BIALLELIC_LOSS_OBSERVED"
    assert "mechanism" in report.second_path["differ_in"]


def test_t11_two_starts_from_ledger():
    report = run_query_path(QUERIES / "two_starts.yaml", claim_dirs=[LEDGER])
    ids = {report.primary_path["edges"][0]["claim_id"], report.second_path["edges"][0]["claim_id"]}
    assert ids == {"C-0001", "C-0004"}
    assert report.second_path != "NO_SECOND_ADMISSIBLE_PATH"


def test_negative_and_assay_relations_are_not_walked():
    report = run_query(
        {
            "query_id": "Q-hrd",
            "context": {"disease": "HGSOC", "treatment": "untreated"},
            "start_state": "HRD_HIGH",
        },
        claim_dirs=[LEDGER],
    )
    assert report.primary_path is None
    assert report.second_path == "NO_SECOND_ADMISSIBLE_PATH"
    assert report.why_stopped["code"] == "NO_ADMITTED_PATH"
    assert any(row["claim_id"] == "C-0002" for row in report.receipt["rejected_claims"])


def test_can_measure_is_not_a_parent_edge():
    report = run_query(
        {
            "query_id": "Q-rad51",
            "context": {"disease": "HGSOC", "treatment": "untreated"},
            "start_state": "RAD51_FOCI_COUNT_OBSERVED",
        },
        claim_dirs=[LEDGER],
    )
    assert report.primary_path is None
    assert any(row["claim_id"] == "C-0003" for row in report.receipt["rejected_claims"])


def test_query_generic_cancer_mismatch():
    query = _load_query("brca1.yaml")
    query["context"]["disease"] = "ovarian cancer"
    report = run_query(query, claim_dirs=[LEDGER])
    assert report.verdict == "CONTEXT_MISMATCH"
    assert report.primary_path is None


def test_query_treated_out_of_slice():
    query = _load_query("brca1.yaml")
    query["context"]["treatment"] = "post-NACT"
    report = run_query(query, claim_dirs=[LEDGER])
    assert report.verdict == "OUT_OF_FROZEN_SLICE"


def test_no_fake_support_mass():
    report = run_query_path(QUERIES / "brca1.yaml", claim_dirs=[LEDGER])
    blob = report.as_dict()
    assert "biological_support" not in blob
    assert "support_mass" not in blob
    assert report.primary_path["rank_tuple"]["weakest_evidence_fit"] == 1
    assert report.primary_path["rank_tuple"]["context_exactness"] == 4
    assert "0.82" not in str(blob)


def test_higher_fit_ranks_as_primary(tmp_path):
    extra = yaml.safe_load((EXTRA / "C-T11-B.yaml").read_text(encoding="utf-8"))
    extra["claim_id"] = "C-T11-FIT2"
    extra["evidence"][0]["evidence_fit"] = "FIT_2"
    extra["evidence"][0]["model_system"] = "primary_human_or_ex_vivo"
    extra["assumptions"] = extra["assumptions"][:1]
    (tmp_path / "C-T11-FIT2.yaml").write_text(yaml.safe_dump(extra, sort_keys=False), encoding="utf-8")
    report = run_query(_load_query("brca1.yaml"), claim_dirs=[LEDGER, tmp_path])
    assert report.primary_path["edges"][0]["claim_id"] == "C-T11-FIT2"
    assert report.second_path["edges"][0]["claim_id"] == "C-0001"


def test_receipt_has_g8_fields():
    report = run_query_path(QUERIES / "brca1.yaml", claim_dirs=[LEDGER])
    receipt = report.receipt
    for key in (
        "engine_version",
        "ontology_versions",
        "state_registry_hash",
        "evidence_snapshot_hash",
        "input_context",
        "admitted_claims",
        "rejected_claims",
        "blocked_edges",
        "selected_paths",
        "unmodeled_layers",
        "host_effect_status",
    ):
        assert key in receipt
    assert "C-0001" in receipt["admitted_claims"]
    assert receipt["selected_paths"] == [["C-0001"]]
    assert len(receipt["state_registry_hash"]) == 64


def test_axes_default_not_platinum_sensitive():
    report = run_query_path(QUERIES / "brca1.yaml", claim_dirs=[LEDGER])
    assert report.frozen_slice["A4"]["state_id"] == "A4_NOT_EVALUATED"
    assert report.frozen_slice["A4"]["state_id"] != "platinum_sensitive"
