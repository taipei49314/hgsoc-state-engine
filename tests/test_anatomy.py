from pathlib import Path

from engine.anatomy import load_anatomy, normalize_curie
from engine.gates import gate_claim
from engine.lint import lint_path
from engine.paths import run_query_path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
LEDGER = ROOT / "evidence" / "claims"


def test_uberon_ids_locked():
    anatomy = load_anatomy()
    sites = anatomy["sites"]
    assert sites["fimbria"]["ontology_id"] == "UBERON:8410010"
    assert sites["ovary"]["ontology_id"] == "UBERON:0000992"
    assert sites["peritoneum"]["ontology_id"] == "UBERON:0002358"
    assert sites["omentum"]["ontology_id"] == "UBERON:0005448"
    assert sites["fallopian_tube"]["ontology_id"] == "UBERON:0003889"
    assert sites["ascitic_compartment"]["ontology_id"] == "UBERON:0001179"
    assert normalize_curie("UBERON_8410010") == "UBERON:8410010"


def test_t07_stic_named_with_uberon():
    result = lint_path(FIX / "pass" / "stic_pathology.yaml")
    assert result.verdict == "PASS"
    assert result.naming_status == "NAMED"
    assert "ANATOMICAL_STATE_NAMED" in result.notes
    assert "UBERON:8410010" in result.notes


def test_named_anatomy_without_uberon_blocked():
    result = lint_path(FIX / "blocked" / "stic_named_no_uberon.yaml")
    assert result.verdict == "BLOCKED"
    assert result.naming_status == "UNNAMED"
    assert "UBERON" in result.reason


def test_wrong_uberon_blocked():
    result = lint_path(FIX / "blocked" / "stic_wrong_uberon.yaml")
    assert result.verdict == "BLOCKED"
    assert "ontology_id" in result.reason


def test_sample_origin_never_registered():
    result = lint_path(FIX / "rejected" / "sample_origin.yaml")
    assert result.verdict == "REJECTED"


def test_t08_anatomy_is_not_organ_failure():
    result = lint_path(FIX / "blocked" / "anatomy_to_organ_failure.yaml")
    assert result.verdict == "BLOCKED"


def test_t13_path_reaches_anatomy_and_stops():
    report = run_query_path(FIX / "queries" / "anatomy.yaml", claim_dirs=[LEDGER])
    assert report.verdict == "PASS"
    assert report.deepest_reached_layer == "L5A"
    assert report.deepest_named_layer == "L5A"
    assert report.primary_path["edges"][0]["claim_id"] == "C-0005"
    assert report.primary_path["edges"][0]["ontology_id"] == "UBERON:8410010"
    assert report.why_stopped["code"] == "ORGAN_FUNCTION_UNMODELED"
    assert report.unknown["organ_function"] == "UNMODELED"
    assert report.host_effect["knowledge_status"] == "UNKNOWN"
    assert report.second_path != "NO_SECOND_ADMISSIBLE_PATH"
    second_obj = report.second_path["edges"][-1]["object"]
    primary_obj = report.primary_path["edges"][-1]["object"]
    assert {primary_obj, second_obj} == {"OVARIAN_TUMOR_PRESENT", "PERITONEAL_IMPLANT_PRESENT"}
    assert "anatomical_trajectory" in report.second_path["differ_in"] or "mechanism" in report.second_path["differ_in"]
    assert "organ_failure" not in str(report.as_dict())


def test_cannot_name_sample_origin_on_claim():
    import yaml

    claim = yaml.safe_load((LEDGER / "C-0005.yaml").read_text(encoding="utf-8"))
    claim["names_sample_origin"] = True
    report = gate_claim(claim)
    assert report.verdict == "BLOCKED"
    assert "origin" in report.reason
