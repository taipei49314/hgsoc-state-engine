"""UBERON anatomy lock. Named L5A states require a matching ontology ID."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ANATOMY_PATH = ROOT / "spec" / "anatomy.yaml"


def normalize_curie(value: str) -> str:
    text = value.strip()
    if "UBERON_" in text and text.startswith("http"):
        return "UBERON:" + text.rsplit("UBERON_", 1)[-1]
    if text.startswith("UBERON_"):
        return "UBERON:" + text[len("UBERON_") :]
    return text


def load_anatomy(path: Path = ANATOMY_PATH) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != "anatomy_ontology":
        raise ValueError("anatomy.yaml missing or wrong kind")
    sites = data.get("sites") or {}
    by_state: dict[str, dict[str, Any]] = {}
    for state_id, keys in (data.get("state_sites") or {}).items():
        ids = []
        for key in keys:
            site = sites.get(key) or {}
            oid = site.get("ontology_id")
            if isinstance(oid, str):
                ids.append(normalize_curie(oid))
        by_state[state_id] = {"site_keys": list(keys), "ontology_ids": ids}
    return {"raw": data, "by_state": by_state, "sites": sites}
