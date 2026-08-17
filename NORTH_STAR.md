# HGSOC Untreated Baseline State Engine — North Star

Not a medical device. Not a calibrated predictor. Not CELL//SHIFT.

## Canonical statement

HGSOC State Engine is **not** a model that predicts human fate from a
protein. It is a **cross-scale naming and path-admission system**.

The frozen slice is described by four tissue axes: cell state, spatial
ecology, immune interaction, treatment-response preparedness. Fallopian
tube, ovary, peritoneum, omentum and related sites may be named as
discrete, citable anatomical involvement states. Organ function is
**UNMODELED** in v1. The fifth axis `host_effect` is a **gate-only
projection**, default `UNNAMED + UNKNOWN`. It may be named only when
direct untreated human HGSOC phenotype, tumor–host linkage, a mechanistic
bridge, confounder handling, independent support, and a falsification
condition all hold.

The value of the engine is not that it always continues downward. It is
that it can say: which layer is named, why it stopped, what the second
path is, and which evidence the next layer still lacks.

Short form:

> Not telling a molecular-to-body story. Deciding, layer by layer,
> whether this layer may be named now.

## Product north star (v1)

In a **fixed HGSOC, untreated baseline** context, build an
evidence-gated, context-locked, multi-scale state engine that connects
molecule / protein, DNA-repair and replication process, cell state,
spatial tumor ecology, and anatomical location into **replayable
candidate paths**. Every named state must pass that scale’s naming
permit table and carry PMID (or equivalent source), measurement
definition, assumptions, contradictions, and a falsification condition.

The system **may** reach ovarian, fallopian-tube, peritoneal, and omental
anatomical states. Reaching anatomy **does not** claim organ-function
change. Local signal, inflammatory signature, survival, or treatment
response rate **must not** be translated into a whole-body effect.

`host_effect` defaults to `UNNAMED + UNKNOWN`. Naming is allowed only
under the [HOST_EFFECT_CONTRACT.md](HOST_EFFECT_CONTRACT.md) H3 packet.

## What must stay split

1. **Scale layers** — what kind of thing is being named.
2. **Frozen slice axes A1–A4** — untreated tissue initial condition.
3. **Axis 5 `host_effect`** — not a fifth tissue feature; a gated
   cross-scale projection.

Do not collapse these into `protein → host` as a single story.

## Layers vs axes

Scale layers (`spec/layers.yaml`):

```text
L0   Context
L1   Variant / protein observation
L2   Molecular process / pathway state
L3   Cell state
L4   Tissue / tumor state
L5A  Anatomical involvement
L5B  Organ-function state
L6   Host phenotype / host effect
L7   Clinical outcome
```

Frozen slice axes (`spec/axes.yaml`) describe **L3–L4**:

```text
A1 Cell state
A2 Spatial ecology
A3 Immune interaction
A4 Treatment-response preparedness
```

`host_effect` is a projection from L4 / L5 toward L6. L5B is UNMODELED
in v1. L7 never enters the state graph (`spec/outcome_exclusions.yaml`).

Anatomy is not organ function. `STIC present in distal fallopian tube`
may be named as involvement while `organ_function` stays UNMODELED.

## No fake support numbers

Assay scores, counts, fold-changes, odds ratios, confidence intervals,
and spatial distances may be stored **with units and sources**.

The engine must **not** emit:

```text
biological support = 0.82
host-effect confidence = 78%
probability of organ failure = 64%
```

unless those numbers come from a separately declared, calibrated,
externally validated predictive model — which v1 does not include.

Paper count, p-values, survival, and response rates must not be mixed
into an edge “support” mass. Ranking uses the tuple in
`spec/ranking.yaml`.

## Product loop

Every query must emit seven blocks:

1. Context header (HGSOC, untreated, species, specimen, gate).
2. Frozen slice four axes (named value, measurement, threshold, region,
   or UNKNOWN reason).
3. Primary admissible path, edge by edge.
4. Second admissible path, or `NO_SECOND_ADMISSIBLE_PATH`.
5. Deepest named layer.
6. Why the path stopped (missing unlock packet).
7. Unmodeled / UNKNOWN / OUT_OF_SCOPE layers.

Plus a replayable receipt (`spec/host_effect_gate.yaml` G8).

## Relation to CELL//SHIFT

CELL//SHIFT remains a chamber / visualization / synthetic-geometry
subject. This repo is the biomedical **naming contract**. CELL//SHIFT
must not be treated as evidence for HGSOC states.

## Phase 0 done

This checkout is Phase 0: freeze contracts. No engine, no UI.

Done when a reader can answer, from these files alone:

| Question | Where |
| --- | --- |
| Which layer may name what? | `spec/admissibility.yaml`, `spec/layers.yaml`, `spec/axes.yaml` |
| What missing evidence yields UNKNOWN? | `spec/admissibility.yaml`, [HOST_EFFECT_CONTRACT.md](HOST_EFFECT_CONTRACT.md) |
| What is UNMODELED? | `spec/unmodeled.yaml` |
| What is always OUT_OF_SCOPE? | `spec/outcome_exclusions.yaml`, `spec/unmodeled.yaml` |

Later phases are listed in [PHASES.md](PHASES.md). Phases 0–3 are landed.
Path engine and UI are not.
