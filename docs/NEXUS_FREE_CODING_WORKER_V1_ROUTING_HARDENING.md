# NEXUS Free Coding Worker V1 — Routing Hardening

## Canonical path

`Jarvis -> Programming Plan -> Orchestrator/Router -> _run_local -> LocalTaskHandler -> verifier -> approval`

The handler never invokes Ollama and cannot select a provider or tier. The
Orchestrator owns the local model call, one bounded retry, failure
classification, escalation and Ledger transitions.

## Execution boundary

- Maximum four changed files and 80 KB of proposed content.
- Explicit `files_allowed` is mandatory; an empty scope fails closed.
- Traversal, symlinks, `.env`, secrets, MQL5 and frozen research paths remain
  denied by the manifest boundary.
- Work is written only into a task-specific isolated workspace.
- No generic shell exists. Tests are argv arrays and accept only Python pytest
  against allowlisted test directories with a minimal flag set. Python changes
  default to `py_compile` when no explicit test command exists.
- A successful proposal is never applied to the repository: it transitions to
  `WAITING_APPROVAL` through the existing Orchestrator boundary.
- Push and deploy are absent from the worker. Deploy remains owned by Safe Auto
  Deploy after a separately approved push.

## Provider behavior

Capability matching selects the demonstrated local worker first. Missing or
offline local capability is routed fail-closed by the Router. Free-online
models remain evaluation-only until Provider Policy marks them configured and
production-verified. Premium escalation is processed only by Provider
Connector and remains blocked when the manifest or budget policy disallows it.

## Known limitation

No free-online coding model is currently production-authorized. Therefore the
operational V1 path is local Ministral or a policy-controlled escalation; it
does not silently substitute an evaluation provider.
