# HGSOC State Engine

Evidence-gated, context-locked **naming and path-admission** contracts for
untreated high-grade serous ovarian carcinoma (HGSOC).

This is **not** a medical device. It does not predict survival, treatment
response, or whole-body fate. It decides, layer by layer, whether a named
state is admissible.

CELL//SHIFT is a separate chamber / visualization subject. It is **not** a
biomedical evidence source for this engine. Do not merge these claim
boundaries.

## Phase 0 — contracts

| File | Answers |
| --- | --- |
| [NORTH_STAR.md](NORTH_STAR.md) | What this system is; layers vs axes; product loop; definition of done |
| [FROZEN_SLICE.md](FROZEN_SLICE.md) | HGSOC + untreated lock; four tissue axes |
| [HOST_EFFECT_CONTRACT.md](HOST_EFFECT_CONTRACT.md) | Fifth axis as gated projection (H0–H3) |
| [spec/](spec/) | Machine-readable permits, gates, exclusions |

## Phase 1 — registry + linter

Unknown `state_id` is rejected. `HRD_HIGH` without assay/cutoff is `BLOCKED`.
`FORK_COLLAPSE_PRESENT` without direct fork evidence cannot be `NAMED`.
`HOST_EFFECT` defaults to `UNNAMED + UNKNOWN + GATE_ONLY`.

```bash
pip install -e ".[test]"
python -m pytest
python -m engine.lint fixtures/blocked/fork_collapse_from_brca1.yaml
```

## Status

`host_effect` default: `UNNAMED` + `UNKNOWN` + `GATE_ONLY`.
