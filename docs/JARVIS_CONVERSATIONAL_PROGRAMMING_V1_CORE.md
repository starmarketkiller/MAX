# Jarvis Conversational Programming V1 Core

## Boundary

`JARVIS_MESSAGE_V1` is deterministically resolved into a schema-validated
`JARVIS_PROGRAMMING_PLAN_V1`, then stored with the canonical Queue record.
Jarvis plans intent and capabilities; it does not select or invoke an executor.

The P0 lifecycle is `READ -> INSPECT_CI -> PATCH_WORKSPACE -> TEST -> COMMIT -> PUSH`.
Disabled stages stay explicit. Deploy is never a direct agent capability: a
future approved push may only reach production through Safe Auto Deploy V1.

## Safety invariants

- Default flags are `NO_PUSH` and `NO_DEPLOY`.
- `TEST_ONLY` disables patch, commit, and push.
- `COMMIT_ONLY` disables push.
- A requested push requires `EXPLICIT_USER_APPROVAL`.
- Secrets, `.env`, MQL5 and frozen research artifacts remain forbidden by the
  task manifest unless a separate, explicit task changes that boundary.
- Per-task `files_allowed` is the least-privilege filesystem scope.
- Conversation context resolves references, but Queue and Ledger remain the
  canonical task state.
- Routing remains Provider Policy controlled: deterministic, local, verified
  free-online, then Codex. Unverified free providers remain evaluation-only.

## P0 limitation

This core deliberately stops at planning, queueing, routing and approval
boundaries. It does not add a generic shell runner or autonomous Git writer.
Actual patch execution requires an already-authorized handler/provider and
continues through the existing verifier and approval lifecycle.
