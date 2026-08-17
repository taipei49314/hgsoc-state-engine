# HGSOC State Engine

Evidence-gated, context-locked **naming and path-admission** contracts for
untreated high-grade serous ovarian carcinoma (HGSOC).

This is **not** a medical device. It does not predict survival, treatment
response, or whole-body fate. It decides, layer by layer, whether a named
state is admissible.

CELL//SHIFT is a separate chamber / visualization subject. It is **not** a
biomedical evidence source for this engine. Do not merge these claim
boundaries.

## Phase 0 (this checkout)

Contracts only. No engine, no UI, no scored paths.

| File | Answers |
| --- | --- |
| [NORTH_STAR.md](NORTH_STAR.md) | What this system is; layers vs axes; product loop; definition of done |
| [FROZEN_SLICE.md](FROZEN_SLICE.md) | HGSOC + untreated lock; four tissue axes |
| [HOST_EFFECT_CONTRACT.md](HOST_EFFECT_CONTRACT.md) | Fifth axis as gated projection (H0–H3) |
| [spec/layers.yaml](spec/layers.yaml) | Scale layers; anatomy ≠ organ function |
| [spec/axes.yaml](spec/axes.yaml) | Frozen slice axes A1–A4 |
| [spec/admissibility.yaml](spec/admissibility.yaml) | What each layer may name; forbidden upgrades |
| [spec/context_gate.yaml](spec/context_gate.yaml) | Disease / untreated / specimen gates |
| [spec/host_effect_gate.yaml](spec/host_effect_gate.yaml) | Host observation vs association vs effect |
| [spec/outcome_exclusions.yaml](spec/outcome_exclusions.yaml) | Clinical outcomes never enter the state graph |
| [spec/evidence.yaml](spec/evidence.yaml) | ECO types + project evidence fit |
| [spec/ranking.yaml](spec/ranking.yaml) | No fake support probabilities |
| [spec/unmodeled.yaml](spec/unmodeled.yaml) | v1 coverage: UNMODELED vs UNKNOWN vs OUT_OF_SCOPE |
| [spec/acceptance.yaml](spec/acceptance.yaml) | Frozen expected verdicts T01–T14 |

Anyone reading these files must be able to answer:

1. Which layer may name what?
2. What missing evidence yields `UNKNOWN`?
3. What is `UNMODELED`?
4. What is always `OUT_OF_SCOPE`?

## Status

`host_effect` default: `UNNAMED` + `UNKNOWN` + `GATE_ONLY`.
