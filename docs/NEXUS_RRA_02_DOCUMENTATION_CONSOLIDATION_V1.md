# NEXUS RRA-02 — Documentation Consolidation V1

**Status:** READY_FOR_DOCUMENTATION_REVIEW

**Change class:** documentation only
**RRA-01 source:** `docs/nexus-rra-01-research-recovery@c6bab0652fdbe054b986463bee1e747168cad177`

## Consolidated source set

The following source documents are included without changing their original findings:

1. [RRA-01 Research Recovery Master](NEXUS_RRA_01_RESEARCH_RECOVERY_MASTER.md)
2. [RRA-01 Strategy Ledger and Coverage](NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md)
3. [RRA-01 Shortlist and Roadmap](NEXUS_RRA_01_SHORTLIST_AND_ROADMAP.md)
4. [RRA-02 Independent Review Reconciliation](NEXUS_RRA_02_INDEPENDENT_REVIEW_RECONCILIATION.md)
5. [RRA-02 Final Research Architecture Addendum](NEXUS_RRA_02_FINAL_RESEARCH_ARCHITECTURE_ADDENDUM.md)

## Reconciled design set

- [Reconciliation Matrix V1](NEXUS_RRA_02_RECONCILIATION_MATRIX_V1.md) records the twelve known contradictions and their resolution state.
- [Scientific Status Taxonomy V1](NEXUS_RRA_02_SCIENTIFIC_STATUS_TAXONOMY_V1.md) separates implementation, experiment, evidence and economic status.
- [Research Projector Design V1](NEXUS_RRA_02_RESEARCH_PROJECTOR_DESIGN_V1.md) specifies an idempotent projection into existing Research Intelligence stores.
- [RI-01/RI-02 Integration and Acceptance V1](NEXUS_RRA_02_RI_INTEGRATION_AND_ACCEPTANCE_V1.md) defines reuse, open decisions and implementation acceptance criteria.

## Authority and non-effects

The five source documents remain historical evidence. The reconciled documents are design proposals and read-model rules; they do not mutate source results or canonical registries.

This consolidation does not:

- modify MQL5, runtime, risk, trading or strategy parameters;
- modify Experiment Registry, ResearchMemory, Coverage Matrix, strategy registry or edge registry;
- implement the projector;
- authorize a hypothesis, allocate a research budget or execute a test;
- access a protected holdout;
- promote an economic claim;
- merge PR #47 or PR #36, or duplicate their responsibilities;
- deploy any service.

## Binding roadmap

`SAFETY → RECOVER → COVERAGE → REPAIR → PARITY → SELF-IMPROVE → EXPLORE`

The Strategy-first, Event-first and Outcome-first paradigms share one causal Research Event/Feature Layer. They do not become separate engines, memories, orchestrators or approval systems.

## Next authorized boundary

The next implementation may begin only after review of the taxonomy, open decisions and projector transaction model. Its first deliverable must be a deterministic dry-run projection with no canonical writes.
