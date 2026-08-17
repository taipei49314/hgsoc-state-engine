"""Phase 3 gate engine. One claim packet → one fail-closed verdict."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.claim_lint import _id, lint_claim
from engine.lint import (
    DISEASE_REJECT,
    FORBIDDEN_UPGRADE,
    TREATED_REJECT,
    UNTREATED_OK,
    LintResult,
    lint_state,
    load_registry,
)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_VERSION = "0.3.0-phase3"
ALLOWED_PAIRS = {("L1", "L2"), ("L2", "L3"), ("L3", "L4"), ("L4", "L5A"), ("L5A", "L6")}
ENTAIL = {"entails", "causes", "is", "increases_likelihood_of"}
UNMODELED_LAYERS = [
    "L5B_organ_function",
    "organ_function_dynamics",
    "systemic_immune_dynamics",
    "whole_body_metabolism",
    "cachexia_dynamics",
    "hematologic_coagulation_effects",
    "endocrine_feedback",
    "pharmacokinetics",
    "treatment_driven_evolution",
]
HOST_DEFAULT = {
    "naming_status": "UNNAMED",
    "knowledge_status": "UNKNOWN",
    "coverage_status": "GATE_ONLY",
}


@dataclass
class GateStep:
    gate: str
    status: str
    reason: str


@dataclass
class GateReport:
    verdict: str
    reason: str
    claim_id: str | None
    gates: list[GateStep] = field(default_factory=list)
    host_effect: dict[str, str] = field(default_factory=lambda: dict(HOST_DEFAULT))
    unmodeled_layers: list[str] = field(default_factory=lambda: list(UNMODELED_LAYERS))
    receipt: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "claim_id": self.claim_id,
            "gates": [asdict(g) for g in self.gates],
            "host_effect": self.host_effect,
            "unmodeled_layers": self.unmodeled_layers,
            "receipt": self.receipt,
        }


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_contradictions(path: Path | None = None) -> list[dict[str, Any]]:
    folder = path or (ROOT / "evidence" / "contradictions")
    rows = []
    if folder.is_dir():
        for file in sorted(folder.glob("*.yaml")):
            raw = _load_yaml(file)
            if isinstance(raw, dict):
                rows.append(raw)
    return rows


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(claim_id: str | None, steps: list[GateStep], verdict: str, reason: str, host: dict[str, str] | None = None) -> GateReport:
    report = GateReport(verdict, reason, claim_id, steps, host or dict(HOST_DEFAULT))
    report.receipt = _receipt(claim_id, report)
    return report


def _receipt(claim_id: str | None, report: GateReport) -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "state_registry_hash": _sha(ROOT / "spec" / "state_registry.yaml"),
        "claim_id": claim_id,
        "verdict": report.verdict,
        "host_effect_status": report.host_effect,
        "unmodeled_layers": report.unmodeled_layers,
        "blocked_or_failed_gates": [asdict(g) for g in report.gates if g.status != "PASS"],
    }


def gate_claim(
    claim: dict[str, Any],
    registry: dict[str, Any] | None = None,
    contradictions: list[dict[str, Any]] | None = None,
) -> GateReport:
    registry = registry or load_registry()
    contradictions = contradictions if contradictions is not None else load_contradictions()
    claim_id = claim.get("claim_id") if isinstance(claim.get("claim_id"), str) else None
    steps: list[GateStep] = []
    ctx = claim.get("context") or {}
    disease = ctx.get("disease")
    treatment = ctx.get("treatment")
    subject = _id(claim.get("subject"))
    obj = _id(claim.get("object"))
    relation = (claim.get("relation") or {}).get("type")

    if isinstance(disease, str) and disease.strip().lower() in DISEASE_REJECT:
        steps.append(GateStep("G0", "CONTEXT_MISMATCH", "generic disease is not HGSOC"))
        return _fail(claim_id, steps, "CONTEXT_MISMATCH", steps[-1].reason)
    if disease not in {"HGSOC", "high-grade serous ovarian carcinoma"}:
        steps.append(GateStep("G0", "CONTEXT_MISMATCH", "disease must be explicit HGSOC"))
        return _fail(claim_id, steps, "CONTEXT_MISMATCH", steps[-1].reason)
    steps.append(GateStep("G0", "PASS", "HGSOC"))

    if isinstance(treatment, str) and treatment in TREATED_REJECT:
        steps.append(GateStep("G1", "OUT_OF_FROZEN_SLICE", "not untreated baseline"))
        return _fail(claim_id, steps, "OUT_OF_FROZEN_SLICE", steps[-1].reason)
    if treatment not in UNTREATED_OK:
        steps.append(GateStep("G1", "OUT_OF_FROZEN_SLICE", "treatment_context must be untreated"))
        return _fail(claim_id, steps, "OUT_OF_FROZEN_SLICE", steps[-1].reason)
    steps.append(GateStep("G1", "PASS", "untreated"))

    sub_spec = registry["by_id"].get(subject or "")
    obj_spec = registry["by_id"].get(obj or "")
    if sub_spec and obj_spec:
        if (
            sub_spec.get("state_type") == "ASSAY_CLASSIFICATION"
            and obj_spec.get("state_type") == "BIOLOGICAL_PROCESS_STATE"
            and relation in ENTAIL
        ):
            steps.append(GateStep("G2", "UNKNOWN", "assay classification is not a mechanism state"))
            return _fail(claim_id, steps, "UNKNOWN", steps[-1].reason)
    steps.append(GateStep("G2", "PASS", "state types distinguished"))

    packet = lint_claim(claim, registry)
    if packet.verdict != "PASS":
        steps.append(GateStep("packet", packet.verdict, packet.reason))
        return _fail(claim_id, steps, packet.verdict, packet.reason)
    steps.append(GateStep("packet", "PASS", packet.reason))

    src = claim.get("source_layer")
    tgt = claim.get("target_layer")
    if tgt == "L5B":
        steps.append(GateStep("G4", "UNMODELED", "organ function is UNMODELED in v1"))
        return _fail(claim_id, steps, "UNMODELED", steps[-1].reason)
    if tgt == "L7" or src == "L7":
        steps.append(GateStep("G4", "OUT_OF_SCOPE", "clinical outcome is OUT_OF_SCOPE"))
        return _fail(claim_id, steps, "OUT_OF_SCOPE", steps[-1].reason)
    empirical = claim.get("edge_type") == "EMPIRICAL_CROSS_SCALE_BRIDGE" and claim.get("direct_human_data") is True
    pair_ok = src == tgt or (src, tgt) in ALLOWED_PAIRS or empirical
    if not pair_ok:
        steps.append(GateStep("G4", "SCALE_JUMP_REJECTED", f"scale jump {src} → {tgt}"))
        return _fail(claim_id, steps, "SCALE_JUMP_REJECTED", steps[-1].reason)
    steps.append(GateStep("G4", "PASS", f"{src} → {tgt}"))

    if claim.get("knowledge_status") == "CONFLICTED":
        steps.append(GateStep("G5", "CONFLICTED", "Conflicting evidence"))
        return _fail(claim_id, steps, "CONFLICTED", steps[-1].reason)
    for row in contradictions:
        blocked = row.get("blocks_inference") or {}
        if blocked.get("from") == subject and blocked.get("to") == obj and relation in ENTAIL:
            steps.append(GateStep("G5", "UNKNOWN", row.get("statement") or "contradicted inference"))
            return _fail(claim_id, steps, "UNKNOWN", steps[-1].reason)
    steps.append(GateStep("G5", "PASS", "contradictions retained"))

    upgrade = claim.get("upgrade_to")
    if isinstance(upgrade, str) and upgrade in FORBIDDEN_UPGRADE:
        verdict, reason = FORBIDDEN_UPGRADE[upgrade]
        steps.append(GateStep("G4", verdict, reason))
        return _fail(claim_id, steps, verdict, reason)

    if claim.get("naming_status") == "NAMED" and obj:
        named = lint_state(
            {
                "state_id": obj,
                "naming_status": "NAMED",
                "context": ctx,
                "inferred_from": claim.get("inferred_from"),
                "evidence_kinds": claim.get("evidence_kinds") or [],
                **{k: claim[k] for k in ("assay_name", "assay_version", "cutoff", "specimen") if k in claim},
            },
            registry,
        )
        if named.verdict != "PASS":
            steps.append(GateStep("G3", named.verdict, named.reason))
            return _fail(claim_id, steps, named.verdict, named.reason)
    steps.append(GateStep("G3", "PASS", "naming permit"))

    host = dict(HOST_DEFAULT)
    if obj_spec and obj_spec.get("state_type") == "HOST_EFFECT":
        if claim.get("h3_packet_complete") is True:
            host = {"naming_status": "NAMED", "knowledge_status": "SUPPORTED", "coverage_status": "GATE_ONLY"}
            steps.append(GateStep("G7", "PASS", "H3 packet"))
        else:
            steps.append(GateStep("G7", "BLOCKED", "host_effect NAMED only at H3"))
            report = _fail(claim_id, steps, "BLOCKED", steps[-1].reason, host)
            return report
    elif obj_spec and obj_spec.get("state_type") == "HOST_OBSERVATION":
        steps.append(GateStep("G7", "PASS", "HOST_OBSERVATION does not name host_effect"))
    else:
        steps.append(GateStep("G7", "PASS", "host_effect remains UNKNOWN"))

    report = GateReport("PASS", "all gates passed", claim_id, steps, host)
    report.receipt = _receipt(claim_id, report)
    return report


def gate_path(path: Path) -> GateReport:
    raw = _load_yaml(path)
    if not isinstance(raw, dict):
        return GateReport("REJECTED", "packet must be a mapping", None)
    return gate_claim(raw)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m engine.gates <claim.yaml>", file=sys.stderr)
        return 2
    report = gate_path(Path(args[0]))
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
