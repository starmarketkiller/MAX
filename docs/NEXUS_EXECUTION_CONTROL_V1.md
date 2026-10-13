# NEXUS Execution Control V1

## Scope and baseline

M1 starts from `origin/main@c68a03267a2b8227efe20961d77ac29ae165c849` (merge of PR #51).
It is a coordination layer only. It does not modify the EA, trading parameters,
production, GitHub Issues, pull requests, branches, or worktrees.

## Reuse inventory and canonical ownership

| Concern | Reused canonical component | M1 responsibility |
|---|---|---|
| Portfolio/current work | `SharedCognitiveState.work_graph` | Enforce workflow, WIP and handoff policy |
| Runnable tasks | `TaskQueue` / `TASK_MANIFEST_V1` | No semantic change; referenced as runtime source |
| History and evidence | `EventLedger` | No semantic change; referenced as history source |
| Agent capabilities | existing capability registry and router | Owners are labels, never permissions |
| Artifact coordination | existing reservations in `SharedCognitiveState` | No new lease system |
| Jarvis context | `CONTEXT_PACKET_V2` | Existing work graph remains visible to Jarvis |
| Task handoff files | `jarvis_v1/task_handoff.py` | No duplicate artifact pipeline |
| GitHub | existing repository, PRs and CI | Read-only inventory; sync is disabled |

The single canonical task/milestone registry is therefore
`NEXUS_SHARED_COGNITIVE_STATE_V1.work_graph`. `execution_control_seed_v1.json`
is an idempotent bootstrap/migration artifact, not a second mutable store.

## Workflow

`BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFIED → DELIVERED`

`BLOCKED` is reachable from active non-terminal states and requires a structured
blocker. Returning from `BLOCKED` is allowed only to `BACKLOG` or `READY`.
`DELIVERED` is terminal. Moving to `READY` or `IN_PROGRESS` requires every
dependency to be `VERIFIED` or `DELIVERED`; `VERIFIED` requires evidence.

Implementation WIP is enforced atomically at **2**. Research, review and audit
work remain visible but do not consume implementation slots. This is a
portfolio limit; TaskQueue still owns lower-level execution concurrency.

Every item requires one owner and at least one completion criterion. Handoffs
verify the current owner, change ownership atomically and append a trace. An
agent label never grants a capability or authorization.

## Existing work reconciliation

The bootstrap records:

* M1 as the sole active implementation owned by Codex;
* M2 and M3 as `BACKLOG`, explicitly outside the current authorization;
* the declared Scalper work on `Z_SCORE_BREAKOUT`, `BOLLINGER` and
  `EMA_PULLBACK` without executing or promoting it;
* a fail-closed Claude reconciliation item because the repository does not
  identify one current approved Claude deliverable unambiguously. This record
  does not interrupt or redefine work outside the repository.

## Branch and PR census

`BRANCH_PR_CLASSIFICATION_V1.csv` contains exactly **66** remote branches plus
three separate PR records. The branch classifications are evidence statements,
not cleanup instructions:

* 36 `INTEGRATED_BY_ANCESTRY`;
* 17 `HISTORICAL_UNRECONCILED`;
* 10 `RECENT_UNRECONCILED`;
* PR #10 and #13: `OPEN_DRAFT_DIRTY`;
* PR #17: `OPEN_DRAFT_UNSTABLE` (backend/frontend/image checks passed in its
  last run, security preflight failed).

The census uses branch tip SHA and `git merge-base --is-ancestor`. A non-ancestor
classification does not assert that none of its changes reached main through a
squash or later implementation; it requires reconciliation before any cleanup.
No branch, worktree or PR is changed by M1.

## GitHub compatibility

GitHub Issues are disabled and were not enabled. GitHub Projects is enabled at
repository/account level, but the current token lacks `read:project`, so no
existing project could be verified and no project was created. Work items allow
`external_refs` so a later approved adapter can map:

| Execution Control | GitHub |
|---|---|
| `id` | Issue/project item external key |
| `status` | Project status field |
| `owner.agent_id` | Assignee/custom agent field |
| `completion_criteria` | Acceptance checklist |
| `dependencies`, `blockers` | Linked issues/custom fields |
| `handoffs` | Auditable comment/event projection |

GitHub remains a future projection, not a competing source of truth.

## Operator instructions

From `server/`:

```text
python -m orchestrator_v1.run_execution_control_v1 bootstrap --state <shared-state.json>
python -m orchestrator_v1.run_execution_control_v1 report --state <shared-state.json>
python -m orchestrator_v1.run_execution_control_v1 snapshot --state <shared-state.json>
python -m orchestrator_v1.run_execution_control_v1 report --state <shared-state.json> --queue <task-queue.json>
```

`bootstrap` is idempotent. `report` gives a compact human view of all work,
implementation WIP and suspended items. `snapshot` emits the read-only JSON
projection. None of these commands starts a queued task or contacts GitHub.
When `--queue` is supplied, the same report also projects active runtime tasks
without copying them into the work graph.

Normal operation:

1. Register a work item with owner, completion criteria, dependencies and
   provenance.
2. Move it to `READY` only when dependencies are verified.
3. Start it only if the implementation WIP gate admits it.
4. Move completed work to `REVIEW`; attach independent evidence to `VERIFIED`.
5. A human-authorized delivery moves `VERIFIED` to `DELIVERED`.
6. Use `handoff()` for ownership changes; do not edit owner fields directly.

## Risks and limitations

| Risk | Current treatment | Residual limitation |
|---|---|---|
| Multi-process writers | Atomic replace, process-local lock, revision CAS | Existing JSON store is not a distributed transaction database |
| Direct `upsert_workstream` callers | M1 code uses policy layer | Legacy internal code could bypass M1 policy; no public mutation API exists today |
| GitHub drift | Snapshot includes exact SHAs and evidence method | No approved bidirectional sync; Project could not be read with current token |
| External agent activity | DECLARED provenance and explicit ambiguity | Claude exact current deliverable needs a trusted handoff |
| Branch classification | Ancestry is reproducible and conservative | Squash-equivalent changes require semantic reconciliation |
| Reporting freshness | Generated directly from canonical projection | No scheduler is added; automation can call the CLI later |

## Acceptance evidence

Deterministic tests cover schema/seed validity, restart persistence,
idempotency, dependencies, transition gates, verification evidence, concurrent
WIP enforcement, owned handoff, blocked-work reporting and absence of network
mutation code. Existing Shared Cognitive State tests protect the reused storage
and context projection.

M2 and M3 are intentionally not started by this milestone.
