# NEXUS Durable Queue Dispatcher V1

## Purpose

The dispatcher closes the gap between a task being persisted as `QUEUED` and the existing `Orchestrator.process_task(task_id)` lifecycle. It does not route, execute premium providers, approve work, or finalize scientific conclusions. Those responsibilities remain in the existing Orchestrator, Router, workers, Review Pipeline, and Approval Gate.

## Runtime model

V1 runs one daemon consumer thread inside the single Uvicorn web process:

```text
Telegram / Web
    -> JarvisGateway
    -> TASK_MANIFEST_V1 persisted on /data/jarvis
    -> DurableQueueDispatcher (max concurrency 1)
    -> Orchestrator.process_task
    -> Router / worker / verifier / approval / escalation
    -> RESULT_PACKET_V1
```

A separate Render Background Worker is deliberately not introduced in V1. The current queue is a JSON file on the `nexus-backend` persistent disk, and Render disks cannot be mounted simultaneously by the web service and a second worker service. Sharing this queue safely would require migration to PostgreSQL or Render Key Value, which is outside this task.

## Claim and idempotency rules

- Only `QUEUED` tasks with completed dependencies can be claimed.
- A durable `dispatch_claim` contains an opaque token, owner, claim time, and lease expiry.
- `Orchestrator.process_task` validates the claim before moving to `RUNNING`.
- An active claim prevents manual or duplicate dispatcher execution.
- Queue saves use write/fsync/atomic replace and an in-process reentrant lock.
- Concurrency is fixed at one.
- Expired claims on tasks that never entered `RUNNING` may be reclaimed.
- A `RUNNING` task found after restart is `BLOCKED` as `ORPHANED_RUNNING_AFTER_RESTART`; it is never replayed automatically because side effects may be ambiguous.
- A dispatcher exception before `RUNNING` releases the claim and applies bounded backoff. An exception after `RUNNING` blocks the task fail-closed.

## State boundaries

The dispatcher does not consume or alter tasks in:

- `WAITING_APPROVAL`
- `WAITING_PROVIDER`
- `ESCALATION_REQUIRED`
- `BLOCKED`
- `COMPLETED`
- `FAILED`

`WAITING_DEPENDENCY` becomes `QUEUED` only after every declared dependency is `COMPLETED`.

## Ledger events

- `DISPATCHER_STARTED`
- `DISPATCHER_STOPPED`
- `TASK_CLAIMED`
- `TASK_EXECUTION_STARTED`
- `TASK_DISPATCH_RETRY`
- `TASK_CLAIM_RELEASED`
- `TASK_ORPHANED`

Existing Orchestrator events remain authoritative for routing, execution, approval, completion, failure, and escalation.

## Shutdown

FastAPI shutdown stops accepting new work and waits up to the configured drain timeout for the current task. If Render sends `SIGKILL` after its shutdown window, the next process classifies the persisted `RUNNING` task fail-closed.

## Configuration

The Render Blueprint enables:

```text
NEXUS_QUEUE_DISPATCHER_ENABLED=true
NEXUS_QUEUE_DISPATCHER_POLL_SECONDS=2
NEXUS_QUEUE_DISPATCHER_LEASE_SECONDS=900
NEXUS_QUEUE_DISPATCHER_SHUTDOWN_SECONDS=25
```

Development and tests default to disabled. Production readiness fails if the dispatcher is enabled but its thread is not running. Authenticated operational status is available at:

```text
GET /api/jarvis/dispatcher/status
```

## Known limitations

- V1 assumes one Uvicorn process and one Render service instance. Horizontal scaling requires a transactional shared queue.
- In-flight work is not checkpointed inside arbitrary handlers; ambiguous work is blocked for manual review rather than replayed.
- Jarvis task type `jarvis_task` currently has no generic local handler. The Router therefore produces a real `ESCALATION_REQUIRED` when no registered safe handler can execute it; the dispatcher does not fabricate a worker.
- Claude/Codex connectors remain manual and are not invoked automatically.
