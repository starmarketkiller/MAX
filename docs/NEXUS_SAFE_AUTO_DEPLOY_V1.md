# NEXUS Safe Auto Deploy V1

## Decision

`SAFE_AUTO_DEPLOY_V1_READY_WITH_LIMITATIONS`

Native Render auto-deploy remains off. The controlled GitHub workflow deploys one exact SHA through
a secret Render deploy hook only after the existing `CI` workflow succeeds and the deterministic
risk classifier returns `LOW_RISK` or `MEDIUM_RISK`.

## Flow

`push main -> CI -> risk classification -> exact-SHA deploy hook -> readiness/SHA/dispatcher -> deploy ledger`

`HIGH_RISK` produces `WAITING_APPROVAL` and never reaches the deploy job. High-risk paths include
MQL5/live execution, authentication/security, command/approval contracts, destructive retention or
migration code, Render configuration and this deployment policy itself. Sensitive content patterns
are an additional fail-closed guard. Runtime, frontend, dependency and build changes are medium;
non-runtime documentation/test artifacts are low unless sensitive patterns are present.

## Why controlled hooks instead of native auto-deploy

Render can wait for CI checks, but that setting cannot apply NEXUS's path/content risk policy.
Safe Deploy therefore keeps `autoDeployTrigger: off` and invokes the service's secret deploy hook
with `ref=<verified commit SHA>`. The hook URL is a GitHub Actions secret and is never printed.

## Required GitHub configuration

Repository secret:

- `RENDER_DEPLOY_HOOK_URL`: hook for `nexus-backend`.
- `NEXUS_DEPLOY_VERIFY_USER` and `NEXUS_DEPLOY_VERIFY_PASSWORD`: dedicated verification login.

Repository variable:

- `NEXUS_PUBLIC_URL=https://nexus-backend-8o4y.onrender.com`

Create the GitHub environment `nexus-production-low-medium-risk`. It should not require a manual
reviewer for low/medium automation. High-risk changes never enter this environment.

Do not enable the workflow operationally until the CI baseline is green and a non-production or
explicitly approved canary has validated the complete cycle.

## Verification and ledger

The verifier waits for `/api/version.git_sha` to equal the requested SHA, then requires:

- `/api/ready` HTTP 200;
- authenticated `/api/jarvis/dispatcher/status` with `running=true`;
- matching deployed SHA.

It writes `deploy-ledger.json` with commit, deploy ID, timestamps, risk, checks, result, diagnostic
and recovery instruction. GitHub retains the risk and ledger artifacts. Failure never emits a
success message and explicitly instructs recovery against the last healthy SHA.

## Failure and rollback boundary

V1 prepares rollback/recovery but does not execute rollback automatically. This is deliberate:
the service has a persistent disk, so rollback safety may depend on data/schema compatibility.
Automatic rollback belongs to V1.1 after a compatibility contract and last-known-healthy registry
exist.

## CI baseline repair and canary readiness

- The Funding frozen hash is the SHA-256 of canonical LF Git content. The integrity test normalizes
  checkout CRLF before hashing, preventing a Windows `core.autocrlf` setting from reporting a false
  source-logic change. The source logic did not change (`7dafeae..HEAD` is empty for all seven frozen
  files); six manifest hashes were migrated from checkout-specific CRLF bytes to their canonical Git
  LF blob hashes and the wrapper canonical hash was updated accordingly.
- Research Control Plane expectations are 9 experiments and 9 hypotheses. Phase 7.27 appended the
  canonical cross-strategy BUY-dominance benchmark experiment and linked hypothesis to the eight
  records originally backfilled by Phase 7.26.
- No deploy hook or verification credentials were configured or used in this task.
- Render startup log inspection is not yet automated; readiness, SHA and dispatcher provide the V1
  runtime gate. Render API log triage is a future hardening step.
- Jarvis notification is represented by the GitHub deployment summary; direct Activity Ledger /
  Telegram delivery remains a future integration because it needs a dedicated authenticated ingest.

## GitHub configuration checklist

Configure these only before the explicitly approved canary:

- Repository secret `RENDER_DEPLOY_HOOK_URL`: Render hook for `nexus-backend`; keep the full query
  secret out of logs and artifacts.
- Repository secret `NEXUS_DEPLOY_VERIFY_USER`: dedicated least-privilege dashboard verification user.
- Repository secret `NEXUS_DEPLOY_VERIFY_PASSWORD`: password for that verification user.
- Repository variable `NEXUS_PUBLIC_URL`: `https://nexus-backend-8o4y.onrender.com`.
- GitHub environment `nexus-production-low-medium-risk`: create it with access only to the deployment
  secrets. Do not add a required reviewer for low/medium canaries; HIGH_RISK never enters this job and
  remains `WAITING_APPROVAL` at classification.

Before enabling the workflow, confirm Render native `autoDeployTrigger` remains `off`, the hook accepts
an exact `ref`, and branch protection requires the `CI` workflow.

## Prepared LOW_RISK canary (not executed)

Use a separate commit that changes only
`docs/canary/SAFE_DEPLOY_LOW_RISK_CANARY.md` (for example, update its `canary_run` marker). The risk
classifier must return `LOW_RISK / NON_RUNTIME_CHANGE`. That commit must not alter runtime, workflows,
secrets, research artifacts or trading code. This task neither creates the canary commit nor triggers
the hook.
