# NEXUS RRA-02 — Scientific Status Taxonomy V1

**Status:** proposed projection taxonomy. Source artifacts and canonical registries remain unchanged.

## 1. Rule

A research object MUST NOT be represented by one overloaded status. A projection records four independent dimensions plus provenance and claim scope.

## 2. Dimensions

### 2.1 Implementation Status

Describes whether the tested concept exists and can execute as specified.

- `IMPLEMENTED`: resolvable implementation exists for the stated version.
- `PARTIAL`: only part of the claimed behavior exists.
- `DEFECTIVE`: a confirmed defect invalidates relevant behavior.
- `NOT_EXECUTABLE`: present but unreachable, dead, or disabled in the claimed path.
- `NOT_IMPLEMENTED`: no implementation found within the declared census perimeter.
- `UNKNOWN`: evidence is insufficient.

### 2.2 Experiment Status

Describes what happened to a specific experiment, not what is economically true.

- `COMPLETED_VALID`: method and execution passed the declared validity checks.
- `COMPLETED_INCONCLUSIVE`: valid execution but non-decisive result.
- `INVALID`: execution or method cannot support the claim.
- `PARTIAL`: only a subset of the planned experiment completed.
- `NOT_FEASIBLE`: a preregistered structural or data gate prevented valid execution.
- `NOT_RUN`: the experiment identity exists but no execution began.
- `UNKNOWN`: execution history cannot be established.

### 2.3 Evidence Status

Describes support for one explicit claim.

- `SUPPORTED`: evidence meets the claim's preregistered support threshold.
- `REFUTED`: valid evidence contradicts the claim within its scope.
- `INCONCLUSIVE`: valid evidence does not distinguish support from refutation.
- `INVALID`: cited material cannot evaluate the claim.
- `NOT_EVALUATED`: no admissible evaluation exists.
- `UNKNOWN`: provenance or scope is insufficient.

Evidence status is always paired with `evidence_grade`, if one exists, and cannot be generalized beyond `claim_scope`.

### 2.4 Economic Status

Describes economic validation, separately from code correctness and statistical interest.

- `VALIDATED`: high-threshold independent economic validation has passed.
- `FORWARD_REQUIRED`: discovery or historical evidence warrants forward validation.
- `CANDIDATE`: worth further research; edge is not demonstrated.
- `BORDERLINE`: mixed or marginal evidence.
- `FAILED`: the tested economic formulation did not demonstrate edge.
- `DEFECT_BLOCKED`: implementation defects prevent an economic judgment.
- `UNVALIDATED`: no sufficient economic validation exists.
- `NOT_APPLICABLE`: the claim is mechanical, methodological, or non-economic.
- `UNKNOWN`: evidence cannot determine status.

`FAILED` applies only to the tested formulation. It does not imply that every reusable component is useless.

## 3. Mandatory projection envelope

Every reconciled projection must contain conceptually equivalent fields:

```json
{
  "projection_schema": "RRA02_SCIENTIFIC_STATUS_PROJECTION_V1",
  "projection_id": "stable-id",
  "subject_id": "canonical-or-source-qualified-id",
  "claim_scope": "explicit bounded claim",
  "implementation_status": "UNKNOWN",
  "experiment_status": "UNKNOWN",
  "evidence_status": "UNKNOWN",
  "economic_status": "UNKNOWN",
  "source_status": {
    "vocabulary": "source vocabulary name",
    "value": "unaltered original value"
  },
  "provenance": [{"artifact": "path", "commit": "sha", "locator": "section-or-record"}],
  "reconciliation_rule": "versioned-rule-id",
  "confidence": "HIGH|MEDIUM|LOW|UNKNOWN",
  "conflicts": [],
  "projected_at": "deterministic build metadata supplied outside semantic identity"
}
```

## 4. Mapping rules

- RRA-01 `TESTED_VALID` requires inspection of its claim. A validated fix maps to `COMPLETED_VALID` + `SUPPORTED` + economic `NOT_APPLICABLE`, not economic `VALIDATED`.
- `TESTED_INCONCLUSIVE` maps to `COMPLETED_INCONCLUSIVE` + `INCONCLUSIVE` only when method validity is supported.
- `TESTED_INVALID` maps to experiment `INVALID` when the method or implementation failed. It maps to economic `FAILED` only when a valid economic test refuted the bounded formulation.
- `PARTIALLY_TESTED` maps to experiment `PARTIAL`; evidence and economic dimensions remain independently derived.
- `NEVER_TESTED` maps to `NOT_RUN` only when the census perimeter proves an experiment was defined and not executed. A feasibility failure maps to `NOT_FEASIBLE`.
- `UNKNOWN` remains `UNKNOWN`; absence of an artifact never becomes `NOT_RUN` automatically.

## 5. Invariants

1. Original values are immutable and always retained.
2. Every projection is claim-scoped and provenance-bearing.
3. Code correctness cannot promote economic status.
4. A URL supplied by a user is not verified evidence by itself.
5. Multiple records are not independent evidence unless dataset, split, lineage, timeframe and overlap checks support independence.
6. `SUPPORTED` and `VALIDATED` require evidence appropriate to their declared scope.
7. Conflicts remain visible; deterministic precedence may select a projection but may not erase dissenting sources.
8. No projected status authorizes execution, holdout access, promotion, deployment, or live trading.
