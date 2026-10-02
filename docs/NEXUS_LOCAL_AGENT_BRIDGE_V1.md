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

Simplest path - copy `LocalBridge/.env.example` to `LocalBridge/.env`, fill in
the values (never commit `.env`, it is already gitignored), then run:

```powershell
powershell -ExecutionPolicy Bypass -File LocalBridge\start_bridge.ps1
```

This loads `.env`, runs a read-only `--diagnose` pass (checks `NEXUS_URL`,
the secret length, `NEXUS_REPO_ROOT`, Ollama reachability and backend
reachability - no job is claimed), and only then starts the polling client.
Equivalent manual steps, for reference:

```powershell
$env:NEXUS_URL = "https://nexus-backend-8o4y.onrender.com"
$env:NEXUS_LOCAL_AGENT_BRIDGE_ID = "primary-workstation"
$env:NEXUS_LOCAL_AGENT_BRIDGE_SECRET = "<same secret configured on Render>"
$env:NEXUS_REPO_ROOT = "C:\path\to\MAX"
$env:NEXUS_LOCAL_AGENT_WORKSPACE = "C:\path\outside-or-inside-checkout\nexus-bridge-workspaces"
python LocalBridge/nexus_agent_bridge.py --diagnose   # optional, read-only
python LocalBridge/nexus_agent_bridge.py
```

The process sends signed POST requests only. Authentication covers method,
path, timestamp, nonce and body SHA-256 with HMAC-SHA256. The backend rejects
stale timestamps, replayed nonces, invalid signatures and excessive request
rates. A claimed task has an expiring, bridge-bound lease.

Every log line is timestamped and limited to event names, task/job ids and
safe counters - a secret, signature, prompt, model response or absolute
workspace path is never printed.

## Stopping the bridge

`Ctrl+C` (or a normal process termination signal) triggers a graceful
shutdown: the in-flight lease-renewal thread is stopped, a final `DEGRADED`
heartbeat is sent so the backend's status view reflects it immediately, and
the process exits. There is no abrupt kill path required for a clean stop.

## Checking bridge status / heartbeat

- From the workstation, without touching the backend: run
  `python LocalBridge\nexus_agent_bridge.py --diagnose` at any time (does not
  interrupt a running bridge process in a different terminal; it only reads
  state and sends one heartbeat).
- From the backend, as an authenticated operator:
  `GET /api/jarvis/local-bridge/status` returns every known bridge, its
  declared capabilities, and `ONLINE` / `DEGRADED` / `OFFLINE` derived from
  `heartbeat_age_seconds` versus `NEXUS_LOCAL_AGENT_BRIDGE_HEARTBEAT_TTL`
  (default 45s). A bridge that stops sending heartbeats (process killed,
  machine asleep, network down) is reported `OFFLINE` automatically - no
  manual flag to flip.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `--diagnose` reports `NEXUS_LOCAL_AGENT_BRIDGE_SECRET` too short | `.env` not filled in, or copy/paste truncated the value | Regenerate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`, paste the full value on both Render and `.env` |
| `--diagnose` reports Ollama unreachable | Ollama service not running locally | Start Ollama (`ollama serve`), confirm the configured model is pulled |
| `--diagnose` reports backend unreachable at `/api/health` | Wrong `NEXUS_URL`, no internet, or Render service asleep/down | Confirm the URL, check Render dashboard status |
| Heartbeat accepted but `claim` never returns a job | No `conversational_programming` task is currently `WAITING_PROVIDER` for this capability, or the Router routed it elsewhere | Check `/api/jarvis/local-bridge/status` and the task's state via the Jarvis/activity endpoints - this is often expected idle behavior, not a bug |
| Backend returns `invalid bridge signature` | Secret mismatch between Render and the workstation `.env`, or a proxy/clock skew altering the request | Re-copy the exact secret on both sides; verify the workstation clock is within ~60s of real time (the HMAC check rejects stale timestamps) |
| Backend returns `bridge rate limit exceeded` | Too many requests within a minute (misconfigured polling loop, or two bridge processes running with the same `bridge_id`) | Ensure only one process runs per `NEXUS_LOCAL_AGENT_BRIDGE_ID`; do not lower `NEXUS_LOCAL_AGENT_POLL_SECONDS` below a few seconds |
| A claimed task never completes and eventually fails | Local Ollama call failed, or the verifier rejected the proposed patch (bounds/allowlist/test failure) | This is the intended fail-closed path - the task falls through to the Core's existing escalation, nothing is lost |

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
