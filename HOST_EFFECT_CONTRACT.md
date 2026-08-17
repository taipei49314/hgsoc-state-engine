# Host-effect contract

Fifth axis name: `host_effect`.

It is **not** a fifth continuous tissue feature in the frozen slice.
It is a **non-integrating boundary channel**: a projection from tumor /
anatomy toward a human phenotype.

Machine-readable copy: `spec/host_effect_gate.yaml`.

## Three fields (do not collapse)

```yaml
host_effect:
  naming_status: UNNAMED    # NAMED | UNNAMED
  knowledge_status: UNKNOWN # OBSERVED | ASSOCIATED | SUPPORTED | INFERRED | CONFLICTED | UNKNOWN
  coverage_status: GATE_ONLY  # MODELED | GATE_ONLY | UNMODELED | OUT_OF_SCOPE
```

v1 default means: the exit exists and the gate is implemented; evidence
does **not** yet permit naming.

`UNKNOWN` is a **knowledge** status. `UNMODELED` is an **engineering
coverage** status. Do not swap them.

`coverage_status: GATE_ONLY` is not `UNMODELED`. Organ-function dynamics
are UNMODELED; host_effect is GATE_ONLY.

## Observation vs association vs effect

| Type | Means | Upgrades host_effect? |
| --- | --- | --- |
| `HOST_OBSERVATION` | Human phenotype was directly measured | No. Effect stays UNKNOWN |
| `HOST_ASSOCIATION` | Tumor/anatomical state co-varies with phenotype in a cohort | No. `causal_claim: false` |
| `HOST_EFFECT` | Named projection that the tumor/anatomy state contributes to the phenotype | Only at H3 |

Example: `malignant ascites present` may be `HOST_OBSERVATION: OBSERVED`.
`fork collapse caused malignant ascites` is `HOST_EFFECT` and needs the
full H3 packet.

Human phenotype names should use HPO or an explicit operational
definition. Do not invent “body affected”.

## Ladder

### H0 — UNKNOWN (default)

```yaml
host_effect:
  naming_status: UNNAMED
  knowledge_status: UNKNOWN
```

Triggers include: no direct human endpoint; only cell/tumor evidence;
only animal or cell-line mechanism; only generic literature; only
survival correlation; unresolved cross-scale gap.

### H1 — Observed host phenotype

```yaml
host_observation:
  phenotype: specified
  subject: human
  disease: HGSOC
  treatment_context: untreated
  measurement: specified
  status: OBSERVED
```

Means: the phenotype was seen. Does **not** mean an upstream molecular
path caused it. `host_effect` remains UNKNOWN.

### H2 — Associated host phenotype

Requires: human HGSOC cohort; untreated endpoint measurement; specified
tumor/anatomical state; specified host phenotype; effect estimate;
uncertainty; confounder handling.

```yaml
host_association:
  tumor_state: specified
  host_phenotype: specified
  effect_measure: specified
  confidence_interval: specified
  causal_claim: false
```

Display: `associated with`. Never: `causes`, `drives`, `leads to`.

### H3 — Supported host effect (only here may we NAME)

```yaml
host_effect:
  naming_status: NAMED
  knowledge_status: SUPPORTED
```

v1 minimum packet, **all** required:

1. Typed endpoint (HPO or operational clinical definition).
2. Direct human measurement (not expression enrichment alone, not model
   inference alone).
3. Exact context: human, HGSOC, untreated at measurement, specified
   anatomical compartment.
4. Tumor–host linkage: same-patient matched, same-specimen cross-modal,
   prospective stratified cohort, or longitudinal matched observation.
5. Mechanistic bridge: at least one orthogonal packet (primary human
   tissue, ex vivo, organoid/co-culture, or validated mechanistic model).
6. Temporal plausibility: tumor state precedes or accompanies host
   change; not retrospective endpoint correlation alone.
7. Confounder record: stage, tumor burden, age, comorbidities, treatment
   exposure, sampling site, sample timing.
8. Independent support: at least two evidence packets that are not
   copies of each other. One model paper does not reach H3.
9. Falsification condition (observable, assay, expected result,
   threshold).
10. No unresolved protein→host jump with no inspectable bridge.

### Hx — Conflicted

High-quality studies disagree:

```yaml
host_effect:
  naming_status: UNNAMED
  knowledge_status: CONFLICTED
```

UI: `Conflicting evidence`. Do **not** average into `support = 0.54`.

## First host pilot (not yet implemented)

Intended first phenotype: `ascites present / absent`.

Initial identity: `HOST_OBSERVATION`, not `HOST_EFFECT`.

Until H3 passes:

```yaml
host_observation:
  phenotype: ascites_present
  status: OBSERVED_or_UNKNOWN

host_effect:
  naming_status: UNNAMED
  knowledge_status: UNKNOWN
  coverage_status: GATE_ONLY
```

Ascites must not be converted into survival or treatment-response
support.

## Unlock packet (display when stopped)

```text
- matched untreated HGSOC endpoint
- patient-level tumor–host linkage
- mechanistic bridge
- independent validation
- confounder handling
- falsification condition
```
