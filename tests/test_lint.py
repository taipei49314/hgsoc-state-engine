from pathlib import Path

from engine.lint import lint_path, load_registry

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"


def test_registry_loads_first_batch():
    reg = load_registry()
    for state_id in (
        "CTX_HGSOC",
        "CTX_UNTREATED_BASELINE",
        "HRD_HIGH",
        "FUNCTIONAL_HR_DEFICIENT",
        "FORK_COLLAPSE_PRESENT",
        "TP53_PATHOGENIC_VARIANT_OBSERVED",
        "G2M_CHECKPOINT_DEFECTIVE",
        "A1_PROLIFERATIVE",
        "A2_INVASIVE_MARGIN",
        "A3_IMMUNE_EXCLUDED",
        "A4_NOT_EVALUATED",
        "STIC_LESION",
        "STIC_PRESENT",
        "HOST_EFFECT",
        "HOST_OBSERVATION_ASCITES",
    ):
        assert state_id in reg["by_id"]


def test_unknown_state_name_rejected():
    result = lint_path(FIX / "rejected" / "unknown_name.yaml")
    assert result.verdict == "REJECTED"
    assert result.reason == "unknown state name"


def test_never_register_rejected():
    result = lint_path(FIX / "rejected" / "never_register.yaml")
    assert result.verdict == "REJECTED"


def test_hrd_high_missing_cutoff_blocked():
    result = lint_path(FIX / "blocked" / "hrd_high_no_cutoff.yaml")
    assert result.verdict == "BLOCKED"
    assert "missing required fields" in result.reason


def test_hrd_high_complete_passes():
    result = lint_path(FIX / "pass" / "hrd_high_complete.yaml")
    assert result.verdict == "PASS"
    assert result.naming_status == "NAMED"


def test_fork_collapse_from_brca1_blocked():
    result = lint_path(FIX / "blocked" / "fork_collapse_from_brca1.yaml")
    assert result.verdict == "BLOCKED"
    assert result.naming_status == "UNNAMED"


def test_fork_collapse_without_direct_evidence_blocked():
    result = lint_path(FIX / "blocked" / "fork_collapse_no_direct_assay.yaml")
    assert result.verdict == "BLOCKED"


def test_functional_hr_from_hrd_unknown():
    result = lint_path(FIX / "unknown" / "functional_hr_from_hrd.yaml")
    assert result.verdict == "UNKNOWN"


def test_host_effect_defaults_unnamed_unknown():
    result = lint_path(FIX / "unmodeled" / "host_effect_default.yaml")
    assert result.verdict == "PASS"
    assert result.naming_status == "UNNAMED"
    assert result.knowledge_status == "UNKNOWN"
    assert result.coverage_status == "GATE_ONLY"


def test_host_effect_named_without_h3_blocked():
    result = lint_path(FIX / "blocked" / "host_effect_named_without_h3.yaml")
    assert result.verdict == "BLOCKED"
    assert result.naming_status == "UNNAMED"
    assert result.knowledge_status == "UNKNOWN"


def test_ascites_observation_does_not_name_effect():
    result = lint_path(FIX / "pass" / "ascites_observation.yaml")
    assert result.verdict == "PASS"
    assert result.naming_status == "NAMED"


def test_generic_ovarian_context_mismatch():
    result = lint_path(FIX / "context_mismatch" / "generic_ovarian.yaml")
    assert result.verdict == "CONTEXT_MISMATCH"


def test_stic_with_pathology_named():
    result = lint_path(FIX / "pass" / "stic_pathology.yaml")
    assert result.verdict == "PASS"
    assert result.naming_status == "NAMED"
    assert "ANATOMICAL_STATE_NAMED" in result.notes


def test_anatomy_is_not_organ_failure():
    result = lint_path(FIX / "blocked" / "anatomy_to_organ_failure.yaml")
    assert result.verdict == "BLOCKED"


def test_local_ifn_not_systemic():
    result = lint_path(FIX / "blocked" / "local_ifn_to_systemic.yaml")
    assert result.verdict == "SCALE_JUMP_REJECTED"


def test_survival_not_an_edge_mass():
    result = lint_path(FIX / "blocked" / "survival_leak.yaml")
    assert result.verdict == "OUTCOME_LEAKAGE_REJECTED"
