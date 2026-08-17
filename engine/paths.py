"""Phase 4 path engine. Walk gated edges only. Do not invent a second path."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.claim_lint import _id
from engine.gates import (
    ENGINE_VERSION as GATE_ENGINE_VERSION,
    HOST_DEFAULT,
    UNMODELED_LAYERS,
    GateReport,
    gate_claim,
    load_contradictions,
)
from engine.lint import (
    DISEASE_REJECT,
    HGSOC_OK,
    TREATED_REJECT,
    UNTREATED_OK,
    load_registry,
)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_VERSION = "0.5.0-phase5"
DEFAULT_CLAIMS = ROOT / "evidence" / "claims"
ONTOLOGY_LOCK = ROOT / "evidence" / "ontology-lock.json"
MAX_DEPTH = 8
PARENT_RELATIONS = {"increases_likelihood_of", "entails", "causes", "is"}
FIT_RANK = {"FIT_0": 0, "FIT_1": 1, "FIT_2": 2, "FIT_3": 3, "FIT_4": 4}
LAYER_RANK = {
    "L0": 0,
    "L1": 1,
    "L2": 2,
    "L3": 3,
    "L4": 4,
    "L5A": 5,
    "L5B": 6,
    "L6": 7,
    "L7": 8,
}
NEXT_LAYER = {
    "L1": "L2",
    "L2": "L3",
    "L3": "L4",
    "L4": "L5A",
    "L5A": "L5B",
    "L5B": "L6",
    "L6": "L7",
}
UNLOCK = {
    "L2": ["process-layer assay", "threshold", "specimen on this untreated HGSOC slice"],
    "L3": ["marker_panel", "assay", "cell_population", "threshold", "location"],
    "L4": ["operational region or tissue evidence on this specimen"],
    "L5A": ["pathology, cytology, imaging, surgery, or matched sequencing"],
    "L5B": ["organ function remains UNMODELED in v1"],
    "L6": ["H3 packet for host_effect; HOST_OBSERVATION is a separate type"],
    "L7": ["clinical outcome is OUT_OF_SCOPE"],
}
OUT_OF_SCOPE = [
    "L7_clinical_outcomes",
    "survival",
    "treatment_efficacy_as_state",
    "personal_treatment_recommendation",
]
AXIS_DEFAULTS = {
    "A1": {
        "state_id": "A1_UNKNOWN",
        "naming_status": "UNNAMED",
        "knowledge_status": "UNKNOWN",
        "reason": "no cell-state packet on this query",
    },
    "A2": {
        "state_id": "A2_UNKNOWN_REGION",
        "naming_status": "UNNAMED",
        "knowledge_status": "UNKNOWN",
        "reason": "no spatial-region packet on this query",
    },
    "A3": {
        "state_id": "A3_UNKNOWN",
        "naming_status": "UNNAMED",
        "knowledge_status": "UNKNOWN",
        "reason": "no local immune packet on this query",
    },
    "A4": {
        "state_id": "A4_NOT_EVALUATED",
        "naming_status": "UNNAMED",
        "knowledge_status": "UNKNOWN",
        "reason": "preparedness not evaluated; not a platinum_sensitive label",
    },
}
FORBIDDEN_OUTPUT_KEYS = {
    "biological_support",
    "support_mass",
    "host_effect_confidence",
    "probability_of_organ_failure",
}


@dataclass
class RankTuple:
    weakest_evidence_fit: int
    context_exactness: int
    direct_human_edge_count: int
    same_patient_linkage: int
    unresolved_transfer_gap_count: int
    contradiction_burden: int
    assumption_count: int
    path_length: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)

    def sort_key(self, claim_ids: str) -> tuple[Any, ...]:
        return (
            -self.weakest_evidence_fit,
            -self.context_exactness,
            -self.direct_human_edge_count,
            -self.same_patient_linkage,
            self.unresolved_transfer_gap_count,
            self.contradiction_burden,
            self.assumption_count,
            self.path_length,
            claim_ids,
        )


@dataclass
class WalkedPath:
    states: list[str]
    claims: list[dict[str, Any]]
    rank: RankTuple

    @property
    def claim_ids(self) -> list[str]:
        return [c["claim_id"] for c in self.claims]

    def as_dict(self) -> dict[str, Any]:
        edges = []
        for claim in self.claims:
            obj_node = claim.get("object") if isinstance(claim.get("object"), dict) else {}
            edges.append(
                {
                    "claim_id": claim.get("claim_id"),
                    "subject": _id(claim.get("subject")),
                    "relation": (claim.get("relation") or {}).get("type"),
                    "object": _id(claim.get("object")),
                    "ontology_id": obj_node.get("ontology_id"),
                    "source_layer": claim.get("source_layer"),
                    "target_layer": claim.get("target_layer"),
                    "evidence": _edge_evidence(claim),
                    "assumptions": claim.get("assumptions") or [],
                    "contradictions": claim.get("contradictions") or [],
                    "falsify": claim.get("falsify") or {},
                    "transfer_gaps": claim.get("transfer_gaps") or [],
                    "knowledge_status": claim.get("knowledge_status"),
                    "naming_status": claim.get("naming_status"),
                }
            )
        return {
            "states": list(self.states),
            "edges": edges,
            "rank_tuple": self.rank.as_dict(),
        }


@dataclass
class PathReport:
    verdict: str
    reason: str
    query_id: str | None
    context_header: dict[str, Any] = field(default_factory=dict)
    frozen_slice: dict[str, Any] = field(default_factory=dict)
    primary_path: dict[str, Any] | None = None
    second_path: dict[str, Any] | str | None = None
    divergence_point: str | None = None
    convergence_point: str | None = None
    weakest_link: dict[str, Any] | None = None
    blocked_continuation: list[dict[str, Any]] = field(default_factory=list)
    deepest_reached_layer: str | None = None
    deepest_named_layer: str | None = None
    why_stopped: dict[str, Any] = field(default_factory=dict)
    unmodeled_layers: list[str] = field(default_factory=lambda: list(UNMODELED_LAYERS))
    unknown: dict[str, Any] = field(default_factory=dict)
    out_of_scope: list[str] = field(default_factory=lambda: list(OUT_OF_SCOPE))
    host_effect: dict[str, str] = field(default_factory=lambda: dict(HOST_DEFAULT))
    receipt: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "verdict": self.verdict,
            "reason": self.reason,
            "query_id": self.query_id,
            "context_header": self.context_header,
            "frozen_slice": self.frozen_slice,
            "primary_path": self.primary_path,
            "second_path": self.second_path,
            "divergence_point": self.divergence_point,
            "convergence_point": self.convergence_point,
            "weakest_link": self.weakest_link,
            "blocked_continuation": self.blocked_continuation,
            "deepest_reached_layer": self.deepest_reached_layer,
            "deepest_named_layer": self.deepest_named_layer,
            "why_stopped": self.why_stopped,
            "unmodeled_layers": self.unmodeled_layers,
            "unknown": self.unknown,
            "out_of_scope": self.out_of_scope,
            "host_effect": self.host_effect,
            "receipt": self.receipt,
        }
        _assert_no_fake_mass(payload)
        return payload


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_no_fake_mass(payload: Any) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"forbidden output key {key}")
            _assert_no_fake_mass(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_fake_mass(item)


def _edge_evidence(claim: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in claim.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "PMID": item.get("PMID"),
                "DOI": item.get("DOI"),
                "dataset_accession": item.get("dataset_accession"),
                "evidence_type": item.get("evidence_type"),
                "evidence_fit": item.get("evidence_fit"),
                "model_system": item.get("model_system"),
                "assay": item.get("assay"),
                "endpoint": item.get("endpoint"),
                "raw_effect": item.get("raw_effect"),
                "confidence_interval": item.get("confidence_interval"),
                "limitations": item.get("limitations"),
            }
        )
    return rows


def load_claim_files(claim_dirs: list[Path] | None = None) -> list[tuple[Path, dict[str, Any]]]:
    dirs = claim_dirs or [DEFAULT_CLAIMS]
    rows: list[tuple[Path, dict[str, Any]]] = []
    seen: set[str] = set()
    for folder in dirs:
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.yaml")):
            raw = _load_yaml(path)
            if not isinstance(raw, dict):
                continue
            claim_id = raw.get("claim_id")
            if isinstance(claim_id, str) and claim_id in seen:
                continue
            if isinstance(claim_id, str):
                seen.add(claim_id)
            rows.append((path, raw))
    return rows


def _start_states(query: dict[str, Any]) -> list[str]:
    if isinstance(query.get("start_state"), str):
        return [query["start_state"]]
    raw = query.get("start_states") or []
    return [item for item in raw if isinstance(item, str)]


def _query_gate(query: dict[str, Any]) -> tuple[str, str] | None:
    ctx = query.get("context") or {}
    disease = ctx.get("disease")
    treatment = ctx.get("treatment")
    if isinstance(disease, str) and disease.strip().lower() in DISEASE_REJECT:
        return "CONTEXT_MISMATCH", "generic disease is not HGSOC"
    if disease not in HGSOC_OK:
        return "CONTEXT_MISMATCH", "disease must be explicit HGSOC"
    if isinstance(treatment, str) and treatment in TREATED_REJECT:
        return "OUT_OF_FROZEN_SLICE", "not untreated baseline"
    if treatment not in UNTREATED_OK:
        return "OUT_OF_FROZEN_SLICE", "treatment_context must be untreated"
    return None


def _fits(claim: dict[str, Any]) -> list[int]:
    ranks = []
    for item in claim.get("evidence") or []:
        if isinstance(item, dict):
            ranks.append(FIT_RANK.get(item.get("evidence_fit"), 0))
    return ranks or [0]


def _context_score(claim: dict[str, Any], query_ctx: dict[str, Any]) -> int:
    ctx = claim.get("context") or {}
    score = 0
    if ctx.get("disease") in HGSOC_OK:
        score += 2
    if ctx.get("treatment") in UNTREATED_OK:
        score += 2
    anatomy = ctx.get("anatomy")
    if anatomy and anatomy not in {"unspecified", "unknown"}:
        score += 1
    specimen = str(ctx.get("specimen") or "")
    if specimen in {"this_slice", "fresh_frozen", "FFPE"}:
        score += 1
    q_anatomy = query_ctx.get("anatomy")
    if q_anatomy and anatomy == q_anatomy:
        score += 1
    return score


def _rank(claims: list[dict[str, Any]], query_ctx: dict[str, Any]) -> RankTuple:
    weakest = min(min(_fits(c)) for c in claims) if claims else 0
    exact = min(_context_score(c, query_ctx) for c in claims) if claims else 0
    human = 0
    same = 0
    gaps = 0
    contradictions = 0
    assumptions = 0
    for claim in claims:
        fits = _fits(claim)
        if any(value >= 3 for value in fits):
            human += 1
        if any(value >= 4 for value in fits):
            same += 1
        for gap in claim.get("transfer_gaps") or []:
            if isinstance(gap, dict) and gap.get("resolved") is not True:
                gaps += 1
        contradictions += len(claim.get("contradictions") or [])
        if claim.get("knowledge_status") == "CONFLICTED":
            contradictions += 1
        assumptions += len(claim.get("assumptions") or [])
    return RankTuple(weakest, exact, human, same, gaps, contradictions, assumptions, len(claims))


def _pmids(claim: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for item in claim.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        for key in ("PMID", "DOI", "dataset_accession"):
            value = item.get(key)
            if isinstance(value, str) and value:
                out.add(f"{key}:{value}")
    return out


def _assumptions(claim: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in claim.get("assumptions") or []:
        if isinstance(row, dict) and row.get("statement"):
            out.add(str(row["statement"]))
        elif isinstance(row, str):
            out.add(row)
    return out


def _anatomy(claim: dict[str, Any]) -> str:
    return str((claim.get("context") or {}).get("anatomy") or "unspecified")


def _differ(primary: WalkedPath, other: WalkedPath) -> dict[str, Any] | None:
    """G6: second path must differ in at least one declared axis. Synonym rewrite is not a path."""
    shared = 0
    for left, right in zip(primary.claims, other.claims):
        if left.get("claim_id") == right.get("claim_id"):
            shared += 1
        else:
            break
    divergence = primary.states[shared] if shared < len(primary.states) else primary.states[-1]
    mechanism_a = tuple(_id(c.get("object")) for c in primary.claims)
    mechanism_b = tuple(_id(c.get("object")) for c in other.claims)
    anatomy_a = tuple(_anatomy(c) for c in primary.claims)
    anatomy_b = tuple(_anatomy(c) for c in other.claims)
    evidence_a = set().union(*(_pmids(c) for c in primary.claims)) if primary.claims else set()
    evidence_b = set().union(*(_pmids(c) for c in other.claims)) if other.claims else set()
    assume_a = set().union(*(_assumptions(c) for c in primary.claims)) if primary.claims else set()
    assume_b = set().union(*(_assumptions(c) for c in other.claims)) if other.claims else set()
    differ_in = []
    if mechanism_a != mechanism_b:
        differ_in.append("mechanism")
    if anatomy_a != anatomy_b:
        differ_in.append("anatomical_trajectory")
    if evidence_a != evidence_b:
        differ_in.append("evidence_set")
    if assume_a != assume_b:
        differ_in.append("assumption")
    if divergence != primary.states[0] or primary.states[0] != other.states[0]:
        differ_in.append("divergence_point")
    if not any(item in differ_in for item in ("mechanism", "anatomical_trajectory", "evidence_set", "assumption")):
        return None
    later_b = set(other.states[shared + 1 :])
    meet = [state for state in primary.states[shared + 1 :] if state in later_b]
    return {
        "differ_in": differ_in,
        "divergence_point": divergence,
        "convergence_point": meet[0] if meet else None,
    }


def _enumerate(start: str, adjacency: dict[str, list[dict[str, Any]]], query_ctx: dict[str, Any]) -> list[WalkedPath]:
    found: list[WalkedPath] = []

    def rec(node: str, claims: list[dict[str, Any]], states: list[str]) -> None:
        if len(claims) >= MAX_DEPTH:
            found.append(WalkedPath(states, claims, _rank(claims, query_ctx)))
            return
        nxt = adjacency.get(node) or []
        progressed = False
        for claim in nxt:
            obj = _id(claim.get("object"))
            if not obj or obj in states:
                continue
            progressed = True
            rec(obj, claims + [claim], states + [obj])
        if not progressed:
            found.append(WalkedPath(states, claims, _rank(claims, query_ctx)))

    rec(start, [], [start])
    return found


def _weakest_link(path: WalkedPath) -> dict[str, Any] | None:
    if not path.claims:
        return None
    best = None
    best_fit = 99
    for claim in path.claims:
        fit = min(_fits(claim))
        if fit < best_fit:
            best_fit = fit
            unresolved = [
                gap
                for gap in (claim.get("transfer_gaps") or [])
                if isinstance(gap, dict) and gap.get("resolved") is not True
            ]
            best = {
                "claim_id": claim.get("claim_id"),
                "subject": _id(claim.get("subject")),
                "object": _id(claim.get("object")),
                "weakest_evidence_fit": f"FIT_{best_fit}",
                "unresolved_transfer_gaps": unresolved,
            }
    return best


def _layer_of(state_id: str, registry: dict[str, Any]) -> str | None:
    spec = registry["by_id"].get(state_id) or {}
    layer = spec.get("layer")
    return layer if isinstance(layer, str) else None


def _deepest(states: list[str], registry: dict[str, Any], named: set[str]) -> tuple[str | None, str | None]:
    reached = None
    named_layer = None
    for state_id in states:
        layer = _layer_of(state_id, registry)
        if not layer:
            continue
        if reached is None or LAYER_RANK.get(layer, -1) >= LAYER_RANK.get(reached, -1):
            reached = layer
        if state_id in named:
            if named_layer is None or LAYER_RANK.get(layer, -1) >= LAYER_RANK.get(named_layer, -1):
                named_layer = layer
    return reached, named_layer


def _why_stopped(
    path: WalkedPath,
    registry: dict[str, Any],
    blocked: list[dict[str, Any]],
) -> dict[str, Any]:
    terminal = path.states[-1]
    layer = _layer_of(terminal, registry)
    nxt = NEXT_LAYER.get(layer or "", None)
    code = "NO_ADMITTED_CONTINUATION"
    if nxt == "L5B":
        code = "ORGAN_FUNCTION_UNMODELED"
    elif nxt == "L7":
        code = "OUT_OF_SCOPE"
    return {
        "code": code,
        "terminal_state": terminal,
        "terminal_layer": layer,
        "next_layer": nxt,
        "missing_unlock_packet": UNLOCK.get(nxt or "", []),
        "blocked_edges_from_terminal": blocked,
    }


def _snapshot_hash(files: list[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(files, key=lambda p: p.as_posix()):
        h.update(path.name.encode("utf-8"))
        h.update(path.read_bytes())
    return h.hexdigest()


def _ontology_versions() -> dict[str, Any]:
    if ONTOLOGY_LOCK.is_file():
        raw = json.loads(ONTOLOGY_LOCK.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    return {}


def _empty_report(query: dict[str, Any], verdict: str, reason: str) -> PathReport:
    query_id = query.get("query_id") if isinstance(query.get("query_id"), str) else None
    ctx = query.get("context") or {}
    report = PathReport(verdict, reason, query_id)
    report.context_header = {
        "disease": ctx.get("disease"),
        "treatment": ctx.get("treatment"),
        "species": ctx.get("species") or "human",
        "specimen": ctx.get("specimen"),
        "context_gate": verdict,
    }
    report.frozen_slice = {k: dict(v) for k, v in AXIS_DEFAULTS.items()}
    report.second_path = "NO_SECOND_ADMISSIBLE_PATH"
    report.host_effect = dict(HOST_DEFAULT)
    report.unknown = {
        "host_effect": "UNKNOWN",
        "unnamed_on_path": [],
        "organ_function": "UNMODELED",
    }
    return report


def run_query(
    query: dict[str, Any],
    claim_dirs: list[Path] | None = None,
    registry: dict[str, Any] | None = None,
    contradictions: list[dict[str, Any]] | None = None,
) -> PathReport:
    registry = registry or load_registry()
    contradictions = contradictions if contradictions is not None else load_contradictions()
    gated = _query_gate(query)
    if gated:
        report = _empty_report(query, gated[0], gated[1])
        report.receipt = _receipt(report, query, [], [], [], [])
        return report

    starts = _start_states(query)
    if not starts:
        report = _empty_report(query, "REJECTED", "query needs start_state or start_states")
        report.receipt = _receipt(report, query, [], [], [], [])
        return report
    for state_id in starts:
        if state_id not in registry["by_id"]:
            report = _empty_report(query, "REJECTED", f"unknown start state {state_id}")
            report.receipt = _receipt(report, query, [], [], [], [])
            return report

    loaded = load_claim_files(claim_dirs)
    query_ctx = query.get("context") or {}
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    blocked_edges: list[dict[str, Any]] = []
    gated_reports: dict[str, GateReport] = {}

    for path, claim in loaded:
        report = gate_claim(claim, registry, contradictions)
        cid = claim.get("claim_id")
        if isinstance(cid, str):
            gated_reports[cid] = report
        relation = (claim.get("relation") or {}).get("type")
        parent = bool(claim.get("allowed_as_parent")) and relation in PARENT_RELATIONS
        row = {
            "claim_id": cid,
            "file": path.name,
            "verdict": report.verdict,
            "reason": report.reason,
            "relation": relation,
            "allowed_as_parent": claim.get("allowed_as_parent"),
        }
        if report.verdict == "PASS" and parent:
            admitted.append(claim)
        else:
            if report.verdict != "PASS":
                blocked_edges.append(row)
            else:
                rejected.append(row)

    adjacency: dict[str, list[dict[str, Any]]] = {}
    for claim in admitted:
        src = _id(claim.get("subject"))
        if src:
            adjacency.setdefault(src, []).append(claim)

    walked: list[WalkedPath] = []
    for start in starts:
        walked.extend(_enumerate(start, adjacency, query_ctx))
    walked = [p for p in walked if p.claims]
    walked.sort(key=lambda p: p.rank.sort_key(",".join(p.claim_ids)))

    report = _empty_report(query, "PASS", "path search on gated edges")
    report.context_header["context_gate"] = "PASS"
    report.frozen_slice = {k: dict(v) for k, v in AXIS_DEFAULTS.items()}

    named: set[str] = set()
    for claim in admitted:
        if claim.get("naming_status") == "NAMED":
            obj = _id(claim.get("object"))
            if obj:
                named.add(obj)

    primary: WalkedPath | None = walked[0] if walked else None
    second: WalkedPath | None = None
    differ = None
    if primary:
        for candidate in walked[1:]:
            differ = _differ(primary, candidate)
            if differ:
                second = candidate
                break

    if primary:
        report.primary_path = primary.as_dict()
        report.weakest_link = _weakest_link(primary)
        terminal = primary.states[-1]
        blocked_from = [
            row
            for row in blocked_edges
            if any(_id(c.get("subject")) == terminal for _, c in loaded if c.get("claim_id") == row.get("claim_id"))
        ]
        report.blocked_continuation = blocked_from
        report.why_stopped = _why_stopped(primary, registry, blocked_from)
        reached, named_layer = _deepest(primary.states, registry, named)
        report.deepest_reached_layer = reached
        report.deepest_named_layer = named_layer
        unnamed = [s for s in primary.states if s not in named and _layer_of(s, registry) != "L0"]
        report.unknown = {
            "host_effect": "UNKNOWN",
            "unnamed_on_path": unnamed,
            "organ_function": "UNMODELED",
        }
    else:
        report.why_stopped = {
            "code": "NO_ADMITTED_PATH",
            "terminal_state": starts[0],
            "terminal_layer": _layer_of(starts[0], registry),
            "next_layer": NEXT_LAYER.get(_layer_of(starts[0], registry) or "", None),
            "missing_unlock_packet": UNLOCK.get(
                NEXT_LAYER.get(_layer_of(starts[0], registry) or "", "") or "",
                [],
            ),
            "blocked_edges_from_terminal": [
                row
                for row in blocked_edges
                if any(_id(c.get("subject")) == starts[0] for _, c in loaded if c.get("claim_id") == row.get("claim_id"))
            ],
        }
        report.deepest_reached_layer = _layer_of(starts[0], registry)
        report.unknown = {
            "host_effect": "UNKNOWN",
            "unnamed_on_path": list(starts),
            "organ_function": "UNMODELED",
        }

    if second and differ:
        report.second_path = second.as_dict()
        report.divergence_point = differ["divergence_point"]
        report.convergence_point = differ["convergence_point"]
        report.second_path["differ_in"] = differ["differ_in"]
    else:
        report.second_path = "NO_SECOND_ADMISSIBLE_PATH"

    report.host_effect = dict(HOST_DEFAULT)
    selected = []
    if primary:
        selected.append(primary.claim_ids)
    if second:
        selected.append(second.claim_ids)
    report.receipt = _receipt(
        report,
        query,
        [c.get("claim_id") for c in admitted],
        rejected,
        blocked_edges,
        selected,
        files=[p for p, _ in loaded],
    )
    return report


def _receipt(
    report: PathReport,
    query: dict[str, Any],
    admitted: list[Any],
    rejected: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
    selected: list[list[str]],
    files: list[Path] | None = None,
) -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "gate_engine_version": GATE_ENGINE_VERSION,
        "ontology_versions": _ontology_versions(),
        "state_registry_hash": _sha(ROOT / "spec" / "state_registry.yaml"),
        "evidence_snapshot_hash": _snapshot_hash(files or []),
        "input_context": query.get("context") or {},
        "admitted_claims": admitted,
        "rejected_claims": rejected,
        "blocked_edges": blocked,
        "selected_paths": selected,
        "unmodeled_layers": report.unmodeled_layers,
        "host_effect_status": report.host_effect,
    }


def run_query_path(path: Path, claim_dirs: list[Path] | None = None) -> PathReport:
    raw = _load_yaml(path)
    if not isinstance(raw, dict):
        return PathReport("REJECTED", "query must be a mapping", None)
    return run_query(raw, claim_dirs=claim_dirs)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m engine.paths <query.yaml> [--claims DIR ...]", file=sys.stderr)
        return 2
    query_path = Path(args[0])
    dirs: list[Path] = [DEFAULT_CLAIMS]
    if "--claims" in args:
        idx = args.index("--claims")
        dirs = [Path(item) for item in args[idx + 1 :]]
        if not dirs:
            print("usage: python -m engine.paths <query.yaml> [--claims DIR ...]", file=sys.stderr)
            return 2
    report = run_query_path(query_path, claim_dirs=dirs)
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
