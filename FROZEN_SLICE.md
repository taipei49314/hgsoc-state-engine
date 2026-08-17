# Frozen slice — HGSOC untreated baseline

Machine-readable copy: `spec/axes.yaml`, `spec/context_gate.yaml`.

This freeze names the **disease and untreated tissue initial condition**.
It does not name `host_effect`. It does not admit generic ovarian cancer.

## Disease lock

```yaml
disease:
  name: high-grade serous ovarian carcinoma
  short_name: HGSOC
  histology_required: true
```

These names **cannot** auto-enter the slice:

```text
ovarian cancer
epithelial ovarian cancer
serous cancer
gynecologic cancer
```

Verdict if used as disease context: `CONTEXT_MISMATCH`.

## Untreated baseline

`untreated` means: at specimen collection, the patient had **not** received
any anticancer therapy that systematically remodels the tumor.

At least exclude:

```text
neoadjuvant chemotherapy
prior adjuvant chemotherapy exposure
PARP inhibitor
anti-angiogenic therapy
radiotherapy
experimental anticancer treatment
post-recurrence re-sampling
```

```text
currently off treatment  ≠  treatment-naïve
```

A recurrent specimen after prior therapy is **not** this frozen slice,
even if the patient is not on drug at draw.

Primary debulking tissue **may** be a baseline specimen if:

```yaml
collection:
  before_systemic_therapy: true
  prior_anticancer_exposure: none
  ischemia_time: known_or_unknown
  fixation_or_freezing_delay: recorded_or_unknown
```

Pre-treatment HGSOC already has spatial, transcriptional, and metabolic
heterogeneity. Post-treatment remodeling must not be mixed into this
baseline.

Verdict if treated / post-NACT is offered as this slice:
`OUT_OF_FROZEN_SLICE` (also recorded as `TREATED_CONTEXT`).

## Species and models

v1 core data:

```yaml
species: human
disease: HGSOC
treatment_context: untreated
```

These systems may support **mechanism**, not human `host_effect` alone:

```text
primary human cells
organoids
ex vivo tissue
cell lines
PDX
mouse models
computational models
```

Every such packet must carry:

```yaml
transfer_gap:
  from: model_system
  to: human_untreated_HGSOC
  unresolved: true   # until explicitly resolved
```

## Four axes (do not rename)

Axes describe L3–L4 tissue. They are **not** the protein→host scale chain.

### A1 — Cell state

Concept endpoints: proliferative ↔ quiescent / stressed.

Stored values: `PROLIFERATIVE` | `QUIESCENT` | `STRESSED` | `MIXED` | `UNKNOWN`

Naming requires: marker set, assay, threshold, cell population, spatial
region. One proliferation marker must not name the whole slice.

### A2 — Spatial ecology

Concept endpoints: tumor core ↔ invasive margin / stromal interface.

Stored values: `TUMOR_CORE` | `INVASIVE_MARGIN` | `STROMAL_INTERFACE` | `MIXED_REGION` | `UNKNOWN_REGION`

Each region needs an operational definition, e.g. distance from tumor
boundary in µm and a specified segmentation method. Image intuition is
not enough.

### A3 — Immune interaction

Concept endpoints: immune-excluded ↔ inflamed / immune-engaged.

Stored values: `IMMUNE_EXCLUDED` | `INFLAMED_LOCAL` | `IMMUNE_ENGAGED` | `MIXED` | `UNKNOWN`

This axis is **local** tissue / tumor immune context. Local IFN,
infiltration, or cytokine expression must not be upgraded to systemic
inflammation, whole-body immune activation, or immune failure.

Precursor, primary, ascites, and distinct anatomical sites may differ.
The immune axis is bound to location and specimen.

### A4 — Treatment-response preparedness

Concept endpoints (visual only): response-permissive ↔ response-refractory.

Those two words are **not** stored bare values.

Stored form:

```text
PERMISSIVE(perturbation, assay, endpoint, threshold)
REFRACTORY(perturbation, assay, endpoint, threshold)
NOT_EVALUATED
UNKNOWN
```

v1 default:

```yaml
treatment_response_preparedness:
  status: NOT_EVALUATED
```

`platinum_sensitive` as a clinical outcome is **not** an untreated
baseline state. BRCA mutation, HRD genomic score, or RAD51 status must
not be equated with “treatment will work”.

## Fifth axis

`host_effect` is **not** a fifth tissue gradient. See
[HOST_EFFECT_CONTRACT.md](HOST_EFFECT_CONTRACT.md).

v1 default:

```yaml
host_effect:
  naming_status: UNNAMED
  knowledge_status: UNKNOWN
  coverage_status: GATE_ONLY
```
