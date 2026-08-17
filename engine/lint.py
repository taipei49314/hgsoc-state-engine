"""Phase 1 naming linter. No path engine. No support masses."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "spec" / "state_registry.yaml"

HGSOC_OK = {"HGSOC", "high-grade serous ovarian carcinoma"}
UNTREATED_OK = {"untreated", "UNTREATED_BASELINE", "treatment-naive", "treatment_naive"}
DISEASE_REJECT = {
    "ovarian cancer",
    "epithelial ovarian cancer",
    "serous cancer",
    "gynecologic cancer",
}
TREATED_REJECT = {
    "post-NACT",
    "post_NACT",
    "treated",
    "recurrent",
    "on_treatment",
    "currently_off_treatment",
}

FORBIDDEN_UPGRADE = {
    "organ_failure": ("BLOCKED", "anatomy is not organ function"),
    "ORGAN_FAILURE": ("BLOCKED", "anatomy is not organ function"),
    "ovarian_failure": ("BLOCKED", "anatomy is not organ function"),
    "systemic_inflammation": ("SCALE_JUMP_REJECTED", "local signal must not become systemic"),
    "overall_survival": ("OUTCOME_LEAKAGE_REJECTED", "outcomes cannot support a state edge"),
    "platinum_sensitive": ("OUTCOME_LEAKAGE_REJECTED", "clinical outcome is not an untreated state"),
}


@dataclass
class LintResult:
    verdict: str
    reason: str
    state_id: str | None
    naming_status: str | None = None
    knowledge_status: str | None = None
    coverage_status: str | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "state_id": self.state_id,
            "naming_status": self.naming_status,
            "knowledge_status": self.knowledge_status,
            "coverage_status": self.coverage_status,
            "notes": self.notes,
        }


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != "state_registry":
        raise ValueError("state_registry.yaml missing or wrong kind")
    by_id = {row["id"]: row for row in data["states"]}
    return {"raw": data, "by_id": by_id, "never": set(data.get("never_register") or [])}


def _present(instance: dict[str, Any], key: str) -> bool:
    value = instance.get(key)
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _context_gate(instance: dict[str, Any], spec: dict[str, Any]) -> LintResult | None:
    ctx = instance.get("context") or {}
    disease = ctx.get("disease")
    treatment = ctx.get("treatment")
    needs_slice = spec.get("state_type") not in {"CONTEXT"} and instance.get("naming_status") == "NAMED"

    if isinstance(disease, str) and disease.strip().lower() in DISEASE_REJECT:
        return LintResult("CONTEXT_MISMATCH", "generic disease is not HGSOC", instance.get("state_id"))
    if needs_slice and disease not in HGSOC_OK:
        return LintResult("CONTEXT_MISMATCH", "NAMED states require explicit HGSOC context", instance.get("state_id"))
    if isinstance(treatment, str) and treatment in TREATED_REJECT:
        return LintResult("OUT_OF_FROZEN_SLICE", "not untreated baseline", instance.get("state_id"))
    if needs_slice and treatment not in UNTREATED_OK:
        return LintResult("OUT_OF_FROZEN_SLICE", "NAMED states require untreated baseline", instance.get("state_id"))
    return None


def lint_state(instance: dict[str, Any], registry: dict[str, Any] | None = None) -> LintResult:
    registry = registry or load_registry()
    state_id = instance.get("state_id")
    if not state_id or not isinstance(state_id, str):
        return LintResult("REJECTED", "missing state_id", None)
    if state_id in registry["never"] or state_id not in registry["by_id"]:
        return LintResult("REJECTED", "unknown state name", state_id)

    spec = registry["by_id"][state_id]
    gated = _context_gate(instance, spec)
    if gated:
        return gated

    upgrade = instance.get("upgrade_to")
    if isinstance(upgrade, str) and upgrade in FORBIDDEN_UPGRADE:
        verdict, reason = FORBIDDEN_UPGRADE[upgrade]
        return LintResult(verdict, reason, state_id)

    naming = instance.get("naming_status") or spec.get("default_naming_status") or "UNNAMED"
    knowledge = instance.get("knowledge_status") or spec.get("default_knowledge_status") or "UNKNOWN"
    coverage = instance.get("coverage_status") or spec.get("default_coverage_status")

    if spec.get("state_type") == "HOST_EFFECT":
        return _lint_host_effect(instance, spec, naming, knowledge, coverage)

    if spec.get("does_not_name") == "HOST_EFFECT":
        he = instance.get("host_effect") or {}
        if he.get("naming_status") == "NAMED":
            return LintResult(
                "BLOCKED",
                "HOST_OBSERVATION must not name HOST_EFFECT",
                state_id,
                naming,
                knowledge,
            )
        if he and he.get("knowledge_status") not in (None, "UNKNOWN"):
            if he.get("knowledge_status") not in {"OBSERVED", "ASSOCIATED", "UNKNOWN"}:
                return LintResult("BLOCKED", "observation cannot upgrade host_effect", state_id, naming, knowledge)

    if naming != "NAMED":
        return LintResult("PASS", "admitted as UNNAMED", state_id, naming, knowledge, coverage)

    inferred = instance.get("inferred_from")
    forbidden = set(spec.get("forbidden_inference_from") or [])
    if inferred in forbidden:
        verdict = spec.get("forbidden_inference_verdict") or spec.get("named_without_direct_evidence") or "BLOCKED"
        return LintResult(verdict, f"forbidden inference from {inferred}", state_id, "UNNAMED", "UNKNOWN")

    required = spec.get("required_to_name") or []
    missing = [key for key in required if not _present(instance, key)]
    if missing:
        verdict = spec.get("missing_required") or "BLOCKED"
        return LintResult(verdict, f"missing required fields: {', '.join(missing)}", state_id, "UNNAMED", "UNKNOWN")

    any_ev = spec.get("required_to_name_any_evidence") or []
    if any_ev:
        kinds = set(instance.get("evidence_kinds") or [])
        if kinds.isdisjoint(any_ev):
            verdict = spec.get("named_without_direct_evidence") or "BLOCKED"
            return LintResult(
                verdict,
                "NAMED requires direct evidence at this layer",
                state_id,
                "UNNAMED",
                "UNKNOWN",
            )

    return LintResult("PASS", "named under permit", state_id, "NAMED", knowledge, coverage)


def _lint_host_effect(
    instance: dict[str, Any],
    spec: dict[str, Any],
    naming: str,
    knowledge: str,
    coverage: str | None,
) -> LintResult:
    coverage = coverage or spec.get("default_coverage_status") or "GATE_ONLY"
    if naming == "NAMED":
        if instance.get("h3_packet_complete") is True:
            return LintResult("PASS", "H3 packet asserted", instance.get("state_id"), "NAMED", "SUPPORTED", coverage)
        return LintResult(
            spec.get("named_without_H3") or "BLOCKED",
            "host_effect may be NAMED only at H3",
            instance.get("state_id"),
            "UNNAMED",
            "UNKNOWN",
            coverage,
        )
    return LintResult(
        "PASS",
        "host_effect default UNNAMED + UNKNOWN",
        instance.get("state_id"),
        "UNNAMED",
        "UNKNOWN",
        coverage,
    )


def lint_path(path: Path, registry: dict[str, Any] | None = None) -> LintResult:
    instance = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(instance, dict):
        return LintResult("REJECTED", "instance must be a mapping", None)
    return lint_state(instance, registry)


def main(argv: list[str] | None = None) -> int:
    import json
    import sys

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m engine.lint <state.yaml>", file=sys.stderr)
        return 2
    result = lint_path(Path(args[0]))
    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
