# PR8 — Command and LocalBridge contract

## Canonical protocol

`contracts/command.schema.json` defines schema version 1, command types, target
fields and the lifecycle states `PENDING`, `LEASED`, `RUNNING`, `SUCCEEDED`,
`FAILED_RETRYABLE`, `FAILED_FINAL`, `EXPIRED` and `CANCELLED`.

Bridge commands require an explicit `target.host_id`. Polling atomically leases
only commands for the registered host. ACKs must match command ID, host ID and
lease ID, preventing a different machine or an expired worker attempt from
completing the command.

## Reliability

- leases expire after 45 seconds and can be retried;
- attempts are counted and capped per command;
- exhausted commands move to `FAILED_FINAL` (dead-letter state);
- idempotency keys return the original command instead of enqueueing a duplicate;
- command transitions are appended to `command_events`;
- external timestamps are ISO-8601 UTC rather than ambiguous epoch units.

## Worker and deployment

`LocalBridge/nexus_local_worker.py` is the only worker source. The duplicate
under `server/` was removed and the download endpoint now serves the canonical
file. Worker 2.0 sends `RUNNING` and terminal ACKs with its lease ID.

File deployment validates per-file SHA-256, rejects paths outside MQL5 and
restores backups if a multi-file deployment fails. The versioned manifest at
`deploy/deployment-manifest.json` is generated from tracked sources and records
release `nexus-3.40`, file hashes and minimum worker version.

## Compatibility and verification

Responses retain legacy `id`/`action` aliases during migration while exposing
canonical fields. The frontend uses canonical states, the observed host ID and
ISO timestamps. Tests cover idempotency, wrong-host isolation, lease retry,
dead-letter behavior, ACK lease validation, single worker ownership and manifest
checksums.
