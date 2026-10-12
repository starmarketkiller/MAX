# NEXUS RRA-02 — RI-01/RI-02 Integration and Acceptance V1

**Status:** implementation plan and acceptance contract only.

## 1. Consolidated sequence

The binding order remains:

`SAFETY → RECOVER → COVERAGE → REPAIR → PARITY → SELF-IMPROVE → EXPLORE`

- **SAFETY:** PR #47 owns Max Total Drawdown. Its effective MQL5 save/shutdown/restore and broker-flow replay remain live-readiness blockers; RRA-02 does not duplicate the patch. PR #36 remains separate.
- **RECOVER:** import RRA-01 observations through the proposed projector after implementation approval.
- **COVERAGE:** derive a sparse matrix and reconcile identity counts before making absence claims.
- **REPAIR:** verify cross-timeframe globals and other documented defects with deterministic traces.
- **PARITY:** MACD, BREAKOUT_ACC, then SAR using common-input golden traces and residual attribution.
- **SELF-IMPROVE:** run the three approved process trials against independent baselines.
- **EXPLORE:** only approved, preregistered work may move from proposal to execution.

## 2. Reuse plan

| Need | Existing authority | Planned integration |
|---|---|---|
| Historical observations | RRA-01 documents and cited artifacts | Source adapters with commit/blob provenance |
| Append-only learning | ResearchMemory hash chain | Append reconciliation records; no second memory |
| Experiment identities/results | Existing Experiment Registry | Idempotent projections with revision checks |
| Gaps and coverage | RRA-01 sparse coverage plus canonical read model | Derived sparse projection; missing means `UNKNOWN` |
| Hypotheses and prioritization | Hypothesis Registry and `research_priority_queue_v1.json` | Top 20 imported as non-authorized proposals only |
| Failure learning | Existing failure map and RI review | Link recovered defects and prevention tests |
| Orchestration | RI-02 research loop and existing orchestrator | No new orchestrator; execution remains approval-bound |
| Human review | Existing proposal/approval boundaries | Reconciliations requiring policy remain pending decisions |
| UI/read model | Research Control Center/read model | Consume projected records only after schema implementation |

## 3. Self-improvement trials retained

1. **Provenance completeness:** compare a frozen baseline corpus against projector-assisted completeness for dataset, split, commit, parameters and output. Count false completeness claims.
2. **Invalid experiment prevention:** measure invalid experiments detected before costly execution and false blocks against an independently labeled fixture set.
3. **First divergence localization:** compare time and accuracy for locating seeded Python/MT5 divergence in MACD, BREAKOUT_ACC and SAR traces.

No trial may modify its baseline after reading the treatment result. A new record or filename does not establish an independent dataset or split.

## 4. Open decisions before implementation

- Definitions and current values for implemented, enabled, live-configured and operational strategy counts.
- Reconciled defect identity set and count.
- Representation of source vocabulary in target registry schemas.
- Transaction boundary when one projection targets multiple existing stores.
- Human authority for resolving policy conflicts.
- Whether Coverage Matrix is persisted as a versioned artifact or rebuilt as a deterministic read model.
- Exact current-source impact of suspected cross-timeframe indicator globals.

## 5. Acceptance criteria for the projector implementation

### Functional

- Ingests the five consolidated documents through an explicit allowlist.
- Produces stable source, experiment and projection identities.
- Preserves original statuses and emits four-dimensional reconciled statuses.
- Projects valid records into the existing Experiment Registry, ResearchMemory and sparse Coverage Matrix without creating parallel stores.
- Imports all Top 20 items as `authorized_for_execution=false` proposals and deduplicates them against existing hypotheses.
- Emits unresolved conflicts without silently selecting a winner.

### Determinism and persistence

- Two runs over identical bytes and rules produce byte-identical semantic output and zero second-run mutations.
- Concurrent runs cannot duplicate records or partially advance a canonical revision.
- Restart after an interrupted run resumes safely or rolls back the incomplete revision.
- Rule-version rollback restores the prior read-model projection without deleting history.

### Provenance and scientific safety

- Every important field resolves to artifact, commit and stable locator.
- Missing artifacts remain missing; no reconstruction is invented.
- Dataset/split/timeframe/lineage independence is checked mechanically before replication claims.
- `UNKNOWN` is retained where the declared census cannot prove absence.
- No `SUPPORTED` or `VALIDATED` projection can be produced from an unresolved conflict or invalid experiment.
- No holdout access, test execution, economic promotion, live operation or gate modification occurs.

### Compatibility and regression

- Existing RI-01/RI-02 records remain readable and unchanged.
- Existing hash-chain verification passes.
- Existing prioritization budgets, including BL-H4M15 6/6, remain unchanged.
- Research Control Center and canonical read models tolerate the new projection version and older records.
- No MQL5, strategy registry, edge registry, runtime, risk or trading files change in the implementation PR unless separately authorized.

## 6. Documentation-PR completion criteria

This documentation consolidation is complete when:

- all five source documents are present unchanged;
- the 12-item Reconciliation Matrix is reviewable;
- the four-dimensional taxonomy is explicit;
- projector identity, deduplication, conflict, versioning and rollback behavior are specified;
- RI reuse and open decisions are documented;
- no operational code or canonical registry changed;
- link and whitespace checks pass.
