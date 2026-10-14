# M1 Verification Report

## Baseline and scope

* Base: `origin/main@c68a03267a2b8227efe20961d77ac29ae165c849`.
* Dedicated branch: `feature/execution-control-v1`.
* MQL5, trading/risk parameters, frontend, deployment and production: unchanged.
* GitHub Issues, Projects, pull requests, branches and worktrees: no mutation.

## Executed verification

| Check | Result |
|---|---|
| M1 + Shared Cognitive State targeted suite | 22 passed |
| Python module compilation | PASS |
| CLI bootstrap/report/snapshot smoke | PASS; implementation WIP 1/2 |
| Branch census | 66 branch rows + PR #10/#13/#17 records |
| `git diff --check` | PASS |
| Full backend regression | 1345 passed, 1 skipped, 1 failed |

The remaining full-suite failure is a hash-integrity failure in untouched
research artifacts:

1. `test_bl01_results_v1.py::test_committed_memory_holds_the_run_and_its_analysis`

M1 changes none of the files read by that test and does not update frozen
hashes. It remains visible rather than being weakened or relabelled as M1
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

## Correctness closure

The final M1 correction adds an operating-system advisory lock around every
public `SharedCognitiveState` transaction and snapshot. State is reloaded only
after acquiring that lock, policy checks run against that revision, and success
is returned only after fsync plus atomic replace. Windows and Linux use their
native locking primitives; process exit releases abandoned locks.

Authentic spawn-process tests cover three simultaneous implementation starts,
same-task collision, timeout, process death before persistence and process death
during atomic persistence. Bootstrap is a single semantic transaction and
remains idempotent after more than 500 unrelated idempotency keys while
preserving advanced owner/status/history state.

M1 workflow history is embedded in the canonical work graph. `EventLedger` is
not dual-written in V1 because an uncoordinated second write would weaken the
atomicity guarantee; global EventLedger integration remains future work.

## Not claimed

* No guarantee for writers that bypass the public transaction API or for
  distributed/network filesystems whose lock/replace semantics differ from a
  local Windows/Linux filesystem.
* No GitHub Project synchronization.
* No automatic mutation of PRs or branches.
* No start of M2 or M3.
