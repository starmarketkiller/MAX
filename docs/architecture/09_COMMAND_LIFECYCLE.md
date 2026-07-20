# 9. Command Lifecycle

## Current command channels

The repository contains at least two command concepts:

1. EA/dashboard command polling.
2. LocalBridge command queue with acknowledgement.

## Current defects

### EA commands

- commands are not clearly targeted to a unique account/instance;
- oldest pending command can be consumed globally;
- consumption can occur before execution confirmation;
- frontend may refresh immediately after enqueue and present stale state.

### LocalBridge commands

The lifecycle is closer to:

```text
pending → sent → done/error
```

but lacks robust leasing, retries, attempt count and dead-letter handling.

## Canonical command envelope

```json
{
  "command_id": "uuid",
  "command_type": "RESTART_EA",
  "schema_version": 1,
  "created_at": "...",
  "created_by": "operator-id",
  "target": {
    "instance_id": "...",
    "host_id": "...",
    "account_id": "...",
    "symbol": "..."
  },
  "payload": {},
  "idempotency_key": "...",
  "expires_at": "...",
  "status": "PENDING"
}
```

## Canonical states

```text
PENDING
LEASED
RUNNING
SUCCEEDED
FAILED_RETRYABLE
FAILED_FINAL
EXPIRED
CANCELLED
```

## Lease protocol

1. Worker requests commands for its authenticated `host_id`.
2. Backend atomically assigns a lease with expiry.
3. Worker acknowledges start.
4. Worker sends heartbeat/progress if long-running.
5. Completion includes structured result and logs.
6. Expired leases return to pending until max attempts.
7. Commands exceeding max attempts enter dead-letter state.

## Security rules

- host identity must be issued server-side, not trusted from arbitrary client input;
- command types and payloads require per-type validation;
- destructive commands require authorization and UI confirmation;
- secrets must never be embedded in command payloads;
- every transition is appended to the event ledger.

## Frontend behavior

The UI must display command state from backend acknowledgement. A successful enqueue is not equivalent to successful execution.
