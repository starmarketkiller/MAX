# NEXUS RRA-02 — Reconciliation Matrix V1

**Status:** documentation-only reconciliation proposal. No source result, runtime registry, scientific gate, or operational state is changed by this document.

## 1. Purpose and provenance

This matrix reconciles the RRA-01 recovery at commit `c6bab0652fdbe054b986463bee1e747168cad177` with the independent RRA-02 review and the Final Research Architecture Addendum. Original statements remain immutable. A reconciled classification is a projection with an explicit claim scope, not a rewrite of the source.

Primary sources:

- `NEXUS_RRA_01_RESEARCH_RECOVERY_MASTER.md`
- `NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md`
- `NEXUS_RRA_01_SHORTLIST_AND_ROADMAP.md`
- `NEXUS_RRA_02_INDEPENDENT_REVIEW_RECONCILIATION.md`
- `NEXUS_RRA_02_FINAL_RESEARCH_ARCHITECTURE_ADDENDUM.md`
- `contracts/strategy-registry.json`
- `contracts/edge-validation-registry.json`
- the cited Phase 5–7 artifacts and vault records

Resolution states are `RESOLVED_BY_EVIDENCE`, `RESOLVED_BY_SCOPE`, `OPEN_REQUIRES_EVIDENCE`, `OPEN_REQUIRES_POLICY`, and `SUPERSEDED`.

## 2. Versioned matrix

| ID | Subject | Source statements | Reconciled decision | State | Required follow-up |
|---|---|---|---|---|---|
| RRA2-CON-001 | TSI defect | Edge registry says `DEFECT_BLOCKED`; Phase 7.17/7.18 says `FIX_CAUSALLY_VALIDATED` on the tested trace | Preserve both source records. Project remediation as validated only for the documented timeframe guard and trace. Do not infer standalone or economic edge | `RESOLVED_BY_SCOPE` | Verify artifact identity and then propose, but do not perform here, a registry remediation update with exact provenance |
| RRA2-CON-002 | VOLBRK Serious 3Y | Older memory says blocked/not run; Phase 7.8g–i records two infrastructure failures and one valid negative run | Canonical projection records three attempts separately. The valid run is negative evidence for the tested design; failed runs are not independent economic tests | `RESOLVED_BY_EVIDENCE` | Locate every stale summary before proposing an append-only correction |
| RRA2-CON-003 | Live strategy count | Strategy registry reports 53 live identities; Phase 7.11 census reports 55 | Do not select a number until `live`, `implemented`, `registered`, `enabled`, and `operational` are defined and counted independently | `OPEN_REQUIRES_EVIDENCE` | Deterministic identity/implementation census against current MQL5 and registry |
| RRA2-CON-004 | 83 strategy identities vs implementations | Registry has 83 historical identities; component-collapse work shows aliases, placeholders, and shared paths | Preserve all 83 lineage identities. Derive implementation status separately from resolvable source, handler, execution path, and tests | `RESOLVED_BY_SCOPE` | Produce an identity-to-implementation projection; no enum or ID migration in this documentation PR |
| RRA2-CON-005 | MACD cross-engine parity | RRA-01 describes three-engine agreement; registry has no `EXACT`; no canonical event-by-event proof exists | Treat agreement as aggregate/approximate. `EXACT_ON_FIXTURE` requires common bars, parameters, causal timestamp and event-by-event golden trace | `RESOLVED_BY_SCOPE` | First parity tranche: MACD 12/26/9 closed-bar crossover |
| RRA2-CON-006 | Sequence 0009/0014/0015 | Ledger uses `NEVER_TESTED`; artifacts say structural feasibility failed before outcome access | Preserve the source label and project experiment status `NOT_FEASIBLE`, with `outcome_accessed=false`; it is neither refuted nor economically tested | `RESOLVED_BY_SCOPE` | Add mapping rule to the projector contract |
| RRA2-CON-007 | IFVG/FVG_MIT/OB_MIT | Ledger uses `TESTED_INVALID`; reason is dead code/disabled execution, not a negative economic test | Project implementation status `DEFECTIVE` or `NOT_EXECUTABLE`, experiment status `INVALID`, and economic status `UNKNOWN` | `RESOLVED_BY_SCOPE` | Verify exact source paths before any repair proposal |
| RRA2-CON-008 | TSI `TESTED_VALID` | RRA-01 uses `TESTED_VALID` for a causal fix; edge registry concerns economic validation | Validity applies only to the remediation claim. Economic and standalone-edge status remain unchanged | `RESOLVED_BY_SCOPE` | Require `claim_scope=IMPLEMENTATION_REMEDIATION` in projections |
| RRA2-CON-009 | Defect count | Narrative count and enumerated defect list do not reconcile consistently | No corrected total is canonical yet. Counts must be derived from a versioned set of strategy IDs, not prose | `OPEN_REQUIRES_EVIDENCE` | Reconcile the list against Phase 7.10 and the current edge registry |
| RRA2-CON-010 | SAR mixed verdicts | Vault, Serious 3Y, external validation and live-6y records disagree | Preserve every experiment as a separate identity. No aggregate verdict until datasets, periods, engines and definitions are normalized | `OPEN_REQUIRES_EVIDENCE` | SAR closed-bar golden trace, followed by lineage-aware evidence synthesis |
| RRA2-CON-011 | Status vocabularies | RRA-01 combines test validity and outcome in `TESTED_*`; RRA-02 requires `REFUTED`, `INCONCLUSIVE`, `INVALID`, `NOT_FEASIBLE` distinctions | Adopt the multidimensional taxonomy in `NEXUS_RRA_02_SCIENTIFIC_STATUS_TAXONOMY_V1.md`; never overwrite source vocabulary | `RESOLVED_BY_SCOPE` | Implement only after schema and migration review |
| RRA2-CON-012 | Cross-timeframe globals | `g_atr`, `g_adx`, `g_rsi`, `g_macd`, and `g_macdSig` may retain entry-timeframe state during router passes; some earlier timeframe defects are already repaired | Record as a high-priority repair hypothesis, not a confirmed defect for every strategy. Existing validated fixes remain distinct | `OPEN_REQUIRES_EVIDENCE` | Deterministic per-pass trace on current source; no threshold tuning and no operational modification in this PR |

## 3. Decisions already supported

- RRA-01 is the completed historical census for its declared perimeter; uncensused areas remain `UNKNOWN`.
- The 83 registry entries are lineage identities, not proof of 83 independent implementations.
- TSI fix validity and TSI economic edge are different claims.
- VOLBRK has one valid negative run plus two infrastructure failures.
- `NEVER_TESTED`, `INVALID`, and economic refutation are not interchangeable.
- Cross-engine aggregate similarity is not event-level exact parity.
- Top 20 questions are candidate proposals only.
- PR #47 owns the Max Total Drawdown correction; RRA-02 must not duplicate it.

## 4. Open decisions

1. Current counts for implemented, enabled, live-configured, and operational strategies.
2. Exact defect-confirmed identity set and derived count.
3. SAR synthesis after lineage and parity normalization.
4. Current impact of each suspected cross-timeframe global.
5. Product/schema decision for representing source vocabulary alongside reconciled projections.

No open decision authorizes a test, mutation, promotion, deployment, or live operation.
