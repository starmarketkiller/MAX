# 10. LocalBridge Protocol

## Current implementation

Two identical worker copies were observed:

- `LocalBridge/nexus_local_worker.py`
- `server/nexus_local_worker.py`

**Risk:** duplicate source files can diverge. One canonical package should own the worker.

## Current contract mismatch

The React page expects concepts including:

- `worker`;
- statuses such as `running` and `failed`;
- `_id`;
- `result`.

The backend uses concepts including:

- `hosts`;
- `sent` and `error`;
- `id`;
- a different response shape.

Other observed issues:

- frontend hardcodes `host_id="default"`;
- epoch seconds can be interpreted as JavaScript milliseconds;
- deploy version is hardcoded;
- deploy file list may be empty;
- restart/deploy controls lack a fully confirmed lifecycle.

## Target protocol

### Host registration

A host receives a stable server-issued `host_id` and credential. Registration stores:

- OS and architecture;
- worker version;
- MT5 terminal paths;
- supported capabilities;
- last heartbeat;
- current deployment version.

### Heartbeat

```json
{
  "host_id": "...",
  "worker_version": "2.1.0",
  "status": "ONLINE",
  "capabilities": ["DEPLOY_EA", "RESTART_MT5"],
  "active_command_id": null,
  "timestamp": "ISO-8601"
}
```

### Command result

```json
{
  "command_id": "...",
  "status": "SUCCEEDED",
  "started_at": "...",
  "finished_at": "...",
  "exit_code": 0,
  "result": {},
  "log_excerpt": "..."
}
```

## Deployment package

Deployments should reference a manifest rather than a hardcoded version:

```json
{
  "release_id": "nexus-2.0.14",
  "sha256": "...",
  "files": [
    {"path": "MQL5/Experts/NEXUS_EA_v2.ex5", "sha256": "..."}
  ],
  "minimum_worker_version": "2.1.0"
}
```

## Required tests

- host registration and credential rejection;
- lease timeout and retry;
- duplicate command idempotency;
- failed deployment rollback;
- timestamp contract;
- worker/frontend/backend status compatibility;
- wrong-host command isolation.
