# NEXUS — Jarvis Access Layer V1

Status: **OPERATIONAL_WITH_LIMITATIONS · WAITING_DEPLOY_APPROVAL**

Jarvis V1 is a channel-neutral access layer over the existing Orchestrator. It
does not choose agents, invent canonical facts, or create a parallel approval
system. Telegram is the first adapter and is fail-closed behind webhook secret,
user allowlist, idempotency and rate limiting.

Canonical implementation and limitations:

- `docs/NEXUS_JARVIS_ACCESS_LAYER_V1.md`
- `contracts/jarvis-message.schema.json`
- `contracts/jarvis-response.schema.json`
- `contracts/jarvis-card.schema.json`
- `server/jarvis_v1/`

Production remains unchanged by this task. `/api/version` must be deployed
before production alignment can move from `PRODUCTION_UNKNOWN`.

