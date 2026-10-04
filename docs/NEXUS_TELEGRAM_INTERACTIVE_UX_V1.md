# NEXUS Telegram Interactive UX V1

## Boundary

Telegram is a presentation adapter. It decodes compact `J1` callback data and
passes a structured UI intent to `JarvisService`. It never mutates TaskQueue,
approval state, recovery state, or the Ledger directly.

## Callback contract

| Code | UI action | Canonical service path |
|---|---|---|
| `TS` | refresh task | `follow_up()` |
| `TD` | technical details | `follow_up(technical_details=True)` |
| `LC` | lifecycle page | `task_lifecycle()` |
| `DG` | diagnostics | `follow_up(technical_details=True)` |
| `AP` | approve | `approval(APPROVE)` |
| `RJ` | reject | `approval(REJECT)` |
| `RS` | resume recovery | `JarvisService.resume_orphaned()` → `Orchestrator.resume_orphaned_task()` |
| `AD` | agent details | `agent_view()` |
| `AC` | capabilities | `agent_view()` |
| `PS` | provider state | `agent_view()` |
| `Q` | quick action | existing command handlers |

Mutating callbacks carry a compact expected-state code. The service reloads
the canonical queue record and rejects stale cards. Approval/rejection are
already idempotent through the state boundary; a second click cannot perform a
second mutation. Interactive recovery is intentionally limited to
`ORPHANED_RUNNING_AFTER_RESTART`.

## Views

- Task cards expose state, title, executor, blocker/recovery, escalation
  classification and target separately, and the next canonical step.
- Technical details expose attempts, retry, verifier/failure, decision and
  lifecycle preview.
- Lifecycle pages contain six events and expose `Mostra altro` only when more
  history exists.
- Agent rows come from the canonical capability registry and expose ID, role,
  provider, state and a short capability preview. Missing provider facts remain
  `UNKNOWN`.
- Unknown/error responses expose safe read-only quick actions.

## Known limitations

- Telegram callback query acknowledgement is not yet a separate transport
  operation; the bot sends the resulting message through the existing path.
- V1 shows up to eight agent navigation buttons in one message and ten agent
  rows. A dedicated multi-page agent catalog is deferred until the registry
  grows beyond this bounded view.
- Provider status is the registry projection. It does not probe providers and
  does not change routing policy.

