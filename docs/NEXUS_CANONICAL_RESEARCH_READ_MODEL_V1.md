# NEXUS Canonical Research Read Model v1

## Purpose

This read-only model is the first stable Research boundary for NEXUS Terminal. It projects versioned Phase 5, 5.5 and 6 artifacts into canonical entities without changing research calculations, trading logic or source artifacts. It is deliberately a materialized in-process read model, not a graph database and not a mutation API.

## Source-of-truth rules

1. Structured JSON wins over Markdown. Markdown remains raw evidence and is not used to assign canonical status when structured data exists.
2. Phase 5.5 `hypothesis_registry_v1.json`, `experiment_registry_v1.json` and `dataset_version_v1.json` are direct sources.
3. Phase 6 `H006_frozen_spec.json`, `true_holdout_declaration.json`, `h006_primary_result.json` and `h006_robustness_diagnostics.json` are direct sources for H006 facts.
4. A record assembled across structured artifacts is marked `source.mode = DERIVED`; copied facts are marked `DIRECT`.
5. Missing fields remain `null`. The model never supplies zero as a missing-value fallback.
6. A missing or malformed artifact produces a catalog warning and does not invalidate unrelated entities.
7. Duplicate canonical IDs keep the first deterministic record and produce `DUPLICATE_ID`; broken relations are omitted and reported.
8. Source paths are repository-relative. Every source includes a SHA-256 hash when readable.

## Canonical IDs

Existing registry IDs are preserved. Materialized Phase 6 IDs are stable constants:

| Entity | Canonical ID |
|---|---|
| Hypothesis | `H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT` |
| Experiment | `EXP-P6-H006-TRUE-HOLDOUT` |
| Dataset | `DATASET-P6-H006-HOLDOUT-20220204-20230203` |
| Evidence | `EVIDENCE-P6-H006-TRUE-HOLDOUT` |
| Edge component | `EC-LIQUIDITY_SWEEP_RECLAIM` |
| Decision card | `DECISION-P6-H006` |

The stable ID is the `id` field in every entity. Display titles are not identifiers.

## Common entity envelope

Every entity exposes:

```json
{
  "id": "stable canonical ID",
  "entity_type": "Hypothesis | Experiment | Dataset | Evidence | EdgeComponent | DecisionCard",
  "title": "display title or null",
  "status": "source status or null",
  "provenance": "RESEARCH",
  "source": {
    "source_file": "repository-relative path",
    "source_hash": "sha256 or null",
    "source_version": "version or null",
    "mode": "DIRECT | DERIVED"
  },
  "version": "version or null",
  "created_at": "source timestamp or null",
  "updated_at": "source timestamp or null",
  "relations": [],
  "limitations": [],
  "conflicts": [],
  "uncertainty": null,
  "grade_cap_reason": null,
  "validation_integrity": null
}
```

Entity-specific fields retain only facts present in structured sources. Hypotheses expose outcome, grade, holdout and execution fields; experiments expose code/split/assumption fields; datasets expose time range, symbols and source hashes; evidence exposes metrics and grade; edge components expose grade/execution state; decision cards expose decision and summary.

## Relation schema

Relations use stable IDs only:

```json
{"type": "EXPERIMENT_PRODUCES_EVIDENCE", "source_id": "EXP-…", "target_id": "EVIDENCE-…"}
```

Supported relation types:

- `HYPOTHESIS_TESTED_BY_EXPERIMENT`
- `EXPERIMENT_USES_DATASET`
- `EXPERIMENT_PRODUCES_EVIDENCE`
- `EVIDENCE_SUPPORTS`
- `EVIDENCE_REFUTES`
- `EVIDENCE_LIMITS`
- `EDGE_COMPONENT_DERIVED_FROM_HYPOTHESIS`
- `DECISION_CARD_SUMMARIZES`

The first version uses `EVIDENCE_LIMITS` for H006 because the true holdout is positive but BORDERLINE: it neither validates E3 nor supports treating the SELL diagnostic as a new edge.

## H006 truth contract

The canonical representation is intentionally conservative:

- canonical status: `BORDERLINE`; source detail: `WEAK`;
- evidence grade: `E2`;
- true holdout performed: `true`;
- promoted to E3: `false`;
- holdout DeltaP: source precision `0.05715373486636721` (display may round to `+0.057`);
- confidence intervals overlap: `true`;
- BUY delta is negative and recorded as instability;
- SELL delta is recorded only as `sell_delta_p_diagnostic` and explicitly identified as post-hoc diagnostic;
- execution status: `NOT_TESTED`;
- grade cap: `true holdout BORDERLINE, no E3 promotion`.

No `EVIDENCE_SUPPORTS` relation or separate SELL edge is created for this diagnostic.

## API contract

All routes are authenticated with the existing dashboard authentication and are GET-only.

| Endpoint | Filters | Response |
|---|---|---|
| `/api/research/hypotheses` | `status`, `evidence_grade` | list envelope |
| `/api/research/hypotheses/{id}` | — | entity or 404 |
| `/api/research/experiments` | `status`, `hypothesis_id`, `dataset_id` | list envelope |
| `/api/research/experiments/{id}` | — | entity or 404 |
| `/api/research/datasets` and `/{id}` | `status` | list envelope or entity/404 |
| `/api/research/evidence` and `/{id}` | `status`, `evidence_grade`, `hypothesis_id` | list envelope or entity/404 |
| `/api/research/edge-components` and `/{id}` | `status`, `evidence_grade`, `hypothesis_id` | list envelope or entity/404 |
| `/api/research/decision-cards` and `/{id}` | `status`, `hypothesis_id` | list envelope or entity/404 |

List envelope:

```json
{
  "schema_version": "1.0",
  "items": [],
  "count": 0,
  "warnings": []
}
```

Warnings are deterministic diagnostic records such as `MISSING_ARTIFACT`, `MALFORMED_ARTIFACT`, `INVALID_RECORD`, `DUPLICATE_ID` and `BROKEN_RELATION`. They contain repository-safe source names, never arbitrary local filesystem paths.

## Minimal frontend proof

`/app/research` provides a deliberately small end-to-end proof:

- hypothesis list and selection;
- status and evidence grade;
- holdout/promotion/execution/DeltaP facts;
- grade cap;
- stable relation IDs;
- connected experiment, dataset and evidence records;
- repository-relative provenance.

It reuses the existing API client, auth shell, provenance badge and responsive card system. It is not the final Research workspace and does not introduce Galaxy, market, execution or assistant redesigns.

## Known limitations

- Phase 6.5 methodological-audit artifacts landed after the requested baseline. They explicitly preserve the Phase 6 verdict, do not promote SELL and do not assign E3; v1 does not yet normalize their directional-baseline and dependence diagnostics as separate Evidence entities.
- The catalog is rebuilt from repository artifacts per request; v1 has no persistent indexed cache.
- Phase 5 experiment dataset references are descriptive legacy strings, so canonical `EXPERIMENT_USES_DATASET` relations are currently complete only for the Phase 6 materialization.
- Phase 5 evidence/decision information is not fully normalized in dedicated JSON entities; v1 does not infer it from Markdown.
- Source artifacts do not consistently carry updated timestamps or semantic versions; those fields remain `null` where unavailable.
- H006 code commit is not asserted because the structured Phase 6 artifacts do not expose a single authoritative commit field.
- The current relation set is a read projection, not a graph persistence layer.
- Filtering is exact and intentionally basic; pagination and full-text search are future concerns.
