# NEXUS RRA-02 — Research Projector Design V1

**Status:** design only; the projector is not implemented by this change.

## 1. Objective

Project recovered RRA-01 evidence into the existing Experiment Registry, ResearchMemory, and sparse Coverage Matrix without creating a second ledger or mutating source artifacts.

```text
immutable source artifacts
        |
        v
source adapters -> normalized observations -> reconciliation rules
        |                                      |
        +------------ provenance --------------+
                                               v
                                      projection bundle
                                      /       |       \
                         Experiment Registry  Memory  Coverage
```

ResearchMemory remains append-only history. Registries remain canonical domain stores. The Coverage Matrix is a derived sparse view.

## 2. Inputs and outputs

Initial allowed inputs are the five consolidated RRA documents and explicitly referenced canonical artifacts. Input discovery must use an allowlist and record commit/blob hashes. Untracked vault material cannot be promoted silently.

Outputs are proposed append-only records or deterministic read models. The implementation must support `--dry-run` and produce a signed-off diff bundle before any canonical write.

The projector must not execute hypotheses, modify scientific gates, read protected holdouts, or mutate strategy/runtime configuration.

## 3. Canonical identity

### 3.1 Source identity

`source_observation_id = sha256(repository + commit + path + stable_locator + source_record_hash)`

### 3.2 Experiment identity

Experiment identity is derived from normalized, explicit fields:

- hypothesis/claim identifier;
- strategy/component identity and version;
- dataset fingerprint and split;
- timeframe, period, direction and session;
- engine and implementation version;
- parameter set;
- cost/execution model;
- method/preregistration identifier.

Missing identity fields remain explicit `UNKNOWN`; they are not filled by guesswork. Records with materially different identities are separate experiments, not duplicates.

### 3.3 Projection identity

`projection_id = sha256(projector_version + reconciliation_rules_version + normalized_semantic_payload)`

Timestamps, file paths that are not semantic, and run-local metadata are excluded from the semantic hash.

## 4. Idempotency and deduplication

- Reprocessing identical sources with identical rules produces the same projection IDs and zero writes.
- Exact source duplicates collapse to one source observation with multiple provenance references.
- Similar titles or strategy aliases do not establish duplication.
- Alias resolution uses a versioned identity map and preserves the original identifier.
- Repeated experiments on the same data are linked but are not counted as independent replication.
- Conflicting observations remain separate and create a conflict record.
- Concurrent projection uses compare-and-swap or an equivalent repository-supported revision check; partial multi-target updates must fail closed.

## 5. Conflict policy

The projector never resolves a conflict by source recency alone. It applies versioned rules based on:

1. exact artifact provenance;
2. claim-scope match;
3. method validity;
4. implementation/version match;
5. dataset/split identity;
6. causal timestamp and independence checks;
7. explicit human decision, when policy is required.

Unresolved conflicts are emitted with all candidates, reason codes and required evidence. They cannot produce `SUPPORTED`, `VALIDATED`, or execution authorization.

## 6. Target projections

### Experiment Registry

Append or propose experiment identities, execution status, methods, datasets, results, limitations and provenance. Preserve every historical run, including failed infrastructure attempts.

### ResearchMemory

Append reconciliation observations and decisions using the existing hash-chain model. Imported documents are sources, not self-authenticating evidence. Human approvals remain explicit records.

### Coverage Matrix

Build sparse cells over observed dimensions only. Each cell links experiment IDs and expresses coverage quality. Missing cells default to `UNKNOWN`, not `NEVER_TESTED`.

### Priority queue

Top 20 questions enter only as `PROPOSAL_ONLY` candidates with:

- `authorized_for_execution=false`;
- no allocated holdout;
- no run budget;
- provenance to RRA-01;
- deduplication against existing hypotheses;
- normal RI review and approval requirements.

## 7. Versioning and rollback

- Version source adapters, normalization schema, identity map, reconciliation rules and output schema independently.
- A new rule version creates a new projection revision; it never edits an earlier projection in place.
- Rollback disables a projection revision in the read model and restores the prior revision. Append-only memory records remain intact.
- Every run emits source hashes, rule versions, output hashes, counts, conflicts, rejects and a deterministic manifest.
- Schema migration requires backward-read tests and a dry-run comparison against the previous projector version.

## 8. Security and scientific boundaries

- Read-only by default; canonical write mode requires separate authorization.
- Path allowlist and size limits for inputs.
- No network retrieval while projecting historical sources.
- No user-provided owner, evidence grade, authorization or verification flag is trusted.
- Secrets, private prompts and protected dataset locations are redacted from public projections.
- No autoapproval, no economic promotion, no live action, and no protected-holdout access.

## 9. Failure behavior

Malformed input, unknown schema, ambiguous identity, intermediate corruption, revision conflict, missing provenance or partial target failure must stop the affected projection and produce a diagnostic record. The projector must never silently skip a material conflict or manufacture a replacement artifact.
