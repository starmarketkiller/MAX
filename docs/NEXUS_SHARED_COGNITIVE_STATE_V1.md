# NEXUS Shared Cognitive State V1

`NEXUS_SHARED_COGNITIVE_STATE_V1` is the canonical current-state projection shared by
Jarvis and execution/review agents. It is not a replacement for the append-only Activity
Ledger or Task Queue.

## Components

- `CURRENT_STATE_V1`: production identity, milestones, roadmap, blockers, priorities and
  declared agent/provider state.
- `WORK_GRAPH_V1`: owned workstreams plus explicit typed dependencies. Runtime task state
  is projected from `TaskQueue` at read time.
- `DECISION_REGISTRY_V1`: explicit decisions with lifecycle and supersession metadata.
- `ARTIFACT_RESERVATION_V1`: advisory leases for repo-safe artifact paths. They expose
  overlap before edits but never implement destructive Git locks.
- `CONTEXT_PACKET_V2`: compact read-only materialization for “where are we?”, current
  ownership, availability, P0, live SHA and recent results.

## Truth and persistence rules

Writes are atomic JSON replacements guarded by a process-local lock and monotonic revision.
Callers may use expected revision (compare-and-swap) and idempotency keys. Only `VERIFIED`
or explicitly `DECLARED` provenance can enter canonical state. `UNVERIFIED` observations are
rejected rather than silently promoted. Reservations use TTL and become `STALE`; they never
block Git directly.

The V1 store is single-process, matching the current Orchestrator deployment. Moving to
multiple writers requires a transactional shared database; the revision contract is designed
to remain stable through that migration.

## Integration

Authenticated `GET /api/jarvis/context` returns `CONTEXT_PACKET_V2`. There is deliberately
no public mutation API in V1. Internal trusted workflows update the store via
`SharedCognitiveState`; existing Jarvis, Router, Queue and Ledger behavior remains unchanged.
