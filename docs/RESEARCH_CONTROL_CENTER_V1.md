# Research Control Center V1 (RI-03)

RI-03 is an authenticated, read-only projection of the canonical RI-01/RI-02 research memory. It does not run the autonomous loop, rank hypotheses, approve proposals, access protected holdouts, or alter scientific evidence.

## API

`GET /api/research/intelligence/control-center`

- Requires the existing authenticated dashboard session.
- Reads `research_memory_v1.jsonl` through the canonical `ResearchMemory` implementation.
- Verifies the memory hash chain and checkpoints before reporting the source as verified.
- Returns explicit `UNAVAILABLE`, `NOT_MATERIALIZED`, `INACTIVE`, or `IDLE_NOT_RUN` states when canonical records do not exist.
- Exposes no mutation route. Approval actions remain disabled in RI-03.

Response sections:

- `research_loop`: persisted cycle/transitions and next action, if present.
- `experiment_registry`: experiment records, dataset references, evidence level and provenance.
- `hypothesis_queue`: latest persisted `PRIORITIZATION`; never computed in the read model.
- `improvement_center`: current proposals and linked trial results.
- `research_memory`: persisted observations and reviews.
- `agent_activity`: registered RI roles and their persisted transition outcome.
- `approval_center`: proposals awaiting human attention, display-only.
- `provenance`: canonical source path, record count, head hash and verification state.

The response is defined by `contracts/research-control-center-v1.schema.json`.

No client-provided owner, tenant, statistics or evidence is trusted. No output is presented as scientific validation merely because it is present in memory.

## Frontend

The existing Research workspace includes `/research/intelligence`. Empty and unavailable states are rendered explicitly. The Approval Center intentionally has no decision buttons; enabling them requires a separately verified authentication, authorization, replay-protection and audit contract.

## Render

RI-03 runs inside the existing `nexus-backend` service and dashboard bundle. It adds no service, paid dependency or environment variable. The canonical memory is currently packaged with the repository; if it is absent or corrupt the API fails closed at the projection boundary.

## Safety boundaries

- No scientific engine changes.
- No access to protected holdouts.
- No trading, risk, EA or execution changes.
- No background loop activation.
- No approval mutation.
- No production or Render configuration changes.
