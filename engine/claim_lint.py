"""Phase 2 claim ledger linter. LLM extracts cannot upgrade knowledge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.lint import LintResult, load_registry

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "claim_id",
    "subject",
    "relation",
    "object",
    "source_layer",
    "target_layer",
    "context",
    "evidence",
    "assumptions",
    "contradictions",
    "falsify",
    "transfer_gaps",
    "knowledge_status",
    "naming_status",
    "allowed_as_parent",
    "host_effect_eligible",
    "curator_status",
    "source",
]
HUMAN_SUPPORTED = {"SUPPORTED", "OBSERVED"}
FIT_WEAK = {"FIT_0", "FIT_1"}


def _id(node: Any) -> str | None:
    if isinstance(node, dict):
        value = node.get("state_id")
        return value if isinstance(value, str) else None
    return None


def lint_claim(claim: dict[str, Any], registry: dict[str, Any] | None = None) -> LintResult:
    registry = registry or load_registry()
    claim_id = claim.get("claim_id") if isinstance(claim.get("claim_id"), str) else None
    missing = [key for key in REQUIRED if key not in claim]
    if missing:
        return LintResult("BLOCKED", f"missing claim fields: {', '.join(missing)}", claim_id)

    if claim.get("source") == "llm_extract" and claim.get("knowledge_status") in HUMAN_SUPPORTED:
        return LintResult("BLOCKED", "LLM extract cannot auto-upgrade to SUPPORTED", claim_id)
    if claim.get("source") == "llm_extract" and claim.get("curator_status") == "ADMITTED":
        return LintResult("BLOCKED", "LLM extract cannot self-admit", claim_id)
    if claim.get("host_effect_eligible") is True:
        return LintResult("BLOCKED", "LLM/curator must not auto-add host_effect", claim_id)
    if claim.get("contradictions") is None:
        return LintResult("BLOCKED", "contradictions cannot be dropped", claim_id)
    if not isinstance(claim.get("contradictions"), list):
        return LintResult("BLOCKED", "contradictions must be a list", claim_id)

    subject = _id(claim.get("subject"))
    obj = _id(claim.get("object"))
    if not subject or subject not in registry["by_id"]:
        return LintResult("REJECTED", "unknown subject state name", claim_id)
    if not obj or obj not in registry["by_id"]:
        return LintResult("REJECTED", "unknown object state name", claim_id)

    evidence = claim.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return LintResult("BLOCKED", "evidence[] required", claim_id)
    fits = []
    for i, item in enumerate(evidence):
        if not isinstance(item, dict):
            return LintResult("BLOCKED", f"evidence[{i}] must be an object", claim_id)
        if not item.get("PMID") and not item.get("DOI") and not item.get("dataset_accession"):
            return LintResult("BLOCKED", f"evidence[{i}] needs PMID, DOI, or accession", claim_id)
        fit = item.get("evidence_fit")
        if fit not in {"FIT_0", "FIT_1", "FIT_2", "FIT_3", "FIT_4"}:
            return LintResult("BLOCKED", f"evidence[{i}] missing evidence_fit", claim_id)
        fits.append(fit)

    if claim.get("knowledge_status") in HUMAN_SUPPORTED and any(f in FIT_WEAK for f in fits):
        return LintResult(
            "BLOCKED",
            "FIT_0/FIT_1 cannot be knowledge_status SUPPORTED for human untreated HGSOC",
            claim_id,
        )

    gaps = claim.get("transfer_gaps")
    if not isinstance(gaps, list):
        return LintResult("BLOCKED", "transfer_gaps must be a list", claim_id)
    if any(f in FIT_WEAK for f in fits) and not gaps:
        return LintResult("BLOCKED", "model evidence requires an explicit transfer_gap", claim_id)

    falsify = claim.get("falsify")
    if not isinstance(falsify, dict) or not falsify.get("observable"):
        return LintResult("BLOCKED", "falsify.observable required", claim_id)

    ctx = claim.get("context") or {}
    if ctx.get("disease") not in {"HGSOC", "high-grade serous ovarian carcinoma"}:
        return LintResult("CONTEXT_MISMATCH", "claim disease_context must be HGSOC", claim_id)

    if claim.get("naming_status") == "NAMED" and claim.get("knowledge_status") not in HUMAN_SUPPORTED:
        return LintResult("BLOCKED", "cannot NAMED without human-grade knowledge_status", claim_id)

    return LintResult("PASS", "claim admitted to ledger", claim_id, claim.get("naming_status"), claim.get("knowledge_status"))


def lint_claim_path(path: Path, registry: dict[str, Any] | None = None) -> LintResult:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return LintResult("REJECTED", "claim must be a mapping", None)
    return lint_claim(raw, registry)


def lint_ledger(claims_dir: Path | None = None) -> list[tuple[Path, LintResult]]:
    claims_dir = claims_dir or (ROOT / "evidence" / "claims")
    out = []
    for path in sorted(claims_dir.glob("*.yaml")):
        out.append((path, lint_claim_path(path)))
    return out
