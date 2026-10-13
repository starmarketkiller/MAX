# RRA-02 Max Total Drawdown Safety Specification

Status: implementation contract for Checkpoint A. This document does not authorize live trading.

## Four separate concepts

1. **Adjusted equity**: `A(t) = account_equity(t) - verified_net_capital_flow(t)`.
2. **High-water mark**: `P(t) = max(P(t-1), A(t))`.
3. **Protection latch**: once `100 * (P-A)/P >= InpMaxTotalDDPct`, new exposure remains blocked across day rollover and restart.
4. **Reset**: only the existing authenticated, confirmed and audited `reset_protections` command may establish a new epoch. It sets `P` to current equity, resets the capital-flow accumulator/cursor, clears recovery and the latch, and persists immediately. Snapshot schema v7 stores the command ID atomically with the epoch, so replay after interruption cannot move the baseline twice.

The gate applies to creation of new exposure. Position management and emergency flattening remain available.

## Capital-flow policy

No broker-history deal type is sufficient provenance for an owner deposit or withdrawal. In particular, `DEAL_TYPE_BALANCE` can also represent an economic correction. Until a separately authenticated capital-flow attestation exists, balance, credit, bonus and correction records enter recovery mode and block new exposure. They are not neutralized automatically. An authorized, audited reset may deliberately establish a new epoch; it is not an implicit classification of the accounting entry.

Ambiguous balance-changing records (`BALANCE`, `CREDIT`, `BONUS`, `CORRECTION`) cannot safely be classified as owner capital or performance. They put the protection in `RECOVERY_REQUIRED` and block new exposure until an authorized reset. Missing, corrupt, foreign or pre-v7 snapshots have the same fail-closed outcome outside Strategy Tester.

## Numerical examples

| Event | Raw equity | Net verified flow | Adjusted equity | Peak | DD | Result |
|---|---:|---:|---:|---:|---:|---|
| Authorized epoch starts | 10,000 | 0 | 10,000 | 10,000 | 0% | enabled |
| Trading profit | 12,000 | 0 | 12,000 | 12,000 | 0% | peak advances |
| Trading loss | 11,000 | 0 | 11,000 | 12,000 | 8.33% | below 10% |
| Deposit | 13,000 | +2,000 | 11,000 | 12,000 | 8.33% | unchanged |
| Withdrawal | 12,000 | +1,000 | 11,000 | 12,000 | 8.33% | unchanged |
| New trading loss | 11,700 | +1,000 | 10,700 | 12,000 | 10.83% | latch + flatten |
| Daily rollover | 11,700 | +1,000 | 10,700 | 12,000 | 10.83% | latch remains |
| Restart | restored | restored | restored | restored | restored | latch remains |
| Authorized reset | 11,700 | 0 | 11,700 | 11,700 | 0% | new audited epoch |

## Edge choices

- A deposit does not create performance and a withdrawal does not create drawdown.
- A withdrawal larger than current equity is invalid broker/account state and is fail-closed through the non-positive adjusted-equity check.
- An ordinary loss followed by a deposit remains a loss because both raw equity and net flow rise by the same amount.
- The latch is independent of daily protection flags; rollover may reset daily ESL/DPT state but never this latch.
- Snapshot schema v5 cannot be safely migrated because it did not contain the high-water mark, flow cursor or latch. It is rejected for Max-DD purposes and requires explicit recovery; no values are invented.

## Known integration boundary

The current `main` branch enforces the protection in `NXS_CommonExposurePreflight()` through `NXS_Prot_EntryBlocked()`. PR #36 separately adds the same preflight to final raw Buy/Sell helpers. This Safety PR does not duplicate or merge PR #36; final-helper coverage remains an explicit integration dependency until that PR is reviewed.
