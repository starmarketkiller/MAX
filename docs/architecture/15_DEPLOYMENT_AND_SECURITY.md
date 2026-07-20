# 15. Deployment and Security

## Current deployment assets

- root `docker-compose.yml`;
- `server/Dockerfile`;
- `render.yaml`;
- `DEPLOY.md`;
- LocalBridge worker;
- frontend build;
- static backend pages.

## Confirmed security risks

### Unsafe defaults

Backend configuration can default to values such as an administrative username/password, a shared bridge token and open licensing behavior when environment variables are omitted.

### JWT behavior

A randomly generated JWT secret on restart invalidates sessions unpredictably. Long default token lifetime increases exposure.

### Shared trust boundary

One bridge-style token is used across multiple functions, reducing isolation between EA telemetry, LocalBridge, settings and licensing.

### Authentication duplication

React uses httpOnly cookie behavior while legacy static pages use older browser-token patterns.

### Missing controls

No complete evidence of:

- login rate limiting;
- lockout;
- MFA;
- immutable login/settings audit;
- scoped service credentials;
- command authorization by target/capability.

## Required environment policy

Production startup must fail when required secrets are missing. No production-safe component should generate or accept known default credentials.

Required distinct credentials:

- application JWT/session secret;
- EA instance credential;
- LocalBridge host credential;
- license signing/verification secret;
- database encryption/backup credentials as applicable.

## Release policy

Every release should record:

- Git commit SHA;
- EA version and compiled artifact checksum;
- backend and frontend versions;
- settings/registry schema versions;
- database migration version;
- release manifest for LocalBridge;
- rollback instructions.

## CI minimum

A `.github/workflows` pipeline should eventually include:

1. Python syntax, lint and unit tests.
2. API contract tests.
3. frontend build and tests.
4. migration tests on an empty and legacy database.
5. duplicate/partial-close ledger tests.
6. package manifest/checksum generation.
7. secret/default-credential checks.

MQL5 compilation may require a dedicated Windows/MetaTrader runner or controlled external build step.

## Legacy static dashboard decision

Choose one:

- remove it;
- keep only public marketing pages;
- retain as explicit diagnostic fallback with the same auth contract.

It should not remain an undocumented second operational interface.
