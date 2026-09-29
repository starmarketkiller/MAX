# NEXUS Jarvis Access Layer V1

## Decision

`JARVIS_ACCESS_LAYER_V1_OPERATIONAL_WITH_LIMITATIONS`

The code, contracts, Orchestrator integration and Telegram adapter are ready. A
production Telegram conversation remains deliberately gated by deployment,
secret configuration and webhook approval.

## Production baseline

- Local and `origin/main` at implementation start: `ceb0ace6ba35d3ca8352c27448fe63f3ca0b8cde`.
- NEXUS TASK #0007 is present and preserved.
- Current production before this change: healthy and ready, but `/api/version`
  is absent, therefore `PRODUCTION_UNKNOWN`.
- The new public `/api/version` exposes only app version, environment, build
  time and `RENDER_GIT_COMMIT`/approved equivalent. It exposes no secrets.
- No deployment is performed by this task.

## Architecture

```text
TelegramAdapter (future: PWA / WhatsApp / Voice / Desktop / AR)
        |
   JarvisGateway  -- validates JARVIS_MESSAGE_V1 / JARVIS_RESPONSE_V1
        |
   JarvisService  -- classification, factual query projection, task handoff
        |
 NEXUS Orchestrator V1
        |
 TaskQueue / Router / EventLedger / approval transitions / capability registry
```

Jarvis never selects an executor. Operational requests create a real
`TASK_MANIFEST_V1`; the Router retains exclusive executor authority. A chat
returns a durable `task_id`, not a long-running HTTP request.

## Contracts

- `contracts/jarvis-message.schema.json`
- `contracts/jarvis-response.schema.json`
- `contracts/jarvis-card.schema.json`

Only `TEXT` is executable in V1. Other declared input types return
`UNAVAILABLE` rather than being simulated.

## Query path

“Jarvis, cosa è successo oggi?” reads the real TaskQueue, append-only
EventLedger, provider registry, Funding priority artifact and recent Vault
metadata. Ministral is attempted locally. No premium fallback occurs; when
Ollama is offline the response is deterministic, source-backed and `PARTIAL`,
with `premium_calls=0`.

## Task and approval paths

- Task messages create a schema-valid `TASK_MANIFEST_V1` and queue it.
- Follow-ups resolve the conversation's last task or an explicit `task_id`.
- Second opinion/review intent becomes structured capability metadata; Jarvis
  does not fan out to every provider.
- Approve/reject callbacks use TaskQueue's existing fail-closed transitions and
  append approval events to the existing ledger.

## Telegram security

- `TELEGRAM_BOT_TOKEN` only from environment.
- `JARVIS_TELEGRAM_ALLOWED_USER_IDS` required and fail-closed.
- `JARVIS_TELEGRAM_WEBHOOK_SECRET` required with constant-time comparison.
- update ID persistence provides idempotency; per-user rate limit is 20/minute.
- secrets and message text are not copied to ledger events.
- irreversible operations remain behind Orchestrator approval.

Required production variables:

```text
JARVIS_STATE_DIR=/data/jarvis
JARVIS_TELEGRAM_ALLOWED_USER_IDS=<numeric IDs, comma separated>
JARVIS_TELEGRAM_WEBHOOK_SECRET=<random secret>
NEXUS_PUBLIC_URL=https://nexus-backend-8o4y.onrender.com
TELEGRAM_BOT_TOKEN=<existing Render secret>
```

After an approved deploy, configure the webhook explicitly with
`server/jarvis_v1/configure_telegram_webhook.py`. It is never registered during
application startup.

## API

- `GET /api/version` (public non-sensitive build identity)
- `POST /api/jarvis/message`
- `GET /api/jarvis/tasks/{id}`
- `GET /api/jarvis/activity`
- `GET /api/jarvis/agents`
- `GET /api/jarvis/approvals`
- `POST /api/jarvis/approvals/{id}`
- `GET /api/jarvis/telegram/status`
- `POST /api/jarvis/telegram/webhook` (Telegram secret + user allowlist)

Dashboard endpoints reuse existing cookie/CSRF authentication. Telegram uses
its dedicated webhook secret because Telegram cannot hold a dashboard cookie.

## Notification policy

`INFO` remains ledger-only and is aggregatable. `IMPORTANT`, `HIGH` and
`URGENT` can reach Telegram. V1 has no voice interruption. Direct replies to a
user message are not treated as unsolicited notifications.

## Known limitations / deployment gate

- Runtime state is JSON/JSONL and assumes a single Render instance; a durable
  multi-replica engine remains future work.
- Conversation-to-task memory is process-local in V1; explicit task IDs remain
  durable. Persisting conversation pointers belongs to Durable Workflows.
- Local Ministral requires Ollama on the same host. Render normally lacks it,
  so factual fallback is expected there unless a local runtime is connected.
- Provider quota states are projected from the canonical capability registry;
  no provider is called to infer quota.
- Production Telegram acceptance tests require deployment and secrets.

Final operational gate: `WAITING_DEPLOY_APPROVAL`.

