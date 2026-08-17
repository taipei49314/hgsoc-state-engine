from pathlib import Path

from engine.claim_lint import lint_claim_path, lint_ledger

ROOT = Path(__file__).resolve().parents[1]


def test_seed_ledger_all_pass():
    results = lint_ledger()
    assert results, "expected curated claims"
    failed = [(path.name, r.verdict, r.reason) for path, r in results if r.verdict != "PASS"]
    assert failed == []


def test_llm_cannot_upgrade_to_supported():
    result = lint_claim_path(ROOT / "fixtures" / "blocked" / "llm_upgrade_supported.yaml")
    assert result.verdict == "BLOCKED"
    assert "LLM extract cannot auto-upgrade" in result.reason


def test_cannot_auto_add_host_effect():
    result = lint_claim_path(ROOT / "fixtures" / "blocked" / "claim_host_effect_eligible.yaml")
    assert result.verdict == "BLOCKED"
    assert "host_effect" in result.reason


def test_contradictions_cannot_be_dropped():
    result = lint_claim_path(ROOT / "fixtures" / "blocked" / "claim_dropped_contradictions.yaml")
    assert result.verdict == "BLOCKED"
    assert "contradictions" in result.reason


def test_hrd_does_not_name_functional_hr():
    result = lint_claim_path(ROOT / "evidence" / "claims" / "C-0002.yaml")
    assert result.verdict == "PASS"
    assert result.naming_status == "UNNAMED"


def test_fork_mechanism_stays_unnamed_on_human_slice():
    result = lint_claim_path(ROOT / "evidence" / "claims" / "C-0001.yaml")
    assert result.verdict == "PASS"
    assert result.knowledge_status == "SUPPORTED_IN_MODEL"
    assert result.naming_status == "UNNAMED"
