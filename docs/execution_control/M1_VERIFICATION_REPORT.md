# M1 Verification Report

## Baseline and scope

* Base: `origin/main@c68a03267a2b8227efe20961d77ac29ae165c849`.
* Dedicated branch: `feature/execution-control-v1`.
* MQL5, trading/risk parameters, frontend, deployment and production: unchanged.
* GitHub Issues, Projects, pull requests, branches and worktrees: no mutation.

## Executed verification

| Check | Result |
|---|---|
| M1 + Shared Cognitive State targeted suite | 16 passed |
| Python module compilation | PASS |
| CLI bootstrap/report/snapshot smoke | PASS; implementation WIP 1/2 |
| Branch census | 66 branch rows + PR #10/#13/#17 records |
| `git diff --check` | PASS |
| Full backend regression | 1336 passed, 1 skipped, 3 failed |

The three full-suite failures are hash-integrity failures in untouched research
artifacts:

1. `test_bl01_results_v1.py::test_committed_memory_holds_the_run_and_its_analysis`
2. `test_contextual_edge_phase1_foundation.py::test_preregistration_hash_and_diagnostic_outcome_blindness`
3. `test_contextual_edge_phase1_foundation.py::test_execution_result_preserves_frozen_family_and_no_promotion`

M1 changes none of the files read by those tests and does not update frozen
hashes. They remain visible rather than being weakened or relabelled as M1
success. CI on the PR is the authoritative clean-run check.

## Deterministic guarantees demonstrated

* Seed import is restart-persistent and idempotent.
* Duplicate item registration cannot bypass transition policy.
* Dependencies gate `READY` and `IN_PROGRESS`.
* A three-thread concurrent start admits exactly two implementation items.
* `VERIFIED` requires evidence and `DELIVERED` cannot be skipped to.
* `BLOCKED` requires a reason; leaving it clears stale blockers.
* Handoff requires the current owner and is idempotent.
* Active TaskQueue records are projected without copying them into the work graph.
* The policy module imports no network or process-execution client.

## Not claimed

* No distributed multi-process transaction guarantee for the existing JSON store.
* No GitHub Project synchronization.
* No automatic mutation of PRs or branches.
* No start of M2 or M3.
