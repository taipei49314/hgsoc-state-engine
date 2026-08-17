# Phase 2 evidence ledger.

Human-curated first. An LLM may propose sentences, metadata, or ontology
IDs. It must not:

- auto-upgrade `knowledge_status` to `SUPPORTED`
- set `host_effect_eligible: true`
- drop `contradictions`

Seed PMIDs are **not** auto-admitted as named human untreated states.

```bash
py -3.11 -m pytest
```
