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

## Current blockers before activation

- The repository-wide CI baseline still has three unrelated failures: one frozen Funding checksum
  and two stale Research Control Plane experiment-count assertions.
- No deploy hook or verification credentials were configured or used in this task.
- Render startup log inspection is not yet automated; readiness, SHA and dispatcher provide the V1
  runtime gate. Render API log triage is a future hardening step.
- Jarvis notification is represented by the GitHub deployment summary; direct Activity Ledger /
  Telegram delivery remains a future integration because it needs a dedicated authenticated ingest.
