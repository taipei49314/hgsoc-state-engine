# Later phases

| Phase | Intent | Status |
| --- | --- | --- |
| 0 | Freeze contracts | landed |
| 1 | State registry + linter | landed (`python -m pytest`) |
| 2 | Evidence ledger (human curate; LLM may extract, not upgrade) | landed (`python -m pytest`) |
| 3 | Gate engine (full claim packets, not only naming) | landed (`python -m pytest`) |
| 4 | Path engine (primary + second admissible path) | landed (`python -m pytest`) |
| 5 | Anatomy layer with ontology IDs; still no organ-function ODE | not started |
| 6 | Product loop UI | not started |
| 7 | Host observation pilot (`ascites`) as product surface | not started |
| 8 | First host-effect **challenge** fixture (UNKNOWN is a valid finish) | not started |
| 9 | Dynamic integration only after units, time series, identifiability, calibration, validation | not started |

A layer may move from discrete named state to an integration variable
only with: defined variable, units, time series, transition rule,
identifiability, calibration set, external validation, uncertainty
propagation, and evidence for feedback direction.
