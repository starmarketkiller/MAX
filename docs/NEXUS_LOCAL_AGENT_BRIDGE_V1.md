# NEXUS Local Agent Bridge V1

## Boundary

The bridge is an outbound-only transport for a task that the existing Router
has already assigned to a local tier. It does not select a tier, provider,
capability, path, test command, approval outcome, push or deployment action.

```text
Telegram / Jarvis (Render)
  -> Queue / Dispatcher
  -> Router + capability match
  -> WAITING_PROVIDER
  -> HTTPS long polling by the workstation
  -> Ollama + FreeCodingWorkerHandler in an isolated workspace
  -> bounded verifier receipt
  -> RESULT_PACKET_V1
  -> WAITING_APPROVAL
```

There is no inbound listener on the workstation. There is no generic shell or
arbitrary command API. V1 accepts only `complex_code_change` jobs whose action
is `conversational_programming`; the existing file patterns, patch-size limit,
pytest argv allowlist and one-retry ceiling remain authoritative.

## Backend configuration (Render)

Set one new secret in the Render environment:

```text
NEXUS_LOCAL_AGENT_BRIDGE_SECRET=<random value of at least 32 characters>
```

Optional non-secret tuning:

```text
NEXUS_LOCAL_AGENT_BRIDGE_HEARTBEAT_TTL=45
NEXUS_LOCAL_AGENT_BRIDGE_LEASE_SECONDS=300
```

The same secret is installed only in the local machine's environment. Never
commit it. If the backend secret is absent, bridge endpoints fail closed and
the Orchestrator keeps its previous local-execution behavior. If the bridge is
configured but offline, a local task follows normal fail-closed escalation.

## Start on the Windows workstation

Prerequisites: the repository checkout at the same intended source revision,
Python production dependencies, Ollama running locally, and the configured
Ministral model.

PowerShell (values are examples; do not save the secret in the repository):

```powershell
$env:NEXUS_URL = "https://nexus-backend-8o4y.onrender.com"
$env:NEXUS_LOCAL_AGENT_BRIDGE_ID = "primary-workstation"
$env:NEXUS_LOCAL_AGENT_BRIDGE_SECRET = "<same secret configured on Render>"
$env:NEXUS_REPO_ROOT = "C:\path\to\MAX"
$env:NEXUS_LOCAL_AGENT_WORKSPACE = "C:\path\outside-or-inside-checkout\nexus-bridge-workspaces"
python LocalBridge/nexus_agent_bridge.py
```

The process sends signed POST requests only. Authentication covers method,
path, timestamp, nonce and body SHA-256 with HMAC-SHA256. The backend rejects
stale timestamps, replayed nonces, invalid signatures and excessive request
rates. A claimed task has an expiring, bridge-bound lease.

## Endpoints

All mutation endpoints require signed bridge headers and expose no secret:

- `POST /api/jarvis/local-bridge/heartbeat`
- `POST /api/jarvis/local-bridge/claim`
- `POST /api/jarvis/local-bridge/renew`
- `POST /api/jarvis/local-bridge/result`
- `POST /api/jarvis/local-bridge/failure`

The dashboard-authenticated status projection is:

- `GET /api/jarvis/local-bridge/status`

## Operational limitation

V1 uses the existing JSON state store and single Render process. It is not a
multi-replica distributed queue. A real Telegram/Ollama E2E test requires the
backend secret to be configured and this client to be running; implementation
tests use no external network and do not deploy.

The first controlled E2E task must remain bounded to one existing test file,
with `NO_PUSH`, `NO_DEPLOY`, an allowlisted test argv and final state
`WAITING_APPROVAL`.
