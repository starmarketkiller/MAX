# RRA-02 Checkpoint A — Safety Report

Baseline: `main@a61bca3db6d2bc8ef4f477c1bf59eee827527c40`
Scope: Max Total Drawdown only. No live trading, production deploy, merge, or holdout access.

## Root cause

| Finding | Evidence before patch | Decision |
|---|---|---|
| SAFETY-DD-001 | `NXS_Prot_CheckMaxTotalDD()` set `g_maxDDHit`, but `NXS_Prot_EntryBlocked()` did not read it and `NXS_Prot_OnNewDay()` cleared the shared pause flag. | Verified bug. Make the permanent latch an independent entry gate. |
| SAFETY-DD-002 | State schema v5 serialized neither `g_maxDDPeakEquity` nor `g_maxDDHit`. | Verified bug. Schema v6 persists peak, latch, capital-flow accumulator/cursor and recovery state. |
| 22.83% historical observation | Research preset explicitly used `InpResearchUseTotalDD=false`. | Not evidence of formula failure; keep distinct from operational policy. |
| Capital flows | Raw equity high-water mark treated deposits as profit and withdrawals as drawdown. | Use verified-flow-adjusted equity defined in the companion specification. |
| Restart during incomplete flatten | Latch could persist after this patch while an immediately-following flatten state had not yet been saved. | Persist after flatten and explicitly resume flatten on startup when latched exposure survives. |

## Implemented safety contract

- Permanent high-water mark over adjusted equity.
- Only `DEAL_TYPE_BALANCE` neutralized as verified owner capital flow.
- Ambiguous `CREDIT`, `BONUS`, and `CORRECTION` records fail closed.
- Replay cursor `(DEAL_TIME_MSC, ticket)` is durable and sorted before replay.
- Missing, corrupt, foreign, or schema-v5 snapshots fail closed outside Strategy Tester when Max Total DD is enabled.
- Existing authenticated, confirmed, rate-limited and append-only-audited `reset_protections` command is the sole reset authority.
- Reset establishes a new explicit epoch and persists it immediately.
- New exposure is blocked; position management and emergency flattening remain reachable.

## Risk safety matrix

| Scenario | Expected behavior | Verification |
|---|---|---|
| Below threshold | No latch | Deterministic reference-model test |
| At/above threshold | Latch, flatten, durable save | Source-contract test + MetaEditor compile |
| Daily rollover | Latch remains an independent gate | Source-contract test |
| Restart after trigger | Restored latch/peak; surviving exposure flattened again | Source-contract test |
| Missing/corrupt/legacy snapshot | No new exposure; explicit recovery reason | Source-contract test |
| Deposit/withdrawal | Adjusted equity and DD unchanged | Deterministic reference-model test |
| Ambiguous account flow | `RECOVERY_REQUIRED`, new exposure blocked | Source-contract test |
| Concurrent/same-ms deals | Ordered by `(time_msc,ticket)`, processed once | Source-contract review; runtime broker replay remains to be exercised |
| Manual reset | Audited new epoch, immediate persistence | Existing command-policy tests + new source-contract test |
| Incomplete flatten | Retry loop and restart recovery | Source-contract test |
| Strategy Tester without persistence | Isolated run allowed; no operational snapshot touched | Code path + tester-specific state filename |

## Verification executed

- Targeted pytest: `35 passed` before the final restart-recovery addition; rerun required in final gate.
- MetaEditor from `C:\MT5-Tester`: `0 errors, 2 warnings`. Both warnings pre-exist this change (`NXS_MAX_SIGNALS` macro redefinition and an unrelated ulong→long conversion).
- Backend regression: `1267 passed, 1 skipped, 3 failed`. The three failures are pre-existing cross-platform canonical-artifact hash failures in BL-01/MACD preregistration; no failing test touches this Safety diff and their expected/actual hashes match the previously documented Windows newline issue. They are not changed in this PR.

## DEMO/LIVE and PR #45 boundaries

- DEMO/LIVE enforcement remains assigned to PR #36 and is not duplicated here. This patch relies on the existing common exposure preflight; PR #36 remains the reviewed path for final raw Buy/Sell helper defense-in-depth.
- PR #45 remains telemetry-only and separate. Its known gaps are closure/disappearance reconciliation, partial fills and error observability; none are silently folded into Max-DD safety.

## Residual risks / review points

1. Strategy Tester cannot natively inject broker deposit/withdrawal history into an ordinary backtest. The arithmetic and persistence contracts are deterministic tests, but a broker-history replay fixture is still needed for a dynamic capital-flow scenario.
2. Final raw helper coverage depends on review/integration of PR #36; this PR does not change execution helper authorization.
3. Schema v5 cannot be safely auto-migrated because the missing peak/latch cannot be reconstructed. The chosen fail-closed manual recovery is intentional and operationally disruptive by design.
4. No production or live-account validation has been performed or authorized.

Rollback: revert this PR. Existing schema-v5 snapshots remain untouched on disk but are intentionally incompatible with schema v6; rollback must be treated as a safety migration, not a casual hot rollback on an attached account.
