# NEXUS Terminal — Phase UI-4 Library Workspace + Explain Path v1

## Scope and source of truth

The canonical Library v1 is a read-only projection of structured artifacts in `server/research_scripts/phase6_6/`. It does not parse Markdown to manufacture canonical state and it does not modify research artifacts. The projection currently ingests:

- `h006_evidence_v2.json`
- `h006_decision_card_v2.json`
- `post_hoc_observations_v1.json`
- `research_evidence_ledger_v1.json`
- `research_relations_v1.json`
- `artifact_manifest.json`

Each wrapper's canonical payload SHA is checked when present. Source file SHA, canonical SHA, schema version, phase and commit are exposed when the source contains them. Missing metadata remains `null` and renders as `—` or unavailable.

## Canonical entity model

Every entity has a stable `id`, `type`, `title`, `status`, optional `evidence_grade`, `phase`, created/updated metadata, limitations, attributes, provenance, and explicit inbound/outbound relations.

Types materialized in v1 are `Hypothesis`, `Experiment`, `Dataset`, `Evidence`, `EvidenceAudit`, `DecisionCard`, and `PostHocObservation`. `EdgeComponent` and `FailurePattern` are supported product concepts but no Phase 6.6 record provides a formal entity of those types, so v1 does not create them.

The Decision Card source has no formal card ID. The read model supplies deterministic ID `DEC-H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT-V2` and labels its provenance as derived from a structured artifact. This is an indexing identity, not a research claim.

## Historical truth preservation

`EVD-H006-PRIMARY-001` is primary Phase 6 evidence: `E2`, `BORDERLINE`, aggregate Baseline Engine v2. `EVD-H006-AUDIT-001` is a distinct Phase 6.5 retrospective audit: dependence `HIGH`, direction-aware Baseline Engine v3, and no authority to revise the primary grade. The audit is never merged into or substituted for the primary evidence.

H006 remains `BORDERLINE`, `E2`, not promoted to E3, with decision `RETAIN_E2`. `SELL_SWEEP_RECLAIM_ASYMMETRY` remains a `PostHocObservation` with `is_edge=false` and `is_validated=false`. No H007 entity is created.

## Relation model

Only relation rows in `research_relations_v1.json` are exposed. Allowed types are:

- `TESTS`
- `SUPPORTS`
- `REFUTES`
- `LIMITS`
- `AUDITS`
- `DERIVED_FROM`
- `SUPERSEDES`

Both endpoints must exist in the canonical entity index. A malformed type or broken endpoint emits a warning and that edge is excluded without breaking the catalog. Similar names, shared words, or UI context never create relations.

Phase 6.6 currently includes two edges involving `DEPENDENCE_AUDIT_PASS_GATE` and `H006_PRE_PHASE6.5_RECORD`, which are not canonical entity records. They are therefore reported as broken relations rather than synthesized. It also contains no explicit Decision Card relation, so the Decision Card is returned as `current_decision`, clearly separate from `typed_edges`.

## Explain Path v1

`GET /api/library/explain/{id}` builds a deterministic connected view from:

1. explicit, valid Phase 6.6 relations;
2. matching append-only ledger transitions;
3. direct entity lookup;
4. a matching structured Decision Card returned separately.

The response contains `root_entity`, ordered `path_nodes`, `typed_edges`, `chronological_transitions`, `current_decision`, limitations, provenance and catalog warnings. It explicitly reports `inferred_relations=false`. The UI renders a vertical evidence path and does not use anthropomorphic language.

Because the current Relations Model uses edge direction as recorded, v1 does not rewrite it to make a prettier narrative. A future artifact version should add explicit experiment-to-evidence (`PRODUCES`) and evidence-to-decision (`SUMMARIZED_BY`) relations if those paths are desired canonically.

## API contract

All endpoints are authenticated and read-only:

- `GET /api/library/entities` — filters: `type`, `status`, `evidence_grade`, `phase`, `relation_type`, `q`
- `GET /api/library/entities/{id}`
- `GET /api/library/relations` — optional `relation_type`
- `GET /api/library/explain/{id}`

Unknown entity IDs return 404; unsupported relation types return 422. Client input is never interpreted as a filesystem path.

## Library UI

`/library` is the canonical entry point. It provides text search, compact metadata filters, an entity index, a responsive inspector, provenance, inbound/outbound relations, and Explain Path. Evidence is visually identified as `PRIMARY`; methodological evidence is `AUDIT`. The legacy `/knowledge` and `/journal` routes remain accessible, with the former linked as **Raw / Legacy Knowledge**.

On desktop the filters and index share a dense two-column workspace while the inspector opens as a right-side sheet. On mobile filters collapse and the inspector becomes a full-width vertical sheet. Long IDs, SHA values and source paths wrap without horizontal page overflow.

## Failure and negative knowledge

V1 exposes negative facts already structured in the sources: contaminated H004 validation, H006 grade cap, overlapping confidence intervals, dependence limitations, failed directional consistency, unresolved questions, and post-hoc non-actions. It does not create `FailurePattern` entities because the artifact set does not yet assign them stable IDs.

## Performance and caching

The backend keeps a materialized in-process catalog and rebuilds it only when one of the six source artifact modification times changes. Entity detail and explain requests use indexed dictionaries rather than reparsing the directory. This is suitable for the small v1 catalog. A process-shared versioned cache or prebuilt index will be needed when multiple hypotheses and large ledgers are added.

## Validation and fault isolation

Artifacts are parsed individually. Missing/malformed JSON, canonical hash mismatches, duplicate IDs, malformed observations and broken relations become warnings. A single bad artifact cannot invalidate successfully parsed entities. The model never writes to its sources.

## Known limitations and prerequisites for Galaxy

- Phase 6.6 covers one normalized research thread; catalog breadth is intentionally narrow.
- The manifest validates the file hashes of the six ingested artifacts; coverage outside this Phase 6.6 subset is not part of Library v1.
- Decision Card lacks a native stable ID and explicit graph edge.
- Experiment-to-evidence and evidence-to-decision production relations are absent from the declared relation vocabulary.
- Gate and historical pre-audit records referenced by two edges are not canonical entities.
- Edge components and failure patterns need explicit schemas and IDs.
- A larger catalog needs pagination and a persistent/shared index.

Galaxy remains blocked until those entity IDs and relation gaps are resolved, provenance coverage spans more than H006, and graph integrity can be enforced without inferred edges. No WebGL, 3D canvas, SSE, or simulated activity is introduced in this phase.
