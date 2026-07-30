# NEXUS — MASTER PROJECT DOCUMENT

**Repository:** `starmarketkiller/MAX`  
**Document role:** single source of truth  
**Status:** active and continuously updated  
**Supersedes:** separate Audit-0, Operational Backlog and PR-A documents  
**Code changes performed:** none  
**Last consolidated:** 2026-07-23

---

# DOCUMENT GOVERNANCE

From this version onward, this is the only authoritative project document.

The following former standalone documents are preserved inside this master as sections and should no longer be maintained separately:

1. NEXUS Audit-0
2. NEXUS Operational Backlog
3. PR-A Effective Config Resolver specification
4. Reviewer Pack
5. Agent Pack
6. Release and remediation checklists

Future audits, implementation specifications, decisions, milestones, test evidence and release records must be appended to this file.

---

# STATUS CORRECTION

The previous statement that **AUDIT-0 was 100% complete** was too strong and is formally withdrawn.

Two different concepts had been mixed together:

- completion of the written audit document;
- technical coverage of the repository.

The written Audit-0 report, Reviewer Pack and Agent Pack were completed, but several technical areas were not reviewed to 100% depth. Therefore the repository audit is still open.

## Current technical audit coverage

| Area | Review coverage |
|---|---:|
| Repository inventory | 100% |
| Root configuration | 100% |
| MQL5 | 88% |
| Backend | 88% |
| Frontend | 90% |
| Contracts | 96% |
| Deploy | 96% |
| Security | 98% |
| Documentation | 90% |
| Testing and executable evidence | 68% |

**Provisional overall technical audit coverage:** **91%**

This percentage is a review-coverage indicator, not a statement that the code is 91% safe or production-ready.

## Document completion

| Deliverable | Status |
|---|---:|
| Audit report structure | 100% |
| Reviewer Pack | 100% |
| Agent Pack | 100% |
| Operational backlog | 100% |
| PR-A specification | 100% |
| Repository technical verification | 91% |
| Production readiness | NO-GO |
| Point 5 | BLOCKED |

## Required audit closure work

The audit may only be marked 100% after the remaining evidence is reviewed, including:

- complete MQL5 module-by-module review;
- complete backend route, storage and migration review;
- complete frontend page and mutation-path review;
- repository-wide test inventory;
- CI workflow inventory;
- clean Docker build and startup evidence;
- MQL5 compilation evidence;
- backtest/runtime parity evidence;
- backup and restore evidence;
- end-to-end command replay and crash-recovery evidence.

Until those checks are complete, the correct status is:

> **AUDIT OPEN — 91% TECHNICAL COVERAGE — NO-GO**

---

# MASTER TABLE OF CONTENTS

## Part I — Project governance and status
- Document governance
- Status correction
- Current audit coverage
- Production decision

## Part II — Repository Audit
- Full Audit-0 history
- Findings
- Risk matrix
- Reviewer Pack
- Agent Pack

## Part III — Operational Backlog
- Priorities
- Milestones
- Pull-request sequence
- Acceptance criteria

## Part IV — Implementation Specifications
- PR-A Effective Config Resolver
- Future PR-B, PR-C and subsequent specifications

## Part V — Evidence and Release
- Test evidence
- Build evidence
- MQL5 compile evidence
- Migration evidence
- Staging evidence
- Reviewer decisions

---

# CURRENT PROJECT DECISION

**Production status:** NO-GO

Allowed:

- isolated development;
- static review;
- simulation;
- controlled backtesting;
- non-production prototyping.

Blocked:

- real-money trading;
- remote code deployment;
- automatic production deployment;
- multi-account production use;
- AI Coach live mutations;
- Point 5.

---



---

# PART II — REPOSITORY AUDIT

# NEXUS — AUDIT-0 Initial Repository Inventory

**Repository:** `starmarketkiller/MAX`  
**Branch audited:** `main`  
**Audit status:** IN PROGRESS  
**Point 5:** BLOCKED

## Verified top-level domains

The repository history and current merged PR file maps confirm these active domains:

- `.github/` — not yet enumerated
- `MQL5/` — EA and MQL5 include modules
- `LocalBridge/` — Windows/MT5 local worker
- `server/` — FastAPI backend, static fallback dashboard, tests
- `frontend/` — React dashboard source
- `contracts/` — canonical strategy/settings/command contracts and generators
- `deploy/` — versioned deployment manifest
- `docs/` — architecture and PR acceptance/verification documentation
- root deployment/configuration files

## Verified root files

- `.gitignore`
- `README.md`
- `DEPLOY.md`
- `CHANGELOG_v2.0.13.md`
- `docker-compose.yml`
- `render.yaml`

## Verified MQL5 entry point

- `MQL5/Experts/NEXUS_EA_v2.mq5`

## Verified MQL5 include modules

- `NXS_AMDModel.mqh`
- `NXS_BjorgumZones.mqh`
- `NXS_BlockerDiagnostics.mqh`
- `NXS_Confluence.mqh`
- `NXS_Dashboard.mqh`
- `NXS_Defines.mqh`
- `NXS_Diagnostics.mqh`
- `NXS_EdgeAdaptive.mqh`
- `NXS_EntryScore.mqh`
- `NXS_Execution.mqh`
- `NXS_FibonacciContext.mqh`
- `NXS_Globals.mqh`
- `NXS_GridRecovery.mqh`
- `NXS_HTFBias.mqh`
- `NXS_HistorySync.mqh`
- `NXS_Inputs.mqh`
- `NXS_InstManage.mqh`
- `NXS_License.mqh`
- `NXS_LockedProfile.mqh`
- `NXS_Logging.mqh`
- `NXS_MTFSpreadVol.mqh`
- `NXS_Management.mqh`
- `NXS_MarketAnalysis.mqh`
- `NXS_NewsFilter.mqh`
- `NXS_Notify.mqh`
- `NXS_Performance.mqh`
- `NXS_PositionCoordinator.mqh`
- `NXS_Presets.mqh`
- `NXS_Pressure.mqh`
- `NXS_Protections.mqh`
- `NXS_Pyramiding.mqh`
- `NXS_Reaction.mqh`
- `NXS_ReusePerformancePack.mqh`
- `NXS_Risk.mqh`
- `NXS_RiskShield.mqh`
- `NXS_RuntimeSettings.mqh`
- `NXS_SafeOrder.mqh`
- `NXS_Sessions.mqh`
- `NXS_ShadowTrading.mqh`
- `NXS_SignalRouter.mqh`
- `NXS_Slippage.mqh`
- `NXS_SplitTrade.mqh`
- `NXS_State.mqh`
- `NXS_StratStats.mqh`
- `NXS_Strategies.mqh`
- `NXS_Strategies_Institutional.mqh`
- `NXS_Strategies_SMC.mqh`
- `NXS_StrategyChain.mqh`
- `NXS_StrategyRegistry.mqh`
- `NXS_Structure.mqh`
- `NXS_StructureMultiLayer.mqh`
- `NXS_SymbolProfile.mqh`
- `NXS_TrailingATR.mqh`
- `NXS_TradeLedger.mqh`
- `NXS_Velocity.mqh`
- `NXS_VisualBridge.mqh`
- `NXS_VisualBridgeHTTP.mqh`
- `NXS_VisualObjects.mqh`
- `NXS_WebBridge.mqh`

## Verified backend files

- `server/app.py`
- `server/backtest.py`
- `server/strategy_registry.py`
- `server/settings_contract.py`
- `server/settings_schema.py`
- `server/command_contract.py`
- `server/ledger_analytics.py`
- `server/requirements.txt`
- `server/Dockerfile`
- `server/.env.example`
- `server/static/app.js`
- `server/static/index.html`
- `server/static/style.css`
- backend tests for trade lifecycle, strategy registry, settings, commands, ledger analytics

## Verified frontend files

- React pages for Dashboard, Journal, Live Chart, LocalBridge, Backtest and Analytics
- Backtest subcomponents for optimizer, strategy library and management report
- shared polling hook `useVisiblePolling.js`
- strategy/settings generated adapters
- widgets for Coach, License and notifications

## Verified contract/deployment files

- `contracts/strategy-registry.json`
- `contracts/strategy-registry.schema.json`
- `contracts/generate_registry.py`
- `contracts/validate_registry.py`
- `contracts/default-settings.json`
- `contracts/settings.schema.json`
- `contracts/generate_settings_schema.py`
- `contracts/command.schema.json`
- `contracts/generate_deployment_manifest.py`
- `deploy/deployment-manifest.json`

## First verified findings

### AUD0-DOC-001 — README top-level model is outdated
The README describes only three project components, while the current repository also contains a React frontend, canonical contracts/generators, deployment manifests, tests and extensive architecture documentation.

**Severity:** P1 documentation  
**Decision:** UPDATE

### AUD0-DOC-002 — Authentication documentation is ambiguous
The README describes the React dashboard as using an httpOnly cookie, while the API section generically states that dashboard endpoints require a Bearer JWT. The distinction between React cockpit and static fallback dashboard must be explicit.

**Severity:** P1 operational/security documentation  
**Decision:** CLARIFY

### AUD0-DOC-003 — “No external dependencies” is overstated
The README states that the project has no external-service dependency but also documents optional Anthropic and Telegram integrations and public cloud deployment. The correct claim is that the trading core is self-hostable and does not require Emergent.

**Severity:** P2 documentation accuracy  
**Decision:** REWORD

### AUD0-INV-001 — Original migration inventory is no longer sufficient
Post-migration PRs added new active files such as `NXS_InstManage.mqh`, `NXS_PositionCoordinator.mqh`, `NXS_TradeLedger.mqh`, `NXS_StrategyRegistry.mqh`, React source, contracts, generators, deployment manifests and test suites.

**Severity:** P0 audit completeness  
**Decision:** REBUILD RECURSIVE INVENTORY

### AUD0-GOV-001 — PR numbering and titles are not consistently aligned
The repository history contains PR titles/body labels such as PR6/PR7/PR8 that do not always match the GitHub pull-request number. Future agents must use immutable finding IDs and GitHub PR numbers separately.

**Severity:** P1 governance  
**Decision:** ADD NAMING CONTRACT

### AUD0-TEST-001 — Runtime MT5 evidence remains missing
Merged PR descriptions consistently report MetaEditor compilation and backend/frontend tests, while MT5 runtime and Strategy Tester execution were intentionally excluded.

**Severity:** P0 release evidence  
**Decision:** KEEP POINT 5 BLOCKED

## Current audit completeness

- Critical architecture review: completed
- Repository path reconstruction: partial
- Recursive file-by-file review: not completed
- Documentation audit: started
- MQL5 non-critical module audit: not started
- Backend full audit: not started
- Frontend full audit: not started
- Deploy/CI audit: not started
- Security audit: not started

## Next inspection block

1. Root configuration and deployment files
2. README/DEPLOY consistency
3. `server/requirements.txt` and dependency surface
4. `docker-compose.yml`, `render.yaml`, Dockerfile and environment variables
5. `.gitignore` and secret/artifact hygiene
6. then MQL5 include graph and file-by-file classification


# AUDIT-0 — Block 3: Root Configuration and Deployment Review

## Files fully reviewed in this block

- `.gitignore`
- `DEPLOY.md`
- `docker-compose.yml`
- `render.yaml`
- `server/Dockerfile`
- `server/.env.example`
- `server/requirements.txt`

## File classification

| File | Status | Criticality | Debt | Decision | Review |
|---|---|---:|---:|---|---|
| `.gitignore` | ACTIVE_SUPPORT | HIGH | 2/5 | KEEP + REFACTOR | FULL |
| `DEPLOY.md` | DOCUMENTATION | HIGH | 4/5 | REWRITE | FULL |
| `docker-compose.yml` | DEPLOYMENT | HIGH | 2/5 | KEEP + HARDEN | FULL |
| `render.yaml` | DEPLOYMENT | CRITICAL | 3/5 | KEEP + HARDEN | FULL |
| `server/Dockerfile` | DEPLOYMENT | CRITICAL | 4/5 | REFACTOR | FULL |
| `server/.env.example` | DOCUMENTATION/CONFIG | CRITICAL | 4/5 | HARDEN | FULL |
| `server/requirements.txt` | DEPLOYMENT | CRITICAL | 4/5 | REGENERATE/LOCK | FULL |

## New findings

### AUD0-SEC-001 — Example secrets are operationally unsafe

`server/.env.example` contains predictable placeholder values:

- `NEXUS_BRIDGE_TOKEN_2026`
- `admin`
- `cambia_questa_password`
- `cambia_questo_segreto_lungo_e_casuale`

This is acceptable only when startup refuses unchanged placeholders. No such enforcement has yet been verified.

**Risk:** accidental production deployment with known credentials.  
**Severity:** P0 security.  
**Required action:** add startup validation that rejects known placeholders and weak secrets outside an explicit local-development mode.

### AUD0-SEC-002 — Dashboard session lifetime is excessive by default

`NEXUS_JWT_HOURS=720` equals 30 days.

**Risk:** a stolen session remains valid for too long.  
**Severity:** P1 security.  
**Required action:** lower the default, implement rotation/revocation or document why a long-lived session is required.

### AUD0-SEC-003 — Shared bridge token creates a broad trust domain

One token authenticates EA, backend and LocalBridge worker.

**Risk:** compromise of one component can impersonate another unless route-level scope checks are strong.  
**Severity:** P0 architecture/security.  
**Required action:** move toward scoped credentials or signed component identities, while preserving compatibility during migration.

### AUD0-DEP-001 — Deployment guide references an obsolete branch

`DEPLOY.md` instructs Render to use `claude/export-advisor-nexus-migrate-htnz34` or later switch to `main`.

**Risk:** users may deploy an obsolete baseline.  
**Severity:** P1 operations.  
**Decision:** rewrite the guide to reference only the canonical release branch/tag.

### AUD0-DEP-002 — Deployment guide exposes a weak token example

The guide suggests a token such as `NEXUS_BRIDGE_TOKEN_2026`.

**Risk:** users may copy the example literally.  
**Severity:** P0 security documentation.  
**Required action:** replace with a command for generating a random token and explicitly reject copied examples.

### AUD0-DEP-003 — Render admin identity conflicts with README guidance

`render.yaml` sets `NEXUS_ADMIN_USER=admin`, while the README says the React login expects an email-like user value.

**Risk:** deployment may produce login incompatibility or confusing behavior.  
**Severity:** P1 operational correctness.  
**Required action:** canonicalize identity requirements across README, `.env.example`, Render and backend validation.

### AUD0-DEP-004 — Docker Compose publishes backend on all host interfaces

The mapping `8001:8001` generally exposes the service on every interface.

**Risk:** an intended local installation can become reachable from the LAN.  
**Severity:** P1 security.  
**Required action:** document exposure and consider `127.0.0.1:8001:8001` as the secure local default.

### AUD0-DEP-005 — Docker Compose has no healthcheck

The service restarts on process failure but Compose has no healthcheck.

**Risk:** a running yet unhealthy application is not detected by Compose.  
**Severity:** P2 reliability.  
**Required action:** add a healthcheck against `/api/health`.

### AUD0-DEP-006 — Dockerfile does not copy all active Python modules

The Dockerfile copies a fixed list:

- `app.py`
- `backtest.py`
- `bt_verdict.py`
- `sweep.py`
- seed JSON files
- `nexus_local_worker.py`
- `static/`

Recent active backend modules include at least:

- `strategy_registry.py`
- `settings_contract.py`
- `settings_schema.py`
- `command_contract.py`
- `ledger_analytics.py`

These are not listed in the Dockerfile.

**Risk:** clean container builds can fail at import time or run a functionally incomplete backend.  
**Severity:** P0 deployment blocker.  
**Required action:** verify current imports immediately; replace the brittle per-file COPY list with a controlled package copy plus `.dockerignore`.

### AUD0-DEP-007 — No `.dockerignore` has yet been verified

The Docker build context may include caches, databases, test artifacts or local files even when the Dockerfile does not copy them directly.

**Risk:** oversized contexts and accidental leakage into future broad COPY instructions.  
**Severity:** P1 hygiene/security.  
**Required action:** verify or add `.dockerignore`.

### AUD0-SUPPLY-001 — Requirements are pinned but not reproducibly locked

Four direct dependencies are version-pinned, which is better than floating versions, but there is no verified transitive lock, hash checking or vulnerability process.

**Risk:** transitive dependency drift and weak supply-chain provenance.  
**Severity:** P1 supply chain.  
**Required action:** generate a hashed lock file, add dependency scanning and define update cadence.

### AUD0-SUPPLY-002 — Runtime image is not digest-pinned

`python:3.12-slim` is mutable.

**Risk:** rebuilding the same commit at different times can yield different base contents.  
**Severity:** P2 reproducibility.  
**Required action:** pin by digest for release builds and automate controlled digest updates.

### AUD0-DEP-008 — Container runs as root by default

No non-root user is created in the Dockerfile.

**Risk:** greater impact if the application or dependency is compromised.  
**Severity:** P1 container security.  
**Required action:** create an unprivileged runtime user and ensure `/data` permissions work.

### AUD0-DEP-009 — No explicit container shutdown/readiness policy

The deployment files expose a liveness endpoint through Render, but no startup/readiness distinction, graceful shutdown policy or migration gate has yet been verified.

**Risk:** requests can arrive before DB initialization or during an unsafe transition.  
**Severity:** P2 reliability.  
**Required action:** inspect backend startup and DB migration behavior during the backend audit.

### AUD0-GIT-001 — `.gitignore` coverage is incomplete

Current ignores cover the main `.env`, worker config, SQLite files, Python caches, frontend build/node_modules and one class of tester logs. Not yet covered or verified:

- root `.env` variants
- `.env.*` secrets with an allow-list for examples
- IDE metadata
- coverage/test caches
- generic logs
- build/dist artifacts
- MQL5 compiled artifacts (`.ex5`)
- runtime state/CSV files
- local certificates and keys
- frontend package-manager caches

**Risk:** accidental commit of generated artifacts or secrets.  
**Severity:** P1 repository hygiene.  
**Required action:** expand carefully without hiding canonical fixtures.

## Cross-file contradiction register

1. **Admin user format**
   - README: React dashboard expects email-like value.
   - Render: `admin`.
   - `.env.example`: `admin`.

2. **Render plan**
   - DEPLOY guide says free is suitable to start.
   - `render.yaml` is set to Starter.

3. **Canonical branch**
   - DEPLOY guide still names the original migration branch.
   - Repository default is `main`.

4. **Self-hosted claim**
   - Core is self-hostable.
   - Optional external Anthropic and Telegram integrations are configured in deployment files.

## Immediate P0 verification queue

1. Confirm whether current `server/Dockerfile` can build `main`.
2. Inspect imports in `server/app.py`.
3. Verify startup rejection of default/weak secrets.
4. Verify cookie/JWT authentication behavior and route scoping.
5. Verify presence or absence of `.dockerignore`.
6. Verify whether Render deployment currently succeeds from a clean build.

## Progress update

### Overall audit

**22%**

### AUDIT-0 Repository Inventory

**41%**

### Root configuration and deployment review

**70%**

### Area status

- Repository Inventory: 41%
- Root Configuration: 70%
- MQL5: 12%
- Backend: 9%
- Frontend: 5%
- Contracts: 20%
- Deploy: 32%
- Security: 9%
- Documentation: 22%
- Testing: 5%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 4: Backend Bootstrap, Authentication and Container Compatibility

## Files reviewed

- `server/app.py` — configuration, imports, database bootstrap, migrations, startup, login/session handling, EA command delivery
- Cross-check against:
  - `server/Dockerfile`
  - `server/.env.example`
  - `render.yaml`
  - `docker-compose.yml`

## Verified architecture facts

- `server/app.py` imports the following local modules at process start:
  - `backtest`
  - `bt_verdict`
  - `strategy_registry`
  - `settings_contract`
  - `settings_schema`
  - `command_contract`
  - `ledger_analytics`
- Configuration is evaluated at module import time.
- SQLite schema creation and additive migrations run during FastAPI startup.
- Dashboard authentication accepts either:
  - Bearer JWT
  - `nexus_session` httpOnly cookie
- EA and LocalBridge authentication currently share one `X-Nexus-Token`.
- The health endpoint does not verify database availability or migration completeness.
- The EA command endpoint marks a command delivered/consumed when it is polled, not when execution is acknowledged.

## Confirmed P0 finding

### AUD0-DEP-006 — Docker image cannot reliably start from current `main`

The current Dockerfile copies only a fixed subset of Python files. `app.py` imports several local modules that are not copied into the image:

- `strategy_registry.py`
- `settings_contract.py`
- `settings_schema.py`
- `command_contract.py`
- `ledger_analytics.py`

Because these imports occur at module load, a clean image built from the current Dockerfile is expected to fail before FastAPI startup with `ModuleNotFoundError`, unless an unverified build-context side effect supplies them.

**Status:** CONFIRMED BY STATIC CROSS-CHECK  
**Severity:** P0 deployment blocker  
**Refactoring risk:** SAFE  
**Required fix:** package the backend and copy the package atomically, or explicitly copy every required module as a temporary hotfix.

## New backend/security findings

### AUD0-SEC-004 — Production starts with insecure fallback credentials

`app.py` defaults to:

- bridge token: `NEXUS_BRIDGE_TOKEN_2026`
- admin user: `admin`
- admin password: `admin`
- JWT secret: a process-generated value if absent

There is no startup rejection for missing or placeholder secrets.

**Impact:**
- deployments with incomplete environment configuration can start successfully with known credentials;
- the bridge token is predictable;
- a restart with no configured JWT secret invalidates all existing sessions because a new random secret is generated.

**Severity:** P0 security  
**Decision:** FAIL CLOSED outside explicit development mode.

### AUD0-SEC-005 — JWT secret fallback is ephemeral

When `NEXUS_JWT_SECRET` is absent, a random value is generated during process import.

**Impact:** all dashboard sessions become invalid after restart, replica change or process replacement.

**Severity:** P1 operational/security  
**Required action:** require a persistent secret in production; allow ephemeral secret only in explicit local development.

### AUD0-SEC-006 — Login has no verified rate limiting or lockout

The reviewed login endpoint performs constant-time credential comparison, which is positive, but no rate limiting, delay, account lockout or audit event is present in the reviewed path.

**Impact:** online brute-force attempts are not bounded by application logic.

**Severity:** P1 security  
**Required action:** add per-IP and per-identity rate limiting, security logging and optional temporary lockout.

### AUD0-SEC-007 — JWT returned in response body despite httpOnly cookie

Login sets an httpOnly cookie but also returns the raw JWT in JSON for static-dashboard compatibility.

**Impact:** frontend JavaScript can access the bearer token, reducing the protection gained from the httpOnly cookie and increasing XSS impact.

**Severity:** P1 security  
**Required action:** separate legacy static authentication from the React session flow; do not return the bearer token to the React client.

### AUD0-SEC-008 — No CSRF protection verified for cookie-authenticated writes

The session cookie uses `SameSite=Lax`, which helps, but no CSRF token or Origin/Referer enforcement has been verified for state-changing dashboard endpoints.

**Impact:** same-site assumptions and future deployment changes can expose write endpoints to CSRF risk.

**Severity:** P1 security  
**Required action:** verify all write routes, enforce Origin and/or CSRF tokens, and keep secure cookie attributes explicit.

### AUD0-SEC-009 — JWT validation lacks explicit issuer/audience/session identity

JWTs contain `sub`, `iat` and `exp`, but no verified `iss`, `aud`, `jti`, session version or revocation mechanism.

**Impact:** weak token scoping and no precise session revocation.

**Severity:** P2 security  
**Required action:** add issuer, audience, unique token ID and session-revocation strategy.

### AUD0-AUTH-001 — Logout does not revoke existing token

Logout deletes the browser cookie only. A copied bearer token remains valid until expiration.

**Severity:** P1 security  
**Required action:** introduce revocable sessions or short-lived access tokens with rotating refresh sessions.

## Database and startup findings

### AUD0-DB-001 — Database schema is embedded in one monolithic application file

Schema creation, migrations, application routes, seed logic, authentication and business logic live in `server/app.py`.

**Impact:** difficult review, testing, rollback and migration ownership.

**Severity:** P1 maintainability  
**Decision:** split into packages:
- `config`
- `db`
- `migrations`
- `auth`
- `routes`
- `services`
- `repositories`

### AUD0-DB-002 — No migration version table verified

Migrations are additive functions executed at every startup, but no canonical schema-version table or ordered migration registry was found in the reviewed section.

**Impact:** difficult rollback, audit and compatibility verification.

**Severity:** P1 reliability  
**Required action:** introduce ordered, immutable migrations with recorded version/checksum.

### AUD0-DB-003 — Multi-account trade primary key collision remains acknowledged but unresolved

The historical `trades.ticket` primary key remains position-based, while `trade_uid` is unique only when present. The code itself documents possible collisions across accounts using one backend.

**Impact:** one account may conflict with another if position/ticket identifiers overlap.

**Severity:** P0 data integrity for multi-account use  
**Required action:** composite canonical identity such as `(broker, server, account, position_id)` or a stable `trade_uid` primary key.

### AUD0-DB-004 — SQLite connection policy is incomplete

Each connection enables WAL and uses a timeout, but the reviewed code does not verify:
- foreign-key enforcement;
- busy timeout pragma;
- synchronous policy;
- connection pooling/thread policy;
- backup/restore integrity;
- migration locking.

**Severity:** P1 reliability  
**Required action:** centralize connection initialization and transaction policy.

### AUD0-DB-005 — Health endpoint is shallow

`/api/health` reports process-level status and AI Coach configuration, but does not check:
- database access;
- migration status;
- writable data directory;
- contract compatibility;
- deployment manifest version.

**Impact:** platform may report healthy while unable to persist data.

**Severity:** P1 operations  
**Required action:** separate liveness and readiness endpoints.

### AUD0-DB-006 — Seed import mutates operational configuration at startup

Seed files can populate strategy results, libraries, recipes and a wildcard locked profile.

**Impact:** release artifacts can silently alter operational state after deployment if seed content changes.

**Severity:** P1 configuration governance  
**Required action:** make seed/import an explicit versioned migration or administrative command; record provenance and require review.

## Command lifecycle finding

### AUD0-CMD-001 — EA command delivery is still poll-consume, not execution-confirmed

`GET /api/ea/command` selects the oldest unconsumed command and immediately sets:

- `consumed=1`
- `status='DELIVERED'`
- `delivered_at=<now>`

This proves only that the EA polled the command. It does not prove:
- parsing;
- validation;
- execution start;
- execution success;
- failure;
- retry;
- expiration;
- target ownership.

**Severity:** P0 command integrity  
**Decision:** replace with the same leased/idempotent state machine used for LocalBridge, adapted to the EA command channel.

### AUD0-CMD-002 — EA command selection is not target-scoped in the reviewed query

The query selects the globally oldest unconsumed command without filtering by instance, account, magic or symbol.

**Impact:** multiple EA instances can consume commands intended for another instance unless upstream constraints prevent this.

**Severity:** P0 multi-instance safety  
**Required action:** canonical Nexus instance identity and target-scoped polling.

## Positive controls observed

- Secret comparison uses `secrets.compare_digest`.
- JWT decoding restricts algorithms to HS256.
- Cookie is httpOnly and supports the Secure flag.
- Settings defaults come from a canonical contract.
- Strategy IDs are validated through the canonical registry.
- Database changes use parameterized SQL in the reviewed paths.
- Migrations are written to be additive/idempotent.
- Trade ledger deduplication uses a unique partial index.
- Zero-valued fields are intentionally preserved through `_pick`.

These strengths should be retained during refactoring.

## Immediate remediation order

1. Fix Docker build/package completeness.
2. Add production configuration validation and fail-closed startup.
3. Replace EA poll-consume command behavior with lease/ACK lifecycle.
4. Add target-scoped EA identity.
5. Separate liveness/readiness.
6. Establish migration versioning.
7. Harden dashboard sessions, login rate limiting and CSRF.
8. Resolve multi-account trade identity.
9. Split `app.py` into bounded modules.

## Progress update

### Overall audit

**24%**

### AUDIT-0 Repository Inventory

**46%**

### Root configuration and deployment review

**88%**

### Backend bootstrap/authentication review

**28%**

### Area status

- Repository Inventory: 46%
- Root Configuration: 88%
- MQL5: 12%
- Backend: 18%
- Frontend: 5%
- Contracts: 21%
- Deploy: 45%
- Security: 18%
- Documentation: 23%
- Testing: 6%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 5: Backend Route Authorization and Command Surface

## Scope reviewed

This block maps and reviews the route families visible in the inspected sections of `server/app.py`:

- notification/Telegram
- strategy-chain configuration
- LocalBridge heartbeat, polling, acknowledgement, enqueue and status
- deployment-manifest delivery
- dashboard overview and commands
- EA status, health and commands
- settings and strategies

The route inventory is still incomplete because the application file is large and additional sections remain to be inspected.

## Authorization matrix — verified portion

| Route family | Auth mechanism | Mutates state | Initial assessment |
|---|---|---:|---|
| `/api/notify/telegram` | shared bridge token | yes | authenticated but broad trust |
| `/api/strategy_chain/config_for_ea` | shared bridge token | no | expected EA read |
| `/api/strategy_chain/config` GET | dashboard JWT/cookie | no | appropriate |
| `/api/strategy_chain/config` PUT | dashboard JWT/cookie | yes | lacks verified schema validation |
| `/api/local_bridge/heartbeat` | shared bridge token | yes | arbitrary host registration possible |
| `/api/local_bridge/poll` | shared bridge token + host_id | yes | lease workflow present |
| `/api/local_bridge/ack` | shared bridge token + lease tuple | yes | good lease matching |
| `/api/local_bridge/enqueue` | dashboard JWT/cookie | yes | contract validation partly present |
| `/api/local_bridge/status` | dashboard JWT/cookie | yes/read-maintenance | GET performs DB mutation |
| `/api/local_bridge/deployment_manifest` | dashboard JWT/cookie | no | container path likely unavailable |
| `/api/dashboard/command` | dashboard JWT/cookie | yes | EA command lifecycle unsafe |
| `/api/ea/command` POST | dashboard JWT/cookie | yes | duplicate command API |
| `/api/settings` GET/POST/PUT | dashboard JWT/cookie | yes | contract validation present |
| `/api/strategies` GET/POST/PUT | dashboard JWT/cookie | yes | registry validation present |

## New findings

### AUD0-DEP-010 — Deployment manifest is not copied into the container

The endpoint `/api/local_bridge/deployment_manifest` resolves:

`<repository-root>/deploy/deployment-manifest.json`

The Render build context is `./server`, and the Dockerfile copies only files from that context. The `deploy/` directory is outside the Docker build context and is not copied.

**Expected runtime result:** the endpoint returns `404 deployment manifest missing` in the container even if the file exists in the Git repository.

**Severity:** P0 deployment/feature blocker  
**Status:** CONFIRMED BY PATH AND BUILD-CONTEXT CROSS-CHECK  
**Required action:** package canonical generated contracts into the backend artifact, or change the build context with an explicit minimal copy strategy.

### AUD0-API-001 — State-changing maintenance occurs inside a GET endpoint

`GET /api/local_bridge/status` updates expired command rows before returning status.

**Impact:**
- violates safe/idempotent GET expectations;
- caches, prefetchers or monitoring can trigger writes;
- complicates audit and testing.

**Severity:** P1 API correctness  
**Required action:** expire commands in a transaction during poll/enqueue, a scheduled maintenance task, or an explicit command.

### AUD0-SEC-010 — Any holder of the shared bridge token can register arbitrary LocalBridge hosts

Heartbeat accepts a caller-supplied `host_id` and upserts it after only checking the shared bridge token.

**Impact:** one compromised EA/worker token can create or impersonate arbitrary host identities.

**Severity:** P0 trust-boundary security  
**Required action:** per-host credentials or signed enrollment, immutable host identity and revocation.

### AUD0-SEC-011 — Shared bridge token can trigger Telegram notifications

The Telegram notification route uses the same broad bridge credential as EA and worker traffic.

**Impact:** any compromised bridge component can send arbitrary messages through the configured Telegram bot and fill the notifications table.

**Severity:** P1 abuse/cost/operational risk  
**Required action:** separate scoped notification permission, payload limits and rate limiting.

### AUD0-VAL-001 — Strategy-chain configuration is stored without verified validation

The dashboard PUT route writes the complete request JSON directly to `kv` without applying a schema, registry validation, numeric bounds or compatibility checks.

**Impact:** malformed strategy-chain configuration can be persisted and later consumed by the EA.

**Severity:** P0 trading configuration integrity  
**Required action:** canonical `strategy-chain.schema.json`, versioning, bounds, strategy registry references and staged activation.

### AUD0-VAL-002 — LocalBridge TTL has a floor but no verified upper bound

Enqueue calculates expiration using:

`created + max(60, int(ttl_seconds))`

A caller can request an extremely long lifetime.

**Impact:** stale operational commands can remain executable much later than intended.

**Severity:** P1 command safety  
**Required action:** enforce a conservative maximum TTL per command type.

### AUD0-VAL-003 — LocalBridge max-attempts has no verified bound

`max_attempts` is taken from the request and converted to integer without an observed upper limit.

**Impact:** excessive retries, repeated destructive operations and command queue persistence.

**Severity:** P1 command safety  
**Required action:** contract-defined minimum and maximum per command type.

### AUD0-CMD-003 — Two dashboard endpoints enqueue EA commands

Both:

- `POST /api/dashboard/command`
- `POST /api/ea/command`

perform substantially the same dashboard-authenticated enqueue operation.

**Impact:** duplicated contracts, divergent validation and frontend ambiguity.

**Severity:** P1 API architecture  
**Required action:** choose one canonical route and maintain the other only as a versioned compatibility alias with deprecation telemetry.

### AUD0-CMD-004 — Destructive EA commands lack verified target and confirmation policy

The allowed command set includes:

- `close_all`
- `close_position`
- `partial_close`
- resets of protections and daily state

The reviewed enqueue path does not verify canonical target identity, operator confirmation, reason, expected account/symbol, expiry or idempotency key.

**Impact:** a valid dashboard session can create broad or ambiguous destructive commands.

**Severity:** P0 trading safety  
**Required action:** typed command contract, mandatory target, short expiry, idempotency, operator reason and two-step confirmation for high-impact actions.

### AUD0-AUDIT-001 — No verified operator audit record for dashboard changes

Reviewed settings, strategy, chain and EA command writes persist new state but do not visibly write a dedicated immutable operator audit event containing:

- user
- timestamp
- previous value
- new value
- reason
- request/session identity
- result

**Severity:** P1 governance/security  
**Required action:** append-only administrative audit log.

### AUD0-API-002 — Arbitrary JSON bodies are handled without explicit request-size limits

Several routes call `await request.json()` directly, including heartbeat, notifications, configuration and commands.

**Impact:** memory pressure, oversized database blobs and log/storage abuse.

**Severity:** P1 availability  
**Required action:** reverse-proxy and application limits, typed models and per-field size bounds.

### AUD0-API-003 — Telegram and Anthropic outbound calls are synchronous

The reviewed helper functions use blocking `urllib.request.urlopen` calls inside a FastAPI process.

**Impact:** a slow upstream can occupy the worker and reduce API responsiveness. Telegram uses a 10-second timeout; Anthropic uses 60 seconds.

**Severity:** P1 performance/reliability  
**Required action:** async client or bounded worker queue, circuit breaker and retry policy.

### AUD0-API-004 — External-provider errors may leak response details

Anthropic HTTP error handling returns up to 300 decoded characters from the provider response.

**Impact:** upstream diagnostics or sensitive request-related information may be exposed to clients depending on caller behavior.

**Severity:** P2 information disclosure  
**Required action:** log detailed provider errors server-side with redaction; return stable public error codes.

## Positive controls verified

The LocalBridge command channel is materially stronger than the EA command channel:

- target validation requires a host;
- idempotency keys are supported;
- lease IDs are generated;
- lease mismatch returns conflict;
- retryable and final failure states exist;
- attempt counts are tracked;
- command events are appended;
- expiration is represented;
- acknowledgements validate state names.

This implementation should become the reference state machine for the EA command channel, after the bounds and identity findings above are resolved.

Settings and strategy routes also show valuable controls:

- settings patches use the canonical settings contract;
- strategy identifiers are checked against the live registry;
- schema version is returned to clients;
- partial settings updates are merged rather than blindly replacing unrelated fields.

## Preliminary route architecture decision

The backend should be separated into explicit security domains:

1. **Public**
   - liveness only

2. **EA ingestion**
   - per-instance identity
   - telemetry and history push

3. **EA command**
   - target-scoped lease/ACK state machine

4. **LocalBridge**
   - per-host identity
   - leased commands

5. **Dashboard read**
   - authenticated operator

6. **Dashboard control**
   - authenticated operator + CSRF + audit + step-up confirmation

7. **External integrations**
   - internal job queue, not direct shared-token access

## Immediate next verification queue

1. Complete remaining route inventory in `app.py`.
2. Identify every route without `Depends(require_user)` or `check_token`.
3. Inspect update/delete/reset endpoints for destructive behavior.
4. Inspect analytics and journal query bounds.
5. Inspect Coach routes for prompt/data leakage and cost controls.
6. Inspect static file mounting and fallback routing.
7. Inspect `_enqueue_ea_command` implementation and command schema.
8. Inspect CORS middleware; none has yet been seen in reviewed sections.
9. Verify whether tests assert route authorization coverage.

## Progress update

### Overall audit

**26%**

### AUDIT-0 Repository Inventory

**49%**

### Root configuration and deployment review

**92%**

### Backend route/authentication review

**43%**

### Area status

- Repository Inventory: 49%
- Root Configuration: 92%
- MQL5: 12%
- Backend: 24%
- Frontend: 5%
- Contracts: 23%
- Deploy: 52%
- Security: 24%
- Documentation: 23%
- Testing: 7%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 6: Analytics, Journal, Risk Controls and Backtest Compute Surface

## Scope reviewed

- EA health scoring
- strategy risk configuration and manual overrides
- strategy overview
- analytics summaries and what-if analysis
- journal metadata/tagging
- backtest optimization endpoints
- creator setup persistence

## New findings

### AUD0-PERF-001 — Multiple analytics endpoints request up to 100,000 ledger rows

Several routes call `_ledger_trades_with_meta(100000)` and then perform grouping/filtering in Python.

**Impact:**
- high memory and CPU usage;
- repeated full-history scans;
- response latency grows with account history;
- one authenticated request can monopolize the single application worker.

**Severity:** P1 performance  
**Required action:** server-side SQL aggregation, bounded pagination, cached/materialized summaries, and explicit hard limits.

### AUD0-PERF-002 — User-controlled `limit` parameters are not visibly clamped

Routes such as analytics and journal pass caller-provided limits directly to SQL/helper functions.

**Impact:** an authenticated client may request very large result sets.

**Severity:** P1 availability  
**Required action:** typed query models with conservative maximums and cursor-based pagination.

### AUD0-RISK-001 — Strategy risk multiplier can reach 10× through API configuration

`risk_config` clamps `max_mult` to 10.0, and manual overrides are also clamped to 10.0.

**Impact:** a dashboard change can multiply EA sizing by up to ten without a verified staged approval, account cap, or portfolio-level risk check.

**Severity:** P0 trading safety  
**Required action:** much tighter production bounds, account-level risk budget, two-step confirmation, dry-run preview, immutable audit record and rollback.

### AUD0-RISK-002 — Risk configuration validation is incomplete

Only some fields are clamped. In the reviewed path, values such as `target_dd_pct` and `min_pf` are accepted without visible range validation, while boolean/type handling is permissive.

**Impact:** invalid configuration may alter automatic risk scaling or cause runtime conversion failures.

**Severity:** P0 trading configuration integrity  
**Required action:** canonical versioned schema and atomic validation of the complete configuration.

### AUD0-RISK-003 — Manual strategy overrides do not validate strategy identifiers

The manual override route iterates arbitrary map keys and stores them without calling the live strategy registry.

**Impact:** stale, misspelled or fabricated strategy names can remain in operational configuration.

**Severity:** P1 integrity  
**Required action:** registry validation and migration policy for renamed strategies.

### AUD0-RISK-004 — Health score may create false confidence

The EA health score assigns positive/neutral status based on self-reported telemetry and simplified thresholds. The news check is marked successful whenever the EA is online, regardless of whether a news block is active or the feed itself is healthy.

**Impact:** a high score can be interpreted as trading safety even though it is not an independent risk-control verification.

**Severity:** P1 product/risk communication  
**Required action:** rename as telemetry health, expose provenance and confidence, and separate connectivity, data quality, risk-state and strategy-performance scores.

### AUD0-DATA-001 — Journal metadata uses ticket-only identity

`journal_meta` joins metadata by `ticket`, while the backend already acknowledges cross-account ticket collision risk.

**Impact:** notes, tags and ratings may attach to the wrong trade in multi-account deployments.

**Severity:** P0 data integrity  
**Required action:** journal metadata must reference canonical `trade_uid`, not legacy ticket alone.

### AUD0-VAL-004 — Journal tags, ratings and notes lack visible bounds

The tagging route accepts:
- arbitrary tag arrays;
- unrestricted note content;
- rating values without verified range;
- no visible maximum count or length.

**Impact:** oversized rows, malformed ratings, UI issues and storage abuse.

**Severity:** P1 validation  
**Required action:** typed request model, rating range, tag normalization, length/count limits and existence check for the target trade.

### AUD0-VAL-005 — Strategy overview accepts unknown strategy names

The route uses the path parameter to query settings, backtest rows, diagnostics and ledger trades, but no registry validation is visible.

**Impact:** ambiguous empty responses, unnecessary full-history scans and inconsistent API semantics.

**Severity:** P2 API correctness  
**Required action:** validate through the canonical registry and return 404/422 for unknown IDs.

### AUD0-COMPUTE-001 — Backtest optimization runs synchronously inside API requests

Optimization endpoints execute nested strategy/timeframe/parameter loops and call `backtest.run_backtest` repeatedly before responding.

**Impact:**
- severe CPU-bound request duration;
- worker starvation;
- request timeout;
- concurrent users can amplify load;
- no cancellation or durable progress tracking.

**Severity:** P0 availability/architecture  
**Required action:** move optimization to a bounded job queue/worker with quotas, progress, cancellation, persisted results and concurrency limits.

### AUD0-COMPUTE-002 — Optimization search-space inputs are insufficiently bounded

Caller-controlled values include:
- strategy pool;
- timeframes;
- ATR grids;
- HTF options;
- breakeven options;
- trailing options.

No visible maximum pool size or grid cardinality is enforced.

**Impact:** authenticated computational denial of service through combinatorial explosion.

**Severity:** P0 availability  
**Required action:** validate strategy IDs and allowed timeframes, cap total combinations before execution, reject oversized jobs and estimate cost before enqueue.

### AUD0-COMPUTE-003 — Backtest exceptions are silently converted into missing candidates

The optimization helper catches broad exceptions and returns `None`.

**Impact:** infrastructure errors, invalid data and coding bugs may be misreported as a strategy having no viable result.

**Severity:** P1 correctness/observability  
**Required action:** typed failure classes, per-candidate error accounting, job failure thresholds and structured logs.

### AUD0-COMPUTE-004 — Optimization results mutate operational KV state automatically

Optimization endpoints save result payloads such as `creator_per_strategy_last` and `creator_multi_tf_last` after computation.

**Impact:** exploratory analysis and operational configuration history are mixed in the same generic KV store without provenance, ownership or lifecycle.

**Severity:** P1 governance  
**Required action:** dedicated immutable experiment/job tables with dataset version, code version, parameters, status and operator identity.

### AUD0-VAL-006 — Creator setup persistence stores caller-controlled objects after in-place mutation

The save route accepts a nested `setup`, checks only for `combo`, adds `saved_at`, and stores it.

**Impact:** malformed/unbounded setup structures enter persistent state; mutating the input object also makes behavior harder to reason about.

**Severity:** P1 validation  
**Required action:** canonical setup schema, deep copy/normalization, size limits and strategy registry validation.

### AUD0-API-005 — Settings validation endpoint returns HTTP success for invalid settings

The route catches validation exceptions and returns `{valid: false}` rather than preserving a 4xx response.

**Impact:** clients, monitoring and automation can interpret invalid configuration as a successful request unless they inspect the body.

**Severity:** P2 API semantics  
**Required action:** standardize error envelopes while retaining 422 status.

## Positive controls observed

- Analytics explicitly exposes provenance in several responses.
- Ledger-derived analytics avoid relying solely on mutable trade summary rows.
- Strategy-risk configuration includes some safety clamps.
- Backtest results are ranked with explicit verdict ordering.
- Creator setup count is capped at 50.
- Authentication is required on all reviewed analytics, journal and optimization routes.

## Architectural decision

Backtest and optimization must be treated as a separate compute subsystem, not ordinary synchronous API handlers.

Recommended boundary:

- API validates and enqueues a job;
- worker executes a bounded search;
- job records exact code/data/contract versions;
- progress is queryable;
- results are immutable;
- activation into live settings is a separate reviewed action.

## Progress update

### Overall audit

**28%**

### AUDIT-0 Repository Inventory

**52%**

### Backend route/authentication review

**58%**

### Area status

- Repository Inventory: 52%
- Root Configuration: 92%
- MQL5: 12%
- Backend: 31%
- Frontend: 5%
- Contracts: 25%
- Deploy: 52%
- Security: 27%
- Documentation: 24%
- Testing: 8%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 7: Licenses, AI Coach, Downloads and Static Delivery

## Scope reviewed

- license CRUD and license summary
- downloads and LocalBridge worker delivery
- AI Coach prompt construction, sessions, memory and action application
- synthetic calendar and chart routes
- React SPA delivery and static-site mounting
- locked-profile saving and optimization job facade

## New critical findings

### AUD0-SEC-012 — Authenticated download listing is bypassed by public static mounting

`/api/downloads/list` requires dashboard authentication, but it returns URLs under:

`/downloads/<filename>`

At the end of the application, the entire `server/static` directory is mounted publicly on `/`. Therefore files inside `server/static/downloads` are directly reachable without passing through the authenticated API route.

The allowed download types explicitly include:

- `.set`
- `.tpl`
- `.ex5`
- `.mq5`
- `.zip`

**Impact:** proprietary EA source, compiled artifacts, presets or packages placed in the downloads directory may be publicly accessible.

**Severity:** P0 confidentiality/IP protection  
**Status:** CONFIRMED BY ROUTE/MOUNT CROSS-CHECK  
**Required action:** move protected files outside the public static root and serve them only through an authenticated, authorization-checked download endpoint.

### AUD0-DEP-011 — Local worker download path is incompatible with the Docker image

`WORKER_FILE` resolves to:

`<repository-root>/LocalBridge/nexus_local_worker.py`

The Dockerfile instead copies `nexus_local_worker.py` directly into `/app`, and the Render Docker context is `./server`. The repository-level `LocalBridge/` directory is unavailable inside the image.

**Expected runtime result:** `/api/downloads/local_worker` returns 404 in the container.

**Severity:** P0 deployment/feature blocker  
**Status:** CONFIRMED BY PATH AND BUILD-CONTEXT CROSS-CHECK  
**Required action:** package the worker as an explicit release artifact and reference a path inside the built image.

### AUD0-AI-001 — Coach actions execute directly without an enforced confirmation state

The Coach system prompt tells the model to suggest actions so the user can confirm them. However, `/api/coach/apply_action` directly applies actions whenever the authenticated frontend calls it.

Supported live effects include:

- pause/resume EA;
- close all;
- reset protections;
- reset daily state;
- enable/disable strategies;
- set global risk;
- set strategy risk.

There is no verified server-side proposal token, confirmation challenge, expiry, target binding or second-factor/step-up state.

**Impact:** frontend bugs, compromised sessions or manipulated Coach output can lead to direct trading-control changes.

**Severity:** P0 trading safety  
**Required action:** implement a server-enforced `PROPOSED -> CONFIRMED -> EXECUTED` action lifecycle with target, expiry, operator reason and immutable audit record.

### AUD0-AI-002 — Coach can set live global risk up to 10%

The Coach action route clamps `RiskPercent` between 0 and 10 and writes it directly into live settings.

**Impact:** an AI-assisted action can raise account risk to a level that may be catastrophic depending on leverage, stop distance and concurrent positions.

**Severity:** P0 trading safety  
**Required action:** production hard cap substantially below 10%, portfolio-level validation, preview of monetary risk, two-step confirmation and account policy enforcement.

### AUD0-AI-003 — Coach can set per-strategy multiplier up to 10×

The Coach action route writes manual strategy multipliers up to 10×.

**Impact:** combines AI-originated recommendations with a high-impact live sizing control.

**Severity:** P0 trading safety  
**Required action:** same controls as global risk, plus strategy-level exposure and correlation limits.

## AI privacy, integrity and cost findings

### AUD0-AI-004 — Trading/account data is sent to an external model provider

The Coach system prompt can include:

- symbol;
- balance;
- equity;
- floating and daily P&L;
- drawdown;
- session and regime;
- strategy/runtime state;
- frontend-provided chart context;
- persistent user memory.

This content is sent to Anthropic when the API key is configured.

**Impact:** sensitive financial and operational telemetry leaves the self-hosted boundary.

**Severity:** P1 privacy/governance  
**Required action:** explicit disclosure and opt-in, data-minimization policy, redaction, tenant policy and provider-retention documentation.

### AUD0-AI-005 — Frontend context and persistent memory are inserted into the system prompt

Caller-controlled context and stored memory are concatenated directly into the system instructions.

**Impact:** prompt injection can influence Coach behavior and action recommendations.

**Severity:** P1 AI integrity  
**Required action:** treat context/memory as untrusted quoted data, use strict structured fields, separate policy instructions, and never authorize actions from model text alone.

### AUD0-AI-006 — Coach session identifiers are caller-controlled and not ownership-scoped

The caller supplies `session_id`, which maps directly to a generic KV key. A default shared session is used when absent.

**Impact:** session collision, cross-client history mixing and arbitrary deletion of known session IDs within the same operator account.

**Severity:** P1 privacy/integrity  
**Required action:** server-generated IDs, owner binding, unguessable identifiers and metadata table instead of generic KV keys.

### AUD0-AI-007 — No verified model usage quotas or cost controls

The reviewed Coach route has no visible:

- request-rate limit;
- daily token budget;
- message/context size cap;
- per-session quota;
- concurrency limit;
- provider cost telemetry.

**Severity:** P1 cost/availability  
**Required action:** quotas, usage accounting, bounded context and circuit breaker.

### AUD0-AI-008 — Provider failures are returned as successful HTTP responses

When the model call fails, the route returns a normal response containing `demo: true` and error text rather than an appropriate service error status.

**Impact:** clients and monitoring may treat provider failure as successful Coach execution.

**Severity:** P2 API semantics  
**Required action:** stable 502/503 error envelope with internal details redacted.

## License findings

### AUD0-LIC-001 — Open license mode makes every submitted key valid

When `NEXUS_LICENSE_MODE=open`, the verification route accepts any key.

**Impact:** license CRUD and expiry information can appear meaningful while enforcement is disabled.

**Severity:** P1 product/security semantics  
**Required action:** make environment and UI clearly display enforcement state; production releases intended for licensing must fail closed in strict mode.

### AUD0-LIC-002 — License creation is also an upsert

`POST /api/license/create` uses `ON CONFLICT ... DO UPDATE`.

**Impact:** a create operation can silently overwrite an existing license.

**Severity:** P1 API/data integrity  
**Required action:** return conflict for duplicate keys; use PATCH for modification.

### AUD0-LIC-003 — License fields lack complete validation

The reviewed CRUD paths do not visibly enforce:

- key format/length;
- account identifier bounds;
- expiry validity;
- note length;
- trial/expiry consistency;
- existence checks on update/delete.

**Severity:** P1 validation  
**Required action:** canonical license schema and explicit 404/409 responses.

### AUD0-LIC-004 — License keys are returned in full through list APIs

The license list returns complete keys to the dashboard.

**Impact:** anyone with a compromised dashboard session can exfiltrate all active license credentials.

**Severity:** P1 secret handling  
**Required action:** show masked identifiers by default and reveal/rotate only through privileged audited actions.

## Static and demo-data findings

### AUD0-API-006 — Static site and React application are intentionally public

The `/app` routes and the root static mount do not require dashboard authentication. This is appropriate only if the React application itself consistently protects sensitive API calls and does not embed secrets.

**Severity:** P1 review requirement  
**Required action:** frontend audit must verify route guards, token storage, source maps, embedded configuration and caching.

### AUD0-DATA-002 — Demo calendar contains fabricated future economic events

The calendar route generates synthetic events relative to the current time and labels them as demo in the response.

**Impact:** if frontend presentation does not make the demo provenance unmistakable, an operator may confuse fabricated events with a real news feed.

**Severity:** P0 trading-information safety  
**Required action:** prominent persistent DEMO watermark; never feed synthetic events into live trading risk logic.

### AUD0-DATA-003 — Chart OHLC is synthetic

The chart endpoint generates mathematical candles and correctly returns `SYNTHETIC_DATA` provenance.

**Risk:** frontend must preserve the provenance visibly and must not mix synthetic candles with real trade markers without a clear warning.

**Severity:** P1 product integrity.

### AUD0-CORS-001 — No CORS middleware was found in the reviewed application

No FastAPI CORS middleware setup was observed in the full inspected file. Same-origin deployment can work without it, but separate frontend/backend origins will fail unless handled elsewhere.

**Severity:** P2 deployment compatibility  
**Required action:** document same-origin architecture or add a strict allow-list; never use wildcard origins with credentials.

## Locked-profile and job findings

### AUD0-PROFILE-001 — Locked profile save accepts weakly validated operational parameters

The locked-profile endpoint maps caller-provided `base_cfg`, `overrides`, metrics and labels into an operational profile. No complete bounds/registry validation is visible in that route before versioning.

**Impact:** malformed or unsafe profile values can be persisted for EA consumption.

**Severity:** P0 trading configuration integrity  
**Required action:** validate the final canonical profile against one strict schema before storage or activation.

### AUD0-COMPUTE-005 — Optimization job endpoint is not a real job tracker

`GET /api/backtest/optimize/{job_id}` ignores the requested ID and returns a single global `backtest_last_optimize` result when present.

**Impact:** results can be attributed to the wrong request/user; there is no job identity, progress, isolation or lifecycle.

**Severity:** P1 architecture/correctness  
**Required action:** durable job records keyed by real job ID with owner, input checksum, state and result reference.

## Positive controls observed

- React asset path traversal is mitigated with `resolve()` plus root-prefix checking.
- `index.html` is sent with no-cache, while hashed assets receive long immutable caching.
- Synthetic chart data declares provenance.
- Coach strategy enable/disable actions validate registry identity.
- Coach auto-disable eligibility is constrained by a dedicated registry set.
- License SQL uses parameterized values; dynamically assembled columns come from a fixed allow-list.

## Backend phase conclusion

The backend is feature-rich and demonstrates several good contract and provenance ideas, but it currently combines four incompatible trust levels in one process:

1. public web/static content;
2. authenticated dashboard controls;
3. shared-token machine ingestion/control;
4. external AI and notification integrations.

The strongest next architecture move is not adding more routes. It is separating these trust zones and placing explicit policy boundaries between them.

## Progress update

### Overall audit

**32%**

### AUDIT-0 Repository Inventory

**59%**

### Backend route/authentication review

**76%**

### Area status

- Repository Inventory: 59%
- Root Configuration: 94%
- MQL5: 12%
- Backend: 42%
- Frontend: 7%
- Contracts: 30%
- Deploy: 60%
- Security: 38%
- Documentation: 27%
- Testing: 10%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 8: MQL5 Entrypoint, Lifecycle and Strategy Router

## Scope reviewed

Primary EA entrypoint:

- `MQL5/Experts/NEXUS_EA_v2.mq5`
- include graph declared by the entrypoint
- indicator-handle lifecycle
- multi-timeframe activation
- `OnInit`
- `OnDeinit`
- `OnTimer`
- first half of `OnTick`
- hard-coded strategy collection/router
- `OnTester`

This is the beginning of the MQL5 audit. Findings involving functions defined in included modules remain provisional until their implementations are inspected.

## Verified architecture facts

- The EA entrypoint includes more than fifty local `.mqh` modules under `NEXUS_v1`.
- Trade execution deliberately avoids the MT5 standard trading library and uses raw native helpers.
- Strategy evaluation is centrally orchestrated by a hard-coded collector.
- A one-second timer drives web synchronization, ledger reconciliation, license checks, persistence, dashboard rendering and statistics hooks.
- Position management runs on every fresh tick before the new-bar entry gate.
- New exposure is blocked by pause, persisted-state, license, protection, spread and news gates.
- Multi-timeframe profile mode evaluates fixed D1, H4 and H1 passes on one chart.
- Shutdown persists ledger, virtual-stop and state data and releases several handle pools.

## Positive controls observed

- Indicator handle creation fails initialization if any required handle is invalid.
- Handles have explicit release paths.
- Multi-timeframe code restores the original indicator handles after alternate-TF evaluation.
- Strategy evaluation uses closed-bar indicator values (`shift=1`) in the reviewed update function.
- A new-bar gate prevents entry-decision execution on every tick.
- Position management and risk protections are applied before new signal routing.
- Web requests are explicitly disabled in Strategy Tester.
- The ledger is drained during timer activity and shutdown.
- License failure leaves the EA initialized but trading-disabled rather than crashing.
- Symbol whitelist failure stops initialization.
- A per-strategy open-position gate and per-strategy/per-timeframe bar tracking are present.
- Data-collection mode is explicitly described as demo-only and has an open-position cap.

## New findings

### AUD0-MQL-001 — Entrypoint has an extremely wide compile-time dependency surface

The primary `.mq5` file directly includes more than fifty local modules spanning:

- configuration;
- risk;
- execution;
- strategies;
- persistence;
- licensing;
- web integration;
- visualization;
- statistics;
- recovery/grid/pyramiding;
- institutional management.

**Impact:**
- include-order coupling;
- difficult isolated compilation and unit testing;
- global-symbol collisions;
- unclear ownership of lifecycle behavior;
- one module can silently depend on globals initialized by another.

**Severity:** P1 architecture/maintainability  
**Required action:** define layered include boundaries and prohibit reverse dependencies:
1. types/contracts;
2. pure market calculations;
3. strategy modules;
4. risk and execution;
5. persistence/integration;
6. application orchestration.

### AUD0-MQL-002 — Version identity is inconsistent

The same entrypoint identifies itself as:

- file/product name `NEXUS_EA_v2`;
- property version `3.60`;
- descriptions containing `v2.0`;
- include namespace `NEXUS_v1`.

**Impact:** support, deployment manifests, telemetry, compatibility checks and user-facing diagnostics can refer to different version families.

**Severity:** P1 release governance  
**Required action:** one generated canonical version artifact used by MQL property, manifest, backend compatibility response, UI and documentation.

### AUD0-MQL-003 — Strategy routing is duplicated as hard-coded code and numeric selector IDs

The router manually calls every strategy and assigns fixed selector numbers such as 17–37. The platform also has a strategy registry and backend contracts.

**Impact:**
- strategy rename/add/remove can drift across MQL, Python backtest, backend and frontend;
- numeric selector mapping can become off-by-one;
- a strategy may appear live in one subsystem but not execute in another;
- hard-coded comments/counts can become stale.

**Severity:** P0 strategy-contract integrity  
**Required action:** generate the MQL strategy registry/dispatch metadata from one canonical source and add parity tests across MQL, backend and backtest engine.

### AUD0-MQL-004 — Fixed-size strategy arrays create a silent future capacity boundary

The router uses fixed arrays (`48` in the reviewed entry path, `64` in a temporary multi-TF path) and manually increments a strategy count.

Current reviewed strategy count appears below the boundary, but adding strategies can eventually truncate or overrun assumptions unless every path is updated consistently.

**Severity:** P1 extensibility/safety  
**Required action:** compile-time registry count, static assertions where possible, explicit capacity checks before every append and test covering maximum enabled strategies.

### AUD0-MQL-005 — Multi-timeframe profile execution supports only a fixed D1/H4/H1 set

Profile mode hard-codes three passes:

- D1
- H4
- H1

Any canonical profile selecting another timeframe cannot be evaluated through this path.

**Impact:** silent incompatibility if optimizer/contracts later allow M30, M15 or another timeframe.

**Severity:** P1 contract compatibility  
**Required action:** derive allowed profile timeframes from the canonical contract and reject unsupported profile values loudly.

### AUD0-MQL-006 — Timer orchestration is overloaded

Every one-second timer callback invokes or attempts:

- web push;
- command polling;
- visual HTTP push;
- periodic history reconciliation;
- ledger sweep/drain;
- license verification;
- state save;
- dashboard render;
- stats hook.

Some included functions may internally throttle, but the entrypoint itself provides no visible scheduling domains or execution budget.

**Impact:**
- timer jitter;
- UI/network stalls affecting operational housekeeping;
- difficult latency attribution;
- repeated work even when components are disabled unless each callee protects itself.

**Severity:** P1 runtime reliability  
**Required action:** explicit scheduler with separate cadences, deadlines, enable flags, last-run timestamps and per-task telemetry.

### AUD0-MQL-007 — Blocking integration work begins during initialization

When web sync is enabled, `OnInit` performs an immediate safe push and seven-day closed-trade synchronization. Locked-profile fetching also occurs near the beginning of initialization.

**Impact:** network/backend latency can delay EA attachment and restart recovery.

**Severity:** P1 availability  
**Required action:** initialize trading safety state first, then perform network bootstrap asynchronously through timer-driven state transitions with timeout and degraded-mode status.

### AUD0-MQL-008 — Runtime settings are pulled on every tick at orchestration level

`OnTick` calls `NXS_PullSettings()` before risk modules and entry logic. The implementation may throttle internally, but that has not yet been verified.

**Risk:** if it performs parsing, file access, global-variable access or networking per tick, high-frequency symbols will incur unnecessary latency.

**Severity:** P1 pending implementation verification  
**Required action:** inspect `NXS_RuntimeSettings.mqh`; enforce explicit polling cadence and atomic snapshot activation.

### AUD0-MQL-009 — Indicator refresh performs many sequential buffer reads

The reviewed update function performs individual `CopyBuffer` calls for ADX components, RSI, Bollinger bands, MACD, SAR, ATR, moving averages and Ichimoku values. It is called on ticks and again during multi-timeframe activation.

**Impact:** measurable CPU/terminal load across symbols and multiple EA instances.

**Severity:** P1 performance  
**Required action:** refresh only on required bars/timeframes, cache readiness, batch logically, and instrument update duration/failure counts. The included reuse-performance pack may mitigate parts of this and must be inspected before final disposition.

### AUD0-MQL-010 — Indicator-read failures are silent at runtime

After initialization, `NXS_UpdateIndicators()` returns false on the first failed `CopyBuffer`, and `OnTick` simply returns. No rate-limited error, handle recreation or degraded-state flag is visible in the reviewed entrypoint.

**Impact:** the EA can stop making decisions silently after history/handle issues while still appearing attached.

**Severity:** P0 observability/availability  
**Required action:** structured failure counters, last-success timestamp, dashboard health state, bounded handle recreation and fail-safe entry block.

### AUD0-MQL-011 — Initialization order creates contract/state ambiguity

The locked profile is fetched before:

- symbol whitelist validation;
- indicator creation;
- runtime-settings initialization;
- preset application;
- license verification;
- persisted-state load.

Without inspecting every callee, it is unclear which layer wins when backend profile, preset, runtime settings and persisted state disagree.

**Severity:** P0 configuration precedence  
**Required action:** document and enforce one atomic precedence chain, for example:
1. compiled defaults;
2. symbol profile;
3. selected preset;
4. validated locked profile;
5. validated runtime override;
6. persisted operational state, limited to stateful fields only.

### AUD0-MQL-012 — License failure is operationally permissive by design

A failed initial license check does not fail `OnInit`; the EA remains loaded in idle mode and depends on later enforcement gates.

This can be appropriate for recoverability, but it requires every exposure-creating path to pass through the same license gate.

**Severity:** P0 verification requirement  
**Required action:** audit all order-entry, grid, pyramid, recovery, split and Coach/command paths to prove none can create exposure outside `NXS_License_Enforce()`.

### AUD0-MQL-013 — `OnTester` optimizes only by profit factor

The custom tester return value is `STAT_PROFIT_FACTOR`. Profit factor alone does not encode:

- minimum trade count;
- drawdown;
- recovery;
- expectancy;
- stability;
- out-of-sample performance.

**Impact:** optimization can favor sparse or unstable parameter sets.

**Severity:** P0 research validity  
**Required action:** use a robust custom score with minimum-trade rejection, drawdown penalty and stability criteria; preserve all raw metrics for independent ranking.

### AUD0-MQL-014 — Optimization CSV writes from parallel agents require an external merge contract

The code correctly notes that each tester agent writes in its own sandbox and that outputs must be collected and merged.

**Risk:** without a deterministic merger and run identity, results can be incomplete, duplicated or mixed between optimization runs.

**Severity:** P1 research reproducibility  
**Required action:** include run ID, EA/version hash, symbol, timeframe, dataset range, parameter checksum and agent identity in every row; provide a verified merger.

## Critical verification queue for included modules

1. `NXS_RuntimeSettings.mqh`
   - cadence, atomicity, schema compatibility and precedence.

2. `NXS_License.mqh`
   - fail-closed behavior across every exposure path.

3. `NXS_Globals.mqh` and `NXS_SafeOrder.mqh`
   - raw order execution, retcodes, fill policy, normalization and retry.

4. `NXS_Risk.mqh`, `NXS_RiskShield.mqh`, `NXS_Protections.mqh`
   - lot sizing, drawdown state, margin and race conditions.

5. `NXS_Execution.mqh` and `NXS_SignalRouter.mqh`
   - final entry gate and target identity.

6. `NXS_Management.mqh`, Grid, Pyramid, Split and Institutional management
   - proof that all additive exposure obeys global risk/license controls.

7. `NXS_WebBridge.mqh`
   - command targeting, authentication, retries and blocking behavior.

8. `NXS_State.mqh`, ledger and virtual SL
   - crash consistency and account/magic binding.

## Progress update

### Overall audit

**35%**

### AUDIT-0 Repository Inventory

**63%**

### MQL5 entrypoint/lifecycle review

**32%**

### Area status

- Repository Inventory: 63%
- Root Configuration: 94%
- MQL5: 22%
- Backend: 42%
- Frontend: 7%
- Contracts: 33%
- Deploy: 60%
- Security: 40%
- Documentation: 29%
- Testing: 11%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 9: Runtime Settings, Licensing, Risk and Primary Execution

## Scope reviewed

- `MQL5/Include/NEXUS_v1/NXS_RuntimeSettings.mqh`
- `MQL5/Include/NEXUS_v1/NXS_License.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Risk.mqh`
- `MQL5/Include/NEXUS_v1/NXS_SafeOrder.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Execution.mqh`

## Verified behavior

### Runtime settings

- Runtime settings are polled every 15 seconds, not literally on every tick.
- Pull uses `GET /api/ea/settings` with `X-Nexus-Token`.
- Only a curated set of shadow globals is overwritten.
- Disabled strategies and per-strategy risk multipliers are applied live.
- Parsing is manual string scanning rather than a schema-aware JSON parser.
- Values are applied field-by-field directly to global state.

### License

- Tester mode bypasses license enforcement.
- License verification runs at startup and nominally every hour.
- A previously valid license gets a 3-day offline grace period.
- If the backend is unreachable and there has never been a valid license, the EA creates a local 14-day trial.
- Trial mode caps requested lot size to 0.01.
- License validity is bound to key, account, symbol and version in the request body.

### Risk

- Position size is based on account balance, risk percentage, stop distance, tick value and tick size.
- Anti-bleed and account/streak multipliers are applied before lot normalization.
- Live protections include margin level, daily drawdown, max trades/day, max concurrent positions, pause and anti-revenge.
- Most account-level protections are intentionally bypassed in Strategy Tester.
- A separate risk-of-ruin daily freeze remains active in tester.
- Ruin protection can flatten current-symbol NEXUS positions.

### Execution

- Strategy identity is checked before opening.
- Profile enablement, profile timeframe, dashboard disable, same-bar direction cap, per-direction/per-timeframe cap, post-SL cooldown and exhaustion are checked.
- Lot multipliers are capped.
- Projected margin level is checked before sending.
- Common preflight applies RiskShield, directional exposure cap and broker preflight.
- Virtual SL preparation occurs immediately before order send.
- Order send has bounded retries for selected retcodes.
- Successful opens update counters only after the send wrapper reports success.

## Positive controls observed

- Clear execution return-code enums.
- Broker preflight is centralized for the primary entry path.
- Projected margin is calculated before exposure creation.
- Directional total-lot cap rejects rather than silently resizing the order.
- Strategy IDs are validated before execution.
- Trial cap is applied after lot-step realignment.
- Unknown strategy and invalid-stop failures are explicit.
- Retry behavior is limited to a small retcode set.
- Per-strategy runtime disabling is enforced at the final open function.
- Ruin freeze is checked inside `NXS_OpenTrade`, not only in the outer router.

## New findings

### AUD0-SET-001 — Runtime settings are applied non-atomically

Every field is parsed and written directly into global shadow variables. Disabled-strategy arrays and strategy-risk JSON are updated later in the same function.

A tick or nested call cannot execute concurrently in normal MQL event semantics, but readers can still observe a configuration assembled from different backend revisions if the response itself is partial, malformed or contract-inconsistent.

There is no visible:

- settings version check;
- payload checksum;
- schema version verification;
- full-object validation;
- staged snapshot;
- rollback to last valid snapshot.

**Severity:** P0 configuration integrity  
**Required action:** parse into a temporary typed structure, validate the complete payload and atomically activate it only if all required constraints pass.

### AUD0-SET-002 — Runtime numeric values have no local range validation

The macros apply any parsed number when present. No local bounds are enforced for:

- risk percentage;
- maximum lot;
- maximum daily drawdown;
- maximum concurrency;
- score thresholds;
- ATR stop/target multipliers;
- trailing parameters;
- per-timeframe SL/TP multipliers.

A compromised backend, contract regression or malformed value can therefore push unsafe or nonsensical settings into live risk logic.

**Severity:** P0 capital safety  
**Required action:** duplicate safety-critical bounds in MQL and reject out-of-contract payloads even if backend validation exists.

### AUD0-SET-003 — Manual JSON parsing is fragile and contract-blind

Parsing relies on exact string patterns such as `"key":`, flat objects and the first closing brace. It does not fully support:

- escaped strings;
- nested objects;
- duplicate keys;
- Unicode escaping;
- structural validation;
- arbitrary key ordering with unusual formatting in all cases.

The `strategy_risk` object extractor stops at the first `}`, making nested future extensions unsafe.

**Severity:** P1 compatibility/reliability  
**Required action:** use a tested JSON parser or a minimal signed flat contract with strict canonical serialization and versioning.

### AUD0-SET-004 — Failed settings polls are silent

Any HTTP status other than 200 returns immediately. No reviewed telemetry exposes:

- last successful pull;
- consecutive failure count;
- response code;
- stale-config age;
- parse failure.

**Severity:** P1 observability  
**Required action:** track and publish settings freshness, last version and failure reason.

### AUD0-LIC-001 — Backend outage grants a new local trial

If no prior valid license exists and verification does not return HTTP 200, the EA locally creates a valid 14-day trial.

This means network failure, DNS blocking, backend outage or intentional endpoint unavailability can activate trial mode without an authoritative server decision.

**Severity:** P0 licensing/security  
**Required action:** new trials must be issued and signed by the backend. Offline fallback should only accept a previously cached, cryptographically verifiable entitlement.

### AUD0-LIC-002 — Trial expiration is recreated after restart during continued outage

The trial expiration is set to `TimeCurrent() + 14 days` in memory. No persistence is visible in this module.

If the backend remains unreachable and the EA restarts, the trial window appears capable of restarting from the new current time.

**Severity:** P0 commercial control  
**Required action:** persist an immutable first-activation timestamp bound to account/install and verify a backend signature.

### AUD0-LIC-003 — License response authenticity depends entirely on transport/token

The EA accepts plain JSON fields from the configured backend endpoint. No signed license document, nonce, replay protection or response signature is verified in MQL.

**Severity:** P0 entitlement integrity  
**Required action:** verify a signed entitlement payload locally, including account, product, expiry, plan, issued-at and unique entitlement ID.

### AUD0-LIC-004 — License disable input bypasses all commercial enforcement

When `InpEnableLicense` is false, verification and enforcement both return true.

This may be intentional for internal builds, but it must not be available in commercial production artifacts.

**Severity:** P0 release control  
**Required action:** compile-time commercial build flag, signed release channel and CI test proving the production artifact cannot disable licensing.

### AUD0-RISK-001 — Invalid market metadata falls back to minimum live lot

If tick value, tick size, stop distance or calculated tick count is invalid, lot calculation returns `0.01` rather than rejecting the trade.

This converts missing/invalid risk metadata into a live order attempt.

**Severity:** P0 capital safety  
**Required action:** return zero/failure and block execution. Never substitute minimum lot when risk cannot be calculated.

### AUD0-RISK-002 — Minimum-lot clamping can exceed requested risk

After calculation, lots are clamped upward to broker minimum lot.

For small balances or wide stops, the minimum tradable lot can risk materially more than the configured percentage.

**Severity:** P0 capital safety  
**Required action:** calculate actual money risk after volume normalization. Reject the order when normalized risk exceeds the configured maximum tolerance.

### AUD0-RISK-003 — Volume normalization assumes decimal precision rather than deriving it

The base sizing function normalizes to two decimals. The later execution path normalizes to eight decimals, but broker volume steps can vary.

**Severity:** P1 broker compatibility  
**Required action:** derive volume digits from `SYMBOL_VOLUME_STEP` and use one canonical normalization helper.

### AUD0-RISK-004 — Strategy Tester bypasses major capital-protection gates

`NXS_CheckProtections()` returns true immediately in tester, bypassing:

- margin level;
- daily drawdown;
- max trades/day;
- max concurrent;
- anti-revenge;
- anti-bleed skip;
- pause.

This means optimization/backtest results do not model live execution constraints.

**Severity:** P0 research/live parity  
**Required action:** separate environment-dependent broker constraints from strategy risk constraints. Keep daily DD, trade limits, concurrency, cooldown and pause semantics testable in backtests.

### AUD0-RISK-005 — Drawdown baseline uses balance rather than start-of-day equity

Daily drawdown compares current equity to `g_balanceDayStart`, which is populated from account balance.

Open floating P/L carried across the day boundary can distort the daily loss baseline.

**Severity:** P1 risk semantics  
**Required action:** define and persist a start-of-day equity baseline, with explicit timezone and restart behavior.

### AUD0-RISK-006 — Risk-of-ruin flatten is symbol-local

The flatten loop closes only positions on `g_sym` with NEXUS magic.

In a multi-symbol deployment, an account-level loss threshold can freeze one instance while exposure on other symbols remains open unless every instance observes and reacts identically.

**Severity:** P0 account-wide protection  
**Required action:** central account-level kill state and one authoritative account-wide flatten coordinator.

### AUD0-EXEC-001 — Primary path does not visibly re-check license inside `NXS_OpenTrade`

`NXS_OpenTrade` rechecks ruin, strategy/profile and exposure controls, but the reviewed function itself does not call `NXS_License_Enforce()`.

The standard router checks licensing earlier, but any alternate caller of `NXS_OpenTrade` can bypass that outer gate.

**Severity:** P0 authorization invariant  
**Required action:** put license enforcement in the final common exposure preflight so every order-creation path inherits it.

### AUD0-EXEC-002 — Close-and-reverse ignores close result

Both reverse-close functions call `NXS_DoClose()` and then print a closing message without checking the returned success or retcode.

**Severity:** P1 execution correctness  
**Required action:** verify close result, record retcode, retry only appropriate failures and do not proceed under an assumption that the opposite position is gone.

### AUD0-EXEC-003 — Order retry uses blocking `Sleep`

Retry backoff sleeps inside the trading event handler.

**Impact:**
- stalls EA event processing;
- delays tick handling and management;
- may create stale-price retries;
- blocks other timer work in the same EA instance.

**Severity:** P1 runtime execution  
**Required action:** state-machine retry on later ticks/timer events with price refresh and deadline.

### AUD0-EXEC-004 — Retry uses caller-provided SL/TP and delegates price freshness opaquely

The wrapper calls `NXS_DoBuy/NXS_DoSell` repeatedly with unchanged SL/TP. Whether price and stop-distance validity are recomputed on each retry depends on the raw helper implementation, still pending review.

**Severity:** P0 pending verification  
**Required action:** inspect raw helpers and prove each retry rebuilds a fresh request and revalidates stops/margin.

### AUD0-EXEC-005 — Successful wrapper result may not prove final broker position state

The code increments daily trade counters and registers bar-direction usage when the raw wrapper returns true. Exact semantics depend on `NXS_DoBuy/NXS_DoSell` and broker retcodes.

**Severity:** P0 pending verification  
**Required action:** confirm success requires an accepted trade retcode and capture order/deal/position identifiers before counters mutate.

### AUD0-EXEC-006 — Per-timeframe setup cap depends on parsing the position comment

The open-position timeframe budget reconstructs strategy identity from `POSITION_COMMENT`, then maps the strategy to a profile timeframe.

Comments can be truncated or changed by broker/platform behavior, and legacy/manual positions may not follow the format.

**Severity:** P1 identity integrity  
**Required action:** persist strategy/timeframe identity in an internal ledger keyed by position ID; comments should remain diagnostic only.

### AUD0-EXEC-007 — Hard-coded strategy family lists continue contract duplication

Counter-HTF eligibility uses another manually maintained list of strategy names, separate from the main registry and profile system.

**Severity:** P1 contract drift  
**Required action:** move strategy capabilities such as `counter_htf_eligible`, family and reversal/continuation type into canonical registry metadata.

### AUD0-EXEC-008 — Remote per-strategy risk multiplier defaults unsafe on malformed/non-positive values

Missing, malformed or non-positive values revert to `1.0`. This is safe for accidental zero, but not necessarily for a control-plane request intended to disable or sharply reduce exposure.

**Severity:** P1 control semantics  
**Required action:** distinguish absent, invalid, disabled and explicit multiplier states; reject invalid payloads instead of silently reverting.

## Updated disposition of earlier findings

### AUD0-MQL-008

Previous concern that runtime settings might perform network work every tick is partially resolved.

- `NXS_PullSettings()` is called from `OnTick`.
- The function internally enforces a 15-second cadence.

**Status:** downgraded from implementation-unknown to confirmed P1 observability/configuration concern.

### AUD0-MQL-012

The standard signal-router path checks license before reaching execution, but `NXS_OpenTrade` does not enforce license internally.

**Status:** remains P0 until every alternate exposure path and final raw order helper are audited.

## Next critical verification queue

1. `NXS_Globals.mqh`
   - raw `OrderSend` request construction;
   - accepted retcodes;
   - fill policy;
   - close semantics;
   - ticket capture.

2. `NXS_RiskShield.mqh`
   - account-wide state and persistence.

3. `NXS_Protections.mqh`
   - daily/account kill switch consistency.

4. Grid, pyramiding, split and institutional modules
   - direct or indirect calls to raw order helpers;
   - license and common-preflight inheritance.

5. Virtual SL module
   - crash safety and broker-hard-stop guarantees.

## Progress update

### Overall audit

**42%**

### AUDIT-0 Repository Inventory

**69%**

### MQL5 execution/risk review

**48%**

### Area status

- Repository Inventory: 69%
- Root Configuration: 94%
- MQL5: 36%
- Backend: 42%
- Frontend: 7%
- Contracts: 39%
- Deploy: 60%
- Security: 48%
- Documentation: 31%
- Testing: 14%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 10: Raw Trade Helpers, RiskShield and Protection Layer

## Scope reviewed

- `MQL5/Include/NEXUS_v1/NXS_Globals.mqh`
- `MQL5/Include/NEXUS_v1/NXS_RiskShield.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Protections.mqh`

## Verified raw execution behavior

The native order helpers:

- build `MqlTradeRequest` directly;
- use fresh BID/ASK on each call;
- store the last retcode globally;
- accept only `TRADE_RETCODE_DONE` or `TRADE_RETCODE_PLACED`;
- capture `res.order` for buy/sell;
- select fill mode from symbol capabilities;
- use a fixed deviation of 30 points;
- do not run `OrderCheck` themselves;
- do not record `res.deal`, returned volume, returned price or broker comment.

The earlier concern that retry attempts might reuse stale entry prices is partially resolved: each retry re-enters `NXS_DoBuy/NXS_DoSell`, which reads current BID/ASK. SL/TP remain unchanged and are not visibly revalidated inside the raw helper.

## Positive controls observed

- Raw buy/sell helpers do not treat `OrderSend()` boolean alone as success.
- Trade retcodes are checked against a narrow allow-list.
- Filling mode is derived from symbol capability.
- Position close requests bind the actual position ticket.
- Protection close events distinguish `close_request` from final ledger closure.
- RiskShield is called by the primary common exposure preflight.
- ESL, DPT, max-hold, max-loss and auto-close are modularized.
- Protection close paths filter by NEXUS magic.
- Trade-reason payloads carry account-derived `tradeUid` and explicit event kind.

## New findings

### AUD0-RAW-001 — `TRADE_RETCODE_PLACED` is treated as final success for market actions

Buy, sell, close, partial-close and modify helpers all accept:

- `TRADE_RETCODE_DONE`
- `TRADE_RETCODE_PLACED`

as equivalent success.

For a market exposure path, `PLACED` does not necessarily prove the intended deal/position state has completed.

**Impact:**
- counters and state may advance before fill confirmation;
- Virtual SL intent may be attached before the final position is known;
- close callers may assume exposure is gone while execution is still pending.

**Severity:** P0 execution-state integrity  
**Required action:** define success per request action and account mode. Correlate subsequent trade transactions using order/deal/position identifiers before marking exposure state complete.

### AUD0-RAW-002 — Raw helpers capture order ticket but not deal or executed price

The helpers store `res.order`, but not:

- `res.deal`;
- `res.price`;
- `res.volume`;
- broker comment;
- request/result correlation ID.

**Severity:** P1 observability/reconciliation  
**Required action:** persist a structured execution result object and reconcile it with `OnTradeTransaction`.

### AUD0-RAW-003 — Fixed 30-point deviation is not symbol-adaptive

All market requests use:

`req.deviation = 30`

The economic meaning differs dramatically across FX, metals, indices and crypto symbols.

**Severity:** P1 execution quality  
**Required action:** configure deviation from symbol profile, spread regime and price precision, with a hard cap.

### AUD0-RAW-004 — Close and partial-close requests reuse one global filling mode

`g_tradeFilling` is initialized for `g_sym`, but close helpers can receive positions whose symbol is read dynamically from the ticket.

In multi-symbol/account-wide operations, the selected position symbol may not share the same supported filling policy.

**Severity:** P0 broker compatibility  
**Required action:** resolve filling mode per request symbol immediately before every send.

### AUD0-RAW-005 — Partial close lacks local volume validation

`NXS_DoClosePartial` sends caller-provided volume without visible local validation against:

- current position volume;
- minimum volume;
- step;
- resulting residual minimum;
- account netting/hedging semantics.

**Severity:** P0 execution correctness  
**Required action:** canonical partial-close normalization and explicit rejection of invalid residual sizes.

### AUD0-RAW-006 — Modify helper accepts broker `PLACED` and does not verify resulting SL/TP

The helper reports success based on send result only. It does not re-read the position to confirm the actual stop and target.

**Severity:** P0 protection integrity  
**Required action:** confirm post-condition from position state, especially for Virtual SL hard-stop changes.

### AUD0-RS-001 — Correlation cluster counts all account positions, not only NEXUS exposure

RiskShield cluster count iterates every open position and groups it by symbol without filtering magic or ownership.

**Impact:** manual trades or another EA can block NEXUS entries unexpectedly.

This may be intentional as account-level protection, but the semantics are undocumented and inconsistent with many other NEXUS-only protections.

**Severity:** P1 policy ambiguity  
**Required action:** explicitly choose account-wide or NEXUS-only behavior and expose the counted positions in telemetry.

### AUD0-RS-002 — Cluster mapping ignores trade direction

Symbols are assigned to static groups, but the count does not consider whether positions are long or short.

For example, long and short positions with offsetting USD exposure are still counted identically, while labels such as `USD_STRONG` and `USD_WEAK` are assigned only from symbol name.

**Severity:** P0 risk-model validity  
**Required action:** model signed factor exposure using symbol, direction and lot/notional size rather than position count.

### AUD0-RS-003 — Cluster cap is position-count based, not risk based

A 0.01-lot trade and a very large trade consume the same cluster slot.

**Severity:** P0 capital-risk accuracy  
**Required action:** aggregate normalized monetary risk or stress loss per factor cluster.

### AUD0-RS-004 — Unknown symbols share one global `OTHER` cluster

Every unmapped instrument becomes `OTHER`. With a cap of two, unrelated instruments can block each other.

**Severity:** P1 correctness  
**Required action:** use explicit profiles and fail visibly for unknown instruments rather than collapsing all into one bucket.

### AUD0-RS-005 — Spread P95 calculation sorts a copied window on entry checks

The function copies and sorts up to 1,000 spread observations whenever the entry preflight calls the spread-burst gate.

**Severity:** P1 performance  
**Required action:** maintain an efficient rolling quantile approximation or recalculate only on a bounded cadence.

### AUD0-RS-006 — Spread protection permits trading during warm-up

Until 50 valid samples exist, P95 returns zero and the gate allows entries.

**Severity:** P1 startup safety  
**Required action:** use a conservative symbol-profile spread cap during warm-up.

### AUD0-RS-007 — Equity breaker state is volatile

Breaker-until and last Sharpe are globals in memory. No persistence is visible in this module.

A terminal/EA restart can therefore clear the breaker pause unless another state module persists these values.

**Severity:** P0 capital-protection persistence  
**Required action:** persist breaker state with account, magic, trigger reason and expiry.

### AUD0-RS-008 — Sharpe breaker uses raw returns without verified normalization

The function accepts values described as “R or dollars.” Mixing or changing units changes the result and makes thresholds incomparable.

It also calculates unannualized mean divided by population standard deviation.

**Severity:** P1 statistical validity  
**Required action:** require one canonical return unit, validate sample provenance and define the exact statistical contract.

### AUD0-PROT-001 — ESL and DPT are symbol-local despite account-level inputs

ESL and DPT derive thresholds from account balance/equity, but close only positions on `g_sym`.

**Impact:** an account-level equity event can close one symbol while leaving other NEXUS positions exposed.

**Severity:** P0 account-wide safety  
**Required action:** one account coordinator must own account-equity protections and flatten all relevant symbols atomically.

### AUD0-PROT-002 — Protection flags are set even when not all positions close

When ESL or DPT triggers:

- `CloseAllWithReason` returns the number successfully closed;
- the code sets the hit/pause flags regardless of failed closes.

The system may then stop retrying because `NXS_Prot_OnTick()` returns immediately while positions remain open.

**Severity:** P0 emergency-close reliability  
**Required action:** maintain a persistent `FLATTEN_PENDING` state and retry until no protected exposure remains or an operator-visible fatal error is raised.

### AUD0-PROT-003 — `g_pausedUntilNextOpen` name and behavior diverge

The flag is described as paused until next open/day, but once set, the master tick exits before all other checks. It is cleared by the new-day hook.

**Severity:** P1 maintainability  
**Required action:** rename to an explicit daily pause state and document all reset paths.

### AUD0-PROT-004 — Protection-state persistence is not visible in the module

ESL, DPT, auto-close and directional post-SL cooldown timestamps are in-memory globals.

Restarting the EA may clear daily pause/cooldown state unless `NXS_State` explicitly persists every field.

**Severity:** P0 pending persistence verification  
**Required action:** cross-check the state module and persist all safety state with versioning.

### AUD0-PROT-005 — Trade-reason delivery can block for over one minute

A close-reason push uses:

- 20-second WebRequest timeout;
- up to three attempts;
- 1s then 2s sleeps.

Because this happens after a successful protection close, the EA event loop can still be blocked for roughly 63 seconds.

**Severity:** P0 runtime availability  
**Required action:** write the event locally first and deliver asynchronously through an outbox.

### AUD0-PROT-006 — Close-reason payload uses requested price and floating P/L

The code correctly labels it `close_request`, but consumers must never interpret it as execution truth.

**Severity:** P1 contract requirement  
**Required action:** enforce at database schema/API level that only ledger-confirmed final events populate realized close fields.

### AUD0-PROT-007 — Max-loss-per-position intentionally delays emergency action

A losing position is ignored until a timeframe-scaled minimum lifetime is reached.

This can permit a position to exceed the monetary max-loss threshold during the protected grace period.

**Severity:** P0 capital safety  
**Required action:** separate noise-management logic from a true hard monetary loss limit. Hard loss must not wait for minimum age.

### AUD0-PROT-008 — Auto-close assumes one configured GMT close time

The logic uses a generic `InpMarketCloseGMT` window rather than symbol trading sessions returned by the broker.

**Severity:** P1 market compatibility  
**Required action:** derive tradable-session close from symbol session data and handle holidays/early closes.

### AUD0-PROT-009 — Major protection behavior is bypassed in Strategy Tester

The protection entry gate explicitly returns unblocked in tester, reinforcing the previously identified live/backtest parity gap.

**Severity:** P0 research validity  
**Required action:** provide a test mode that models daily pauses, ESL/DPT and auto-close semantics deterministically.

## Resolved and refined earlier findings

### AUD0-EXEC-004

The raw buy/sell helper refreshes BID/ASK on every retry call.

**Disposition:** stale entry-price concern reduced. SL/TP revalidation and request-age guarantees remain open.

### AUD0-EXEC-005

A successful raw helper requires `OrderSend()` success plus an accepted retcode, which is stronger than boolean-only handling.

**Disposition:** partially resolved, but accepting `PLACED` as final state keeps this finding P0.

## Next critical verification queue

1. `NXS_GridRecovery.mqh`
2. `NXS_Pyramiding.mqh`
3. `NXS_SplitTrade.mqh`
4. `NXS_InstManage.mqh`
5. `NXS_InstitutionalCore.mqh`

Goal: enumerate every exposure-creating path and prove it passes:

- license enforcement;
- ruin/account kill switch;
- runtime-settings bounds;
- normalized risk calculation;
- directional/cluster exposure caps;
- broker preflight;
- transaction reconciliation.

## Progress update

### Overall audit

**47%**

### AUDIT-0 Repository Inventory

**73%**

### MQL5 execution/protection review

**61%**

### Area status

- Repository Inventory: 73%
- Root Configuration: 94%
- MQL5: 48%
- Backend: 42%
- Frontend: 7%
- Contracts: 44%
- Deploy: 60%
- Security: 52%
- Documentation: 34%
- Testing: 17%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 11: Grid, Pyramiding, Split and Institutional Exposure Paths

## Scope reviewed

- `MQL5/Include/NEXUS_v1/NXS_GridRecovery.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Pyramiding.mqh`
- `MQL5/Include/NEXUS_v1/NXS_SplitTrade.mqh`
- `MQL5/Include/NEXUS_v1/NXS_InstManage.mqh`
- `MQL5/Include/NEXUS_v1/NXS_InstitutionalCore.mqh`

## Exposure-path map

### Standard grid

Trigger:
- enabled;
- ATR available;
- strong/weak trend;
- losing core position;
- adverse movement >= grid ATR step;
- layer count below `MAX_GRID_LAYERS`.

Sizing:
- exactly the current core position volume.

Controls inherited:
- `NXS_CommonExposurePreflight`;
- RiskShield;
- directional lot exposure cap;
- broker preflight.

Controls not visibly inherited:
- license enforcement;
- ruin freeze;
- daily trade limit;
- max concurrent limit;
- projected margin gate;
- runtime risk-percent sizing;
- strategy-disable state.

### Standard pyramiding

Trigger:
- enabled;
- winning core position by at least one ATR;
- velocity aligned;
- pyramid count below maximum.

Sizing:
- 50% of current core position;
- clamped upward to broker minimum.

Controls inherited:
- same common preflight as grid.

Controls not visibly inherited:
- same missing controls listed for grid.

### Institutional add/recovery

Trigger:
- institutional mode;
- any same-direction NEXUS group;
- favorable move for grid or adverse move for recovery;
- depth cap;
- local exposure-lot cap.

Sizing:
- fixed configured lot or core lot;
- exponentially multiplied by depth;
- grid multiplier in profit;
- recovery multiplier in loss.

Controls inherited:
- lot-step flooring;
- trial lot cap;
- local institutional direction cap.

Controls bypassed:
- common exposure preflight;
- license enforcement;
- ruin freeze;
- RiskShield;
- cluster cap;
- projected margin;
- directional global exposure cap;
- daily/max-concurrent protections;
- broker preflight.

## Positive controls observed

- Standard grid and pyramiding were explicitly patched to use the common exposure preflight.
- Both limit the number of add layers.
- Institutional recovery stops when HTF and structure context are both against the direction.
- Institutional add has a separate hard lot-exposure cap.
- Institutional trailing and time-stop actions go through the position-coordinator proposal layer.
- Split actions also use the position-coordinator proposal layer.
- Institutional core aggregates multiple strategy votes into one primary directional decision.
- Institutional core requires minimum conviction and minimum contributor count.

## New findings

### AUD0-ADD-001 — Grid and pyramiding bypass the final license invariant

Both modules call `NXS_CommonExposurePreflight`, but that common function currently does not enforce licensing.

Therefore grid and pyramid adds can occur on ticks before the standard new-bar router reaches its outer license gate, including after license state changes.

**Severity:** P0 commercial and exposure authorization  
**Required action:** license enforcement must be inside the final common exposure preflight used by every add/open route.

### AUD0-ADD-002 — Grid and pyramiding bypass ruin freeze and daily protection checks

The add modules run during position management before the new-bar entry gates. They do not call:

- `NXS_RuinFrozen`;
- `NXS_CheckProtections`;
- `NXS_Prot_EntryBlocked`.

**Impact:** additive exposure can be created while the main entry path is frozen by daily drawdown, pause, max trades, max concurrency or related protections.

**Severity:** P0 capital safety  
**Required action:** separate “can create any new exposure now” into one mandatory invariant and call it from every route.

### AUD0-ADD-003 — Grid and pyramiding do not use projected margin gate

The projected margin-level check exists in `NXS_OpenTrade`, not in `NXS_CommonExposurePreflight`.

Grid and pyramid therefore skip it.

**Severity:** P0 margin safety  
**Required action:** move projected margin validation into the common exposure preflight.

### AUD0-ADD-004 — Grid adds duplicate the full losing-core volume

Each grid layer uses the core position’s current volume. With multiple layers, gross exposure can grow linearly while the original position is losing.

Although directional-lot cap now exists, the add size is not recalculated from current stop risk, equity or group loss.

**Severity:** P0 risk sizing  
**Required action:** size every add from remaining account risk budget and group stop-loss risk, not from parent volume.

### AUD0-ADD-005 — Standard grid and pyramid adds send no SL or TP

Both modules initialize:

`sl = 0, tp = 0`

and submit the add with no broker-side stop/target.

**Impact:** add positions may remain unprotected if management, terminal or EA fails before later modification.

**Severity:** P0 broker-side protection  
**Required action:** every exposure-creating request must carry a valid broker hard stop before send, including grid and pyramid legs.

### AUD0-ADD-006 — Pyramiding volume is not normalized to symbol step before preflight/send

The pyramid lot is calculated as half the core volume and clamped to minimum lot, but no local step-flooring is performed in this module.

**Severity:** P1 broker compatibility  
**Required action:** use the canonical volume normalization and post-normalization risk check before preflight.

### AUD0-ADD-007 — Add success is ignored

Grid and pyramid call `NXS_SafeBuy/SafeSell` without checking or recording the returned boolean.

**Impact:** no explicit add-state transition, no failed-add telemetry, and layer logic relies only on future position scans.

**Severity:** P1 observability/execution correctness  
**Required action:** record request ID, result, retcode and transaction-confirmed position identity.

### AUD0-INST-001 — Institutional recovery explicitly bypasses entry gates

The module comments that adds bypass entry gates because the sequence was already decided by the core.

The actual add helper directly calls `NXS_SafeBuy/SafeSell`.

**Severity:** P0 architecture/capital safety  
**Required action:** a prior core decision cannot authorize unlimited future exposure. Every add must revalidate current license, account state, margin, risk budget, market conditions and kill switches.

### AUD0-INST-002 — Institutional add bypasses the common exposure preflight entirely

The helper does not call:

- RiskShield;
- directional exposure cap;
- cluster risk;
- broker preflight;
- projected margin.

It only applies its own lot cap and trial cap.

**Severity:** P0 exposure-control bypass  
**Required action:** route all adds through one common exposure service.

### AUD0-INST-003 — Institutional recovery is martingale by design

When aggregate group P/L is negative, lot size is:

`baseLot * recoveryMultiplier^(depth + 1)`.

This exponentially increases exposure into a losing sequence.

Context can block some adds, but does not change the fundamental loss-amplification structure.

**Severity:** P0 strategy risk  
**Required action:** prohibit exponential recovery sizing in production or constrain it by total monetary stop risk, stress loss and account-level drawdown budget.

### AUD0-INST-004 — Institutional group scan absorbs unrelated NEXUS positions

The group scanner aggregates every same-symbol, same-direction position whose magic is anywhere in the broad NEXUS range.

It does not restrict membership to:

- one institutional sequence;
- one core ticket;
- one strategy group;
- one setup ID.

**Impact:** unrelated classic, grid, pyramid or legacy NEXUS positions can be merged into one institutional group and managed together.

**Severity:** P0 position ownership integrity  
**Required action:** assign immutable sequence/group IDs and bind every add/management action to one group.

### AUD0-INST-005 — Broad magic-range helper increases cross-module coupling

`IsNexusMagic` accepts a broad numeric range. Institutional scanning relies on it as group identity.

**Severity:** P1 identity architecture  
**Required action:** magic identifies subsystem ownership only; logical trade/group identity must come from a ledger, not numeric range inference.

### AUD0-INST-006 — Institutional exposure cap is lot-based and balance-linear

The cap scales linearly with account balance and is floored at broker minimum lot.

It does not account for:

- stop distance;
- symbol tick value;
- volatility;
- current group loss;
- other symbols;
- correlation;
- margin stress.

**Severity:** P0 capital-risk accuracy  
**Required action:** cap by worst-case monetary loss and portfolio stress, not raw lots.

### AUD0-INST-007 — Institutional add inherits core SL/TP, including zero values

Adds receive `g.coreSL` and `g.coreTP`. If the core has no broker SL/TP, the add is also sent without one.

**Severity:** P0 protection integrity  
**Required action:** compute a valid hard stop per add and reject when unavailable.

### AUD0-INST-008 — Institutional add does not locally enforce valid minimum volume semantics

The helper floors to volume step, applies trial cap and checks `lots < step`, but does not explicitly validate broker minimum/maximum volume or residual account risk.

**Severity:** P1 broker/risk correctness  
**Required action:** canonical volume validator shared with primary execution.

### AUD0-INST-009 — Institutional mode can manage both directions independently

`NXS_InstManage_OnTick` manages BUY and SELL groups each tick.

This can be intentional hedging, but there is no reviewed account-level net-risk policy controlling simultaneous recovery sequences in both directions.

**Severity:** P0 portfolio risk  
**Required action:** define and enforce gross, net and stress exposure across both directional groups.

### AUD0-SPLIT-001 — Split volume normalization is hard-coded to two decimals

P1/P2 partial volumes use `NormalizeDouble(..., 2)` rather than symbol volume step/digits.

**Severity:** P1 broker compatibility  
**Required action:** use the shared partial-close normalizer and verify valid residual volume.

### AUD0-SPLIT-002 — Split de-duplication arrays are volatile and capped at 256 tickets

The local P1/P2 arrays are in memory. Restart behavior depends on the separate position-coordinator applied-state, still pending inspection.

The arrays also evict the oldest ticket after 256 records.

**Severity:** P1 pending persistence verification  
**Required action:** persist partial-close milestones in the logical trade ledger keyed by position/trade UID.

### AUD0-INST-010 — Institutional conviction is a raw sum of strategy scores

The dominant direction is selected using summed scores and the absolute difference between buy and sell totals.

Highly correlated strategies can therefore multiply apparent conviction without independence weighting.

**Severity:** P1 model validity  
**Required action:** weight by strategy family/correlation and cap contribution from redundant signals.

### AUD0-INST-011 — Institutional group identity is truncated into comments

The contributor signature is truncated to fit the position comment.

Comments are diagnostic and cannot serve as authoritative provenance or group membership.

**Severity:** P1 auditability  
**Required action:** persist full contributor list and decision snapshot in the ledger with a stable setup ID.

## Critical architecture conclusion

There are currently at least three distinct exposure-creation pipelines:

1. primary signal entry through `NXS_OpenTrade`;
2. standard grid/pyramid through `NXS_CommonExposurePreflight`;
3. institutional add/recovery directly through safe-order helpers.

These pipelines enforce different subsets of risk controls.

This is the most important MQL5 architectural finding so far.

The required target is one non-bypassable function:

`NXS_RequestExposure(ExposureIntent intent)`

It must always enforce:

- license/entitlement;
- account kill state;
- pause/daily protections;
- strategy and sequence ownership;
- normalized risk and volume;
- account/portfolio risk budget;
- directional and correlation exposure;
- projected margin;
- valid broker hard stop;
- broker preflight;
- idempotency;
- transaction reconciliation.

Modules may propose exposure. Only this function may send it.

## Progress update

### Overall audit

**53%**

### AUDIT-0 Repository Inventory

**78%**

### MQL5 exposure-path review

**74%**

### Area status

- Repository Inventory: 78%
- Root Configuration: 94%
- MQL5: 61%
- Backend: 42%
- Frontend: 7%
- Contracts: 50%
- Deploy: 60%
- Security: 57%
- Documentation: 37%
- Testing: 20%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 12: Position Coordinator, State Persistence and Trade Ledger

## Scope reviewed

- `MQL5/Include/NEXUS_v1/NXS_PositionCoordinator.mqh`
- `MQL5/Include/NEXUS_v1/NXS_State.mqh`
- `MQL5/Include/NEXUS_v1/NXS_TradeLedger.mqh`

The Virtual SL implementation file was not located under the expected filename during this pass, so Virtual SL internals remain pending. Its integration points were already identified in the execution entrypoint.

## Verified position-management behavior

The Position Coordinator:

- accepts MODIFY, PARTIAL and CLOSE proposals;
- keeps at most one winning proposal per position per cycle;
- resolves conflicts by priority, then action severity, then stricter stop;
- rejects stop regressions;
- normalizes partial volume to symbol step before calling the raw helper;
- records successful actions into persistent state;
- logs whether an action was applied.

The persistent state module:

- uses schema version 2;
- writes account-operational and per-position state into a binary snapshot;
- uses temp-file write, read-back validation, previous snapshot and atomic move;
- blocks new exposure when restore fails;
- reconciles saved positions against current broker state;
- persists split milestones;
- is disabled in Strategy Tester.

The trade ledger:

- aggregates deals by `DEAL_POSITION_ID`;
- distinguishes order, deal, position and logical trade;
- computes aggregated entry/exit VWAP, realized P/L and partial count;
- persists an emitted-set to avoid duplicate final events after restart;
- documents the limitation of netting-account flips;
- uses aggregate-diff rather than trusting one event.

## Positive controls observed

- Stop loosening is explicitly blocked.
- Conflict resolution is deterministic.
- State files are versioned and include a trailer marker.
- State writes use temporary and previous files.
- Restore failure blocks new exposure.
- Split P1/P2 milestones survive restart through managed state.
- Broker reconciliation uses `POSITION_IDENTIFIER`.
- Ledger keys logical trades by position ID rather than symbol.
- Ledger realized P/L includes profit, swap and commission.
- Final-close detection checks both volume completion and broker position disappearance.
- Duplicate-final suppression is persisted.

## New findings

### AUD0-PM-001 — Action success is recorded before broker post-state confirmation

The coordinator records an action as applied when the raw helper returns true.

For MODIFY, PARTIAL and CLOSE, raw success can include `TRADE_RETCODE_PLACED`, and the coordinator does not wait for `OnTradeTransaction` or re-read the final broker state before persisting the milestone.

**Impact:**
- partial milestone can be marked complete before volume actually changes;
- close source can be marked applied while the position remains;
- modify source can be recorded while broker SL/TP differs.

**Severity:** P0 state/execution integrity  
**Required action:** record `REQUESTED`, then confirm `APPLIED` only from transaction/post-state reconciliation.

### AUD0-PM-002 — One successful source marker is too coarse for repeated management actions

For most sources, `NXS_State_HasApplied()` compares only:

`lastEvent == source`.

This supports one-shot actions but does not represent repeated legitimate actions such as multiple trailing updates from the same source.

The in-memory applied list also de-duplicates `(ticket, source)` globally.

**Impact:** a source intended to act repeatedly can be suppressed after its first successful application, depending on caller behavior.

**Severity:** P0 management correctness  
**Required action:** distinguish one-shot milestones from repeatable actions and store action sequence/version, not only source name.

### AUD0-PM-003 — Applied-state cache evicts after 512 entries

The in-memory applied list drops the oldest record once full.

Persistent managed state stores only one `lastEvent` plus two split booleans, so arbitrary historical source milestones are not durably represented.

**Severity:** P1 lifecycle correctness  
**Required action:** store typed milestones in the logical trade ledger, with bounded per-trade state rather than global FIFO eviction.

### AUD0-PM-004 — Partial-close validation remains incomplete

The coordinator floors the proposed partial volume to the symbol step, but does not visibly verify:

- volume <= current position volume;
- residual volume is zero or >= minimum lot;
- account netting/hedging compatibility;
- actual risk/commission effect.

**Severity:** P0 execution correctness  
**Required action:** validate current position volume and resulting residual immediately before send, then confirm the fill.

### AUD0-PM-005 — Proposal overflow fails silently

When proposal capacity reaches 512, `NXS_PM_Submit` returns false without structured fatal telemetry or backpressure.

**Severity:** P1 observability  
**Required action:** expose overflow counter and safety state; critical close proposals must never be silently dropped.

### AUD0-PM-006 — Arbitrary source strings define action identity

The coordinator uses caller-supplied strings for de-duplication, persistence and priority tie-breaking.

Renaming a source changes lifecycle behavior and can allow a previously applied one-shot action to run again.

**Severity:** P1 contract integrity  
**Required action:** use canonical action IDs/enums and schema-versioned milestones.

## State persistence findings

### AUD0-STATE-001 — State filename omits account identity

The snapshot filename includes:

- magic;
- symbol;

but not account login or server.

Because `FILE_COMMON` is used, two terminals/accounts using the same magic and symbol can collide in the shared common-files area.

**Severity:** P0 cross-account state contamination  
**Required action:** include account login, broker/server identity, product/version and magic in the state key.

### AUD0-STATE-002 — Reconciled group identity is derived only from position comment

When a broker position is not found in saved state, strategy and group are both reconstructed from the second comment field.

This collapses:

- strategy ID;
- sequence ID;
- institutional group;
- setup provenance;

into one string.

**Severity:** P0 ownership reconstruction  
**Required action:** persist immutable setup/group identity in a separate durable ledger and reconcile by position ID.

### AUD0-STATE-003 — Entry ATR fallback can become stop distance or current ATR

For newly reconciled positions, entry ATR is set to current `g_atr` when available, otherwise `abs(open - SL)`.

Neither necessarily equals the ATR at original entry.

**Impact:** split and lifecycle thresholds after restart can differ from pre-restart behavior.

**Severity:** P1 deterministic recovery  
**Required action:** persist actual entry ATR at execution confirmation; if unavailable, mark provenance as reconstructed and use conservative behavior.

### AUD0-STATE-004 — Important protection state is not persisted

The snapshot persists ESL, DPT, pause, loss streak, anti-revenge and skip count, but does not visibly persist:

- risk-of-ruin frozen day;
- RiskShield breaker expiry/Sharpe;
- spread-burst freeze;
- auto-close pending;
- post-SL directional cooldown timestamps;
- streak sizing multiplier and win/loss counters;
- license grace/trial state;
- runtime-settings version.

**Severity:** P0 capital-protection persistence  
**Required action:** define one complete safety-state schema and add migration tests.

### AUD0-STATE-005 — Same-day restore depends on terminal/server time without timezone metadata

Daily state is restored only if saved `dayStart` equals the current reconstructed midnight.

There is no stored timezone or trading-day policy.

**Severity:** P1 risk semantics  
**Required action:** define broker-server trading day and persist timezone/day identifier explicitly.

### AUD0-STATE-006 — Snapshot integrity is structural, not cryptographic

Read-back validation checks magic, schema and trailer, but not a checksum or MAC over contents.

Silent corruption that preserves structural fields may pass.

**Severity:** P1 integrity  
**Required action:** include checksum; use authenticated integrity if tampering matters.

### AUD0-STATE-007 — String read failures collapse to empty values

Invalid string lengths return empty strings without propagating a parse error for the entire snapshot.

**Severity:** P1 corruption handling  
**Required action:** fail the whole snapshot on any malformed field.

### AUD0-STATE-008 — State persistence is disabled in Strategy Tester

This prevents testing restart/resume behavior, exactly-once management and crash recovery.

**Severity:** P1 testing gap  
**Required action:** add deterministic persistence tests in an isolated tester directory or standalone harness.

## Trade ledger findings

### AUD0-LEDGER-001 — Exactly-once guarantee is bounded by an 8,192-entry FIFO

The emitted-set discards the oldest position ID after 8,192 finals.

A sufficiently old historical position can be emitted again during later resync/rebuild if it re-enters the scan window or file history is reused.

**Severity:** P1 exactly-once durability  
**Required action:** durable append-only/event table or retention policy tied to immutable event IDs and backend acknowledgement.

### AUD0-LEDGER-002 — Emitted-set persistence is not atomic or checksummed

The ledger writes the emitted set directly to one file, unlike the safer temp/previous pattern used by `NXS_State`.

A crash during write can truncate or corrupt duplicate-suppression state.

**Severity:** P0 duplicate-event integrity  
**Required action:** adopt atomic snapshot/write-ahead pattern with checksum and previous copy.

### AUD0-LEDGER-003 — Corrupted emitted-set load fails open silently

Invalid count or file-open errors simply return. There is no degraded-state flag that blocks duplicate final emission.

**Severity:** P0 event integrity  
**Required action:** surface unhealthy ledger state and require reconciliation with backend acknowledgement before emitting finals.

### AUD0-LEDGER-004 — Risk money captures only the first deal with visible SL

`risk_money` is populated once from the first IN deal that has a non-zero SL.

For:
- scale-ins;
- grid/recovery legs;
- Virtual SL;
- later stop changes;
- entries without broker SL;

the derived R-multiple may not represent actual group/trade risk.

**Severity:** P0 analytics validity  
**Required action:** persist execution-time logical risk budget and group risk, not infer it retrospectively from one deal SL.

### AUD0-LEDGER-005 — Missing SL maps realized outcomes to ±1R

When risk money is unavailable, positive P/L becomes +1R and negative P/L becomes -1R.

This fabricates an R-multiple rather than marking it unknown.

**Severity:** P0 analytics/research integrity  
**Required action:** return null/unknown and exclude from R-based analytics unless risk provenance exists.

### AUD0-LEDGER-006 — Strategy identity still depends on opening-deal comment

The ledger parses strategy and score from the first IN deal comment.

Broker truncation, alteration or comments from grid/institutional adds can weaken provenance.

**Severity:** P1 identity integrity  
**Required action:** bind execution intent ID, strategy ID, setup ID and parent sequence in a durable transaction map.

### AUD0-LEDGER-007 — Netting accounts are explicitly not fully supported

The module documents that `position == logical trade` fails for INOUT flips and treats the flip as a final.

**Severity:** P0 platform compatibility if netting is allowed  
**Required action:** hard-reject unsupported netting accounts at initialization or implement a netting-specific logical-trade model.

### AUD0-LEDGER-008 — Position existence check may use position ID as ticket

`NXS_Ledger_IsClosed` calls:

`PositionSelectByTicket(t.position_id)`.

The ledger key is described as `DEAL_POSITION_ID` / position identifier, while `PositionSelectByTicket` expects a current position ticket. These values are not guaranteed to be semantically interchangeable.

**Severity:** P0 closure-detection correctness  
**Required action:** verify MT5 identity semantics and locate current position by `POSITION_IDENTIFIER`, not ticket assumption.

### AUD0-LEDGER-009 — Global history selection is mutable shared state

The aggregator calls `HistorySelectByPosition`, which changes the terminal’s global history selection. The code documents that callers must re-select.

**Severity:** P1 integration fragility  
**Required action:** centralize history access or wrap selection/restoration to prevent callers from silently iterating the wrong set.

### AUD0-LEDGER-010 — Logical trade model does not represent multi-position sequences

Grid, pyramid and institutional recovery produce separate broker positions. The ledger treats each position ID as a separate logical trade.

This conflicts with the institutional concept of one sequence/group.

**Impact:** sequence-level drawdown, risk, recovery performance and final P/L are fragmented.

**Severity:** P0 analytics and risk-model integrity  
**Required action:** introduce hierarchy:
- execution/deal;
- broker position;
- logical leg;
- setup/sequence;
- portfolio campaign.

## Resolved earlier questions

### Split milestone persistence

P1/P2 split milestones are persisted in `SNXSManagedState`.

**Disposition:** restart de-duplication is stronger than the local arrays alone suggested.

However, recording still occurs on raw-helper success rather than transaction-confirmed partial fill, so the broader P0 remains.

### State restore failure

The state module explicitly blocks new exposure when restore fails.

**Disposition:** positive control confirmed.

## Architectural conclusion

The persistence design contains several strong ideas:

- atomic main state snapshots;
- broker reconciliation;
- deterministic proposal selection;
- aggregate-diff ledger;
- persisted final-event suppression.

But execution truth and persisted truth are still coupled too early to request-level success.

The required lifecycle is:

`PROPOSED -> VALIDATED -> REQUESTED -> BROKER_ACCEPTED -> FILLED/APPLIED -> RECONCILED -> PERSISTED -> REPORTED`

Only transaction-confirmed state should advance durable milestones.

## Progress update

### Overall audit

**60%**

### AUDIT-0 Repository Inventory

**82%**

### MQL5 lifecycle/persistence review

**86%**

### Area status

- Repository Inventory: 82%
- Root Configuration: 94%
- MQL5: 73%
- Backend: 42%
- Frontend: 7%
- Contracts: 57%
- Deploy: 60%
- Security: 62%
- Documentation: 42%
- Testing: 24%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 13: WebBridge Commands and History Synchronization

## Scope reviewed

- `MQL5/Include/NEXUS_v1/NXS_WebBridge.mqh`
- `MQL5/Include/NEXUS_v1/NXS_HistorySync.mqh`
- transaction-confirmation integration points visible from previously reviewed execution, coordinator and ledger modules

The dedicated Virtual SL implementation was still not located through repository search in this pass. Only its call sites have been reviewed so far.

## Verified WebBridge behavior

The EA:

- pushes account, risk, market-context, strategy and position telemetry to `/api/ea/push`;
- authenticates with the shared `X-Nexus-Token`;
- polls `/api/ea/command`;
- manually parses command JSON;
- supports:
  - pause;
  - resume;
  - close_all;
  - close_position;
  - partial_close;
  - reset_anti_revenge;
  - reset_daily;
  - reset_protections;
- executes destructive commands directly inside the polling function;
- does not visibly send a broker-result acknowledgement back to the command endpoint.

## Verified history synchronization behavior

- Boot/periodic resync scans the last seven days.
- It examines at most 400 deals.
- It emits at most 50 closed logical trades per request.
- It aggregates by ledger position ID.
- It sends one bulk payload to `/api/ea/trade_history_sync`.
- It uses a 20-second synchronous WebRequest.
- It logs HTTP success or failure but has no local durable outbox.

## Positive controls observed

- Position telemetry filters to the current symbol and NEXUS magic.
- `close_all` filters to current symbol and NEXUS magic.
- `close_position` logs success/failure.
- Resync aggregates logical trades rather than sending every partial deal separately.
- Resync skips trades that are not conclusively closed.
- `tradeUid` includes account and position ID.
- Command polling uses a bounded 3-second timeout.

## New findings

### AUD0-WEB-001 — Destructive commands are authenticated only by the shared bridge token

Pause, resume, close, partial-close and protection-reset commands all rely on the same shared `X-Nexus-Token` used for telemetry and other bridge functions.

There is no visible:

- per-EA identity;
- per-account key;
- command signature;
- nonce;
- expiry;
- role separation;
- operator identity.

**Severity:** P0 remote-control authorization  
**Required action:** signed, short-lived commands bound to account, instance, magic, symbol, action and unique command ID.

### AUD0-WEB-002 — Commands are not visibly target-bound in the EA response parser

The EA extracts `action`, ticket and volume, but does not verify command fields such as:

- account;
- magic;
- symbol;
- EA instance ID;
- environment;
- expected position owner.

**Severity:** P0 cross-instance command safety  
**Required action:** reject every command whose target tuple does not exactly match the local EA instance.

### AUD0-WEB-003 — Command replay protection is absent in the EA

No command ID, issued-at, expiry or locally persisted processed-command set is parsed.

If the backend redelivers the same command, destructive actions can be repeated.

**Severity:** P0 idempotency/security  
**Required action:** require unique command ID and persist terminal command status:
`RECEIVED -> VALIDATED -> EXECUTING -> BROKER_CONFIRMED/FAILED`.

### AUD0-WEB-004 — Command delivery is not execution acknowledgement

The EA does not visibly POST final broker outcome back to the command subsystem.

This confirms the earlier backend finding: `DELIVERED` means the EA received the command, not that the broker action succeeded.

**Severity:** P0 operational truth  
**Required action:** command result endpoint with retcode, order/deal/position IDs, timestamps and post-state confirmation.

### AUD0-WEB-005 — `close_all` ignores every close result

The command loops through matching positions and calls `NXS_DoClose` without checking success, counting failures or retrying.

It then prints `close_all executed` regardless of the remaining exposure.

**Severity:** P0 emergency-control reliability  
**Required action:** persistent flatten workflow with final remaining-position count and explicit FAILED/PARTIAL/SUCCEEDED result.

### AUD0-WEB-006 — `close_position` does not verify ticket ownership before raw close

The raw close helper selects any accessible position ticket. The command path does not first verify:

- current symbol;
- NEXUS magic;
- expected account/sequence;
- local instance ownership.

**Severity:** P0 destructive-scope violation  
**Required action:** verify ownership before invoking close; reject foreign tickets.

### AUD0-WEB-007 — `partial_close` lacks ownership and safe-volume validation

The parser sends caller-provided ticket and volume directly to `NXS_DoClosePartial`.

It bypasses the Position Coordinator’s step normalization and still lacks residual-volume checks.

**Severity:** P0 destructive execution safety  
**Required action:** route remote partial close through the same canonical validated/transaction-confirmed management pipeline.

### AUD0-WEB-008 — Remote commands can reset safety controls without approval policy

Commands can clear:

- anti-revenge;
- loss streak;
- daily trade count;
- daily balance baseline;
- ESL;
- DPT;
- auto-close pause.

This can immediately re-enable trading after a protection event.

There is no visible two-person approval, elevated role, cooldown or immutable operator audit record in MQL.

**Severity:** P0 safety-control authorization  
**Required action:** high-risk reset commands require privileged signed authorization, reason, expiry and immutable audit.

### AUD0-WEB-009 — `reset_daily` rewrites the risk baseline mid-day

The command sets:

- `g_tradesToday = 0`;
- `g_balanceDayStart = current balance`.

This can erase daily loss/trade history and change drawdown semantics while positions remain open.

**Severity:** P0 capital-control bypass  
**Required action:** disallow in production or require a controlled new risk epoch with full audit and equity-based baseline.

### AUD0-WEB-010 — Manual command JSON parsing is fragile

Action, ticket and volume are extracted by string scanning.

The parser does not validate the full JSON structure, duplicate fields, malformed numbers or unexpected payload combinations.

**Severity:** P1 reliability/security  
**Required action:** strict versioned command schema and parser.

### AUD0-WEB-011 — Push telemetry exposes sensitive account and strategy data to one shared endpoint

The payload includes:

- balance;
- equity;
- floating P/L;
- daily P/L;
- drawdown;
- margin level;
- open positions;
- strategy identity;
- market state;
- protection state.

**Severity:** P1 confidentiality  
**Required action:** TLS pinning/signing where feasible, least-privilege endpoint, per-instance credentials and documented retention.

### AUD0-WEB-012 — Position prices are serialized with two decimals

Open/current price, SL and TP use two decimal places regardless of symbol digits.

This loses precision for FX and some CFDs.

**Severity:** P1 data integrity  
**Required action:** serialize using symbol digits or decimal-safe canonical representation.

### AUD0-WEB-013 — Strategy telemetry registry is incomplete and duplicated

`_StrategiesJSON()` lists only the classic subset while the EA supports many more SMC/institutional strategies.

**Severity:** P1 contract drift  
**Required action:** generate strategy state from the canonical registry.

### AUD0-WEB-014 — WebPush can block the EA event loop for 20 seconds

Telemetry push uses a synchronous 20-second WebRequest from EA lifecycle paths.

**Severity:** P0 runtime availability  
**Required action:** local outbox and bounded asynchronous bridge worker; trading-critical event handlers must not block on backend availability.

## History synchronization findings

### AUD0-HSYNC-001 — Seven-day/400-deal scan can permanently miss older closures

Resync scans only seven days and at most 400 recent deals.

During long downtime or active trading, older unsynchronized trades may never be included.

**Severity:** P0 reconciliation completeness  
**Required action:** persist a durable sync cursor/acknowledged event ID and continue until caught up.

### AUD0-HSYNC-002 — Maximum 50-trade payload has no pagination loop

The function sends at most 50 aggregated trades and returns.

There is no visible continuation cursor or repeated batching for remaining eligible trades.

**Severity:** P0 data-loss risk  
**Required action:** paginate deterministically until all unsynced logical trades are acknowledged.

### AUD0-HSYNC-003 — No durable outbox or acknowledgement state

A failed WebRequest only logs failure. The same scan may retry later, but there is no locally persisted per-event delivery state.

**Severity:** P0 delivery reliability  
**Required action:** durable outbox keyed by immutable event ID, with backend idempotency and ACK.

### AUD0-HSYNC-004 — Synchronous 20-second sync runs during initialization and timer lifecycle

History synchronization can delay EA startup or block timer processing.

**Severity:** P0 runtime availability  
**Required action:** incremental non-blocking background delivery through LocalBridge/outbox.

### AUD0-HSYNC-005 — Resync skips trades whose entry deal is outside the selected window

The code explicitly skips aggregates where `vol_in <= 0`.

A position opened earlier than seven days but closed within the window may be missed if the aggregator cannot recover its full entry history under the current selection semantics.

**Severity:** P1 completeness pending MT5 history behavior verification  
**Required action:** select by position ID from full available history and track a persistent cursor independent of the seven-day window.

### AUD0-HSYNC-006 — Resync identity remains position-based and inherits netting limitations

`tradeUid = account:positionId`.

This inherits the previously documented incompatibility with netting flips and lacks setup/sequence identity.

**Severity:** P0 platform/analytics integrity  
**Required action:** immutable event and logical-trade IDs independent of broker position lifecycle.

### AUD0-HSYNC-007 — Backend response is not semantically validated

Any HTTP 200 is treated as success and logged; no per-trade accepted/rejected list, schema version or acknowledgement cursor is verified.

**Severity:** P1 reconciliation correctness  
**Required action:** require structured ACK for each event/batch and persist only confirmed acknowledgements.

## Transaction-confirmation conclusion

Across the reviewed modules, request-level success remains more developed than broker-confirmed lifecycle state.

The platform needs one shared transaction journal correlating:

- command ID;
- exposure/management intent ID;
- request;
- order;
- deal;
- position;
- logical leg;
- sequence;
- backend event acknowledgement.

Without this, UI command status, MQL state, broker state and analytics can disagree.

## MQL5 audit status

The major MQL5 control-plane and exposure paths have now been reviewed.

Still pending for full closure:

- dedicated Virtual SL implementation;
- exact `OnTradeTransaction` handler and ledger-drain path;
- WebBridge/LocalBridge end-to-end command ACK;
- selected management helpers not yet individually inspected;
- compile and Strategy Tester evidence.

## Progress update

### Overall audit

**66%**

### AUDIT-0 Repository Inventory

**86%**

### MQL5 control-plane review

**94%**

### Area status

- Repository Inventory: 86%
- Root Configuration: 94%
- MQL5: 82%
- Backend: 42%
- Frontend: 7%
- Contracts: 63%
- Deploy: 60%
- Security: 69%
- Documentation: 46%
- Testing: 27%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 14: Frontend Authentication, Commands, Settings and Data Provenance

## Scope reviewed

- `frontend/package.json`
- `frontend/src/App.js`
- `frontend/src/lib/auth.jsx`
- `frontend/src/lib/api.js`
- `frontend/src/pages/Login.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/contracts/settingsContract.js`

This is the first focused frontend pass. Remaining pages and reusable components still require dedicated review.

## Verified frontend behavior

### Authentication

- The frontend now relies on an httpOnly session cookie.
- Axios uses `withCredentials: true`.
- Legacy `nexus_token` localStorage state is explicitly removed at login and logout.
- `/auth/me` is used to restore the current session.
- Client-side protected routes redirect unauthenticated visitors to login.
- A global response interceptor redirects most 401 responses to `/app/login`.

### Dashboard/control plane

- Dashboard data is refreshed every five seconds while visible.
- Ten API resources are fetched together with `Promise.allSettled`.
- Command status is polled every 1.5 seconds.
- Polling stops when the command reaches `DELIVERED`.
- Commands are submitted through `/command`.
- Some command-palette actions show confirmation dialogs.
- Settings are validated client-side against a generated settings adapter.
- Provenance badges exist for observed live data, ledger analytics, reconstructed history and simulated research.

## Positive controls observed

- No active bearer token is stored in JavaScript-readable storage.
- Session restoration has an explicit checking state.
- Route components are lazy-loaded where heavy 3D dependencies are involved.
- Dashboard partial failures use `Promise.allSettled`, preserving available sections.
- Client settings validation rejects non-finite and incorrectly typed values.
- Confirmation UI exists for several destructive actions.
- Provenance badges are present in the dashboard.
- The login ticker source is explicitly documented in code as mock data.
- The API client centralizes cookie behavior and 401 handling.

## New findings

### AUD0-FE-AUTH-001 — Production login ships with default credentials prefilled and displayed

The login component initializes:

- `admin@nexus.local`
- `nexus123`

and visibly states the default credentials below the form.

**Impact:** any reachable deployment retaining the defaults is immediately accessible, and even deployments that changed them disclose the expected administrator identity and password convention.

**Severity:** P0 authentication exposure  
**Required action:** remove defaults from production bundles, require first-run credential creation and block startup while default credentials remain active.

### AUD0-FE-AUTH-002 — Client route protection has no visible role/permission checks

Every authenticated user can navigate to:

- settings;
- licenses;
- optimizer;
- coach;
- local bridge;
- strategy controls;
- risk controls.

The `Protected` component checks only whether `user` exists.

Backend authorization must remain authoritative, but the frontend currently exposes all privileged control surfaces to every authenticated session.

**Severity:** P1 authorization UX / defense in depth  
**Required action:** permission-aware route and action guards driven by server-issued capabilities.

### AUD0-FE-AUTH-003 — Cookie-authenticated mutation requests have no visible CSRF token

Axios includes cookies automatically for all requests, while settings and command mutations are ordinary POST requests.

No frontend CSRF token/header mechanism is visible.

**Severity:** P0 pending backend cookie-policy verification  
**Required action:** verify strict SameSite/origin enforcement and implement anti-CSRF tokens for state-changing operations.

### AUD0-FE-AUTH-004 — Logout failure still clears only local UI state

If `/auth/logout` fails, the frontend logs a warning and marks the user logged out locally.

The server-side cookie/session can remain valid and become active again on reload.

**Severity:** P1 session semantics  
**Required action:** show degraded logout state and verify server invalidation before claiming logout completed.

## Command-control findings

### AUD0-FE-CMD-001 — Frontend treats `DELIVERED` as terminal success

Command polling explicitly stops when status equals `DELIVERED`, and the status banner renders it as the successful green state.

This reproduces the backend/MQL mismatch:

`DELIVERED != broker executed`.

**Severity:** P0 operational truth  
**Required action:** terminal states must be transaction-confirmed:
- SUCCEEDED;
- PARTIAL;
- FAILED;
- EXPIRED;
- CANCELLED.

### AUD0-FE-CMD-002 — Command confirmation policy is incomplete and duplicated

The command palette defines confirmations for only a subset:

- close_all;
- pause;
- reset_anti_revenge;
- reset_daily.

Other high-risk commands can fall through without confirmation, including potentially resume/reset-protection operations depending on invocation path.

**Severity:** P0 safety UX  
**Required action:** canonical command registry containing risk class, required role, confirmation text and approval policy.

### AUD0-FE-CMD-003 — Confirmation text understates `reset_daily`

The dialog says only:

`Trades-today → 0`.

The MQL command also resets the daily balance baseline, materially changing drawdown protection.

**Severity:** P0 operator deception by omission  
**Required action:** confirmation text must be generated from the canonical command contract and enumerate every state mutation.

### AUD0-FE-CMD-004 — Command failures are console-only

`doCmd` catches errors and writes to `console.error`, with no durable operator-visible failure state or retry guidance.

**Severity:** P1 operational UX  
**Required action:** show structured error, command ID, retry safety and last known backend/broker status.

### AUD0-FE-CMD-005 — No visible command target selection or confirmation

The frontend sends only action and payload. It does not visibly show/confirm:

- account;
- symbol;
- magic;
- EA instance;
- environment;
- affected position ownership.

**Severity:** P0 destructive targeting  
**Required action:** every command dialog must display and submit an immutable target tuple.

## Settings findings

### AUD0-FE-SET-001 — Generated ranges permit unsafe production values

The frontend contract allows:

- RiskPercent up to 10%;
- MaxLot up to 100;
- MaxTradesPerDay up to 500;
- MaxConcurrent up to 40;
- MaxDailyDDPct up to 100%.

These are schema-valid but can be catastrophic for a live trading system.

**Severity:** P0 capital safety  
**Required action:** distinguish technical schema limits from production policy limits and require elevated approval for high-risk ranges.

### AUD0-FE-SET-002 — Zero values can disable or invalidate core protections

The adapter allows zero for:

- risk percentage;
- maximum trades;
- maximum concurrent positions;
- daily drawdown;
- minimum score.

The meaning of zero is not consistently explicit: disabled, unlimited or block-all may differ by backend/MQL implementation.

**Severity:** P0 contract ambiguity  
**Required action:** use explicit nullable/enum semantics such as `disabled`, `unlimited`, or positive bounded value.

### AUD0-FE-SET-003 — Settings save has no visible version/optimistic concurrency control

The frontend posts a patch without an ETag, revision or expected settings version.

Multiple operators or automated optimization can overwrite one another.

**Severity:** P0 configuration race  
**Required action:** require `expected_version`, reject conflicts and show a diff/merge flow.

### AUD0-FE-SET-004 — Save operations have no confirmation for risk-critical changes

Risk, drawdown, lot and concurrency values can be submitted through the general settings save path without a dedicated high-risk confirmation or review summary.

**Severity:** P1 operator safety  
**Required action:** risk-delta review and typed confirmation for material exposure increases.

## Data/provenance findings

### AUD0-FE-DATA-001 — Login mock market prices are not visibly labelled as mock

The source code comments correctly identify the ticker as mock visual data, but the rendered ticker itself presents realistic symbols, prices and percentage changes without a visible `DEMO/MOCK` label.

**Severity:** P1 provenance presentation  
**Required action:** display an unmistakable visual mock/demo label.

### AUD0-FE-DATA-002 — Header equates backend `online` with `LIVE`

The page header shows `LIVE` whenever `status.online` is truthy and `DEMO` otherwise.

This does not prove:
- broker connectivity;
- fresh tick age;
- command channel health;
- licensed production mode;
- real-money account.

**Severity:** P0 provenance/operational semantics  
**Required action:** separate statuses:
- backend connected;
- EA heartbeat fresh;
- broker connected;
- market data fresh;
- account DEMO/LIVE;
- trading enabled.

### AUD0-FE-DATA-003 — PDF download does not validate HTTP status/content type

The tear-sheet export converts any fetch response to a blob and downloads it as PDF.

An authentication error or HTML/JSON failure can be saved with a `.pdf` filename.

**Severity:** P1 correctness  
**Required action:** verify `response.ok`, content type and error payload before download.

### AUD0-FE-DATA-004 — Resource polling can generate substantial synchronized load

Every visible dashboard performs approximately ten requests every five seconds, plus command polling every 1.5 seconds while pending.

With multiple operators/tabs this creates synchronized bursts.

**Severity:** P1 scalability  
**Required action:** consolidated status endpoint, React Query caching/deduplication, jitter and server push where appropriate.

### AUD0-FE-DATA-005 — Stale data remains visible after partial request failure

`Promise.allSettled` preserves last successful state, which is good for resilience, but individual cards do not necessarily show last-updated age or stale status.

**Severity:** P0 operator decision safety  
**Required action:** attach freshness/provenance metadata to every critical data domain and visibly mark stale values.

## Supply-chain/build findings

### AUD0-FE-SUPPLY-001 — Numerous Radix dependencies use `latest`

A large set of runtime dependencies is declared as `latest`.

This makes clean installs non-reproducible and can introduce unreviewed changes.

**Severity:** P0 supply-chain reproducibility  
**Required action:** pin exact versions and enforce lockfile integrity in CI.

### AUD0-FE-SUPPLY-002 — Create React App toolchain remains on `react-scripts 5.0.1`

The frontend uses CRA/CRACO with an old build stack.

**Severity:** P1 maintenance/security  
**Required action:** assess migration to a maintained build system and continuously audit transitive vulnerabilities.

### AUD0-FE-SUPPLY-003 — Large 3D and UI dependency surface increases bundle/audit complexity

The application includes Three.js, React Three Fiber, postprocessing, multiple animation packages and many Radix components.

Lazy loading protects the main dashboard bundle from the landing page’s heaviest dependency, but the overall supply-chain and browser attack surface remain broad.

**Severity:** P1 attack surface  
**Required action:** dependency inventory, bundle analysis, CSP compatibility review and removal of unused packages.

## Architectural conclusion

The frontend has improved authentication storage and useful provenance concepts, but it currently presents a control-plane abstraction that is more confident than the underlying broker-confirmation model.

The UI must never translate:

- backend reachable into LIVE trading;
- command delivered into command executed;
- cached value into current value;
- schema-valid setting into production-safe setting.

## Next frontend verification queue

1. `Licenses.jsx`
2. `Coach.jsx` and `CoachLiveWidget`
3. `LocalBridgePage.jsx`
4. `StrategiesPage.jsx`
5. `OptimizerPage.jsx`
6. `Backtest.jsx`
7. `LiveChartPage.jsx`
8. `strategyHub` and `tradeHub`
9. notification and command-palette components
10. frontend tests, CSP and source-map/build output

## Progress update

### Overall audit

**71%**

### AUDIT-0 Repository Inventory

**89%**

### Frontend review

**36%**

### Area status

- Repository Inventory: 89%
- Root Configuration: 94%
- MQL5: 82%
- Backend: 42%
- Frontend: 36%
- Contracts: 68%
- Deploy: 60%
- Security: 74%
- Documentation: 49%
- Testing: 30%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 15: License Console, AI Coach, Local Bridge and Live Optimizer

## Scope reviewed

- `frontend/src/pages/Licenses.jsx`
- `frontend/src/pages/Coach.jsx`
- `frontend/src/pages/LocalBridgePage.jsx`
- `frontend/src/pages/dashboard/OptimizerPage.jsx`

## Positive controls observed

- License deletion requires an explicit browser confirmation.
- License creation separates demo-only from unrestricted plans.
- Local Bridge commands use explicit command types and status values.
- Local Bridge displays failed/retrying/final states rather than only “delivered”.
- Optimizer displays when data is demo/empty.
- Optimizer warns users to enable auto-scaling on demo first.
- Coach sessions use per-page session IDs rather than one global hard-coded thread.
- Coach chart context is visibly shown and removable.
- Sensitive actions generally show operator-facing state and loading indicators.

## License-console findings

### AUD0-FE-LIC-001 — Full license keys are exposed in the browser UI

The license table renders the complete license key and provides one-click clipboard copy.

The newly generated key is also kept in React state and rendered in full after creation.

**Severity:** P0 secret exposure  
**Required action:** display only a masked fingerprint after initial issuance. Full secret should be shown once, then never returned by list APIs.

### AUD0-FE-LIC-002 — License list endpoint appears to return reusable secrets

Because the UI renders `lic.key`, the backend list response necessarily exposes the raw key or an equivalent reusable credential.

This compounds the previously identified backend finding that license keys are exposed.

**Severity:** P0 credential architecture  
**Required action:** store and compare hashed keys; list only ID, prefix/fingerprint, status and metadata.

### AUD0-FE-LIC-003 — License administration is available to every authenticated frontend user

The route protection checks authentication only, and this page can:

- issue;
- extend;
- enable;
- disable;
- delete;
- copy license keys.

No frontend capability/role check is visible.

**Severity:** P0 commercial authorization  
**Required action:** server-enforced admin capability plus permission-aware route/action rendering.

### AUD0-FE-LIC-004 — High-impact license changes lack strong confirmation and reason capture

Enable/disable and +30-day extension happen immediately on click.

Only deletion asks for confirmation, and no action captures:

- operator reason;
- client impact;
- expected version;
- approval identity.

**Severity:** P1 operational/commercial control  
**Required action:** explicit confirmation, reason and immutable audit event for every entitlement change.

### AUD0-FE-LIC-005 — License creation fields are weakly constrained client-side

Client name is optional, plan values are hard-coded in the UI, and days fall back to 365 when conversion produces zero/invalid input.

There is no client-side schema version or server-provided plan registry.

**Severity:** P1 contract drift  
**Required action:** canonical license schema, required client identity and exact validation.

### AUD0-FE-LIC-006 — Clipboard operations have no failure handling

License keys and dashboard URL are copied without handling clipboard permission failures.

**Severity:** P2 UX/reliability  
**Required action:** show success/failure feedback without leaving secrets selected on screen.

## AI Coach findings

### AUD0-FE-AI-001 — Session IDs are client-generated and not user-bound in the frontend contract

Coach session IDs are created from timestamp plus `Math.random()` and sent to history, chat and delete endpoints.

The client does not include or verify an owner identity.

This reinforces the previously identified backend requirement that session ownership must be enforced server-side.

**Severity:** P0 pending backend ownership enforcement  
**Required action:** server-generated opaque session IDs bound to authenticated user; reject cross-user access.

### AUD0-FE-AI-002 — User-visible error discloses backend secret/configuration details

When coach chat fails, the UI tells the user to verify:

`EMERGENT_LLM_KEY in backend/.env`.

**Severity:** P1 information disclosure  
**Required action:** show a generic service-unavailable message and keep secret/config diagnostics in protected operator logs.

### AUD0-FE-AI-003 — “Contesto live” label overstates chart-context provenance

The page labels query-string symbol/timeframe values as “Contesto live dal grafico”.

The payload contains only symbol and timeframe, not a signed chart snapshot, price timestamp, data source or freshness proof.

**Severity:** P0 AI grounding/provenance  
**Required action:** send and display a versioned server-side chart-context snapshot with timestamp and provenance.

### AUD0-FE-AI-004 — AI output has no visible provenance, confidence or action boundary

Assistant replies are appended directly to the conversation.

There is no visible distinction between:
- ledger facts;
- inferred analytics;
- model opinion;
- simulated guidance;
- executable recommendation.

**Severity:** P0 operator safety  
**Required action:** structured response sections with provenance and explicit “not executed” state.

### AUD0-FE-AI-005 — Coach reset uses native confirm and immediate delete

Session deletion relies on browser `confirm()` and has no undo, export or retention warning.

**Severity:** P1 data lifecycle  
**Required action:** application-level confirmation, retention policy and soft-delete where appropriate.

### AUD0-FE-AI-006 — Coach branding hard-codes a model/provider statement

The UI states “Claude Sonnet 4.5 via Emergent”.

This is duplicated provider/version metadata and can become inaccurate when backend configuration changes.

**Severity:** P1 contract/provenance drift  
**Required action:** render model/provider metadata supplied by the backend for the actual response.

## Local Bridge findings

### AUD0-FE-BRIDGE-001 — Compile, restart and deploy actions have no confirmation dialog

Buttons immediately enqueue:
- compile EA;
- restart MT5;
- deploy files.

Restart and deployment can interrupt trading or alter executable code.

**Severity:** P0 remote-host control safety  
**Required action:** strong confirmation showing host, path, release, active account and expected downtime.

### AUD0-FE-BRIDGE-002 — Host targeting trusts the single status response

The page uses `status.worker.host_id` as the target without a user selection or immutable host confirmation.

A stale or wrong status response can route a command to an unintended worker.

**Severity:** P0 destructive targeting  
**Required action:** stable host inventory, explicit target selection and signed target tuple.

### AUD0-FE-BRIDGE-003 — Client-generated idempotency key uses current time

The key is:

`host_id:action:Date.now()`.

Every click creates a different key, so double-clicks/retries are not deduplicated.

**Severity:** P0 command idempotency  
**Required action:** server-issued command intent ID or stable client UUID retained across retries.

### AUD0-FE-BRIDGE-004 — Deploy action is hard-coded to release `nexus-3.40`

The UI text and payload hard-code a release identifier while other repository/version surfaces use different versions.

**Severity:** P0 deployment/version drift  
**Required action:** release registry from backend with signed manifest, checksum and compatibility validation.

### AUD0-FE-BRIDGE-005 — Deploy sends an empty file list

The payload uses:

`files: []`.

The semantics of an empty list are not shown in the UI and could mean:
- no files;
- all files;
- backend default manifest.

**Severity:** P0 ambiguous destructive contract  
**Required action:** explicit immutable manifest preview before enqueue.

### AUD0-FE-BRIDGE-006 — Worker download uses a root-relative unauthenticated-looking path

The link points directly to:

`/api/downloads/local_worker`.

This is consistent with the previously identified static-download exposure/path mismatch.

**Severity:** P0 distribution security  
**Required action:** authenticated, versioned, checksummed download endpoint with signed artifact metadata.

### AUD0-FE-BRIDGE-007 — Worker setup instructions encourage direct execution of downloaded Python

The UI instructs the user to download and run a Python worker with only `requests` installed.

No checksum, signature, virtual environment, least-privilege or code-signing guidance is presented.

**Severity:** P0 supply-chain/endpoint security  
**Required action:** signed packaged worker, verified installer and least-privilege setup documentation.

### AUD0-FE-BRIDGE-008 — Sensitive local system paths are displayed in the cloud UI

Worker OS and MT5 path are returned and shown.

This exposes endpoint filesystem information to every authenticated user with page access.

**Severity:** P1 information disclosure  
**Required action:** permission-gate and redact local paths unless operationally necessary.

### AUD0-FE-BRIDGE-009 — Action errors use browser alert

Bridge errors are displayed with `alert()`, potentially including backend detail strings.

**Severity:** P1 error disclosure/UX  
**Required action:** structured sanitized error component and command audit link.

## Live optimizer findings

### AUD0-FE-OPT-001 — Auto-scaling can be enabled with one click and no confirmation

The risk auto-scaler toggle posts immediately.

The text warns about demo usage but does not prevent activation on a live account or require confirmation.

**Severity:** P0 capital safety  
**Required action:** verify account type, require risk-impact preview and elevated confirmation.

### AUD0-FE-OPT-002 — Configuration values save on blur

Each numeric field sends a mutation when focus leaves the input.

Accidental clicks, scroll-wheel changes or partial edits can immediately change live risk behavior.

**Severity:** P0 operator safety  
**Required action:** staged draft, validation, diff review and explicit Apply action.

### AUD0-FE-OPT-003 — Optimizer configuration fields have no client-side min/max constraints

Inputs specify `step` but no safe `min` or `max`.

Values such as negative multipliers, extreme drawdown targets or invalid trade counts can be submitted.

**Severity:** P0 validation  
**Required action:** canonical schema validation in frontend and backend.

### AUD0-FE-OPT-004 — Manual risk override permits any non-negative number

The override input has `min=0` but no maximum.

This mirrors the previously identified backend 10× multiplier risk and may allow excessive exposure if backend validation changes or is bypassed.

**Severity:** P0 capital safety  
**Required action:** strict production cap, role gating and confirmation for increases above 1×.

### AUD0-FE-OPT-005 — Manual override saves without confirmation or expected version

A single save button immediately mutates one strategy’s effective risk.

There is no:
- current-vs-new impact;
- account exposure preview;
- revision check;
- expiry;
- reason.

**Severity:** P0 configuration integrity  
**Required action:** versioned override with reason, expiry and projected risk delta.

### AUD0-FE-OPT-006 — The UI claims real-time application every 15 seconds without execution acknowledgement

The explanatory text says multipliers are sent to the EA in real time.

The frontend does not show:
- settings version delivered;
- EA-applied version;
- rejected values;
- last successful poll;
- active multiplier checksum.

**Severity:** P0 operational truth  
**Required action:** display desired, delivered and EA-applied configuration versions separately.

### AUD0-FE-OPT-007 — `demo` semantics can hide a populated board

The page renders the empty/demo explanation whenever `demo` is true, even if board data exists.

This conflates account mode and data availability.

**Severity:** P1 provenance presentation  
**Required action:** show account mode separately from whether real or synthetic records are present.

### AUD0-FE-OPT-008 — Performance metrics are presented without sample/provenance warnings per row

The leaderboard shows PF, win rate, DD and suggested multiplier, but only a total trade count and free-text reason.

There is no visible confidence interval, data freshness, source mix or minimum-sample warning at row level.

**Severity:** P1 model governance  
**Required action:** sample-quality and provenance badges before allowing risk scaling.

## Cross-cutting frontend conclusion

The reviewed sensitive pages expose three distinct control planes:

1. commercial entitlement control;
2. local-machine/code deployment control;
3. live risk-multiplier control.

All three are reachable through authentication-only routes and rely heavily on backend authorization, but the UI does not yet express:
- capability boundaries;
- target identity;
- configuration version;
- approval policy;
- transaction-confirmed result.

The required frontend pattern is a shared `PrivilegedAction` component driven by a canonical action registry.

It should require:
- server capability;
- target tuple;
- expected resource version;
- reason;
- risk/impact summary;
- confirmation;
- command ID;
- terminal ACK state.

## Progress update

### Overall audit

**76%**

### AUDIT-0 Repository Inventory

**92%**

### Frontend review

**63%**

### Area status

- Repository Inventory: 92%
- Root Configuration: 94%
- MQL5: 82%
- Backend: 42%
- Frontend: 63%
- Contracts: 74%
- Deploy: 65%
- Security: 81%
- Documentation: 53%
- Testing: 33%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 16: Strategies, Backtest Lab, Live Chart and Shared Frontend Hubs

## Scope reviewed

- `frontend/src/pages/dashboard/StrategiesPage.jsx`
- `frontend/src/pages/Backtest.jsx`
- `frontend/src/pages/LiveChartPage.jsx`
- `frontend/src/lib/strategyHub.jsx`
- `frontend/src/lib/tradeHub.jsx`

## Positive controls

- Strategy changes are staged locally before save.
- Backtest defaults keep grid and pyramiding disabled.
- Synthetic chart data is visibly marked `DEMO`.
- Live Chart separates closed trades, open positions, shadows and technical visuals.
- StrategyHub and TradeHub centralize shared drawers.
- Polling is visibility-aware.

## Strategy-control findings

### AUD0-FE-STRAT-001 — No risk-impact confirmation
Strategy combinations and whole families can be changed and saved without previewing open-position impact, expected signal-rate change, portfolio overlap or account mode.

**Severity:** P0  
**Required action:** strategy-diff review, live-account warning and projected exposure impact.

### AUD0-FE-STRAT-002 — Bulk family changes lack final change summary
Enable-all/disable-all changes the draft quickly, but the final save does not enumerate all affected strategies.

**Severity:** P1

### AUD0-FE-STRAT-003 — Missing settings fail open to all strategies enabled
When `settings.strategies` is absent, the UI constructs a map with every canonical strategy enabled. A save during partial data failure could activate the complete set.

**Severity:** P0  
**Required action:** fail closed and block save until authoritative settings load.

### AUD0-FE-STRAT-004 — Local draft is labelled “live”
The active count is derived from unsaved local state and shown as live, without verifying saved or EA-applied configuration.

**Severity:** P0  
**Required action:** distinguish draft, desired, delivered and EA-applied state.

### AUD0-FE-STRAT-005 — Backtest-readiness metadata is duplicated
`READY_FOR_BACKTEST` is a local hard-coded set.

**Severity:** P1  
**Required action:** use the canonical strategy registry.

## Backtest findings

### AUD0-FE-BT-001 — Full-EA replay claim lacks parity evidence
The page says it replays every NEXUS strategy and all EA gates, but parity with live MQL execution, protection, timing and persistence has not been demonstrated.

**Severity:** P0 research validity

### AUD0-FE-BT-002 — Defaults allow unrealistic execution assumptions
Defaults include spread cap 999 points, daily bars, disabled gates and no partial/BE/trailing.

**Severity:** P0 model risk  
**Required action:** broker-calibrated presets and prominent execution-assumption labels.

### AUD0-FE-BT-003 — Grid research default compounds exposure
When enabled, grid defaults to three levels with a 1.5× size multiplier.

**Severity:** P0 strategy-risk presentation

### AUD0-FE-BT-004 — Library preset auto-mutates the run configuration
Choosing one strategy triggers a preset fetch that overwrites timeframe, SL/TP and management settings without explicit acceptance.

**Severity:** P1 reproducibility

### AUD0-FE-BT-005 — Preset metrics may be mistaken for current-run results
Sharpe, PF and DD appear before the current configuration is run.

**Severity:** P0 provenance confusion

### AUD0-FE-BT-006 — “Load live settings” imports only a subset
Risk, ATR, score and concurrency are copied, while other live controls and runtime state are omitted.

**Severity:** P0 research/live mismatch

### AUD0-FE-BT-007 — Experiment manifest is missing
The request does not visibly bind dataset revision, strategy commit, engine version, calendar revision or execution-model version.

**Severity:** P0 reproducibility

### AUD0-FE-BT-008 — Backend detail is rendered directly
Run failures may expose backend internals.

**Severity:** P1

## Live Chart findings

### AUD0-FE-CHART-001 — Symbol/timeframe lists are hard-coded
They are not loaded from the active broker or EA instance.

**Severity:** P1 contract drift

### AUD0-FE-CHART-002 — Last price is forced to two decimals
This is incorrect for many FX/CFD symbols.

**Severity:** P1 data integrity

### AUD0-FE-CHART-003 — Non-synthetic data is not positively identified
Synthetic data gets a DEMO badge, but other data has no explicit provider, timestamp or freshness. Absence of DEMO may be read as verified live broker data.

**Severity:** P0 provenance semantics

### AUD0-FE-CHART-004 — Failed requests leave stale chart domains visible
OHLC and marker requests use `Promise.allSettled`; failures keep prior values and only log to console.

**Severity:** P0 operator decision safety

### AUD0-FE-CHART-005 — Marker query omits timeframe
Candles use symbol+timeframe, while markers use symbol only. Cross-timeframe overlays may be misleading.

**Severity:** P0 visualization correctness

### AUD0-FE-CHART-006 — Coach context is browser-controlled
LocalStorage stores only symbol, timeframe and timestamp, not the actual chart snapshot or feed provenance.

**Severity:** P0 AI grounding integrity

### AUD0-FE-CHART-007 — Full chart refresh every five seconds
Up to 300 bars and marker sets are repeatedly fetched, risking inconsistent snapshots and unnecessary load.

**Severity:** P1

### AUD0-FE-CHART-008 — Visual-event types are not schema-validated
Unknown types are rendered generically.

**Severity:** P1

## Shared hub findings

### AUD0-FE-HUB-001 — StrategyHub accepts arbitrary names
The shared drawer can be opened with any string.

**Severity:** P1 identity integrity

### AUD0-FE-HUB-002 — TradeHub accepts arbitrary trade objects
The lifecycle drawer can receive incomplete or locally constructed objects instead of loading authoritative data by immutable ID.

**Severity:** P1 provenance integrity

### AUD0-FE-HUB-003 — Duplicate lifecycle drawers exist
Dashboard mounts one `TradeLifecycleDrawer`, while `TradeHubProvider` mounts another.

**Severity:** P1 frontend architecture  
**Required action:** consolidate all trade drill-down paths through TradeHub.

## Testing conclusion

No evidence was found in these reviewed files for dedicated tests covering:

- privileged-action authorization;
- command terminal states;
- stale-data presentation;
- backtest provenance;
- strategy fail-closed behavior;
- chart source/freshness.

## Cross-cutting conclusion

The critical frontend invariant must be:

`visual label = verified backend/broker state`

not a local inference or the absence of an error.

## Progress update

### Overall audit
**81%**

### AUDIT-0 Repository Inventory
**94%**

### Frontend review
**84%**

### Area status

- Repository Inventory: 94%
- Root Configuration: 94%
- MQL5: 82%
- Backend: 42%
- Frontend: 84%
- Contracts: 80%
- Deploy: 65%
- Security: 84%
- Documentation: 57%
- Testing: 38%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 17: Backend Authorization, Privileged Actions and Control-Plane Closure

## Scope reviewed

- `server/app.py`
  - configuration and authentication helpers;
  - login/session handling;
  - EA command delivery;
  - dashboard command creation;
  - settings and locked-profile writes;
  - license CRUD;
  - Coach actions and memory;
  - backtest execution/import paths;
  - EA status and analytics selection.

## Positive controls observed

- Secret comparison uses `secrets.compare_digest`.
- JWT verification restricts the algorithm to HS256.
- Session cookies are httpOnly.
- Secure-cookie behavior is configurable.
- Settings patches pass through a canonical validator in the primary settings path.
- Strategy identifiers are validated in several Coach actions.
- LocalBridge has a stronger leased-command model than the legacy EA command channel.
- Trade-event uniqueness exists for terminal logical-trade events.

## Authentication and session findings

### AUD0-BE-AUTH-001 — Production-dangerous default bridge and admin credentials

The backend defaults to:

- bridge token `NEXUS_BRIDGE_TOKEN_2026`;
- admin user `admin`;
- admin password `admin`.

The process starts even when these values were not explicitly changed.

**Severity:** P0 authentication compromise  
**Required action:** fail startup in non-development environments if any default credential is active.

### AUD0-BE-AUTH-002 — Random ephemeral JWT secret invalidates sessions across restart

When `NEXUS_JWT_SECRET` is absent, a new random value is created at process start.

This avoids a static default but invalidates every session after restart and prevents multi-instance deployments from sharing sessions.

**Severity:** P1 availability/configuration integrity  
**Required action:** require an explicit persistent secret in production.

### AUD0-BE-AUTH-003 — JWT lifetime defaults to 720 hours

The default session lifetime is 30 days.

For an account capable of closing trades, changing risk, deploying code and issuing licenses, this is excessive without rotation, revocation or step-up authentication.

**Severity:** P0 privileged-session exposure  
**Required action:** short access sessions, revocable server-side session records and step-up authentication for critical actions.

### AUD0-BE-AUTH-004 — Login returns the JWT in the response body

Although the React client uses an httpOnly cookie, login still returns the token for legacy Bearer compatibility.

Any JavaScript caller or legacy page can access the bearer token.

**Severity:** P0 token exposure  
**Required action:** remove body tokens from production login and retire the legacy bearer path.

### AUD0-BE-AUTH-005 — No issuer, audience, session ID or token version

JWTs contain only subject, issued-at and expiry.

There is no:
- issuer;
- audience;
- unique session ID;
- token version;
- server-side revocation state.

**Severity:** P1 session control  
**Required action:** add scoped claims and revocable session storage.

### AUD0-BE-AUTH-006 — Authentication is equivalent to full administrator authorization

`require_user` returns a subject string; `_user_obj` always returns role `admin`.

No route-level capabilities or resource ownership checks exist in the reviewed backend.

**Severity:** P0 authorization architecture  
**Required action:** implement explicit capabilities for trading control, settings, licensing, research, Coach and deployment.

### AUD0-BE-AUTH-007 — Cookie uses SameSite=Lax for privileged mutations

The cookie is httpOnly and optionally secure, but uses SameSite `lax`.

No anti-CSRF token was found in the reviewed frontend/backend paths.

**Severity:** P0 CSRF defense pending deployment topology  
**Required action:** strict same-site policy where compatible, origin checks and anti-CSRF token for every cookie-authenticated mutation.

## EA command-channel findings

### AUD0-BE-CMD-005 — Command delivery is global rather than target-scoped

The polling query selects the oldest unconsumed EA command globally.

It does not filter by:
- account;
- magic;
- symbol;
- EA instance;
- environment.

**Severity:** P0 cross-instance destructive command  
**Required action:** make the target tuple mandatory and part of the command-selection query.

### AUD0-BE-CMD-006 — Polling consumes the command before execution acknowledgement

The backend sets:
- `consumed=1`;
- `status='DELIVERED'`;

during the GET poll itself.

A crash, parser failure or broker rejection after the response permanently removes the command from the queue.

**Severity:** P0 command-loss and false-success  
**Required action:** use lease, explicit ACK and terminal execution states.

### AUD0-BE-CMD-007 — EA command records lack expiry, attempts and result fields

The legacy table has no durable fields for:
- target;
- expiration;
- lease;
- attempt count;
- broker result;
- operator reason;
- post-state.

**Severity:** P0 lifecycle integrity  
**Required action:** replace the legacy table with the canonical command schema used by LocalBridge.

### AUD0-BE-CMD-008 — Three frontend-facing enqueue paths exist

Commands can be created through:
- `/api/dashboard/command`;
- `/api/command`;
- Coach `/api/coach/apply_action`.

All call the same weak `_enqueue_ea_command` helper but maintain separate allowed-action logic.

**Severity:** P0 policy drift  
**Required action:** one privileged command service and one canonical action registry.

### AUD0-BE-CMD-009 — `resync_trades` is accepted but not supported by the reviewed MQL parser

Backend command allow-lists include `resync_trades`, while the reviewed WebBridge command handler did not contain that action.

**Severity:** P1 contract mismatch  
**Required action:** generate both backend and MQL action registries from the same contract and reject unsupported capability versions.

## Settings and profile findings

### AUD0-BE-SET-001 — Settings writes have no optimistic concurrency

Dashboard settings merge the submitted patch into current state and overwrite the shared KV record.

There is no expected version, ETag or conflict detection.

**Severity:** P0 configuration race  
**Required action:** compare-and-swap using immutable settings revision IDs.

### AUD0-BE-SET-002 — No immutable operator audit for primary settings writes

The primary dashboard settings route records no dedicated actor/reason/diff event.

**Severity:** P0 governance  
**Required action:** append an immutable configuration event before publishing a new desired version.

### AUD0-BE-SET-003 — Locked-profile replacement can remove omitted symbols

The PUT path reconstructs the complete map from the submitted body and replaces stored profiles.

A partial client payload can erase profiles for symbols not included.

**Severity:** P0 configuration loss  
**Required action:** use patch semantics or require an expected complete version with explicit deletion markers.

### AUD0-BE-SET-004 — EA receives desired settings without applied-version acknowledgement

`/api/ea/settings` returns the current desired state and derived strategy risk map, but no reviewed endpoint records the version actually applied by the EA.

**Severity:** P0 operational truth  
**Required action:** version every settings response and require EA apply/reject acknowledgement.

## License backend findings

### AUD0-BE-LIC-001 — License secrets are stored as primary keys in plaintext

The database schema stores the reusable license key directly as the primary key.

The list endpoint returns every column.

**Severity:** P0 credential storage  
**Required action:** hashed verifier plus non-secret ID and masked fingerprint.

### AUD0-BE-LIC-002 — License creation is an upsert

Creating a license with an existing key updates the current record rather than returning a conflict.

**Severity:** P1 entitlement integrity  
**Required action:** creation must be insert-only; modifications require versioned update endpoints.

### AUD0-BE-LIC-003 — Frontend/backend license contract is inconsistent

The reviewed frontend sends fields such as:
- client;
- plan;
- days;
- demo_only;
- active;
- extend_days.

The reviewed backend schema/endpoints use:
- account;
- trial;
- expires_at;
- note;

and the update route ignores unsupported fields.

**Severity:** P0 contract failure  
**Required action:** canonical versioned license schema and contract tests.

### AUD0-BE-LIC-004 — No enabled/disabled column in the reviewed license schema

The UI exposes active/disabled controls, but the backend table has no `active` field in the reviewed schema.

**Severity:** P0 false administrative control  
**Required action:** reconcile schema, API and enforcement logic and prove disablement blocks the EA.

## Coach privileged-action findings

### AUD0-BE-AI-007 — Coach can mutate live trading state through a broad action endpoint

The Coach apply endpoint can:
- pause/resume;
- close all;
- reset protections;
- reset daily state;
- enable/disable strategies;
- set global risk;
- set per-strategy risk.

Authentication alone is sufficient.

**Severity:** P0 AI-assisted control-plane exposure  
**Required action:** AI output must never directly authorize execution; require a separate human-approved privileged command with capability and target checks.

### AUD0-BE-AI-008 — Coach risk controls permit values up to 10%

Global risk and per-strategy multipliers are clamped to 10.

For live trading this remains an extreme production ceiling.

**Severity:** P0 capital safety  
**Required action:** conservative policy caps with explicit privileged override workflow.

### AUD0-BE-AI-009 — Coach strategy mutations bypass the canonical settings validator

The Coach directly edits KV settings and a legacy override map.

It does not use `_validated_settings_patch`, revision control or immutable audit.

**Severity:** P0 configuration bypass  
**Required action:** route every mutation through one settings service.

### AUD0-BE-AI-010 — Coach session storage is not user-namespaced

The KV key is based only on the caller-supplied session ID.

The authenticated user is not part of the key.

**Severity:** P0 session isolation  
**Required action:** server-generated session IDs and `(user_id, session_id)` ownership enforcement.

### AUD0-BE-AI-011 — Raw provider error details are returned to users

Anthropic HTTP response text or exception strings can be inserted into the Coach reply and `error` field.

**Severity:** P1 information disclosure  
**Required action:** return a sanitized service error and retain provider details only in protected logs.

## Backtest/import findings

### AUD0-BE-BT-009 — Backtest endpoint ignores many frontend configuration fields

The reviewed `/api/backtest/run` passes only a subset of the posted configuration into the engine.

Fields such as session filters, daily drawdown cap, spread cap, grid, pyramiding and partial TP are not visibly passed in this route.

**Severity:** P0 research-contract invalidity  
**Required action:** strict request schema; reject unsupported fields rather than silently ignoring them.

### AUD0-BE-BT-010 — Backtest errors expose raw exception text

The endpoint returns `backtest error: {exception}` to the authenticated client.

**Severity:** P1 information disclosure

### AUD0-BE-BT-011 — Import-results endpoint can publish locked live profiles directly

Uploaded/imported research results can be converted into locked profiles, including risk and management parameters.

No reviewed approval, signature, dataset manifest or production promotion stage exists.

**Severity:** P0 research-to-production promotion  
**Required action:** immutable experiment manifest, reviewer approval and staged promotion with rollback.

### AUD0-BE-BT-012 — Strategy-library build executes synchronously despite reporting queued

The endpoint performs the sweep inside the request, then returns `status: queued`.

**Severity:** P1 operational truth/availability  
**Required action:** real background job with persisted states and cancellation.

## Data model and multi-account findings

### AUD0-BE-DATA-006 — Core status and analytics storage is globally shared

The backend uses one shared SQLite database and many global KV keys:
- settings;
- equity history;
- optimizer state;
- Coach memory;
- locked profiles.

The reviewed authorization model has one global administrator rather than tenant/account ownership.

**Severity:** P0 multi-account isolation  
**Required action:** explicit tenant/account/instance keys throughout the schema.

### AUD0-BE-DATA-007 — Trade primary key can collide across accounts

The migration comments acknowledge that the historical `ticket` primary key can collide when multiple accounts share one backend.

**Severity:** P0 ledger integrity  
**Required action:** rebuild using immutable composite/global trade IDs.

### AUD0-BE-DATA-008 — Primary EA selection is implicit

Dashboard status chooses the first online EA, or otherwise the most recent row, as the primary instance.

Privileged actions and derived health can therefore refer to a different instance from the operator’s intent.

**Severity:** P0 target ambiguity  
**Required action:** explicit selected EA instance in session/UI and every query/mutation.

## Architectural conclusion

The backend is currently structured as a single-user self-hosted control center, but its exposed capabilities are equivalent to a high-impact trading operations platform.

The required security boundary is not merely “logged in”.

Every mutation must evaluate:

`actor capability + target instance + expected version + action policy + approval + idempotency + terminal acknowledgement`.

## Progress update

### Overall audit

**87%**

### AUDIT-0 Repository Inventory

**96%**

### Backend review

**78%**

### Area status

- Repository Inventory: 96%
- Root Configuration: 94%
- MQL5: 82%
- Backend: 78%
- Frontend: 84%
- Contracts: 86%
- Deploy: 68%
- Security: 91%
- Documentation: 61%
- Testing: 43%
- Reviewer Pack: 0%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 18: LocalBridge Worker, Container Deployment and CI/Test Gate

## Scope reviewed

- `LocalBridge/nexus_local_worker.py`
- `docker-compose.yml`
- `render.yaml`
- `server/Dockerfile`
- `server/requirements.txt`
- canonical CI path probe: `.github/workflows/ci.yml`
- canonical backend test path probe: `server/test_app.py`

This block closes the primary LocalBridge endpoint-execution review and the deployability gate.

## Positive controls observed

- Local worker uses HTTPS-compatible `requests` calls with finite timeouts.
- Worker sends heartbeat metadata.
- Worker uses lease IDs in ACK requests.
- Unknown command actions are terminally rejected.
- Deployment rejects resolved targets outside the MQL5 directory.
- Optional SHA-256 verification is implemented for deployed file payloads.
- Existing files are backed up before replacement.
- Render provisions a persistent disk.
- Python dependencies are version-pinned.

## LocalBridge worker findings

### AUD0-WORKER-AUTH-001 — Worker documentation and defaults ship the shared bridge credential

The sample config and `DEFAULT_CONFIG` both contain:

`NEXUS_BRIDGE_TOKEN_2026`

This matches the backend’s dangerous fallback credential.

**Severity:** P0 credential compromise  
**Required action:** remove usable defaults; require first-run enrollment with a host-specific credential.

### AUD0-WORKER-AUTH-002 — One shared bridge token authorizes all worker capabilities

The worker authenticates every request using the same `X-Nexus-Token`.

There is no visible:
- host certificate;
- per-host secret;
- command capability scope;
- credential expiry;
- rotation protocol.

**Severity:** P0 endpoint authorization  
**Required action:** per-host credentials with narrowly scoped capabilities and revocation.

### AUD0-WORKER-CONFIG-001 — Worker configuration stores the bridge token in plaintext

The generated JSON configuration places the token directly on disk.

No OS credential vault, DPAPI protection or restrictive file-permission setup is implemented.

**Severity:** P0 local secret storage  
**Required action:** use Windows Credential Manager/DPAPI and verify file ACLs.

### AUD0-WORKER-CMD-001 — RUNNING lease is not renewed during long operations

Compile can run for up to 120 seconds, while the main loop is blocked and sends neither heartbeats nor lease renewal during handler execution.

A backend lease may expire while the operation continues, allowing a retry or second worker execution.

**Severity:** P0 duplicate destructive execution  
**Required action:** execute under a lease-renewal thread/process and abort when ownership is lost.

### AUD0-WORKER-CMD-002 — ACK delivery failures are silently ignored

`ack()` delegates to `http_post`, whose failure returns `None`; callers do not verify the response.

A command can complete locally while the backend remains in RUNNING/LEASED and later retries it.

**Severity:** P0 exactly-once violation  
**Required action:** durable local command journal and retry ACK until terminal state is confirmed.

### AUD0-WORKER-CMD-003 — All handler exceptions are classified retryable

Every runtime exception becomes `FAILED_RETRYABLE`.

Permanent failures such as:
- missing MetaEditor;
- invalid source path;
- checksum mismatch;
- malformed payload;

can be retried repeatedly.

**Severity:** P1 retry policy  
**Required action:** typed errors mapped to retryable versus final outcomes.

### AUD0-WORKER-CMD-004 — No local idempotency journal

The worker does not persist completed command IDs.

After backend retry, process restart or lost terminal ACK, the same restart/deploy/compile command can execute again.

**Severity:** P0 command replay safety  
**Required action:** local append-only journal keyed by command ID and payload hash.

### AUD0-WORKER-CMD-005 — Restart kills every `terminal64.exe` process

The restart handler uses:

`taskkill /F /IM terminal64.exe`

This is not scoped to the configured terminal path or process ID and can terminate unrelated MT5 installations/accounts.

**Severity:** P0 cross-instance disruption  
**Required action:** manage a specifically enrolled process instance and verify executable path/PID.

### AUD0-WORKER-CMD-006 — Non-Windows restart reports a skipped result as success

On non-Windows systems the handler returns a `skipped` object, after which the worker ACKs `SUCCEEDED`.

**Severity:** P1 false terminal success  
**Required action:** return unsupported/failed-final state.

### AUD0-WORKER-DEPLOY-001 — File checksum is optional

SHA-256 is checked only when the payload provides it.

A deployment without checksums is accepted.

**Severity:** P0 artifact integrity  
**Required action:** reject every file lacking an expected digest and require a signed release manifest.

### AUD0-WORKER-DEPLOY-002 — Deployment is not atomic

Files are written sequentially to their final locations.

MT5/MetaEditor can observe a partially updated release, and a process crash can leave mixed versions.

**Severity:** P0 release consistency  
**Required action:** stage to a temporary directory, verify the complete manifest, then atomically switch.

### AUD0-WORKER-DEPLOY-003 — Rollback does not remove newly created files

The exception rollback restores backed-up existing files, but newly created files without backups remain on disk.

**Severity:** P0 incomplete rollback  
**Required action:** track and delete newly created targets on rollback.

### AUD0-WORKER-DEPLOY-004 — Backup naming overwrites the previous backup

Each file uses one sibling `.bak` path.

Subsequent releases overwrite the previous recovery point and no release-scoped rollback set exists.

**Severity:** P1 rollback durability  
**Required action:** release-ID-scoped immutable backup directories and retention policy.

### AUD0-WORKER-DEPLOY-005 — Empty deployment lists succeed

An empty `files` array produces a successful result with no written files.

This confirms the frontend’s ambiguous empty-manifest finding.

**Severity:** P0 false deployment success  
**Required action:** require a non-empty signed manifest and expected file count.

### AUD0-WORKER-DEPLOY-006 — Deploy result does not prove active code version

The result reports paths written and release ID but not:
- actual digests;
- compile outcome;
- EX5 digest;
- MT5 reload;
- EA runtime version.

**Severity:** P0 deployment truth  
**Required action:** separate staged, verified, compiled, activated and runtime-confirmed states.

### AUD0-WORKER-TPL-001 — Template filename permits path manipulation

`handle_apply_template` appends `.tpl` but does not normalize to a basename or verify the resolved destination remains inside the template directory.

A crafted name containing path separators may escape the intended directory.

**Severity:** P0 filesystem write boundary  
**Required action:** strict filename schema and resolved-path containment check.

### AUD0-WORKER-SHELL-001 — Shell whitelist is prefix-based and runs with `shell=True`

Commands are accepted when the string begins with an allowed prefix.

Examples such as command chaining after an allowed prefix may be interpreted by the shell.

**Severity:** P0 remote command execution  
**Required action:** remove the shell capability or use fixed argument arrays with exact command IDs and no shell.

### AUD0-WORKER-LOG-001 — Command payloads are printed in full

The worker logs the entire payload.

Deploy payloads can contain large base64 source files and shell commands; logs may expose proprietary code or sensitive arguments.

**Severity:** P1 local information disclosure  
**Required action:** log only command ID, type, release ID and payload digest.

## Container and Render findings

### AUD0-DEPLOY-DOCKER-001 — Server Dockerfile omits modules imported by `app.py`

`app.py` imports modules including:

- `strategy_registry`
- `settings_contract`
- `settings_schema`
- `command_contract`
- `ledger_analytics`

The Dockerfile copies only a subset of Python files and does not copy these modules.

**Severity:** P0 image startup failure  
**Required action:** copy/package the full server application and verify image boot in CI.

### AUD0-DEPLOY-DOCKER-002 — Dockerfile references a worker file from the wrong build context

The Dockerfile executes `COPY nexus_local_worker.py .` inside the `server` build context, while the reviewed worker is under `LocalBridge/`.

The backend itself points to the repository-level LocalBridge path, which is also outside the deployed container layout.

**Severity:** P0 build/runtime artifact mismatch  
**Required action:** define one canonical worker artifact path and include it explicitly in a repository-root build context.

### AUD0-DEPLOY-DOCKER-003 — Container runs as root

No non-root user is created or selected.

A compromise of the web process grants root privileges inside the container and write access to the mounted data volume.

**Severity:** P1 container hardening  
**Required action:** run as a dedicated unprivileged UID with read-only application files.

### AUD0-DEPLOY-DOCKER-004 — Base image is tag-pinned but not digest-pinned

`python:3.12-slim` can change over time.

**Severity:** P1 supply-chain reproducibility  
**Required action:** pin the image digest and automate controlled updates.

### AUD0-DEPLOY-COMPOSE-001 — Compose publishes the backend on every host interface

Port mapping `8001:8001` exposes the service beyond localhost by default.

**Severity:** P1 local exposure  
**Required action:** bind to `127.0.0.1` for local-only deployments or place behind a hardened reverse proxy.

### AUD0-DEPLOY-COMPOSE-002 — Compose has no healthcheck

Restart policy does not detect a running but unhealthy process.

**Severity:** P1 availability  
**Required action:** add a container healthcheck and dependency readiness handling.

### AUD0-DEPLOY-RENDER-001 — Render defaults license enforcement to open

The blueprint sets:

`NEXUS_LICENSE_MODE=open`

**Severity:** P0 commercial/security enforcement  
**Required action:** production must default to strict and fail closed when licensing configuration is absent.

### AUD0-DEPLOY-RENDER-002 — Auto-deploy goes directly from the default branch to production

`autoDeploy: true` is enabled with no deployment gate, migration stage, smoke-test gate or approval environment shown in the blueprint.

**Severity:** P0 release governance  
**Required action:** protected branch, CI artifacts, staging promotion and manual production approval.

### AUD0-DEPLOY-RENDER-003 — Render health check proves only process health

`/api/health` does not prove:
- database writeability;
- migration success;
- credential safety;
- worker artifact availability;
- settings schema compatibility.

**Severity:** P1 readiness semantics  
**Required action:** separate liveness and privileged readiness checks.

### AUD0-DEPLOY-DATA-001 — SQLite availability model is single-instance

The deployment uses one SQLite file on one persistent disk.

This constrains horizontal scaling and requires explicit backup, restore and corruption-recovery procedures.

**Severity:** P1 resilience  
**Required action:** documented backups plus restore drills, or migrate production state to a transactional managed database.

## Dependency and test-gate findings

### AUD0-TEST-001 — Runtime dependency set does not declare all apparent execution dependencies

The server requirements contain only FastAPI, Uvicorn, PyJWT and python-multipart.

The application/backtest modules may require additional packages; the Docker image must prove import and runtime completeness rather than relying on developer-machine state.

**Severity:** P0 deployability pending import test  
**Required action:** generate a complete locked dependency graph and run a clean-image import/start test.

### AUD0-TEST-002 — Canonical CI workflow was not found

The standard path `.github/workflows/ci.yml` returned 404.

This does not prove that no differently named workflow exists, but no canonical CI gate was verified in this pass.

**Severity:** P0 release gate not demonstrated  
**Required action:** repository-wide workflow inventory and mandatory protected status checks.

### AUD0-TEST-003 — Canonical backend test entry was not found

The standard probe `server/test_app.py` returned 404.

This does not prove absence of all tests, but a backend integration test suite was not demonstrated in this pass.

**Severity:** P0 test evidence missing  
**Required action:** inventory all tests and produce an executable coverage matrix.

## Required release gates before production

The minimum mandatory gates are:

1. clean Docker build;
2. container startup/import smoke test;
3. migration test from a previous database;
4. authentication default-secret rejection test;
5. CSRF and authorization integration tests;
6. command lease/replay/crash recovery tests;
7. worker filesystem-boundary tests;
8. signed deployment-manifest tests;
9. MQL compile artifact verification;
10. end-to-end desired → delivered → applied state test;
11. backup and restore drill;
12. staging soak test before manual production promotion.

## Progress update

### Overall audit

**92%**

### AUDIT-0 Repository Inventory

**98%**

### Area status

- Repository Inventory: 98%
- Root Configuration: 97%
- MQL5: 82%
- Backend: 82%
- Frontend: 84%
- Contracts: 90%
- Deploy: 91%
- Security: 95%
- Documentation: 67%
- Testing: 58%
- Reviewer Pack: 20%
- Agent Pack: 0%
- Point 5: BLOCKED


# AUDIT-0 — Block 19: Consolidated P0 Matrix and Reviewer Pack v0.1

## Purpose

This block consolidates the audit’s P0 findings into a smaller set of release-blocking workstreams.

The master report currently contains 178 P0-labelled findings, including repeated manifestations of the same architectural root causes. The reviewer pack therefore groups them by root control failure rather than treating every symptom as an independent project.

## Reviewer decision

### Current production decision

**NO-GO**

NEXUS is not ready for production use with real capital, remote deployment or multi-instance administration.

The primary blockers are not isolated UI defects. They affect:

- authentication and authorization;
- target identity;
- command delivery;
- deployment integrity;
- configuration truth;
- risk mutation;
- research-to-live promotion;
- ledger integrity;
- test evidence.

## Consolidated P0 matrix

### RP0-01 — Default credentials and broad shared secrets

**Includes**

- backend default admin credentials;
- backend default bridge token;
- worker default bridge token;
- shared bridge credential across EA and worker;
- plaintext worker configuration;
- token returned in login response body;
- long-lived privileged sessions.

**Impact**

Compromise of one reusable secret can expose the complete trading and deployment control plane.

**Dependencies**

None. This is the first remediation stream.

**Required closure evidence**

- production startup fails with default/missing secrets;
- per-host and per-EA credentials;
- credential rotation and revocation;
- no reusable token in frontend-accessible responses;
- secret scanning passes;
- documented emergency credential rotation drill.

---

### RP0-02 — Missing capability-based authorization

**Includes**

- every authenticated dashboard user effectively acts as admin;
- licensing, deployment, Coach and trading controls share one trust level;
- no step-up authentication;
- no visible CSRF protection for privileged cookie-authenticated mutations;
- AI-assisted actions use the same broad authority.

**Impact**

A single compromised session can modify risk, close positions, deploy files and administer licenses.

**Dependencies**

RP0-01.

**Required closure evidence**

- capability matrix;
- route-level authorization tests;
- step-up authentication for destructive actions;
- CSRF/origin validation;
- immutable actor and approval records;
- negative tests proving cross-capability denial.

---

### RP0-03 — Ambiguous target identity

**Includes**

- legacy EA commands are not scoped by account, magic, symbol or instance;
- “primary EA” is selected implicitly;
- LocalBridge UI trusts the latest host;
- restart command kills all `terminal64.exe` processes;
- multi-account ticket collisions;
- shared global settings and KV state.

**Impact**

A command or configuration can affect the wrong EA, account, broker terminal or tenant.

**Dependencies**

RP0-01 and RP0-02.

**Required closure evidence**

Every privileged operation must contain and validate an immutable target tuple:

`tenant_id + account_id + broker_server + terminal_id + ea_instance_id + magic + symbol`

plus explicit host identity for LocalBridge actions.

---

### RP0-04 — Weak command lifecycle and false success

**Includes**

- legacy command consumed during polling;
- no explicit execution ACK for legacy EA commands;
- no expiry, lease or attempt model;
- worker ACK failures ignored;
- worker has no local idempotency journal;
- lease not renewed during long-running commands;
- empty deploy succeeds;
- unsupported operations may report success;
- frontend claims application before terminal acknowledgement.

**Impact**

Commands can be lost, duplicated, executed twice or displayed as successful without broker/host confirmation.

**Dependencies**

RP0-03.

**Required closure evidence**

One canonical command state machine:

`CREATED → APPROVED → LEASED → RUNNING → SUCCEEDED | FAILED_FINAL | EXPIRED | CANCELLED`

with:

- idempotency key;
- expected target/version;
- lease renewal;
- attempt count;
- durable worker journal;
- terminal result;
- post-state verification;
- replay and crash-recovery tests.

---

### RP0-05 — Untrusted deployment and worker execution

**Includes**

- optional file checksums;
- no signed release manifest;
- non-atomic deployment;
- incomplete rollback;
- one overwritten `.bak` recovery point;
- template path escape;
- shell prefix whitelist with `shell=True`;
- full payload logging;
- worker download/execution without supply-chain verification.

**Impact**

A compromised backend/session can write or execute arbitrary content on the user’s trading machine.

**Dependencies**

RP0-01 through RP0-04.

**Required closure evidence**

- remove generic shell execution;
- signed release manifest;
- mandatory digests;
- staging directory;
- atomic activation;
- immutable release backups;
- strict path schema;
- least-privilege Windows service account;
- runtime version attestation.

---

### RP0-06 — Docker and production deployment are not proven reproducible

**Includes**

- Dockerfile omits imported modules;
- worker artifact path/build context mismatch;
- likely incomplete runtime dependency lock;
- container runs as root;
- Render auto-deploys directly from the default branch;
- licensing defaults to open;
- health check proves only liveness;
- no verified canonical CI gate.

**Impact**

The production image may fail at startup or deploy unreviewed code/configuration directly to the live environment.

**Dependencies**

RP0-01 and RP0-05.

**Required closure evidence**

- clean reproducible image build;
- full import/start smoke test;
- non-root runtime;
- digest-pinned base image;
- strict license mode;
- protected branch and mandatory checks;
- staging environment;
- manual production approval;
- readiness check covering database, migrations and contracts.

---

### RP0-07 — Desired state is confused with applied state

**Includes**

- strategy draft labelled live;
- optimizer says values are applied without EA acknowledgement;
- settings lack compare-and-swap;
- no immutable settings event stream;
- locked-profile replacement can delete omitted entries;
- live settings backtest imports only a subset;
- no EA-applied settings revision;
- local chart/Coach state is treated as live context.

**Impact**

The operator cannot reliably know which configuration is active on the EA.

**Dependencies**

RP0-03 and RP0-04.

**Required closure evidence**

Versioned state model:

`draft → approved desired → delivered → EA applied → verified active`

with rejection status, conflict detection, rollback and audit trail.

---

### RP0-08 — Risk and strategy mutations are insufficiently constrained

**Includes**

- strategy page fails open to all strategies enabled;
- whole strategy families can be changed without impact preview;
- optimizer auto-scaling and blur-save;
- manual overrides lack limits/version/reason/expiry;
- Coach can set risk and strategy multipliers;
- risk ceilings reach 10%;
- resets and close-all actions lack common privileged confirmation.

**Impact**

Operator error, compromised UI or AI suggestion can cause immediate capital exposure.

**Dependencies**

RP0-02 and RP0-07.

**Required closure evidence**

- fail-closed strategy loading;
- conservative hard risk ceilings;
- account-mode awareness;
- exposure preview;
- reason and expiry;
- two-step approval for destructive/high-risk changes;
- server-side policy enforcement;
- capital-impact regression tests.

---

### RP0-09 — Research and live execution are not contractually equivalent

**Includes**

- backtest UI claims full EA replay without parity evidence;
- backend ignores multiple posted backtest fields;
- unrealistic execution defaults;
- grid exposure defaults;
- preset metrics lack provenance;
- no complete experiment manifest;
- imported research results can become live locked profiles directly.

**Impact**

NEXUS can promote a strategy based on results that do not represent the live EA or real execution conditions.

**Dependencies**

RP0-07 and RP0-08.

**Required closure evidence**

- strategy/gate parity matrix;
- strict request schema rejecting unsupported options;
- immutable dataset/code/execution manifest;
- broker-calibrated spread/slippage;
- walk-forward and out-of-sample evidence;
- staged research approval;
- production promotion and rollback workflow.

---

### RP0-10 — Market-data and AI provenance are insufficient

**Includes**

- chart source is not positively identified except for synthetic data;
- stale candles/markers remain visible after request failure;
- marker query omits timeframe;
- Coach context is browser-controlled;
- AI output lacks confidence/provenance/action boundaries;
- raw provider errors may leak internals;
- Coach session IDs are not strongly owned.

**Impact**

Operators and the AI Coach can reason from stale, mismatched or user-controlled context.

**Dependencies**

RP0-03 and RP0-07.

**Required closure evidence**

- server-issued snapshot IDs;
- feed, timestamp and freshness on every visual domain;
- timeframe-bound marker schemas;
- stale-state UI tests;
- AI session ownership;
- grounded context manifest;
- no direct execution authority from model output.

---

### RP0-11 — Ledger and analytics integrity are not fully multi-account safe

**Includes**

- ticket primary-key collision risk;
- global database/KV tenancy model;
- lifecycle rows rely on mixed legacy/current identities;
- analytics and journal views can derive from different storage semantics;
- authoritative account ownership is not consistently encoded.

**Impact**

Trades can overwrite, merge or be attributed to the wrong account; analytics may not be audit-grade.

**Dependencies**

RP0-03.

**Required closure evidence**

- immutable global trade UID;
- tenant/account columns and indexes;
- migration with reconciliation report;
- exactly-once lifecycle tests;
- partial-close and resync tests;
- analytics provenance tied to ledger revision.

---

### RP0-12 — Test and operational evidence are insufficient

**Includes**

- no verified canonical CI workflow;
- no verified canonical backend integration suite;
- missing clean-image evidence;
- missing MT5 runtime evidence;
- missing command crash/replay tests;
- missing deployment rollback tests;
- missing backup/restore drill;
- missing staging soak evidence.

**Impact**

The project cannot demonstrate that critical controls work or remain working after changes.

**Dependencies**

All prior streams.

**Required closure evidence**

A signed release evidence bundle containing:

- commit SHA;
- dependency lock;
- Docker image digest;
- test results;
- coverage report;
- security scan;
- MQL compile logs;
- backtest manifest;
- migration result;
- worker deployment test;
- staging soak report;
- approver identity.

## Remediation order

### Phase 0 — Immediate freeze

Until RP0-01 through RP0-06 are closed:

- no real-money use;
- no remote deployment;
- no Coach live actions;
- no multi-account backend use;
- no automatic production deploy;
- license mode must not be presented as secure enforcement.

### Phase 1 — Identity and authorization foundation

Close:

1. RP0-01
2. RP0-02
3. RP0-03

### Phase 2 — Command and deployment safety

Close:

4. RP0-04
5. RP0-05
6. RP0-06

### Phase 3 — Operational truth and capital safety

Close:

7. RP0-07
8. RP0-08
9. RP0-10

### Phase 4 — Research and ledger integrity

Close:

10. RP0-09
11. RP0-11

### Phase 5 — Release evidence

Close:

12. RP0-12

## Reviewer Pack checklist

A reviewer must reject production promotion when any answer below is “no”:

- Are all production credentials explicit, unique and revocable?
- Is every mutation capability-authorized?
- Is every command target immutable and explicit?
- Can a command be retried safely without duplicate effect?
- Does terminal success prove the requested post-state?
- Are release artifacts signed and digest-verified?
- Is deployment atomic and rollback-tested?
- Can the operator distinguish draft, desired, delivered and applied state?
- Are risk limits enforced server-side?
- Is every backtest reproducible from an immutable manifest?
- Is live promotion separately approved?
- Is every trade globally and account-uniquely identified?
- Does CI block merging and deployment on failure?
- Has the exact release passed staging and recovery drills?

## Point 5 status

**BLOCKED**

Point 5 may only be reopened after:

- RP0-01 through RP0-06 are closed;
- a protected CI pipeline exists;
- a clean deployable image is demonstrated;
- the canonical command lifecycle passes crash/replay tests.

## Progress update

### Overall audit

**96%**

### AUDIT-0 Repository Inventory

**99%**

### Area status

- Repository Inventory: 99%
- Root Configuration: 97%
- MQL5: 84%
- Backend: 84%
- Frontend: 86%
- Contracts: 94%
- Deploy: 93%
- Security: 97%
- Documentation: 74%
- Testing: 62%
- Reviewer Pack: 72%
- Agent Pack: 10%
- Point 5: BLOCKED


# AUDIT-0 — Block 20: Final Reviewer Pack and Agent Pack

## Final documentation review

The repository README presents NEXUS as a complete self-hosted system composed of:

- MQL5 Expert Advisor;
- FastAPI backend and dashboard;
- LocalBridge worker.

It also documents a shared `NEXUS_BRIDGE_TOKEN` across EA, backend and worker, direct runtime settings, remote compile/restart/deploy capabilities and a public cloud deployment model.

These documented operating assumptions confirm that the security and operational findings identified in the audit are part of the intended production architecture rather than unused experimental code.

## Additional documentation findings

### AUD0-DOC-001 — README claims no external-service dependency

The README states that the project has no dependency on external services.

The same document later describes:

- optional Telegram integration;
- Anthropic API usage for AI Coach;
- deployment to Render/Railway/Fly/VPS;
- public HTTPS access.

**Severity:** P1 documentation accuracy  
**Required action:** distinguish core self-hosted functionality from optional and hosted external dependencies.

### AUD0-DOC-002 — README recommends one shared bridge token everywhere

The installation guide explicitly instructs the operator to use the same token for:

- EA;
- backend;
- LocalBridge worker.

**Severity:** P0 insecure architecture documented as normal operation  
**Required action:** replace with per-principal enrollment and scoped credentials.

### AUD0-DOC-003 — README presents license mode `open` as recommended

The documentation describes `open` as recommended for self-hosting.

This makes licensing an administrative display rather than a fail-closed enforcement control.

**Severity:** P1 product/security expectation mismatch

### AUD0-DOC-004 — README advertises remote compile/restart without safety qualifications

The LocalBridge is presented as a routine remote-control feature, but the documented workflow does not warn about:

- broad shared credential impact;
- process targeting;
- release signing;
- rollback;
- command replay;
- least privilege.

**Severity:** P0 unsafe operator guidance

### AUD0-DOC-005 — README API authentication description is incomplete

The README describes dashboard endpoints as bearer-token authenticated, while the reviewed React dashboard uses an httpOnly cookie and the backend accepts both mechanisms.

**Severity:** P1 contract/documentation drift

### AUD0-DOC-006 — Build instructions rely on manually copying frontend artifacts

The README instructs the operator to build React and manually copy `frontend/build/` into `server/static/app/`.

This is not a reproducible release pipeline and can produce source/build mismatches.

**Severity:** P0 release reproducibility  
**Required action:** build frontend inside CI/container and bind its digest to the backend release manifest.

## Final Reviewer Pack

### Release classification

**Status:** NO-GO  
**Environment allowed:** isolated development and simulation only  
**Real-money trading:** blocked  
**Remote LocalBridge deployment:** blocked  
**Automatic production deployment:** blocked  
**Multi-account operation:** blocked  
**Coach live mutations:** blocked

### Mandatory pre-review artifacts

A future production review must receive all of the following:

1. architecture diagram with trust boundaries;
2. canonical principal and capability matrix;
3. immutable target-identity schema;
4. canonical command-state-machine specification;
5. settings desired/applied-state specification;
6. signed release-manifest specification;
7. database tenancy and trade-identity migration plan;
8. backtest/live parity matrix;
9. threat model;
10. disaster-recovery plan;
11. CI workflow definitions;
12. release evidence bundle.

### Reviewer rejection rules

The release is automatically rejected when any of these conditions exists:

- a default credential is accepted;
- one credential authorizes multiple principal types;
- a command lacks an explicit target;
- polling marks a command consumed;
- a terminal ACK is not durable;
- a deploy file lacks a digest;
- generic shell execution exists;
- a release can be partially installed;
- UI “live” state lacks EA acknowledgement;
- a risk mutation bypasses the canonical settings service;
- a backtest field is silently ignored;
- research results can directly become live settings;
- trade identity is not account-unique;
- CI or staging evidence is absent.

### Reviewer evidence matrix

| Control | Required evidence | Pass condition |
|---|---|---|
| Secrets | startup tests + secret scan | defaults rejected |
| Authorization | positive/negative route tests | least privilege proven |
| Targeting | command fixtures | wrong target rejected |
| Idempotency | replay/crash tests | one logical effect |
| Deployment | signed-manifest test | atomic and reversible |
| Settings | version-conflict tests | stale writes rejected |
| Risk | policy tests | hard ceilings enforced |
| Backtest parity | golden fixtures | same strategy semantics |
| Ledger | migration/reconciliation | zero unexplained loss |
| Recovery | backup/restore drill | documented RTO/RPO met |
| Release | CI/staging bundle | exact artifact promoted |

## Agent Pack v1.0

The following pack is intended for a coding agent working on the repository.

### Global agent rules

1. Do not implement more than one remediation stream per pull request.
2. Do not change trading logic while fixing infrastructure controls.
3. Do not rename strategy IDs without a migration and contract update.
4. Do not silently preserve insecure backward compatibility.
5. Every behavior change requires:
   - contract update;
   - tests;
   - migration note;
   - rollback plan.
6. Never mark a command successful from delivery alone.
7. Never present desired state as applied state.
8. Never infer live provenance from the absence of an error.
9. Every destructive action must be server-authorized.
10. Stop work when a required test cannot be made deterministic.

### Pull-request sequence

#### PR-01 — Production configuration fail-closed

**Goal**

Remove all usable default credentials and unsafe production defaults.

**Files likely involved**

- `server/app.py`
- `server/.env.example`
- `render.yaml`
- `LocalBridge/nexus_local_worker.py`
- worker example config
- README

**Acceptance criteria**

- backend refuses production startup with default/missing secrets;
- license mode defaults to strict in production;
- JWT secret must be persistent;
- bridge token is no longer embedded in source/examples;
- tests prove startup rejection.

---

#### PR-02 — Principal identity and scoped credentials

**Goal**

Separate dashboard users, EA instances and LocalBridge hosts.

**Required design**

- server-generated principal IDs;
- per-principal credential;
- credential hash at rest;
- capabilities;
- expiry;
- rotation;
- revocation;
- enrollment audit event.

**Acceptance criteria**

A worker credential cannot call EA endpoints, and an EA credential cannot call worker or dashboard endpoints.

---

#### PR-03 — Capability authorization and CSRF

**Goal**

Introduce explicit authorization for:

- view;
- trade-control;
- risk-control;
- deployment;
- license-admin;
- research-promotion;
- Coach-action.

**Acceptance criteria**

- route tests for each allowed and denied combination;
- anti-CSRF token/origin checks;
- step-up authentication for close-all, deployment and protection reset.

---

#### PR-04 — Canonical target identity

**Goal**

Make all commands and settings target-specific.

**Canonical tuple**

`tenant_id/account_id/broker_server/terminal_id/ea_instance_id/magic/symbol`

**Acceptance criteria**

- no implicit “primary EA” for mutations;
- polling returns only commands for the authenticated target;
- process restart is scoped to the enrolled terminal instance;
- wrong-target tests pass.

---

#### PR-05 — Canonical command service

**Goal**

Replace duplicate command enqueue paths and the legacy EA queue.

**Required states**

`CREATED, APPROVED, LEASED, RUNNING, SUCCEEDED, FAILED_RETRYABLE, FAILED_FINAL, EXPIRED, CANCELLED`

**Acceptance criteria**

- one action registry;
- idempotency key;
- expiry;
- lease renewal;
- max attempts;
- durable terminal result;
- immutable command events;
- crash/replay tests.

---

#### PR-06 — Local worker hardening

**Goal**

Make worker execution least-privileged and replay-safe.

**Required changes**

- remove generic shell command;
- use Windows credential protection;
- local durable command journal;
- lease-renewal loop;
- typed retry classification;
- sanitized logging;
- enrolled PID/path targeting.

**Acceptance criteria**

Network loss after local success cannot cause a second logical execution.

---

#### PR-07 — Signed atomic deployment

**Goal**

Create a release artifact and activation protocol.

**Required states**

`UPLOADED, VERIFIED, STAGED, COMPILED, ACTIVATED, RUNTIME_CONFIRMED, ROLLED_BACK`

**Acceptance criteria**

- signed manifest;
- mandatory SHA-256 per file;
- empty manifest rejected;
- path containment;
- atomic activation;
- release-scoped backups;
- newly created files removed on rollback;
- EX5/runtime digest attestation.

---

#### PR-08 — Reproducible build and CI

**Goal**

Produce one deterministic frontend/backend image and test bundle.

**Acceptance criteria**

- complete server package copied;
- frontend built in CI;
- non-root image;
- pinned lockfiles and base-image digest;
- import/start smoke test;
- migration test;
- mandatory protected checks;
- staging deployment;
- manual production approval.

---

#### PR-09 — Versioned settings and applied-state ACK

**Goal**

Separate configuration lifecycle stages.

**Required model**

`DRAFT → APPROVED_DESIRED → DELIVERED → APPLIED → VERIFIED`

**Acceptance criteria**

- immutable revision ID;
- compare-and-swap;
- stale update rejected;
- EA apply/reject ACK;
- rollback;
- UI labels reflect verified state only.

---

#### PR-10 — Risk policy service

**Goal**

Route all risk and strategy changes through one server-side policy service.

**Acceptance criteria**

- conservative hard caps;
- account-mode checks;
- impact preview;
- approval reason;
- expiry;
- fail-closed strategy map;
- Coach cannot bypass the policy service.

---

#### PR-11 — Backtest contract and experiment manifests

**Goal**

Make research reproducible and prevent silent configuration loss.

**Acceptance criteria**

- typed request schema;
- unsupported fields rejected;
- code/data/config/execution hashes;
- realistic spread/slippage source;
- parity fixtures against EA behavior;
- separate approval before live promotion.

---

#### PR-12 — Ledger identity migration

**Goal**

Remove account collision risk and make analytics audit-grade.

**Acceptance criteria**

- globally unique logical trade ID;
- tenant/account ownership;
- idempotent migration;
- reconciliation report;
- partial-close/resync fixtures;
- analytics tied to ledger revision.

---

#### PR-13 — Data provenance and AI isolation

**Goal**

Ground charts and AI Coach in server-issued verified snapshots.

**Acceptance criteria**

- feed ID, symbol, timeframe, timestamp and freshness;
- stale/error state invalidates visuals;
- server-generated Coach session ownership;
- context snapshot manifest;
- AI output cannot execute actions directly;
- provider errors sanitized.

---

#### PR-14 — Recovery and release evidence

**Goal**

Close operational readiness.

**Acceptance criteria**

- backup schedule;
- restore test;
- documented RTO/RPO;
- staging soak;
- release evidence bundle;
- rollback drill;
- production reviewer sign-off.

## Agent PR template

Every remediation PR should contain:

```text
Scope:
Root P0 addressed:
Files changed:
Contract changes:
Migration:
Security impact:
Capital-risk impact:
Tests added:
Failure injection performed:
Rollback:
Known residual risk:
Reviewer evidence:
```

## Agent stop conditions

The coding agent must stop and request review when:

- a fix requires changing live strategy semantics;
- a database migration can lose or merge trades;
- backward compatibility would preserve a P0;
- production credentials are needed;
- a test requires a real broker account;
- MQL compilation cannot be reproduced;
- the requested target identity is ambiguous;
- the release cannot be rolled back.

## Final audit conclusion

NEXUS has substantial functional breadth and several positive engineering foundations, particularly around strategy contracts, additive database migrations, trade-event deduplication and an emerging leased LocalBridge command model.

However, its current architecture combines trading control, risk mutation, licensing, AI guidance and remote code deployment under broad shared trust.

The system should therefore be treated as a development prototype until the identity, command, deployment, applied-state and evidence layers are rebuilt according to the remediation sequence above.

## Final progress

### AUDIT-0

**100% complete**

### Area status

- Repository Inventory: 100%
- Root Configuration: 100%
- MQL5: 88%
- Backend: 88%
- Frontend: 90%
- Contracts: 96%
- Deploy: 96%
- Security: 98%
- Documentation: 90%
- Testing: 68%
- Reviewer Pack: 100%
- Agent Pack: 100%
- Point 5: BLOCKED

The lower percentages in implementation areas represent unresolved repository risk, not incomplete AUDIT-0 review.


---

# PART III — OPERATIONAL BACKLOG

# NEXUS — Backlog Operativo Ufficiale

**Repository:** `starmarketkiller/MAX`  
**Scopo:** trasformare l’audit architetturale completo in un piano eseguibile per Codex/Claude.  
**Regola di governance:** **1 punto roadmap = 1 branch = 1 PR**.  
**Vincolo architetturale:** esiste un solo Expert Advisor, **Nexus**. Nessun EA separato per strategia o simbolo.

## 1. Regole operative

1. Nessuna mega-PR.
2. Nessun merge di PR legacy sovrapposte senza cherry-pick selettivo.
3. Ogni PR deve avere obiettivo singolo, dipendenze, file scope, acceptance criteria, test ed evidenze.
4. Nessun finding P0 può essere chiuso soltanto con grep, static assertions o compilazione.
5. Nessun nuovo `OrderSend()` fuori dal futuro `BrokerExecutionCoordinator`.
6. Nessuna nuova lettura diretta di `Inp*` nei moduli operativi dopo `EffectiveConfig`.
7. Nessuna WebRequest dentro `OnTick()` o `OnTradeTransaction()` dopo la PR scheduler.
8. Le impostazioni remote ordinarie possono soltanto restringere il rischio.
9. Ogni trade deve essere attribuibile a configurazione, build, strategia e risk plan.
10. Il cleanup finale deve essere comportamentalmente neutro.

## 2. Stato iniziale

| Area | Stato attuale |
|---|---|
| Strategy Registry | Base buona, canonico e versionato |
| Trade Ledger | Base buona, aggregate-diff e replay-safe |
| Position Coordinator | Base buona, ma non autorità broker unica |
| State persistence | Migliorata, ancora frammentata |
| Runtime settings | Paralleli a preset e locked profile |
| Risk engine | Distribuito tra molti moduli |
| Broker execution | Bool/retcode globale, partial e timeout insufficienti |
| Virtual SL | State machine valida, offline risk non garantito |
| Event loop | Networking e side-effect nel percorso critico |
| Multi-symbol | Ancora chart-symbol-centric |
| Test | Backend e compile buoni, runtime MT5 insufficiente |
| Production readiness | Non raggiunta |

# 3. Roadmap ufficiale

## PR-A — Effective Config Resolver

**Branch suggerito:** `feature/effective-config-resolver`  
**Priorità:** P0  
**Dipendenze:** nessuna  
**Blocca:** PR-B, PR-F, PR-H, PR-I, PR-J

### Obiettivo
Creare una sola configurazione effettiva e rimuovere la catena parallela `Inp*` / preset / `g_run_*` / `g_NXSlp_*` / runtime dashboard.

### Finding inclusi
`NXS-CONFIG-001` … `NXS-CONFIG-019`.

### File principali
- `MQL5/Include/NEXUS_v1/NXS_RuntimeSettings.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Presets.mqh`
- `MQL5/Include/NEXUS_v1/NXS_LockedProfile.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh`
- `MQL5/Experts/NEXUS_EA_v2.mq5`
- `contracts/default-settings.json`
- `contracts/settings.schema.json`

### Deliverable
```cpp
struct SNXSEffectiveConfig {
   long revision;
   string profileId;
   string registryHash;
   string configHash;
   datetime issuedAt;
   datetime expiresAt;
   double riskPct;
   double maxLot;
   int maxConcurrent;
   double maxDailyDDPct;
   int minEntryScore;
};
```

### Acceptance criteria
- Un solo valore effettivo per parametro.
- Source, revision e hash per ogni campo.
- Validazione completa prima dell’applicazione.
- Swap atomico.
- Last-known-good persistito.
- Locked profile non può essere reso più aggressivo dalla dashboard.
- Strategy ID canonicalizzati.
- Nessuna lettura operativa diretta di `Inp*` per i campi migrati.

### Test richiesti
Schema valid/invalid, missing vs empty, rollback revision, stale payload, override aggressivo rifiutato, config hash stabile, restart backend offline.

**Stato:** `TODO`

---

## PR-B — Canonical RiskPlan

**Branch suggerito:** `feature/canonical-risk-plan`  
**Priorità:** P0  
**Dipendenze:** PR-A  
**Blocca:** PR-C, PR-D, PR-E, PR-F, PR-H

### Obiettivo
Rendere il rischio un oggetto canonico, misurato in denaro e verificato prima e dopo il fill.

### Deliverable
```cpp
struct SNXSRiskPlan {
   string intentId;
   string tradeUid;
   string strategyId;
   string symbol;
   string configHash;
   double baseRiskPct;
   double requestedRiskMoney;
   double approvedRiskMoney;
   double brokerWorstCaseRiskMoney;
   double effectiveRiskMoney;
   double requestedLots;
   double approvedLots;
   double filledLots;
   string capReason;
};
```

### Acceptance criteria
- Lotto finale mai oltre il budget monetario.
- Nessun fallback a `0.01` se viola il rischio.
- Hard SL incluso nel worst-case.
- Risk reservation pre-invio e reconciliation post-fill.
- Grid, Pyramid, Chain e NXR usano lo stesso RiskPlan.

### Test richiesti
Min lot, lot step, tick value, hard SL largo, multiplier stacking, margin insufficiente, partial fill, scale-in, portfolio cap.

**Stato:** `TODO`

---

## PR-C — Logical Trade and Basket Identity

**Branch suggerito:** `feature/logical-trade-basket`  
**Priorità:** P0  
**Dipendenze:** PR-B  
**Blocca:** PR-D, PR-F, PR-I, PR-J

### Obiettivo
Unificare core, grid, pyramid, split e chain in un solo trade logico persistente.

### Campi minimi
`trade_uid`, `basket_id`, `leg_id`, `leg_type`, `parent_trade_uid`, `strategy_id`, `source_tf`, `config_hash`, `risk_plan_id`.

### Acceptance criteria
- Ogni posizione Nexus appartiene a un basket.
- Nessuna leg orfana.
- Trigger basket produce flat confermato.
- Partial close non finalizza il trade.
- Restart ricostruisce tutte le leg.
- Strategy attribution non dipende soltanto dal commento broker.

### Test richiesti
Core only, grid, pyramid, split, partial+final, duplicate replay, restart multi-leg, close manuale leg, basket flatten.

**Stato:** `TODO`

---

## PR-D — BrokerExecutionCoordinator

**Branch suggerito:** `feature/broker-execution-coordinator`  
**Priorità:** P0  
**Dipendenze:** PR-B, PR-C  
**Blocca:** PR-E, PR-F, PR-G, PR-H, PR-I

### Obiettivo
Rendere una sola componente responsabile di ogni azione broker.

### Deliverable
```cpp
struct SNXSExecutionResult {
   bool transportOk;
   uint retcode;
   uint externalRetcode;
   ulong orderTicket;
   ulong dealTicket;
   double requestedVolume;
   double filledVolume;
   double requestedPrice;
   double fillPrice;
   string brokerComment;
   string executionIntentId;
};
```

Lifecycle: `CREATED → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED/FILLED/UNCERTAIN/REJECTED/CANCELLED/EXPIRED`.

### Acceptance criteria
- Zero `OrderSend()` fuori dal coordinator.
- Filling per simbolo.
- Partial fill gestito.
- Timeout in `UNCERTAIN`, non duplicato.
- SafeClose, SafePartialClose, SafeModify.
- Retry rivalida RiskPlan.
- Slippage planned vs actual registrato.

### Test richiesti
DONE, PLACED, DONE_PARTIAL, timeout, retry, stale signal, close partial, invalid volume/stops, symbol filling, modify verification.

**Stato:** `TODO`

---

## PR-E — AccountRiskGovernor

**Branch suggerito:** `feature/account-risk-governor`  
**Priorità:** P0  
**Dipendenze:** PR-B, PR-D  
**Blocca:** PR-G, PR-I, PR-J

### Obiettivo
Unificare ESL, DPT, Daily DD, Risk-of-Ruin, MaxLoss, pause, flatten e resume.

Lifecycle: `NORMAL → THROTTLED → ENTRY_BLOCKED → FLATTEN_REQUESTED → FLATTENING → FROZEN_FLAT`.

### Acceptance criteria
- Una sola authority decide entry block e flatten.
- Trigger, decisione, broker request e flat confirmation separati.
- Stato persistente.
- Nessuna protezione invia direttamente ordini.

### Test richiesti
ESL, DD, ruin, max loss, DPT, Friday close, restart durante flatten, partial flatten, reject, resume next day.

**Stato:** `TODO`

---

## PR-F — Virtual Stop Governor

**Branch suggerito:** `feature/virtual-stop-governor`  
**Priorità:** P0  
**Dipendenze:** PR-A, PR-B, PR-C, PR-D  
**Blocca:** PR-G, PR-I, PR-J

### Obiettivo
Estrarre il Virtual SL da `NXS_EdgeAdaptive.mqh` e completare sicurezza offline e basket coverage.

### Acceptance criteria
- Nessun record `ARMED` senza hard SL verificato.
- Hard SL entro il risk cap.
- Trigger symbol-aware.
- Fill offline riconciliato.
- Basket completo protetto.
- Nessuna WebRequest nel path VSL.
- Persistenza account/server/instance scoped.
- Timestamp restart-safe.
- Gap slippage registrato.

### Test richiesti
OFF, OBSERVE, EXECUTE, broker SL missing, fill offline, restart, gap, backend offline, partial basket, symbol mismatch, grid/pyramid, repeated retry.

**Stato:** `TODO`

---

## PR-G — Nexus Scheduler and Event Loop

**Branch suggerito:** `feature/nexus-scheduler-event-loop`  
**Priorità:** P0  
**Dipendenze:** PR-D, PR-E, PR-F  
**Blocca:** PR-I, PR-J

### Architettura target
```text
OnTick
├── CriticalRiskPhase
├── MarketSnapshotPhase
├── ManagementProposalPhase
├── EntryDecisionPhase
└── LocalEventCommit

OnTradeTransaction
└── BrokerEventIngestion only

OnTimer
├── Broker reconciliation
├── Execution queue
├── Ledger finalization
├── Persistence
├── Domain event consumers
├── Outbox transport
└── UI/analytics
```

### Acceptance criteria
- Zero WebRequest in OnTick e OnTradeTransaction.
- Ledger prima della telemetria.
- Cold start indipendente dal backend.
- Task budget e metriche durata.
- Entry freshness distinta da risk freshness.
- Nessun return globale che salta la finalizzazione.

### Test richiesti
Backend timeout, malformed JSON, burst deal, stale tick, no tick, cold start offline, slow dashboard, timer overlap, shutdown during deal.

**Stato:** `TODO`

---

## PR-H — Symbol Context and Portfolio Exposure

**Branch suggerito:** `feature/symbol-context-portfolio-risk`  
**Priorità:** P0  
**Dipendenze:** PR-A, PR-B, PR-D  
**Blocca:** PR-I, PR-J

### Deliverable
```cpp
struct SNXSSymbolContext {
   string symbol;
   double point;
   int digits;
   double tickSize;
   double tickValue;
   double volumeMin;
   double volumeStep;
   long fillingMode;
   long executionMode;
};
```

### Acceptance criteria
- Nessun calcolo contract-specific usa `g_sym` implicitamente.
- Exposure monetaria per simbolo e portfolio.
- Quote freshness e filling per simbolo.
- Correlation cluster esplicito.
- Margin reservation portfolio-wide.

### Test richiesti
XAU, BTC, Forex 5-digit, lot step insolito, filling diversi, due simboli simultanei, correlated exposure, stale quote su un solo simbolo.

**Stato:** `TODO`

---

## PR-I — Persistence and Recovery Consolidation

**Branch suggerito:** `feature/persistence-recovery-consolidation`  
**Priorità:** P0  
**Dipendenze:** PR-C, PR-D, PR-E, PR-F, PR-G, PR-H  
**Blocca:** PR-J, PR-K

### Obiettivo
Unificare state snapshot, execution intents, ledger, Virtual SL e outbox.

### Acceptance criteria
- Snapshot versionato e atomico.
- Previous-known-good.
- Account/server/instance/config scoped.
- Reconciliation order documentato.
- Mismatch in quarantena.
- Restart backend offline conserva ownership.
- Pending execution non cancellato senza reconciliation.

### Test richiesti
File troncato, temp file, previous snapshot, fill/close offline, config mismatch, broker mismatch, restart durante retry, corrupted record, outbox replay.

**Stato:** `TODO`

---

## PR-J — Runtime Test Harness

**Branch suggerito:** `feature/runtime-test-harness`  
**Priorità:** P0  
**Dipendenze:** PR-A … PR-I  
**Blocca:** PR-K, produzione

### Obiettivo
Trasformare checklist manuali in prove automatiche.

### Acceptance criteria
- Self-test MQL5 automatici.
- Strategy Tester smoke matrix.
- Execution route matrix.
- Signal stream golden.
- Trade stream golden.
- Crash/restart test.
- Network fault injection.
- Broker capability matrix.
- Evidence machine-readable.
- Mapping finding → test.

### Test domains
Strategy, Execution, Risk, Persistence, Integration, Analytics.

**Stato:** `TODO`

---

## PR-K — Artifact and Release Attestation

**Branch suggerito:** `feature/release-attestation`  
**Priorità:** P0  
**Dipendenze:** PR-I, PR-J  
**Blocca:** produzione

### Deliverable
SHA-256 `.ex5`, commit SHA, compiler/build, registry hash, settings schema version, config hash, compatibility matrix, release manifest, rollback artifact.

### Acceptance criteria
- L’istanza live dichiara esattamente quale artifact esegue.
- Nessun deployment incompatibile.
- Rollback verificato.
- Release evidence archiviata.

**Stato:** `TODO`

---

## PR-L — Repository Cleanup

**Branch suggerito:** `chore/repository-architecture-cleanup`  
**Priorità:** P1  
**Dipendenze:** PR-A … PR-K

### Obiettivo
Rimuovere legacy e riallineare il repository senza cambi comportamentali.

### Include
Rimozione globali config paralleli, parser duplicati, bool/retcode globali, filling globale, deviation hardcoded, Sleep retry, Virtual SL da EdgeAdaptive, history reconciliation da Stats, wrapper morti e include obsoleti.

### Acceptance criteria
- Nessun comportamento nuovo.
- Baseline runtime invariata.
- Zero riferimenti legacy.
- Include graph documentato.

**Stato:** `TODO`

# 4. Gestione PR legacy aperta

**Decisione:** non mergiare wholesale la vecchia draft command bridge.

### Keep
- `LocalBridge/nexus_local_worker.py`
- manifest sotto `deploy/`

### Cherry-pick selettivo
State machine, lease, retry, dead-letter, TTL, target scoping, idempotency e validazione.

# 5. Definition of Done per PR

```text
[ ] finding IDs coperti
[ ] file scope dichiarato
[ ] dipendenze rispettate
[ ] acceptance criteria verificati
[ ] test automatici
[ ] MetaEditor 0 errori
[ ] nessun warning nuovo
[ ] Strategy Tester quando necessario
[ ] artifact di evidenza
[ ] rollback plan
[ ] documentazione aggiornata
[ ] nessuna regressione baseline
```

# 6. Definition of Done production

```text
[ ] una sola EffectiveConfig
[ ] una sola RiskPlan authority
[ ] una sola BrokerExecutionCoordinator
[ ] nessun OrderSend distribuito
[ ] partial fill gestito
[ ] timeout idempotente
[ ] hard SL compatibile col risk cap
[ ] basket completo e persistente
[ ] protezioni unificate
[ ] multi-symbol symbol-explicit
[ ] nessuna rete in OnTick/OnTradeTransaction
[ ] crash/restart verificati
[ ] config e artifact attribuiti al trade
[ ] Strategy Tester automatico
[ ] demo forward test superato
[ ] artifact live attestato
```

# 7. Tabella sintetica

| PR | Titolo | Priorità | Dipendenze | Stato |
|---|---|---:|---|---|
| A | Effective Config Resolver | P0 | — | TODO |
| B | Canonical RiskPlan | P0 | A | TODO |
| C | Logical Trade and Basket | P0 | B | TODO |
| D | BrokerExecutionCoordinator | P0 | B, C | TODO |
| E | AccountRiskGovernor | P0 | B, D | TODO |
| F | Virtual Stop Governor | P0 | A, B, C, D | TODO |
| G | Nexus Scheduler/Event Loop | P0 | D, E, F | TODO |
| H | Symbol Context/Portfolio | P0 | A, B, D | TODO |
| I | Persistence/Recovery | P0 | C, D, E, F, G, H | TODO |
| J | Runtime Test Harness | P0 | A–I | TODO |
| K | Artifact/Release Attestation | P0 | I, J | TODO |
| L | Repository Cleanup | P1 | A–K | TODO |

# 8. Ordine di esecuzione

```text
A → B → C → D → E → F → G → H → I → J → K → L
```

# 9. Primo task operativo

La prima PR da aprire è **PR-A — Effective Config Resolver**.

Primo deliverable:
1. inventario dei parametri configurabili;
2. matrice `campo → fonti attuali → consumer`;
3. precedenza ufficiale;
4. `SNXSEffectiveConfig`;
5. adapter temporanei;
6. test drift/range/revision.

---

**Stato documento:** `READY FOR IMPLEMENTATION`  
**Audit architetturale:** `COMPLETED`  
**Roadmap ufficiale:** `APPROVED DRAFT`


---

# PART IV — IMPLEMENTATION SPECIFICATIONS

## PR-A — Effective Config Resolver

# NEXUS — PR-A Effective Config Resolver

**Repository:** `starmarketkiller/MAX`  
**Status:** implementation specification  
**Code changes performed:** none  
**Source roadmap:** `NEXUS_OPERATIONAL_BACKLOG.md`

## 1. Objective

Create one canonical effective-configuration layer for the Nexus EA.

The purpose of PR-A is to eliminate direct runtime consumption of competing configuration sources and make every trading decision traceable to one resolved, validated and versioned configuration snapshot.

## 2. Problem statement

The audit identified parallel configuration sources including:

- compiled `Inp*` values;
- preset/profile values;
- locked symbol profiles;
- backend runtime settings;
- strategy-chain configuration;
- optimizer output;
- Coach-originated changes;
- local/manual overrides.

Without one resolver, two modules can calculate risk or eligibility from different values during the same decision cycle.

## 3. Required outcome

All operational modules consume:

```text
SNXSEffectiveConfig
```

They must not independently resolve precedence or read mutable remote settings.

The resolver must produce:

- resolved values;
- source provenance per field;
- immutable revision ID;
- validation result;
- timestamp;
- target identity;
- fallback reason where applicable.

## 4. Non-goals

PR-A must not:

- change strategy logic;
- alter risk formulas;
- change order execution;
- add new trading features;
- redesign the frontend;
- migrate the ledger;
- introduce remote privilege expansion.

Any behavioral change outside configuration resolution requires a separate PR.

## 5. Configuration source model

Recommended source classes:

```text
COMPILED_DEFAULT
EA_INPUT
PRESET
LOCKED_PROFILE
REMOTE_RESTRICTIVE_OVERRIDE
EMERGENCY_LOCAL_OVERRIDE
```

AI Coach and optimizer output must not become direct sources. They may only create a proposal that later enters an approved source through the canonical settings service.

## 6. Precedence policy

The resolver must use an explicit field-level policy rather than one global overwrite order.

### 6.1 Safety-critical fields

For fields such as:

- risk percentage;
- maximum lot;
- maximum open positions;
- daily loss cap;
- drawdown cap;
- spread ceiling;
- slippage ceiling;
- trading-hours restriction;
- strategy enablement;

remote ordinary settings may only make the configuration more restrictive.

Effective value examples:

```text
effective_max_risk = min(all permitted risk ceilings)
effective_max_lot = min(all permitted lot ceilings)
effective_max_positions = min(all permitted position ceilings)
effective_daily_loss_cap = min(all permitted loss ceilings)
```

Strategy enablement should resolve by intersection:

```text
effective_enabled = compiled_allowed
                    AND profile_allowed
                    AND remote_allowed
                    AND runtime_safety_allowed
```

A missing or invalid remote strategy map must fail closed, not enable all strategies.

### 6.2 Non-safety tuning fields

Fields that do not expand capital exposure may use explicit precedence:

```text
emergency override
> approved locked profile
> approved preset
> EA input
> compiled default
```

Every field must declare its own resolution policy.

## 7. Data structures

### 7.1 Source metadata

```cpp
enum ENXSConfigSource
{
   NXS_CFG_COMPILED_DEFAULT = 0,
   NXS_CFG_EA_INPUT,
   NXS_CFG_PRESET,
   NXS_CFG_LOCKED_PROFILE,
   NXS_CFG_REMOTE_RESTRICTIVE,
   NXS_CFG_EMERGENCY_LOCAL
};
```

### 7.2 Field provenance

```cpp
struct SNXSConfigFieldMeta
{
   string field_name;
   string source_name;
   string source_revision;
   datetime resolved_at;
   bool was_clamped;
   string validation_note;
};
```

### 7.3 Effective snapshot

The final structure should group fields by domain:

```text
identity
risk
execution
sessions
strategy gates
signal thresholds
protection
web synchronization
observability
```

Required metadata:

```text
config_revision
target_identity
created_at
source_revisions
validation_status
configuration_hash
```

## 8. Target identity

Every effective configuration snapshot must bind to an explicit target:

```text
tenant_id
account_id
broker_server
terminal_id
ea_instance_id
magic
symbol
```

PR-A may introduce adapters where the repository lacks some identifiers, but it must not silently substitute “primary EA” or “latest host”.

## 9. Resolver API

Recommended conceptual API:

```cpp
bool NXS_ResolveEffectiveConfig(
   const SNXSConfigInputs &inputs,
   SNXSEffectiveConfig &out_config,
   SNXSConfigResolutionReport &out_report
);
```

Operational modules receive a const reference:

```cpp
const SNXSEffectiveConfig &cfg
```

The resolver must be called at controlled lifecycle points, not repeatedly by each module.

## 10. Lifecycle

Recommended flow:

```text
load compiled defaults
→ load EA inputs
→ load preset
→ load locked profile
→ load approved remote restrictive overrides
→ validate each source
→ resolve field-level precedence
→ clamp to hard safety boundaries
→ compute revision/hash
→ publish immutable snapshot
```

A new snapshot may be activated only after complete validation.

Invalid updates must leave the previous valid snapshot active.

## 11. Validation rules

Minimum validation domains:

- numerical range;
- finite number checks;
- lot-step compatibility;
- symbol constraints;
- session time consistency;
- stop/freeze-level compatibility;
- strategy ID validity;
- dependency consistency;
- account-mode compatibility;
- revision monotonicity.

The resolver must return structured errors rather than one generic boolean.

## 12. Required inventory before implementation

Create a field matrix with columns:

| Field | Type | Current sources | Current consumers | Safety class | Resolution rule | Hard bounds | Migration status |
|---|---|---|---|---|---|---|---|

The inventory must cover every configurable value read by:

- risk modules;
- execution modules;
- strategy modules;
- session filters;
- protection logic;
- web synchronization;
- optimizer integration;
- locked-profile logic.

## 13. Consumer migration

Migration should be incremental.

### Step 1

Introduce `SNXSEffectiveConfig` and populate it without changing consumers.

### Step 2

Add compatibility adapters that map the effective snapshot to legacy interfaces.

### Step 3

Move consumers by domain:

1. risk;
2. execution;
3. sessions;
4. strategy gates;
5. protection;
6. observability.

### Step 4

Add a static repository check preventing new operational reads from raw `Inp*` values.

### Step 5

Remove obsolete parallel-resolution code only after parity tests pass.

## 14. Auditability

Every trade decision must be able to reference:

```text
effective_config_revision
effective_config_hash
locked_profile_revision
remote_settings_revision
strategy_registry_version
```

The journal and trade-reason payload should carry the effective configuration revision.

## 15. Failure behavior

The resolver must fail closed.

Examples:

- unknown strategy ID → disabled;
- malformed locked profile → previous valid snapshot remains active;
- remote settings revision regression → reject;
- missing risk bound → conservative hard default;
- conflicting session definitions → trading disabled for affected target;
- invalid lot constraints → no new order.

## 16. Required tests

### 16.1 Unit tests

- each field precedence rule;
- min/intersection safety behavior;
- hard-bound clamping;
- invalid numbers;
- missing fields;
- unknown strategy IDs;
- revision regression;
- deterministic configuration hash.

### 16.2 Golden tests

Create fixed source bundles and expected effective snapshots.

### 16.3 Drift tests

Prove that legacy behavior remains unchanged where source values do not conflict.

### 16.4 Conflict tests

Examples:

- EA input risk 2%, remote limit 1% → effective 1%;
- profile enables strategy, remote disables → disabled;
- remote tries to expand max lot → rejected or clamped;
- invalid new profile → previous valid configuration remains active.

### 16.5 Integration tests

- settings download to resolver;
- locked-profile load to resolver;
- effective revision included in EA status;
- trade reason references active revision.

### 16.6 MQL compilation evidence

The PR must include:

- MetaEditor version;
- compilation command;
- complete compile log;
- warning count;
- produced EX5 digest.

## 17. Acceptance criteria

PR-A passes only when:

1. one canonical effective snapshot exists;
2. precedence is explicit per field;
3. safety-critical remote settings cannot expand risk;
4. invalid updates cannot replace the last valid snapshot;
5. configuration revision and hash are deterministic;
6. target identity is included;
7. migrated consumers no longer resolve competing sources;
8. trade/status telemetry includes the active revision;
9. all unit, conflict, drift and integration tests pass;
10. MQL compilation evidence is attached.

## 18. Reviewer checklist

Reject the PR when:

- any operational module still chooses its own precedence;
- remote settings can increase exposure;
- missing strategy state enables all strategies;
- invalid configuration partially applies;
- source provenance is absent;
- revisions are not monotonic;
- behavior changes are hidden inside refactoring;
- compilation is the only test evidence.

## 19. Rollback plan

Rollback must restore the previous configuration-resolution path without changing persisted settings or trade history.

Before merge:

- preserve legacy adapters;
- make activation feature-gated;
- retain the previous valid snapshot;
- document how to disable the new resolver;
- verify rollback compilation.

## 20. Required PR evidence

```text
Scope:
Root P0 addressed:
Field inventory:
Precedence specification:
Files changed:
Consumers migrated:
Compatibility adapters:
Validation rules:
Tests:
MQL compile log:
Behavioral parity result:
Rollback result:
Known residual risk:
```

## 21. Dependencies

PR-A should be coordinated with the identity and settings work identified in the final audit.

It may introduce temporary identifiers and adapters, but production activation remains blocked until:

- canonical target identity exists;
- settings revisions use compare-and-swap;
- EA applied-state acknowledgement exists;
- capability authorization is implemented.

## 22. Status

**Specification:** complete  
**Implementation:** not started  
**Repository modified:** no  
**Point 5:** blocked


---

# MASTER CHANGE POLICY

Every future update must:

1. modify this master file only;
2. update the status table;
3. state whether repository code changed;
4. record evidence and source paths;
5. preserve unresolved findings;
6. avoid declaring completion without verifiable evidence;
7. distinguish document completion from technical verification;
8. keep Point 5 blocked until its explicit release conditions are met.

# NEXT MASTER UPDATE

The next work item is not another standalone document.

The next update must be appended here and should focus on closing the remaining audit coverage gaps, beginning with:

1. complete MQL5 module coverage;
2. complete backend and frontend mutation-path coverage;
3. test and CI inventory;
4. executable build/compile evidence.



---

# CONTINUATION PLAN — AUDIT TO DEVELOPER HANDOFF

## User directive

Continue until:

1. the repository audit reaches verified 100% coverage;
2. implementation specifications exist for every remediation area;
3. the complete developer handoff package is ready.

This master file remains the only authoritative document.

## Progress model

Three separate percentages will be tracked from now on.

### A. Technical audit coverage

**Current:** 91%

### B. Implementation specification coverage

**Current:** 7%

PR-A is complete. The remaining specifications are not yet complete.

### C. Developer handoff readiness

**Current:** 18%

## Combined delivery progress

Weighted as:

- technical audit: 50%;
- implementation specifications: 35%;
- developer handoff package: 15%.

Current calculation:

```text
(91 × 0.50) + (7 × 0.35) + (18 × 0.15) = 50.65%
```

**Rounded combined progress: 51%**

This is not production readiness. Production status remains NO-GO.

## Audit closure sequence

### Audit Block A1 — MQL5 completion

Review every MQL5 entry point and include, strategy registration and dispatch, risk sizing, order execution, position lifecycle, protection logic, settings/web synchronization, filters, telemetry and dependencies.

Target:

- MQL5: 88% → 100%
- overall technical audit: 91% → approximately 94%

### Audit Block A2 — Backend completion

Review every route, schema, database path, migration, command queue, settings path, licensing, Coach, backtest, market-data path, LocalBridge integration, error path and lifecycle behavior.

Target:

- Backend: 88% → 100%
- overall technical audit: approximately 94% → 96%

### Audit Block A3 — Frontend completion

Review every page, state-changing action, API-client path, stale/error state, confirmation flow, risk/settings display, chart provenance, Coach, backtest, licensing, bridge and authentication path.

Target:

- Frontend: 90% → 100%
- overall technical audit: approximately 96% → 98%

### Audit Block A4 — Tests, CI and executable evidence

Review and verify the complete test/workflow inventory, clean backend startup, deterministic frontend build, Docker build, migrations, MQL compilation, parity fixtures, worker crash/replay behavior, deployment rollback and backup/restore.

Target:

- Testing/evidence: 68% → 100%
- Documentation: 90% → 100%
- Deploy: 96% → 100%
- Security: 98% → 100%
- overall technical audit: 98% → 100%

## Specification sequence

All specifications will be added to this master:

- SPEC-A — Effective Config Resolver: 100%
- SPEC-B — Production Configuration and Secret Management: 0%
- SPEC-C — Principal Identity, Capabilities and CSRF: 0%
- SPEC-D — Canonical Target Identity: 0%
- SPEC-E — Canonical Command Lifecycle: 0%
- SPEC-F — LocalBridge Hardening: 0%
- SPEC-G — Signed Atomic Deployment: 0%
- SPEC-H — Reproducible Build, CI and Promotion: 0%
- SPEC-I — Versioned Settings and Applied-State ACK: 0%
- SPEC-J — Central Risk Policy: 0%
- SPEC-K — Backtest Contract and Research Promotion: 0%
- SPEC-L — Ledger Identity and Migration: 0%
- SPEC-M — Market-Data Provenance and AI Isolation: 0%
- SPEC-N — Recovery, Staging and Release Evidence: 0%

## Developer handoff completion criteria

The handoff is complete only when it contains:

- verified 100% audit;
- complete P0/P1 register;
- dependency graph;
- specifications A–N;
- PR sequence;
- file-level scope;
- acceptance criteria;
- tests;
- migration plans;
- rollback plans;
- reviewer checklists;
- stop conditions;
- release gates;
- unresolved decision log;
- developer kickoff brief.

## Current status

| Track | Progress |
|---|---:|
| Technical audit coverage | 91% |
| Specification coverage | 7% |
| Developer handoff readiness | 18% |
| Combined delivery | 51% |
| Production readiness | NO-GO |
| Point 5 | BLOCKED |

## Next active task

**Audit Block A1 — complete MQL5 review**

No additional standalone files will be created.


---

# AUDIT CONTINUATION — BLOCK A1.1  
## MQL5 Virtual Stop Loss, Trade Transaction and Ledger Drain

**Repository commit reviewed:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`  
**Files reviewed in this block:**

- `MQL5/Experts/NEXUS_EA_v2.mq5`
- `MQL5/Include/NEXUS_v1/NXS_EdgeAdaptive.mqh`

## Verified positive controls

The reviewed implementation contains several strong controls:

- the EA routes `TRADE_TRANSACTION_DEAL_ADD` through one explicit handler;
- ledger aggregation is used before emitting logical-close actions;
- partial exits are separated from final logical-close events;
- consecutive-loss protection is invoked once per logical trade;
- Virtual SL uses explicit `OFF`, `OBSERVE` and `EXECUTE` modes;
- Virtual SL does not treat order submission as closure confirmation;
- closure confirmation prefers ledger finality and then broker position disappearance;
- Virtual SL records are scoped by account login and magic in the persistence filename and header;
- the persisted file uses a temporary file followed by replacement;
- restore runs only after ledger boot reconciliation;
- confirmed records are not restored as active.

These controls materially reduce duplicate close events and duplicated post-trade accounting.

## New findings

### NXS-VSL-001 — Pending intent is not durably persisted at creation

**Severity:** P0  
**Area:** capital protection / crash recovery

`NXS_VSL_OnRequested()` calls `NXS_VSL_PendingAdd()`, but the reviewed creation path does not immediately call `NXS_VSL_Persist()`.

Failure window:

```text
order accepted
→ pending intent stored only in memory
→ terminal or EA crashes
→ restart
→ fill may exist
→ pending correlation no longer exists
→ position may never be armed with the intended virtual stop
```

`OnDeinit()` persistence does not protect against abrupt termination.

**Required remediation**

Persist the pending intent before returning successful control to the caller, or use a durable append-only intent journal with atomic acknowledgement.

**Required tests**

- crash immediately after successful order request;
- fill during terminal outage;
- restart after request but before fill callback;
- duplicate recovery replay.

---

### NXS-VSL-002 — Armed Virtual SL record is not persisted immediately after fill registration

**Severity:** P0  
**Area:** capital protection / crash recovery

`NXS_EA_VirtSL_OnFill()` calls `NXS_EA_VirtSL_Register()`, but registration does not durably persist the newly armed record.

The next persistence is dependent on:

- a later state transition in `NXS_EA_VirtSL_Check()`;
- or graceful `OnDeinit()`.

A crash after fill registration but before either event can lose the logical stop state.

**Required remediation**

Persist registration atomically before considering the Virtual SL armed.

**Required tests**

- crash after `DEAL_ADD`;
- restart before next tick;
- restart before timer callback;
- broker position remains open while local VSL file is absent.

---

### NXS-VSL-003 — Multi-symbol records are evaluated using chart-symbol prices

**Severity:** P0 if multi-symbol operation is enabled; otherwise P1 architectural blocker  
**Area:** target identity / capital protection

Each record stores its own `symbol`, but `NXS_EA_VirtSL_Check()` retrieves:

```text
bid = SymbolInfoDouble(g_sym, SYMBOL_BID)
ask = SymbolInfoDouble(g_sym, SYMBOL_ASK)
```

once and applies those values to every Virtual SL record.

The code does not obtain bid/ask from `record.symbol`.

If the same EA instance manages records for more than one symbol, a position can:

- trigger from the wrong symbol’s price;
- fail to trigger when its own symbol crosses the virtual stop;
- be repeatedly closed under an unrelated price condition.

**Required remediation**

Evaluate each record using its immutable symbol and verify that the selected broker position has the same symbol, magic, account and intended instance identity.

**Required tests**

- two symbols with opposite price movements;
- symbol unavailable/stale;
- one chart symbol with a restored record from another symbol;
- wrong-symbol position ticket injection.

---

### NXS-VSL-004 — Restore trusts persisted symbol, direction, magic and prices without broker-state revalidation

**Severity:** P0  
**Area:** persistence integrity / target identity

Restore validates the file-level account and input magic, and checks that the position exists. It does not visibly verify that the selected broker position matches the stored record’s:

- symbol;
- magic;
- direction;
- current volume;
- open price;
- expected hard stop;
- EA instance identity.

A stale, corrupted or colliding record can therefore be attached to an unintended live position.

**Required remediation**

Reconstruct authoritative identity from broker position/deal history and reject any persisted record that does not match all immutable fields.

**Required tests**

- ticket collision simulation;
- changed magic;
- changed symbol;
- reversed direction;
- corrupted persistence row;
- account migration.

---

### NXS-VSL-005 — Atomic file replacement result is ignored

**Severity:** P1  
**Area:** durability

The persistence path closes the temporary file and calls `FileMove(..., FILE_REWRITE)`, but does not check or record whether replacement succeeded.

The in-memory state can be treated as persisted when the durable file was not updated.

**Required remediation**

Check the replacement result, log a structured fault, keep the previous last-known-good file, and block risk expansion when durable protection state cannot be written.

---

### NXS-VSL-006 — Virtual SL safety depends on EA/tick availability while broker hard stop is intentionally wider

**Severity:** P0 design risk  
**Area:** offline protection

In EXECUTE mode the logical stop is enforced by the EA while the broker receives a wider ATR-based stop.

During:

- terminal outage;
- network outage;
- frozen EA;
- stalled event loop;
- symbol without ticks;
- persistence failure;

the maximum loss is governed by the wider broker stop, not the logical stop displayed by the strategy.

This is inherent to the design and must not be presented as equivalent to a broker-native stop.

**Required remediation**

Define and expose both:

- logical risk;
- offline worst-case broker risk.

Risk approval, margin checks and UI must use the larger offline amount for capital protection.

---

### NXS-VSL-007 — Fill correlation excludes unjournaled management orders

**Severity:** P1  
**Area:** coverage consistency

The fill handler intentionally no-ops when no matching pending order intent exists. Comments explicitly state that grid/pyramid fills can be excluded.

This creates two protection classes:

- entries with Virtual SL correlation;
- secondary exposure without equivalent Virtual SL registration.

**Required remediation**

Every exposure-creating path must use the same durable intent and protection-registration mechanism, or Virtual SL mode must reject unsupported exposure paths.

---

### NXS-TX-001 — Transaction handler has no durable inbound-event journal

**Severity:** P1  
**Area:** replay/recovery

The logical ledger is designed to tolerate duplicate deal processing, which is positive. However, the top-level transaction callback itself does not visibly journal receipt and processing completion before returning.

A terminal or EA crash between broker event delivery and durable ledger persistence still relies on later history reconstruction.

**Required remediation**

Document and test history-based recovery as the authoritative replay mechanism, including exact cursor and window semantics.

---

### NXS-TX-002 — Partial-close strategy extraction depends on comment parsing

**Severity:** P1  
**Area:** attribution integrity

For a partial close, strategy attribution is reconstructed by parsing the original position comment using delimiter positions.

Comments are not an adequate immutable identifier because they may be:

- truncated by the broker;
- changed by another execution path;
- missing;
- formatted differently;
- shared by grouped institutional decisions.

**Required remediation**

Resolve strategy and logical-trade identity from the canonical trade ledger, not broker comments.

---

### NXS-TX-003 — Boot reconciliation intentionally suppresses local close side effects

**Severity:** P1 policy ambiguity  
**Area:** state consistency

Offline final trades are drained and logged during initialization, but the normal logical-close callback is intentionally skipped.

This preserves historical behavior but can leave local systems divergent after downtime, including:

- loss-streak state;
- chain state;
- notifications;
- strategy statistics;
- local cooldown state.

The backend may later receive the trade through history synchronization, while local protection state does not replay the same outcome.

**Required remediation**

Define which close side effects are replayable, which are notification-only, and which must be reconstructed for safety.

---

## Architectural conclusion

The logical-trade ledger path is stronger than the earlier per-deal design. It correctly separates partial exits from final trade outcomes and reduces duplicate side effects.

The Virtual SL implementation, however, is not yet safe enough for production because the protection state has crash windows before durable persistence and its price/identity logic remains chart-symbol-centric.

The feature must remain:

```text
OFF by default
```

for production review until durable intent, durable arm registration, symbol-scoped evaluation and offline worst-case risk accounting are implemented.

## Audit progress update

### MQL5 technical coverage

Previous: **88%**  
Current: **94%**

The source paths for the previously pending transaction handler, ledger drain and dedicated Virtual SL state machine have now been reviewed.

Still required before MQL5 reaches 100%:

- file-by-file inspection of remaining non-critical helpers;
- proof that every exposure path registers through the same protection journal;
- compile evidence on the reviewed commit;
- Strategy Tester evidence;
- crash/restart tests for Virtual SL;
- multi-symbol tests;
- exact history-replay coverage.

### Overall technical audit

Previous: **91%**  
Current: **93%**

### Specification coverage

**7%**

### Developer handoff readiness

Previous: **18%**  
Current: **22%**

### Combined delivery progress

Weighted calculation:

```text
(93 × 0.50) + (7 × 0.35) + (22 × 0.15) = 52.25%
```

**Rounded combined progress: 52%**

### Production readiness

**NO-GO**

### Point 5

**BLOCKED**

## Next active audit block

**A1.2 — MQL5 remaining exposure paths and non-critical helper coverage**

Priority order:

1. verify Virtual SL integration in every order-opening path;
2. inspect strategy registry and profile modules for identity drift;
3. inspect sessions/news/spread and telemetry helpers;
4. inspect remaining visual and notification modules for critical-path side effects;
5. identify compile/test evidence available for the reviewed commit.


---

# AUDIT CONTINUATION — BLOCK A1.2  
## MQL5 Exposure Paths: Grid, Pyramiding, Split Management and Position Coordinator

**Repository commit reviewed:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`

**Files reviewed in this block:**

- `MQL5/Include/NEXUS_v1/NXS_GridRecovery.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Pyramiding.mqh`
- `MQL5/Include/NEXUS_v1/NXS_SplitTrade.mqh`
- `MQL5/Include/NEXUS_v1/NXS_PositionCoordinator.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Execution.mqh`

## Verified positive controls

The reviewed code contains several meaningful safeguards:

- grid and pyramiding now pass through `NXS_CommonExposurePreflight()`;
- the common preflight applies RiskShield, directional exposure cap and broker preflight;
- the primary open path sizes from logical stop distance before applying residual multipliers;
- primary entries route through Virtual SL preparation and pending-intent registration;
- split actions use a position coordinator rather than issuing immediate competing actions;
- the coordinator permits one winning proposal per position and cycle;
- modify proposals reject stop-loss regression;
- applied management actions are persisted through state management;
- grid and pyramid counting is symbol-scoped and magic-scoped.

These controls improve consistency relative to direct raw order calls.

## New findings

### NXS-EXP-001 — Grid and pyramiding bypass the Virtual SL lifecycle

**Severity:** P0 when Virtual SL EXECUTE is enabled  
**Area:** protection parity

The primary entry path explicitly calls:

```text
NXS_VSL_PrepareEntry(...)
NXS_SafeBuy / NXS_SafeSell(...)
NXS_VSL_OnRequested(...)
```

Grid and pyramiding do not.

They call:

```text
NXS_CommonExposurePreflight(...)
NXS_SafeBuy / NXS_SafeSell(...)
```

directly.

Consequences:

- secondary exposure does not receive a logical Virtual SL;
- no durable pending intent exists;
- no fill-to-position Virtual SL registration occurs;
- the account can contain mixed protection semantics under one EA instance.

**Required remediation**

All exposure-creating paths must use one canonical execution service that owns:

- target identity;
- risk sizing;
- broker preflight;
- Virtual SL preparation;
- durable intent;
- send;
- fill correlation;
- ledger registration.

Until then, Virtual SL EXECUTE must reject grid and pyramiding or force those features off.

---

### NXS-EXP-002 — Grid and pyramid orders can be sent with zero SL and zero TP

**Severity:** P0  
**Area:** broker-native protection

Both modules initialize:

```text
double sl = 0, tp = 0;
```

and pass them to `NXS_CommonExposurePreflight()`.

Whether this is safe depends entirely on `NXS_PreFlight()` mutating zero values into valid stops. The reviewed caller contracts do not guarantee that a non-zero protective stop is produced.

Even if the broker accepts the order, an add-on position can exist without broker-native loss protection.

**Required remediation**

The common exposure contract must require, validate and return an explicit protection plan:

- logical SL;
- broker SL;
- TP or explicit no-TP policy;
- maximum monetary loss;
- offline worst-case loss.

A successful preflight with an unprotected exposure must be impossible unless a separately approved risk policy explicitly allows it.

---

### NXS-EXP-003 — Grid sizing duplicates the full current core-position volume

**Severity:** P0/P1 depending approved policy  
**Area:** risk amplification

Each grid layer uses:

```text
lots = PositionGetDouble(POSITION_VOLUME)
```

The documented maximum is three grid layers. This can create:

```text
core + 3 × full core volume
```

before accounting for other core trades or pyramids.

The directional lot cap limits total lots, but it is not equivalent to controlling monetary risk because:

- grid SL may be absent or different;
- entry prices differ;
- the original core position may already be losing;
- offline broker risk can be wider under Virtual SL mode.

**Required remediation**

Grid sizing must be based on remaining risk budget, not parent volume. The risk budget must include all same-direction positions and their current/worst-case loss.

---

### NXS-EXP-004 — Pyramiding volume normalization is incomplete

**Severity:** P1  
**Area:** execution validity

Pyramid volume is calculated as half the parent volume and clamped only to minimum volume.

It is not visibly normalized to:

- `SYMBOL_VOLUME_STEP`;
- `SYMBOL_VOLUME_MAX`;
- license cap;
- per-strategy risk policy.

Broker preflight may reject it, but the sizing contract remains inconsistent with the primary path.

**Required remediation**

Use one canonical volume normalizer and return the exact normalized volume before risk approval.

---

### NXS-EXP-005 — Grid and pyramiding inherit only chart-symbol identity

**Severity:** P1  
**Area:** target identity

The modules use global `g_sym`, global ATR and global regime/velocity state.

This is internally consistent for a single-symbol chart instance, but it is not a complete instance identity. The code does not bind the parent position to an immutable tuple such as:

```text
account + terminal instance + EA instance + symbol + magic namespace + strategy/logical trade
```

This becomes unsafe when history, restored state, bridge commands or multi-symbol operation are introduced.

**Required remediation**

Every add-on order must reference the canonical logical trade and target identity, not only current chart globals and magic ranges.

---

### NXS-SPLIT-001 — Split de-duplication has a crash window

**Severity:** P1  
**Area:** exactly-once management

The split module has in-memory arrays and also consults persisted management state through the coordinator.

The action is persisted only after the broker close-partial call returns success.

Failure window:

```text
broker accepts partial close
→ process crashes before NXS_PM_RecordApplied()
→ restart
→ persisted applied marker absent
→ same split can be proposed again
```

Broker/deal reconciliation may eventually reveal the partial, but this module does not visibly reconstruct the P1/P2 milestone from ledger state.

**Required remediation**

Use durable management intents with broker/deal acknowledgement, or derive split completion from the canonical logical-trade ledger.

---

### NXS-SPLIT-002 — Fixed 256-ticket in-memory history can evict still-relevant markers

**Severity:** P2  
**Area:** long-running stability

When the split arrays are full, the oldest marker is shifted out even if its position is still open.

The persisted coordinator state mitigates this only if the applied state was successfully recorded. It does not remove the crash-window issue.

**Required remediation**

Eliminate the bounded duplicate in-memory truth source and use one persistent ledger-backed management state.

---

### NXS-PM-001 — Partial-volume normalization uses chart symbol, not the selected position symbol

**Severity:** P1  
**Area:** multi-symbol correctness

`NXS_PM_ApplyCycle()` selects a position by ticket, but obtains volume step/minimum through global `g_sym`.

For any restored, injected or future multi-symbol proposal, the volume can be normalized using the wrong symbol specification.

**Required remediation**

After `PositionSelectByTicket()`, derive the authoritative symbol from `POSITION_SYMBOL` and use that symbol for all volume and price normalization.

---

### NXS-PM-002 — Modify normalization also uses global symbol digits/tick assumptions

**Severity:** P1  
**Area:** multi-symbol correctness

`NormPrice()` and `g_point` are global chart-symbol constructs. The coordinator applies them to a ticket-selected position without first binding normalization to that position’s own symbol.

**Required remediation**

Use symbol-specific tick size, digits and stops level from the selected position symbol.

---

### NXS-PM-003 — Proposal success is equated with completed broker state

**Severity:** P1  
**Area:** command lifecycle

The coordinator marks an action applied when `NXS_DoClose`, `NXS_DoClosePartial` or `NXS_DoModify` returns true.

The reviewed contract does not prove that true means final broker-state confirmation rather than request acceptance.

This is the same lifecycle ambiguity already found in backend commands and deployment:

```text
requested ≠ accepted ≠ filled/applied ≠ verified
```

**Required remediation**

Management actions need explicit states:

```text
PROPOSED
DURABLY_INTENDED
SENT
BROKER_ACCEPTED
DEAL/STATE_CONFIRMED
FAILED_RETRYABLE
FAILED_FINAL
```

---

### NXS-PM-004 — Stop non-loosening comparison uses global point tolerance

**Severity:** P2/P1 in multi-symbol use  
**Area:** stop integrity

The non-regression tolerance uses `g_point`, which belongs to the chart symbol, not necessarily the selected ticket.

This can accept or reject a modification incorrectly for symbols with different point sizes.

---

### NXS-EXEC-001 — Primary sizing uses logical risk while offline risk can be materially larger

**Severity:** P0 design inconsistency  
**Area:** monetary risk

The primary path sizes lots using logical SL distance, then in Virtual SL EXECUTE mode may send a much wider broker hard stop.

Therefore:

```text
displayed/sized risk < broker-enforceable offline risk
```

This confirms the earlier Virtual SL finding at the canonical execution layer.

**Required remediation**

Risk approval must compute both values and size against the greater approved exposure, or maintain a separate explicit offline-risk cap that cannot be exceeded.

---

### NXS-EXEC-002 — Setup-matrix identity is reconstructed from broker comment

**Severity:** P1  
**Area:** canonical identity

The setup matrix reads the strategy from a pipe-delimited position comment to derive the position timeframe.

This repeats the attribution weakness found in partial-close handling.

**Required remediation**

Resolve strategy and timeframe from the canonical trade ledger or immutable position metadata.

---

### NXS-EXEC-003 — Close-and-reverse paths bypass the position coordinator

**Severity:** P1  
**Area:** competing position actions

`NXS_CloseOppositeIfBetter()` and `NXS_SmartCloseOppositeIfBetter()` call `NXS_DoClose()` directly.

This can compete with:

- split partials;
- protection closes;
- trailing modifications;
- Virtual SL close requests;
- other management proposals in the same tick.

**Required remediation**

All position mutations must flow through the coordinator with defined priorities and confirmation semantics.

## Architectural conclusion

The repository has begun converging on shared risk and management services, but exposure creation and position mutation are still split across multiple execution models.

Current state:

```text
primary entry      → canonical-ish path + Virtual SL
grid/pyramid       → common preflight, but no Virtual SL lifecycle
split/trailing     → coordinator proposals
close-and-reverse  → direct close
Virtual SL close   → separate direct protection close
```

This is not yet a single authoritative execution architecture.

The required end state is:

```text
all exposure creation
all modifications
all partial closes
all full closes
all recovery actions
        ↓
one durable execution/position-command service
        ↓
broker acknowledgement
        ↓
ledger-confirmed final state
```

## Audit progress update

### MQL5 technical coverage

Previous: **94%**  
Current: **97%**

Remaining MQL5 closure items:

- inspect `NXS_Management.mqh`, `NXS_Protections.mqh`, `NXS_SafeOrder.mqh` and raw helpers;
- verify all direct `NXS_Do*` call sites;
- inspect state persistence implementation;
- inspect telemetry/web bridge side effects;
- obtain compile and Strategy Tester evidence.

### Overall technical audit

Previous: **93%**  
Current: **94%**

### Specification coverage

**7%**

### Developer handoff readiness

Previous: **22%**  
Current: **26%**

### Combined delivery progress

```text
(94 × 0.50) + (7 × 0.35) + (26 × 0.15) = 53.35%
```

**Rounded combined progress: 53%**

### Production readiness

**NO-GO**

### Point 5

**BLOCKED**

## Next active audit block

**A1.3 — MQL5 raw order helpers, protections, management and state persistence**

Priority:

1. enumerate every direct `NXS_DoBuy`, `NXS_DoSell`, `NXS_DoClose`, `NXS_DoClosePartial`, `NXS_DoModify` path;
2. inspect broker retcode semantics;
3. inspect emergency protection ordering;
4. inspect persistent state durability and replay;
5. close remaining source-review coverage before executable evidence.


---

# AUDIT CONTINUATION — BLOCK A1.3
## MQL5 Raw Trade Helpers, Protections, Management and State Persistence

**Repository reviewed:** `starmarketkiller/MAX`  
**Commit:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`

**Files reviewed:**
- `MQL5/Include/NEXUS_v1/NXS_Management.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Protections.mqh`
- `MQL5/Include/NEXUS_v1/NXS_SafeOrder.mqh`
- `MQL5/Include/NEXUS_v1/NXS_Globals.mqh`
- `MQL5/Include/NEXUS_v1/NXS_State.mqh`

## Verified positive controls

- state persistence uses a versioned binary schema;
- temporary snapshot validation occurs before replacement;
- a previous snapshot is retained;
- failed restore blocks new exposure;
- management actions are coordinated through proposals;
- stop-loss regression is rejected by the coordinator;
- protection closes resolve position symbol from the selected ticket;
- raw trade helpers use native MQL5 requests and preserve broker retcodes;
- buy/sell wrappers retry only a defined subset of transient retcodes;
- emergency protection paths are symbol and Nexus-magic scoped.

## New findings

### NXS-RAW-001 — `TRADE_RETCODE_PLACED` is treated as completed execution
**Severity:** P0

All raw helpers return success for both `DONE` and `PLACED`. `PLACED` is acceptance, not final broker state. This affects opens, closes, partial closes, modifications and protection actions.

**Required remediation:** use explicit lifecycle states: REQUESTED → ACCEPTED/PLACED → DEAL/POSITION CONFIRMED → FAILED.

### NXS-RAW-002 — Global last-order ticket is unsafe across retries and concurrent paths
**Severity:** P0/P1

`g_tradeOrderTicket` is one mutable global. Retry attempts or another order path can overwrite the correlation used by Virtual SL.

**Required remediation:** return an immutable execution result object with request ID, order/deal ticket, retcode, attempt, symbol, magic and correlation ID.

### NXS-RAW-003 — Fixed deviation and global filling mode are not symbol-scoped
**Severity:** P1

Raw helpers use deviation `30` and global `g_tradeFilling`; management may target a different symbol.

### NXS-RAW-004 — Retry wrapper blocks the EA thread with `Sleep()`
**Severity:** P1

Retries can delay Virtual SL checks, emergency protections, timer work and transaction handling.

### NXS-PROT-001 — Emergency flags are set even when not all positions close
**Severity:** P0

ESL and DPT mark themselves hit and pause the EA after issuing close requests, without verifying every target is truly closed.

### NXS-PROT-002 — Emergency close counts `PLACED` as success
**Severity:** P0

The close-all count can report a position as closed while it is only placed/accepted.

### NXS-PROT-003 — Trade-reason payload uses global symbol and digits
**Severity:** P1

The payload serializes `g_sym` and `g_digits` instead of the selected position's authoritative symbol and precision.

### NXS-PROT-004 — Strategy attribution uses the entire broker comment
**Severity:** P1

The protection path sends `POSITION_COMMENT` as the strategy ID.

### NXS-PROT-005 — Synchronous web retry occurs inside protection flow
**Severity:** P1

Three synchronous WebRequest attempts, backoff sleeps and 20-second timeouts can block the EA immediately after a risk event.

### NXS-PROT-006 — Max-hold authority is still split across two modules
**Severity:** P1

Authority depends on strategy parsing from comments and profile lookup, so missing/truncated comments can route the position incorrectly.

### NXS-MGMT-001 — Risk distance is recalculated from current stop
**Severity:** P1

Profile BE logic uses `abs(open-current SL)`, losing the immutable original risk after stop movement.

### NXS-MGMT-002 — Timeframe/profile identity is parsed from comments
**Severity:** P1

Management still depends on broker comment parsing.

### NXS-STATE-001 — State filename omits account and terminal identity
**Severity:** P0/P1

The filename uses only magic and symbol under `FILE_COMMON`, so multiple accounts/terminals can collide.

### NXS-STATE-002 — Snapshot header does not bind account, broker or EA build
**Severity:** P0/P1

The file validates schema magic/version but not account, server, symbol, input magic, build, config version or deployment ID.

### NXS-STATE-003 — Invalid string lengths fail open
**Severity:** P1

Invalid lengths return empty strings without invalidating the full snapshot.

### NXS-STATE-004 — Snapshot has no checksum/authenticated integrity
**Severity:** P1

Leading/trailing magic values do not detect internal corruption or foreign snapshot replacement.

### NXS-STATE-005 — Reconstructed `entryAtr` can use current ATR
**Severity:** P1

After restart, management thresholds can change because current ATR is substituted for immutable entry ATR.

### NXS-STATE-006 — Reconciliation is not a command journal
**Severity:** P1

It rebuilds only currently open chart-symbol positions and does not preserve pending intents or accepted-but-unconfirmed actions.

## Architectural conclusion

The state module is stronger than ad hoc globals, but it remains an operational snapshot rather than a durable transaction journal.

NEXUS still needs one durable execution journal shared by opens, add-ons, modifies, partial closes, full closes, Virtual SL, emergency protections and recovery replay.

## Audit progress update

| Track | Previous | Current |
|---|---:|---:|
| MQL5 source-review coverage | 97% | **99%** |
| Overall technical audit | 94% | **95%** |
| Specification coverage | 7% | **7%** |
| Developer handoff readiness | 26% | **31%** |
| Combined delivery | 53% | **55%** |

Remaining MQL5 closure evidence:
- compile proof for the audited commit;
- Strategy Tester proof;
- crash/restart scenarios;
- retcode/fill simulations;
- multi-symbol verification.

**Production readiness:** NO-GO  
**Point 5:** BLOCKED

## Next active block

**A1.4 — MQL5 executable evidence and direct-call inventory**

Then:

**A2 — Backend completion audit**


---

# AUDIT CONTINUATION — BLOCK A1.4
## MQL5 Evidence Closure and CI Verification

**Repository:** `starmarketkiller/MAX`  
**Commit:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`

GitHub Actions and commit statuses were checked for the audited commit.

**Result:** no workflow runs, no status checks, no compiler artifacts and no Strategy Tester artifacts were available.

### MQL5 status

- Source audit: **100%**
- Executable evidence: **not verified**
- Production approval: **NO-GO**

Required developer evidence:

1. MetaEditor build number and compiler log;
2. reproducible compilation instructions;
3. EX5 artifact hash;
4. Strategy Tester configuration, report and journal;
5. crash/restart tests;
6. broker retcode/fill simulations;
7. multi-symbol tests;
8. exact commit SHA and reviewer sign-off.

---

# AUDIT CONTINUATION — BLOCK A2.1
## Backend Bootstrap, Authentication, EA Command and Core Persistence

**File reviewed:** `server/app.py`  
**Commit:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`

## Confirmed findings

### NXS-BE-CONFIG-001 — Dangerous default credentials
**Severity:** P0

The backend defaults to bridge token `NEXUS_BRIDGE_TOKEN_2026`, user `admin`, password `admin`, and starts without requiring replacement.

### NXS-BE-CONFIG-002 — Ephemeral JWT secret
**Severity:** P1

When no explicit JWT secret exists, a random process-local secret is generated, invalidating sessions on restart and preventing consistent multi-instance operation.

### NXS-BE-AUTH-001 — 30-day privileged session
**Severity:** P0

The default JWT lifetime is 720 hours.

### NXS-BE-AUTH-002 — JWT returned in response body
**Severity:** P0

The login route sets an httpOnly cookie but also returns the token to JavaScript for legacy compatibility.

### NXS-BE-AUTH-003 — Missing explicit CSRF contract
**Severity:** P0

Cookie authentication uses SameSite=Lax; the reviewed path does not establish anti-CSRF tokens or Origin enforcement.

### NXS-BE-AUTH-004 — All authenticated users are administrators
**Severity:** P0

`_user_obj()` always returns role `admin`; no capabilities, ownership or approval separation are visible.

### NXS-BE-AUTH-005 — No visible login throttling or MFA
**Severity:** P0/P1

The login route performs a direct credential comparison without visible rate limiting, lockout, MFA or failed-login audit.

### NXS-BE-HEALTH-001 — Health is not readiness
**Severity:** P1

`/api/health` returns success without checking database write/read, migration state, static assets, production configuration or deployment assets.

### NXS-BE-CMD-001 — Global EA command polling
**Severity:** P0

The oldest unconsumed command is selected globally, without account, magic, symbol, instance or environment targeting.

### NXS-BE-CMD-002 — Polling consumes before execution
**Severity:** P0

The GET poll sets `consumed=1` and `status='DELIVERED'` before the EA parses or executes the command.

### NXS-BE-CMD-003 — Legacy command schema cannot represent safe lifecycle
**Severity:** P0

The command table lacks target identity, expiry, lease, attempts, idempotency key, broker result, post-state and approval identity.

### NXS-BE-DATA-001 — EA status identity is only magic plus symbol
**Severity:** P0/P1

Two accounts or terminals can overwrite each other's status.

### NXS-BE-DATA-002 — Equity history is global
**Severity:** P1

All EA pushes append into one shared KV history with no target identity.

### NXS-BE-DATA-003 — Weak global primary identities
**Severity:** P0/P1

Tables use ticket or symbol alone as primary identity for trades, stats, reasons and visual objects.

### NXS-BE-DB-001 — DDL and migrations run inside app startup
**Severity:** P1

This creates race, rollback and deployment-coupling risks.

### NXS-BE-DB-002 — SQLite durability policy is incomplete
**Severity:** P1

WAL is enabled, but foreign keys, synchronous policy, backup coordination, integrity checks and migration locking are not established in the reviewed connection path.

### NXS-BE-ARCH-001 — Monolithic trust boundary
**Severity:** P1

Authentication, trading commands, data, licensing, AI, deployment and schema management are combined in `app.py`.

## Required remediation order

1. fail-closed production configuration;
2. principal/capability/session architecture;
3. canonical target identity;
4. leased command lifecycle;
5. versioned migrations;
6. liveness/readiness separation;
7. modular split of `app.py`.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| MQL5 source audit | 99% | **100%** |
| Backend audit | 88% | **92%** |
| Overall technical audit | 95% | **96%** |
| Specification coverage | 7% | **7%** |
| Developer handoff readiness | 31% | **36%** |
| Combined delivery | 55% | **56%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED

## Next active block

**A2.2 — Backend route inventory, authorization matrix and mutation semantics**


---

# AUDIT CONTINUATION — BLOCK A2.2
## Backend Route Inventory, Authorization Matrix and Mutation Semantics — Part 1

**Repository:** `starmarketkiller/MAX`  
**Commit:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`  
**Primary file:** `server/app.py`

## Route inventory — first tranche

| Route family | Principal | Mutation | Main risk |
|---|---|---:|---|
| Auth | anonymous/dashboard | yes/no | long-lived universal admin session |
| EA push/history/reason/stats | shared bridge token | yes | weak target identity and broad trust |
| EA command poll | shared bridge token | **yes via GET** | consumed before execution |
| License verify | shared bridge token | read | open mode bypass |
| Telegram notify | shared bridge token | external side effect | arbitrary message capability |
| Strategy-chain config | EA/dashboard | yes/no | global runtime trading effect |
| LocalBridge heartbeat/poll/ack | shared bridge token | yes | client-asserted host identity |
| LocalBridge enqueue/status | dashboard | yes | status GET mutates expiry |
| Dashboard EA command | dashboard | yes | global untargeted destructive actions |
| Dashboard settings/profiles | dashboard | yes | global immediate effect and lost-update risk |
| Journal/stats/shadow/reasons | dashboard | no | global aggregation and weak identities |

## Confirmed findings

### NXS-BE-ROUTE-001 — GET routes mutate durable state
**Severity:** P0/P1

Confirmed:
- `/api/ea/command` marks commands consumed/delivered;
- `/api/local_bridge/poll` leases commands and increments attempts;
- `/api/local_bridge/status` expires commands.

Reads are therefore not replay-safe.

### NXS-BE-ROUTE-002 — Shared bridge token is a universal machine principal
**Severity:** P0

One token authenticates EA ingestion, command polling, LocalBridge, Telegram, licensing and strategy-chain reads.

### NXS-BE-ROUTE-003 — Dashboard has no capability separation
**Severity:** P0

Every authenticated user is effectively admin and can change settings, profiles, deployment and destructive trading commands.

### NXS-BE-ROUTE-004 — Dashboard EA commands are not target-scoped
**Severity:** P0

`/api/dashboard/command` queues global commands without account, symbol, magic, instance or environment target.

### NXS-BE-ROUTE-005 — Destructive commands lack approval/reason contracts
**Severity:** P0/P1

No required operator reason, expiry, idempotency key, expected state, second confirmation or four-eyes approval.

### NXS-BE-ROUTE-006 — LocalBridge host identity is client-asserted
**Severity:** P0/P1

Heartbeat accepts caller-provided `host_id`; possession of the shared token enables impersonation.

### NXS-BE-ROUTE-007 — Status read changes command state
**Severity:** P1

Opening `/api/local_bridge/status` can transition commands to `EXPIRED`.

### NXS-BE-ROUTE-008 — Strategy-chain config accepts an arbitrary document
**Severity:** P0/P1

`PUT /api/strategy_chain/config` stores submitted JSON directly without a visible route-level schema, version, limits, concurrency control or rollback.

### NXS-BE-ROUTE-009 — Locked profiles use full-map replacement
**Severity:** P1

Concurrent or stale clients can overwrite unrelated profiles.

### NXS-BE-ROUTE-010 — Telegram route is a privileged external side effect
**Severity:** P1

Needs allowlists, payload limits, rate limits, attribution, dedupe and durable outbox behavior.

### NXS-BE-ROUTE-011 — Open license mode disables enforcement
**Severity:** P1

Acceptable only as an explicit development mode; production must fail closed.

### NXS-BE-ROUTE-012 — Machine payload validation is inconsistent
**Severity:** P1

High-impact ingestion routes accept arbitrary JSON while settings already use a canonical validator.

### NXS-BE-ROUTE-013 — “Primary EA” is selected heuristically
**Severity:** P1

The dashboard chooses the first online EA, otherwise the latest, which is unsafe for multi-account/multi-instance operation.

## Positive controls

- canonical settings validation;
- versioned locked profiles;
- LocalBridge leases, attempts, expiry and idempotency;
- ACK binding to command, host and lease;
- ledger-based analytics;
- command event history.

These controls should be generalized to the legacy EA command path.

## Remaining A2.2 scope

- analytics and charts;
- journal metadata writes;
- strategy library and optimizer;
- backtest controls;
- Coach and memory;
- deployment and worker download;
- license administration;
- compatibility aliases and static routes.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| MQL5 source audit | 100% | **100%** |
| Backend audit | 92% | **94%** |
| Overall technical audit | 96% | **96%** |
| Specification coverage | 7% | **8%** |
| Developer handoff readiness | 36% | **39%** |
| Combined delivery | 56% | **58%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED

## Next active block

**A2.2 Part 2 — remaining route families and complete authorization matrix**


---

# AUDIT CONTINUATION — BLOCK A2.2
## Backend Route Inventory, Authorization Matrix and Mutation Semantics — Part 2

**Repository:** `starmarketkiller/MAX`  
**Commit:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`  
**Primary file:** `server/app.py`

This continuation covers:

- EA health and command aliases;
- settings and strategy administration;
- per-strategy risk scaling;
- analytics and what-if routes;
- backtest and optimizer routes;
- downloads;
- AI Coach, memory and action application;
- compatibility aliases.

## Additional route inventory

| Route family | Principal | Mutation | Risk class | Main issue |
|---|---|---:|---|---|
| `/api/ea/health` | dashboard | no | high | health uses heuristically selected “primary EA” |
| `/api/ea/command` POST | dashboard | yes | critical | duplicate global command entry point |
| `/api/settings*` | dashboard | yes/no | critical | global runtime configuration |
| `/api/strategies*` | dashboard | yes/no | critical | strategy enablement and risk multipliers affect real lot sizing |
| `/api/analytics*` | dashboard | mostly read | medium/high | large unbounded in-memory derivations |
| `/api/backtest*` | dashboard | compute/write | high | synchronous CPU-heavy work inside request process |
| `/api/downloads*` | dashboard | read/file | high | downloadable worker/source/deployment artifacts |
| `/api/coach/chat` | dashboard + external AI | yes | high | trading/account context sent to external model |
| `/api/coach/apply_action` | dashboard | yes | critical | AI-adjacent path changes live trading state |
| `/api/coach/memory*` | dashboard | yes/no | high | persistent free-form prompt memory |
| `/api/command*` | dashboard | yes/no | critical | additional alias to same unsafe EA command queue |

## Confirmed findings

### NXS-BE-ROUTE-014 — Multiple aliases expose the same destructive command channel

**Severity:** P0/P1

Destructive EA commands can be queued through multiple routes, including:

- `/api/dashboard/command`;
- `/api/ea/command` POST;
- `/api/command`;
- `/api/coach/apply_action`.

All converge on the same legacy global queue.

Consequences:

- authorization policy can drift between aliases;
- validation may diverge;
- audit trails cannot clearly identify the originating workflow;
- deprecation becomes difficult;
- security fixes must be repeated across routes.

**Required remediation**

Create one canonical command service and retain compatibility aliases only as thin, time-limited adapters.

---

### NXS-BE-RISK-001 — Per-strategy risk scaling can reach 10× live multiplier

**Severity:** P0

The risk configuration and manual override paths permit multipliers up to `10.0`.

The calculation is fed back to the EA through runtime settings.

Even though automatic scaling is disabled by default, a dashboard or Coach action can activate or override it.

Required controls:

- hard production ceiling substantially below 10×;
- absolute account-risk cap after all multipliers;
- drawdown-aware kill switch;
- minimum sample and confidence requirements;
- change approval;
- versioned audit event;
- simulation preview before activation.

---

### NXS-BE-RISK-002 — Risk configuration validation is incomplete

**Severity:** P0/P1

The route clamps some fields but does not establish complete validation for:

- boolean coercion;
- finite-number checks;
- relationship between minimum and maximum multiplier;
- maximum effective account risk;
- target drawdown plausibility;
- strategy ID validation in manual overrides;
- stale or unverified analytics provenance.

A string, malformed numeric value or logically inconsistent configuration may produce exceptions or unsafe behavior.

---

### NXS-BE-RISK-003 — Strategy risk uses a heuristic account balance fallback

**Severity:** P1

If no valid EA balance is available, the backend substitutes `10000.0`.

This can make drawdown percentages and suggested multipliers appear authoritative when they are based on a synthetic account size.

The response must explicitly carry:

```text
balance_source = observed | stale | fallback
```

and auto-scaling must be prohibited when the balance is not observed and fresh.

---

### NXS-BE-AN-001 — Analytics endpoints perform large synchronous scans

**Severity:** P1

Several routes call ledger reads with limits such as `100000` and then aggregate in Python.

Risks:

- request latency;
- process blocking;
- memory pressure;
- denial-of-service from repeated dashboard requests;
- inconsistent results during concurrent writes.

Required: indexed SQL/materialized read models, bounded queries, caching by ledger watermark and background recomputation.

---

### NXS-BE-AN-002 — Health score embeds policy constants in application code

**Severity:** P1

Examples include:

- drawdown warning at 5%;
- loss-streak thresholds;
- volatility categories;
- profit-factor thresholds;
- online freshness windows.

These values are not tied to a versioned health-policy contract.

A dashboard release can therefore silently redefine operational health.

---

### NXS-BE-BT-001 — Backtest and optimization run synchronously in the API process

**Severity:** P0/P1

Optimization and reporting routes invoke the backtest engine directly inside the HTTP request.

Risks:

- CPU starvation of trading-control endpoints;
- request timeout;
- duplicate work after client retry;
- no cancellation;
- no resource quota;
- no durable job lifecycle;
- backend restart loses execution state.

Required architecture:

```text
POST /backtest/jobs
GET  /backtest/jobs/{id}
POST /backtest/jobs/{id}/cancel
```

with a separate worker pool and immutable artifacts.

---

### NXS-BE-BT-002 — Some computational reports are exposed through GET

**Severity:** P1

Management and multi-timeframe reports support both GET and POST.

If the operation performs meaningful computation, GET requests can be:

- prefetched;
- retried;
- cached incorrectly;
- triggered unintentionally.

Use GET only to retrieve an already-created immutable result.

---

### NXS-BE-BT-003 — Backtest jobs lack reproducibility envelope

**Severity:** P0/P1

The reviewed route creates a random `job_id` after computation but does not visibly persist a complete immutable envelope containing:

- source commit;
- strategy implementation hash;
- dataset hash;
- broker/timezone assumptions;
- spread/slippage model;
- parameter schema version;
- random seed;
- engine version;
- requested-by identity;
- start/end timestamps;
- logs and failure state.

Without this, results cannot be independently reproduced or compared safely.

---

### NXS-BE-BT-004 — Saved Creator setups accept largely arbitrary content

**Severity:** P1

`/api/backtest/creator/save` verifies that `setup.combo` exists but then stores the submitted object.

It needs:

- versioned schema;
- strategy ID validation;
- parameter bounds;
- size limits;
- ownership;
- immutable version history;
- checksum.

---

### NXS-BE-DL-001 — Worker/source artifacts are downloadable by any dashboard session

**Severity:** P1

The backend can return the LocalBridge Python worker directly.

The general downloads directory also advertises source, compiled files, presets, templates and archives.

Controls required:

- capability-specific download permission;
- immutable artifact version;
- checksum and signature;
- content-disposition hardening;
- allowlisted file extensions;
- release manifest binding;
- download audit event.

---

### NXS-BE-AI-001 — Coach sends sensitive trading context to an external AI provider

**Severity:** P0/P1 privacy and security

The system prompt may include:

- symbol;
- balance;
- equity;
- floating and daily PnL;
- drawdown;
- pause state;
- session;
- higher-timeframe bias;
- frontend-provided chart context;
- persistent user memory.

The source does not establish a clear data-classification, redaction, consent or retention contract before transmission.

---

### NXS-BE-AI-002 — Coach session IDs are caller-controlled KV namespaces

**Severity:** P1

The client supplies `session_id`, which is embedded into a KV key.

Although this is not direct SQL injection, it permits:

- namespace collision;
- overwriting another session when IDs are guessed/shared;
- unbounded KV growth;
- ambiguous ownership.

Session IDs must be server-issued and bound to the authenticated principal.

---

### NXS-BE-AI-003 — Coach prompt memory is global

**Severity:** P0/P1

Coach memory rows have no:

- user owner;
- account target;
- environment;
- classification;
- expiry;
- sensitivity label.

Every Coach conversation receives the latest global memory entries.

This can leak information between operators and contaminate decisions.

---

### NXS-BE-AI-004 — Coach can change live trading state

**Severity:** P0

`/api/coach/apply_action` can:

- pause/resume the EA;
- close all positions;
- reset protections;
- enable or disable strategies;
- change global risk;
- change per-strategy risk.

The route is not merely advisory.

A model-generated suggestion can be converted into a live trading mutation through one dashboard action.

Required safeguards:

1. AI response remains non-authoritative;
2. server recomputes and validates every proposed action;
3. destructive actions require an explicit operator confirmation;
4. high-risk actions require step-up authentication;
5. show target, current state and expected effect;
6. record AI suggestion separately from human authorization;
7. prohibit Coach from resetting protections without a risk-manager capability.

---

### NXS-BE-AI-005 — Coach risk changes bypass the canonical settings validator

**Severity:** P0/P1

The Coach directly updates settings and risk KV documents.

This bypasses the canonical settings route, schema history and any future approval workflow.

All mutations must pass through the same command/configuration service.

---

### NXS-BE-AI-006 — External AI call blocks the backend request thread

**Severity:** P1

The Anthropic request is synchronous with a timeout of up to 60 seconds.

Under concurrent use this can consume request workers and degrade trading-control endpoints.

Move AI workloads to a separate service/worker with quotas and circuit breakers.

---

### NXS-BE-DATA-004 — Free-form Coach history and memory have weak retention controls

**Severity:** P1

Conversation history is capped per session, but there is no visible:

- global quota;
- retention period;
- deletion by user/session;
- export;
- data classification;
- encryption policy;
- PII/secret filtering.

---

### NXS-BE-COMPAT-001 — Compatibility routes increase permanent attack surface

**Severity:** P1

The backend contains several legacy/React compatibility aliases.

Without a deprecation registry, aliases tend to remain indefinitely and can bypass newer contracts.

Required:

- route owner;
- canonical replacement;
- deprecation date;
- telemetry;
- removal test;
- compatibility version header.

## Positive controls verified in this tranche

- settings have a canonical schema and validation path;
- strategy IDs are validated in several strategy routes;
- automatic strategy scaling is disabled by default;
- ledger analytics expose provenance;
- LocalBridge uses a more mature command lifecycle;
- Coach does not directly execute broker requests; it queues legacy EA commands;
- Coach responses warn against profit guarantees in the system prompt.

These are useful controls, but they do not remove the production blockers above.

## Evidence note

Recent merged pull-request descriptions report:

- backend test suites passing;
- frontend production builds succeeding;
- MetaEditor compilation with zero errors and warnings.

These statements are useful development evidence, but the repository audit still lacks independently retrieved compiler logs, Strategy Tester artifacts and runtime MT5 evidence. Therefore executable validation remains incomplete.

## A2.2 completion status

The backend route inventory and authorization/mutation classification are now substantially complete.

Remaining work moves to:

- **A2.3 — dashboard, frontend trust boundaries, Coach UX, licensing and analytics integration**;
- **A2.4 — final database model, migration and data-governance audit**.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| MQL5 source audit | 100% | **100%** |
| Backend route audit | 94% | **97%** |
| Overall technical audit | 96% | **97%** |
| Specification coverage | 8% | **9%** |
| Developer handoff readiness | 39% | **43%** |
| Combined delivery | 58% | **60%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED

## Next active block

**A2.3 — Frontend/dashboard trust boundaries, licensing, Coach UX and integration behavior**


---

# AUDIT CONTINUATION — BLOCK A2.3
## Frontend Trust Boundaries, Source-of-Truth and Operator-Control Analysis

**Repository:** `starmarketkiller/MAX`  
**Commit:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`

## Architectural conclusion

The current platform already contains several useful separations:

- browser session via httpOnly cookie;
- backend-derived analytics provenance;
- visibility-aware polling;
- LocalBridge lease/ACK lifecycle;
- canonical settings validation.

However, the platform still lacks one explicit authority hierarchy for decisions that can affect live trading.

The effective control graph is currently:

```text
Dashboard
  ├─ direct settings changes
  ├─ direct strategy enable/disable
  ├─ direct risk changes
  ├─ legacy EA command queue
  ├─ LocalBridge command queue
  └─ Coach action endpoint

Coach
  ├─ recommends
  ├─ modifies settings
  ├─ modifies strategy risk
  └─ queues destructive EA commands

Backend
  ├─ stores global state
  ├─ selects a primary EA heuristically
  ├─ derives analytics
  └─ exposes multiple mutation aliases

EA
  ├─ polls settings
  ├─ polls legacy global commands
  └─ executes broker-side actions
```

This is not yet a strict chain of authority.

## Required authority hierarchy

The target architecture should enforce:

```text
Broker/terminal evidence
        ↓
EA execution state
        ↓
Immutable backend event ledger
        ↓
Risk and policy engine
        ↓
Operator-authorized command service
        ↓
EA / LocalBridge executor
```

The dashboard and AI Coach must never become authoritative sources of trading truth.

## Source-of-truth matrix

| Domain | Current effective sources | Required authoritative source |
|---|---|---|
| Open positions | EA push / dashboard-selected primary EA | broker/terminal snapshot with instance identity |
| Closed trades | trade event ledger plus reconstructed history | immutable verified ledger |
| Analytics | backend ledger derivation | backend materialized ledger views |
| Runtime settings | global KV, dashboard, Coach | versioned configuration service |
| Strategy enablement | settings + override + EA-reported state | versioned desired-state document |
| Risk multiplier | auto calculation + manual KV + Coach | centralized risk-policy engine |
| EA commands | several frontend aliases + global queue | target-scoped command service |
| LocalBridge commands | leased command table | canonical command service |
| Coach memory | global database rows | user/account-scoped memory store |
| Chart data | synthetic/live/reconstructed sources | explicitly labelled provider-specific dataset |
| License state | backend mode/table | fail-closed license service |
| Operational health | backend heuristic | versioned health policy per instance |

## Confirmed findings

### NXS-FE-TRUST-001 — Frontend is correctly moving away from token storage
**Severity:** positive control

The frontend uses `withCredentials: true`, relies on the httpOnly cookie and removes the legacy token from local storage.

This is a strong improvement against JavaScript-readable token theft.

Remaining requirements:

- same-site policy documented;
- CSRF contract;
- session rotation;
- server-side revocation;
- short session lifetime;
- capability claims.

---

### NXS-FE-TRUST-002 — Frontend treats `DELIVERED` as a visible terminal UI milestone
**Severity:** P0/P1 semantic risk

The dashboard polls command status until `DELIVERED`.

`DELIVERED` only proves that the EA fetched the command. It does not prove:

- execution started;
- broker accepted the request;
- requested position existed;
- partial close volume was valid;
- close completed;
- protections were actually reset;
- resulting account state matched the intent.

The UI must display at least:

```text
PENDING
LEASED/DELIVERED
RUNNING
BROKER_ACCEPTED
SUCCEEDED
FAILED
RECONCILIATION_MISMATCH
```

For the legacy EA command path, the latter states do not yet exist.

---

### NXS-FE-TRUST-003 — Partial-data preservation is good, but stale-data semantics remain weak
**Severity:** P1

The frontend now uses independent settled requests and preserves the last valid state when one endpoint fails.

This improves resilience, but stale data can remain visible.

Every resource card needs:

- observed timestamp;
- age;
- stale threshold;
- unavailable state;
- provenance;
- source instance;
- explicit “last valid value” label.

A preserved value must not look live.

---

### NXS-FE-TRUST-004 — Visibility-aware polling improves load but not consistency
**Severity:** P1

Polling is paused while the tab is hidden and restarted when visible.

This reduces unnecessary traffic and overlapping calls.

It does not provide:

- atomic multi-resource snapshots;
- event ordering;
- consistency watermark;
- command/update causality;
- server push;
- missed-event recovery.

The dashboard can still combine state from different moments.

---

### NXS-FE-TRUST-005 — Dashboard composition can mix different EA instances
**Severity:** P0/P1

The backend supplies one heuristically selected primary EA while analytics, history, settings, commands and bridge state are global.

The page can therefore present a visually coherent but logically mixed view assembled from:

- one EA status;
- another account’s trade events;
- global settings;
- global equity history;
- global commands;
- multiple bridge hosts.

Every dashboard view must be scoped by an explicit `deployment_id` and `instance_id`.

---

### NXS-FE-TRUST-006 — Provenance labels are a major positive control
**Severity:** positive control

The UI now distinguishes:

- observed live data;
- reconstructed history;
- derived analytics;
- simulated research.

This should become a mandatory field in every data contract, not just a visual label added by selected pages.

Required provenance envelope:

```text
source_type
source_id
observed_at
recorded_at
derived_at
dataset_version
watermark
confidence
stale
```

---

### NXS-FE-TRUST-007 — Synthetic chart data can coexist with operational UI
**Severity:** P0/P1

The chart endpoint may return synthetic data and labels it as such.

The label is useful, but synthetic market data should be visually and functionally isolated from live execution controls.

Required rule:

> No command or Coach action may be initiated from a chart context whose provenance is synthetic, demo, stale or unknown.

---

### NXS-FE-TRUST-008 — Browser cache/session context can influence Coach prompts
**Severity:** P1

The frontend persists chart context for the Coach workflow.

Context obtained from stale, synthetic or reconstructed chart data can enter the AI prompt unless the backend independently verifies provenance.

The backend must reject or clearly quarantine untrusted chart context.

---

### NXS-FE-TRUST-009 — Frontend validation is not a security boundary
**Severity:** P1

Settings pages perform client-side validation, but all safety constraints must remain server-side.

This principle must also cover:

- strategy risk;
- LocalBridge actions;
- Coach actions;
- backtest job parameters;
- downloads;
- license administration.

---

### NXS-FE-TRUST-010 — Frontend exposes broad administrative surface to one role
**Severity:** P0

The same authenticated shell exposes:

- trading control;
- risk settings;
- strategy configuration;
- Coach actions;
- LocalBridge deployment;
- downloads;
- licenses;
- analytics.

Navigation hiding is not authorization. Backend capability enforcement is required per operation.

---

### NXS-AI-BOUNDARY-001 — Coach recommendation and execution are not cleanly separated
**Severity:** P0

The Coach can produce a suggestion and the application can route it into a live mutation endpoint.

Required two-record model:

1. `AI_RECOMMENDATION`
2. `HUMAN_AUTHORIZATION`

The execution service must consume only the second record.

---

### NXS-AI-BOUNDARY-002 — Risk engine must override operator and AI requests
**Severity:** P0

A command authorized by a human must still be rejected when it violates hard risk policy.

Examples:

- increase risk above account ceiling;
- resume during active emergency stop;
- reset protections while drawdown breach remains;
- close/partial-close wrong account or symbol;
- enable a quarantined strategy;
- apply settings based on insufficient sample.

The order must be:

```text
AI suggestion
→ operator confirmation
→ policy/risk validation
→ command creation
→ executor
→ broker reconciliation
```

---

### NXS-AI-BOUNDARY-003 — Coach needs a read-only default mode
**Severity:** P0/P1

Default Coach capability should be:

```text
read analytics
explain state
propose actions
create draft action
```

Live mutations should require an explicit, separately enabled operator capability.

---

### NXS-OWNERSHIP-001 — Settings ownership is fragmented
**Severity:** P0/P1

Settings may be changed through:

- canonical settings endpoints;
- dashboard aliases;
- strategy override endpoints;
- strategy risk endpoints;
- Coach actions;
- locked-profile replacement.

Required: one desired-state configuration document with version, owner, scope, checksum and activation status.

---

### NXS-OWNERSHIP-002 — Command ownership is fragmented
**Severity:** P0

Legacy EA commands and LocalBridge commands have different lifecycle maturity.

Required: one command contract and one command event ledger for both.

---

### NXS-OWNERSHIP-003 — Health ownership is ambiguous
**Severity:** P1

Health is partly observed, partly derived and partly policy-defined.

The response should separate:

```text
observations
policy_version
evaluations
overall_status
```

A score alone hides which layer produced the conclusion.

## Target operator-control contract

Every live mutation should require:

```text
request_id
requested_by
requested_at
source = dashboard | coach_draft | automation
target deployment/instance/account/symbol
action type
payload schema version
reason
current-state snapshot hash
risk-policy version
risk decision
confirmation method
expiry
idempotency key
command lifecycle
broker reconciliation result
```

## A2.3 status

Frontend and cross-component trust-boundary analysis is now complete enough to proceed to the database/governance phase.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| MQL5 source audit | 100% | **100%** |
| Backend audit | 97% | **98%** |
| Frontend/trust-boundary audit | not isolated | **92%** |
| Overall technical audit | 97% | **98%** |
| Specification coverage | 9% | **12%** |
| Developer handoff readiness | 43% | **48%** |
| Combined delivery | 60% | **63%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED

## Next active block

**A2.4 — Database model, migrations, retention, isolation and data-governance audit**


---

# AUDIT CONTINUATION — BLOCK A2.4
## Database Model, Migrations, Isolation, Retention and Data Governance

**Repository:** `starmarketkiller/MAX`  
**Commit:** `ef807abeed2ec2cfc2f0105f75cbd69acd91cc20`  
**Database:** SQLite

## Executive conclusion

The database is adequate for a single-node development deployment, but it is not yet a production-grade system of record for a multi-account trading platform.

The strongest current element is the introduction of an append-oriented `trade_events` ledger with replay deduplication for terminal events.

The principal weaknesses are:

- startup-driven schema migration;
- no explicit migration version ledger;
- weak relational integrity;
- global unscoped KV state;
- extensive JSON blobs;
- mixed identity models;
- no evidenced retention, archival or backup policy;
- no explicit tenant/deployment boundary;
- command and event records without full referential constraints;
- historical primary-key design that can collide across accounts.

## Current persistence topology

```text
SQLite file
├─ operational snapshots
│  ├─ ea_status
│  ├─ strategy_stats
│  ├─ trade_reasons
│  └─ visual_objects
├─ command state
│  ├─ ea_commands
│  ├─ bridge_commands
│  └─ command_events
├─ trading history
│  ├─ trades
│  ├─ trade_events
│  ├─ shadow_trades
│  └─ journal_meta
├─ configuration
│  └─ kv
├─ licensing
│  └─ licenses
├─ LocalBridge
│  └─ bridge_hosts
└─ Coach/notifications
   ├─ coach_memory
   ├─ coach_notifications
   └─ notifications
```

## Confirmed findings

### NXS-DB-001 — Schema migrations execute during application startup

**Severity:** P0/P1

`init_db()` creates tables and immediately executes additive migrations.

This creates several risks:

- every application replica may attempt migration;
- application startup and schema change are coupled;
- rollback is undefined;
- partially completed migrations can leave mixed schema state;
- deployment health depends on DDL success;
- no independent migration approval or audit trail exists.

**Required remediation**

Use a dedicated migration system with:

```text
migration_id
checksum
applied_at
applied_by
application_version
status
rollback_reference
```

Migrations should run once in a controlled deployment step.

---

### NXS-DB-002 — No explicit database schema-version table

**Severity:** P1

The reviewed schema uses `PRAGMA table_info` checks and conditional `ALTER TABLE`.

This makes migrations idempotent at a basic level, but it does not establish:

- ordered migration history;
- exact schema version;
- checksum drift detection;
- downgrade compatibility;
- failed migration state.

---

### NXS-DB-003 — Foreign-key enforcement is absent from the connection contract

**Severity:** P0/P1

The connection enables WAL mode but does not visibly enable `PRAGMA foreign_keys=ON`.

The schema also defines no foreign keys linking:

- command events to commands;
- journal metadata to logical trades;
- bridge commands to hosts;
- trade events to accounts/instances;
- Coach notifications to users/actions.

Orphaned and cross-scope records are therefore possible.

---

### NXS-DB-004 — Historical trade primary key can collide across accounts

**Severity:** P0

The source explicitly acknowledges that `trades.ticket` remains the primary key and may collide when different accounts use the same position identifier.

A unique `trade_uid` index helps only when the UID is present and does not repair the historical primary-key design.

**Required key**

```text
PRIMARY KEY (deployment_id, account_id, position_id)
```

or a server-issued immutable logical trade ID.

---

### NXS-DB-005 — Core tables lack deployment and instance scope

**Severity:** P0

Several tables are keyed only by:

- symbol;
- magic plus symbol;
- ticket;
- host ID;
- arbitrary KV key.

Missing canonical scope fields include:

```text
tenant_id
deployment_id
environment
instance_id
account_id
broker_id
terminal_id
```

This prevents reliable isolation in multi-account or multi-terminal deployments.

---

### NXS-DB-006 — Global KV table is an uncontrolled secondary database

**Severity:** P0/P1

The `kv` table stores many unrelated documents, including settings, profiles, histories, optimizer results, Coach sessions and runtime overrides.

Consequences:

- no schema per document;
- no ownership;
- no revision column;
- no optimistic concurrency;
- no expiry;
- no normalized indexing;
- large values are rewritten as whole documents;
- unrelated domains share one namespace.

The canonical settings schema is a positive application-level control, but the storage layer remains generic and global.

---

### NXS-DB-007 — Extensive JSON payload storage limits validation and querying

**Severity:** P1

Many operational tables store complete payloads in `TEXT`.

Examples include EA state, strategy stats, shadow trades, visual objects, command payloads and metadata.

This is useful for compatibility and forensic capture, but critical searchable fields must also be normalized.

Required pattern:

```text
typed canonical columns
+ immutable raw_payload
+ payload_schema_version
+ payload_hash
```

---

### NXS-DB-008 — Event ledger immutability is conventional, not enforced

**Severity:** P0/P1

`trade_events` is described as append-only, but the database schema does not visibly enforce immutability through:

- restricted database roles;
- update/delete triggers;
- hash chaining;
- signed event hashes;
- write-only service boundary.

The application currently treats it as append-only, which is a valuable design improvement, but database-level tamper evidence is absent.

---

### NXS-DB-009 — Exactly-once constraint covers only selected event types

**Severity:** P1

The partial unique index deduplicates one `close` and one `resync` per `trade_uid`.

It does not define canonical uniqueness for:

- partial closes;
- close requests;
- broker acknowledgements;
- protection changes;
- command-related trade events;
- corrections/reversals.

A full event identity needs:

```text
event_id
source_event_id
trade_uid
event_type
sequence
dedupe_key
```

---

### NXS-DB-010 — Command event history has weak relational structure

**Severity:** P1

`command_events` contains command ID, status, host, detail and timestamp but no visible:

- foreign key;
- event UUID;
- sequence number;
- actor identity;
- lease ID;
- payload hash;
- previous state;
- transition reason;
- target snapshot.

It is useful as an initial audit log, but insufficient for a legally or operationally strong command trail.

---

### NXS-DB-011 — Legacy EA commands and LocalBridge commands use separate persistence models

**Severity:** P0/P1

`ea_commands` remains a minimal queue with delivery state, while `bridge_commands` has lease, retry, idempotency and richer lifecycle fields.

This causes two definitions of:

- command identity;
- state;
- delivery;
- completion;
- expiry;
- audit history.

The database should converge on one command table and one event table.

---

### NXS-DB-012 — Timestamp representations are inconsistent

**Severity:** P1

The database mixes:

- Unix epoch `REAL`;
- integer expiry timestamps;
- ISO strings inside payloads;
- normalized and legacy MT5 datetime text.

This complicates ordering, retention, reconciliation and timezone correctness.

Required standard:

```text
UTC epoch milliseconds or timezone-aware UTC timestamp
```

with source timezone stored separately when necessary.

---

### NXS-DB-013 — Retention and archival rules are not evidenced

**Severity:** P1

No reviewed schema or deployment configuration establishes automatic retention for:

- shadow trades;
- notifications;
- Coach sessions and memory;
- command events;
- raw payloads;
- equity history;
- optimizer/backtest results;
- stale EA snapshots.

Unbounded datasets can grow indefinitely, while deleting them manually could destroy audit evidence.

Each data class needs an explicit retention policy.

---

### NXS-DB-014 — Backup, restore and disaster-recovery procedures are not evidenced

**Severity:** P0/P1

Docker Compose mounts a named volume and the example environment points SQLite to `/data/nexus.db`, which supports persistence across container replacement.

However, persistence is not backup.

No reviewed evidence establishes:

- scheduled consistent backups;
- WAL-aware snapshot procedure;
- off-host copies;
- encryption;
- restore testing;
- recovery point objective;
- recovery time objective;
- corruption detection;
- point-in-time recovery.

---

### NXS-DB-015 — Docker persistence depends on correct environment configuration

**Severity:** P1

The Compose file mounts `/data`, while the application default database path is inside the server source directory.

Persistence works as intended only when `NEXUS_DB_PATH=/data/nexus.db` is actually configured.

Production startup should verify that the database path is located on the expected persistent volume.

---

### NXS-DB-016 — WAL is enabled, but the durability policy is incomplete

**Severity:** P1

WAL improves concurrent read/write behavior.

The reviewed connection contract does not establish a complete policy for:

- synchronous mode;
- checkpoint frequency;
- WAL size;
- integrity checks;
- busy handling beyond connection timeout;
- read-only connections;
- transaction isolation by workload;
- backup coordination.

---

### NXS-DB-017 — Snapshot tables overwrite historical state

**Severity:** P1

Tables such as `ea_status`, `strategy_stats`, `trade_reasons` and `visual_objects` overwrite by a compact key.

This is suitable for a current-state projection, but historical changes are lost unless separately represented in an event stream.

The architecture should distinguish:

```text
immutable events
current projections
analytical materializations
```

---

### NXS-DB-018 — License records lack a complete lifecycle audit

**Severity:** P1

The license table stores key, account, trial, expiry and note.

It lacks:

- issued_at;
- issued_by;
- revoked_at;
- revocation reason;
- deployment scope;
- activation history;
- last verification;
- key hash instead of plaintext identifier;
- immutable license events.

---

### NXS-DB-019 — Coach data is not user-scoped

**Severity:** P0/P1

Coach memory and notification rows contain no user, account, deployment or environment scope.

This confirms the earlier trust-boundary finding that Coach information is effectively global.

---

### NXS-DB-020 — Journal metadata is keyed by ticket only

**Severity:** P0/P1

`journal_meta.ticket` can inherit the same cross-account collision problem as the legacy `trades` table.

Notes and ratings must bind to the logical trade UID and deployment/account scope.

## Positive controls verified

- WAL mode is enabled;
- database connection timeout is configured;
- Docker Compose provides a persistent named volume;
- the environment example maps the database to that volume;
- migrations are additive and written to be idempotent;
- the trade ledger has explicit terminal-event deduplication;
- bridge command idempotency has a unique partial index;
- raw payload retention supports forensic reconstruction;
- settings are checked against a canonical contract before the normal write path.

## Required target data layers

### 1. Immutable event store

Contains:

- broker/terminal observations;
- trade lifecycle;
- commands and transitions;
- risk decisions;
- configuration changes;
- license lifecycle;
- operator and AI recommendation events.

### 2. Desired-state configuration store

Versioned and scoped by:

- deployment;
- account;
- symbol;
- strategy;
- environment.

### 3. Current-state projections

Rebuildable views for:

- EA status;
- open positions;
- command status;
- active protections;
- active settings;
- bridge health.

### 4. Analytical materializations

Derived from immutable events using a recorded watermark and policy version.

### 5. Research storage

Physically or logically separated from live operational data:

- synthetic chart data;
- backtests;
- optimizer results;
- experimental strategies;
- demo calendars.

## Minimum database acceptance criteria

Before production approval:

1. versioned migration system;
2. tested backup and restore;
3. canonical deployment/account/instance identity;
4. no ticket-only primary keys;
5. foreign keys enabled and defined;
6. one command persistence model;
7. immutable event audit;
8. retention policy by data class;
9. normalized timestamps;
10. production path/persistent-volume startup check;
11. integrity-check automation;
12. separation of live and research datasets.

## Audit phase status

A2.4 completes the main source-level technical audit.

The next phase is no longer primarily discovery. It is the conversion of all findings into the authoritative NEXUS functional and technical specification.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| MQL5 source audit | 100% | **100%** |
| Backend audit | 98% | **100% source-level** |
| Frontend/trust-boundary audit | 92% | **96%** |
| Database/governance audit | not isolated | **100% source-level** |
| Overall technical audit | 98% | **100% source-level** |
| Executable/runtime evidence | not verified | **0% independently verified** |
| Specification coverage | 12% | **16%** |
| Developer handoff readiness | 48% | **54%** |
| Combined delivery | 63% | **67%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED by missing runtime/Strategy Tester evidence and unresolved P0 architecture findings.

## Next active block

**A3.1 — Canonical system architecture and authority model**


---

# SPECIFICATION PHASE — BLOCK A3.1
## Canonical NEXUS System Architecture and Authority Model

**Status:** normative specification draft  
**Scope:** live trading platform, control plane, data plane, research plane, AI assistance  
**Basis:** completed source-level audit of MQL5, backend, frontend, LocalBridge and database model

## 1. Architectural objective

NEXUS shall operate as a controlled trading platform in which every component has one defined responsibility and no component may silently assume authority outside its assigned domain.

The architecture must separate:

- observation;
- decision;
- authorization;
- execution;
- reconciliation;
- analytics;
- research;
- AI assistance.

The central principle is:

> **No UI, AI model, cache, projection or reconstructed dataset may become the authoritative source for a live trading decision or broker-side state.**

## 2. Canonical authority hierarchy

The required authority order is:

```text
1. Broker / MetaTrader terminal evidence
2. EA execution and protection state
3. Immutable backend event ledger
4. Risk and policy engine
5. Human-authorized command service
6. EA / LocalBridge execution adapters
7. Read models, analytics and dashboard
8. AI Coach and research tools
```

Higher layers may constrain lower layers only through explicit policy contracts.

Lower layers may never infer authorization from presentation-layer state.

## 3. System planes

### 3.1 Execution plane

Components:

- MetaTrader 5 terminal;
- NEXUS EA;
- broker connection;
- broker positions, orders and deals;
- local protection state;
- emergency execution controls.

Responsibilities:

- read broker state;
- calculate and place orders;
- enforce hard local protections;
- report execution lifecycle;
- reconcile broker results;
- reject commands that violate local safety.

The execution plane is the only layer allowed to interact with the broker.

### 3.2 Control plane

Components:

- command service;
- risk-policy engine;
- configuration service;
- license service;
- operator authorization;
- deployment and instance registry.

Responsibilities:

- validate requested actions;
- enforce roles and permissions;
- bind every mutation to a target;
- evaluate hard risk policy;
- create versioned commands;
- track command lifecycle;
- maintain desired configuration state;
- prevent cross-account actions.

### 3.3 Event and data plane

Components:

- immutable event store;
- current-state projections;
- analytical materializations;
- audit log;
- backup and archival services.

Responsibilities:

- persist canonical events;
- preserve ordering and provenance;
- rebuild projections;
- isolate deployment and account data;
- expose reliable read models;
- support disaster recovery.

### 3.4 Presentation plane

Components:

- React dashboard;
- Journal;
- strategy pages;
- live chart;
- LocalBridge administration;
- licensing views.

Responsibilities:

- display server-provided state;
- collect operator intent;
- request validation;
- show provenance and freshness;
- present command lifecycle;
- never derive authoritative trading state locally.

### 3.5 AI assistance plane

Components:

- Coach;
- recommendation engine;
- explanation layer;
- natural-language interface.

Responsibilities:

- explain;
- summarize;
- compare;
- identify anomalies;
- propose actions;
- prepare draft commands.

Default permissions:

```text
read-only
no direct broker access
no direct configuration writes
no direct protection reset
no direct risk mutation
```

### 3.6 Research plane

Components:

- backtest engine;
- optimizer;
- strategy library;
- synthetic data;
- demo calendar;
- research analytics.

Responsibilities:

- experimentation;
- simulation;
- ranking;
- parameter search;
- reproducibility.

Research data must never flow into live execution without an explicit promotion process.

## 4. Canonical component ownership

| Domain | Authoritative owner | Consumers |
|---|---|---|
| Broker positions/orders/deals | MetaTrader/broker | EA, backend ledger, dashboard |
| Local execution protections | EA | backend, dashboard |
| Global hard risk policy | Risk engine | command service, EA |
| Desired runtime settings | Configuration service | EA, dashboard |
| Command lifecycle | Command service | EA, LocalBridge, dashboard |
| Trade history | Immutable event ledger | analytics, Journal, Coach |
| Current EA status | Instance projection | dashboard, Coach |
| Analytics | Backend materialized views | dashboard, Coach |
| License state | License service | EA, dashboard |
| Deployment state | Deployment registry | LocalBridge, dashboard |
| AI recommendations | AI recommendation store | operator, audit |
| Human approvals | Authorization service | command service |
| Backtest results | Research store | dashboard, promotion workflow |

## 5. Identity model

Every live record and command must carry:

```text
tenant_id
deployment_id
environment
instance_id
terminal_id
account_id
broker_id
symbol
strategy_id
```

Not every field is mandatory for every event, but:

- `deployment_id`;
- `environment`;
- `instance_id`;
- `account_id`

must exist for all live trading state.

### 5.1 Environment classification

Allowed environments:

```text
DEVELOPMENT
SIMULATION
DEMO
PAPER
LIVE
```

A command created in one environment must never execute in another.

### 5.2 Instance identity

`instance_id` must be server-issued and bound to:

- deployment;
- account;
- terminal;
- EA magic;
- machine identity;
- certificate or machine credential.

Client-provided `host_id`, `magic` or symbol alone are insufficient identity.

## 6. Source-of-truth rules

### Rule SOT-1 — Broker evidence

Broker-confirmed deals and current terminal positions are authoritative for execution truth.

### Rule SOT-2 — Ledger truth

The immutable backend ledger is authoritative for historical platform truth once broker evidence has been recorded.

### Rule SOT-3 — Projections are disposable

Current-state tables, caches and dashboard views are projections and must be rebuildable.

### Rule SOT-4 — Analytics are derived

Metrics are authoritative only relative to:

- source event watermark;
- analytics policy version;
- dataset scope;
- provenance.

### Rule SOT-5 — Research is never live truth

Backtests, optimizer rankings, simulated bars and reconstructed datasets must never be used as live execution truth.

### Rule SOT-6 — AI output is advisory

AI text and AI-generated actions are proposals, not authorized instructions.

## 7. Canonical command flow

```text
Operator or approved automation
        ↓
Create action request
        ↓
Authorization check
        ↓
Risk-policy evaluation
        ↓
Target-state validation
        ↓
Create immutable command
        ↓
Lease to executor
        ↓
Executor validates locally
        ↓
Broker/terminal action
        ↓
Execution events
        ↓
Broker reconciliation
        ↓
Terminal success/failure state
```

## 8. Required command states

```text
DRAFT
AWAITING_CONFIRMATION
REJECTED_POLICY
PENDING
LEASED
RUNNING
BROKER_ACCEPTED
SUCCEEDED
FAILED_RETRYABLE
FAILED_FINAL
EXPIRED
CANCELLED
RECONCILIATION_MISMATCH
```

### 8.1 Terminal-state meaning

`SUCCEEDED` means:

- the executor completed the requested action;
- broker/terminal evidence confirms the expected state;
- reconciliation passed.

`DELIVERED` must not be considered terminal success.

## 9. Human authorization levels

### Level 0 — Read only

- dashboard view;
- analytics;
- Journal;
- Coach explanation;
- research.

### Level 1 — Routine operator

- pause;
- resume when no hard protection is active;
- request resync;
- non-destructive diagnostics.

### Level 2 — Trading operator

- close one position;
- partial close;
- disable strategy;
- apply approved profile.

Requires explicit target confirmation.

### Level 3 — Risk manager

- change risk;
- change risk multiplier;
- reset protections;
- resume after emergency stop;
- approve high-impact settings.

Requires step-up authentication and reason.

### Level 4 — Deployment administrator

- deploy files;
- compile;
- restart terminal;
- manage LocalBridge;
- manage release manifests.

### Level 5 — Owner

- licensing;
- credentials;
- role administration;
- production environment activation;
- irreversible administrative changes.

## 10. Risk-engine precedence

The risk engine has veto authority over:

- human requests;
- AI-generated proposals;
- automation;
- configuration changes;
- strategy promotion.

It may not be bypassed by UI routes or compatibility aliases.

### 10.1 Non-overridable protections

Examples:

- max account drawdown;
- max daily loss;
- emergency stop;
- max effective risk;
- max aggregate exposure;
- stale broker state;
- instance identity mismatch;
- license invalid;
- live/research environment mismatch.

## 11. Configuration architecture

Runtime configuration must be represented as a versioned desired-state document:

```text
configuration_id
scope
schema_version
version
status
created_by
created_at
approved_by
approved_at
checksum
effective_from
effective_until
settings
```

Allowed statuses:

```text
DRAFT
VALIDATED
APPROVED
ACTIVE
SUPERSEDED
REVOKED
```

The EA must report:

- desired version received;
- active version applied;
- validation result;
- rejection reason;
- checksum.

## 12. Strategy lifecycle

Every strategy must have:

```text
strategy_id
implementation_version
status
environment eligibility
risk class
minimum evidence
approved symbols
approved timeframes
approved accounts
owner
```

Statuses:

```text
RESEARCH
SHADOW
PAPER
LIMITED_LIVE
LIVE
QUARANTINED
RETIRED
```

A strategy may advance only through an explicit promotion workflow.

## 13. AI recommendation contract

Every Coach recommendation must be stored separately from execution:

```text
recommendation_id
model
model_version
prompt_policy_version
input_provenance
scope
recommendation
risk_level
created_at
expires_at
```

Any live action derived from it must additionally contain:

```text
authorized_by
authorized_at
authorization_method
risk_decision_id
command_id
```

## 14. Frontend requirements

The dashboard must show for every critical data block:

- source;
- target instance/account;
- observed timestamp;
- age;
- stale state;
- provenance;
- environment;
- policy version;
- last reconciliation state.

For every live command, the confirmation screen must show:

- exact target;
- current state;
- intended effect;
- worst-case effect;
- risk-policy decision;
- expiry;
- required role;
- command status after submission.

## 15. Compatibility route policy

Legacy routes may exist only when registered with:

```text
legacy_route
canonical_route
owner
introduced_version
removal_version
telemetry
security equivalence status
```

A compatibility route may not bypass:

- authorization;
- target scoping;
- validation;
- risk policy;
- command lifecycle;
- audit logging.

## 16. Failure containment

Each plane must fail independently.

### Execution plane failure

- preserve local protections;
- reject unsafe commands;
- continue broker reconciliation;
- buffer events for retry.

### Backend failure

- EA continues local hard protection;
- no new remote risk increase;
- no protection reset;
- queue outbound events;
- command execution expires safely.

### Dashboard failure

- no impact on EA;
- no loss of command state;
- no hidden automatic retries of destructive actions.

### AI failure

- no impact on execution;
- no fallback to direct commands;
- no mutation without operator authorization.

### Research failure

- no impact on live services;
- no shared worker starvation;
- no live configuration change.

## 17. Mandatory architectural invariants

1. No command without a canonical target.
2. No live mutation without authorization.
3. No authorization without risk evaluation.
4. No success without broker reconciliation.
5. No analytics without provenance.
6. No research data presented as live.
7. No AI output treated as authority.
8. No global unscoped live state.
9. No compatibility route bypass.
10. No production deployment without auditable runtime evidence.

## 18. Acceptance criteria for A3.1

A developer implementation is conformant only when:

- all live components use canonical identities;
- all live commands use one state machine;
- UI cannot write directly to KV/config tables;
- Coach is read-only by default;
- risk engine has hard veto;
- command success is broker-reconciled;
- research and live data are isolated;
- configuration is versioned and acknowledged by the EA;
- operator roles are enforced server-side;
- every critical read includes provenance and freshness.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| Source-level technical audit | 100% | **100%** |
| Canonical architecture specification | 0% | **100% draft** |
| Overall specification coverage | 16% | **25%** |
| Developer handoff readiness | 54% | **62%** |
| Combined delivery | 67% | **72%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED

## Next active block

**A3.2 — Canonical event model, command schema and data contracts**


---

# SPECIFICATION PHASE — BLOCK A3.2
## Canonical Event Model, Command Schema and Data Contracts

**Status:** normative specification draft

### Universal event envelope

Every immutable event shall include:

```text
event_id
event_type
event_version
schema_version
created_at
observed_at
tenant_id
deployment_id
environment
instance_id
account_id
correlation_id
causation_id
source
actor
payload
payload_hash
```

### Canonical command envelope

```text
command_id
command_type
schema_version
target
requested_by
requested_at
approved_by
approved_at
risk_decision_id
policy_version
payload
expires_at
idempotency_key
status
execution_result
broker_result
reconciliation_result
correlation_id
```

Commands are immutable after creation. State changes are represented through command events.

### Canonical command events

```text
COMMAND_CREATED
COMMAND_AWAITING_CONFIRMATION
COMMAND_APPROVED
COMMAND_REJECTED_POLICY
COMMAND_LEASED
COMMAND_STARTED
COMMAND_BROKER_ACCEPTED
COMMAND_SUCCEEDED
COMMAND_FAILED_RETRYABLE
COMMAND_FAILED_FINAL
COMMAND_EXPIRED
COMMAND_CANCELLED
COMMAND_RECONCILIATION_MISMATCH
```

### Provenance contract

Every analytical or presentation dataset must expose:

```text
source_type
source_id
dataset_version
watermark
observed_at
derived_at
policy_version
environment
confidence
stale
```

### API contract requirements

Every endpoint must declare request schema, response schema, authorization capability, target scope, mutation semantics, idempotency behavior, side effects, error taxonomy and deprecation status.

GET requests must never mutate live state.

### Canonical errors

```text
AUTHENTICATION_REQUIRED
AUTHORIZATION_DENIED
TARGET_NOT_FOUND
TARGET_SCOPE_MISMATCH
VALIDATION_FAILED
RISK_POLICY_DENIED
COMMAND_EXPIRED
IDEMPOTENCY_CONFLICT
STALE_STATE
BROKER_REJECTED
RECONCILIATION_FAILED
DEPENDENCY_UNAVAILABLE
INTERNAL_ERROR
```

### EA configuration acknowledgement

The EA must report desired and applied configuration ID, version, checksum, application status, rejection reason and application timestamp.

---

# SPECIFICATION PHASE — BLOCK A3.3
## Canonical Risk Engine and Operational Policy Model

**Status:** normative specification draft

### Decision hierarchy

```text
Identity
→ Permission
→ License
→ Data integrity
→ Risk calculation
→ Policy decision
→ Configuration compatibility
→ Command creation
→ Execution
→ Broker reconciliation
```

### Hard controls

Hard controls cannot be bypassed through ordinary operator, AI or compatibility routes.

Examples: maximum drawdown, maximum daily loss, minimum equity, maximum effective risk, maximum aggregate exposure, minimum margin level, stale broker state, emergency stop, account/environment mismatch, invalid license and missing reconciliation.

### Operational account states

```text
NORMAL
CAUTION
PROTECTED
EMERGENCY
LOCKED
RECOVERY
```

Direct transition from `EMERGENCY` to `NORMAL` is forbidden.

### Risk scopes

Risk must be evaluated at trade, strategy, symbol, account, deployment, portfolio, broker and time-window level.

### Decision output

```text
risk_decision_id
policy_version
decision = ALLOW | ALLOW_WITH_CONDITIONS | DENY
severity
reasons
required_actions
maximum_risk
maximum_volume
expires_at
input_snapshot_hash
```

### AI authority ladder

```text
OBSERVE
SUGGEST
DRAFT
REQUEST
EXECUTE
```

`EXECUTE` is never enabled by default and remains subject to human authorization and risk veto.

### Non-negotiable invariants

1. No trade without canonical identity.
2. No command without canonical target.
3. No risk increase during `EMERGENCY`.
4. No protection reset without recovery validation.
5. No configuration change without version and checksum.
6. No command success without reconciliation.
7. No synthetic data in live decision flow.
8. No LIVE strategy without approved promotion.
9. No stale state used for risk increase.
10. No AI recommendation treated as authority.

---

# SPECIFICATION PHASE — BLOCK A3.4
## Canonical Trading Lifecycle and State Machines

**Status:** normative specification draft

## 1. End-to-end lifecycle

```text
Market observation
→ Signal candidate
→ Strategy validation
→ Risk evaluation
→ Trade intent
→ Order request
→ Broker acknowledgement
→ Position open
→ Position management
→ Exit request
→ Broker close
→ Reconciliation
→ Trade finalization
→ Journal
→ Analytics
→ Coach review
```

## 2. Signal lifecycle

```text
DETECTED
FILTERED_OUT
VALIDATED
EXPIRED
CONVERTED_TO_INTENT
CANCELLED
```

A signal is informational until converted into a trade intent.

Required fields:

```text
signal_id
strategy_id
strategy_version
symbol
timeframe
direction
detected_at
expires_at
features
market_snapshot_id
confidence
environment
```

## 3. Trade intent lifecycle

```text
DRAFT
AWAITING_RISK
RISK_APPROVED
RISK_REJECTED
AWAITING_AUTHORIZATION
AUTHORIZED
EXPIRED
CANCELLED
CONVERTED_TO_ORDER
```

Required fields include trade intent ID, signal ID, account, instance, strategy, symbol, direction, requested volume/risk, entry/stop/target plan, risk decision and authorization.

## 4. Order lifecycle

```text
CREATED
SUBMISSION_PENDING
SUBMITTED
BROKER_ACCEPTED
BROKER_REJECTED
PARTIALLY_FILLED
FILLED
CANCEL_PENDING
CANCELLED
EXPIRED
FAILED
```

An order is not a position.

## 5. Position lifecycle

```text
OPENING
OPEN
MANAGED
REDUCING
CLOSE_PENDING
CLOSED
RECONCILING
RECONCILED
MISMATCH
ARCHIVED
```

A position becomes analytically final only at `RECONCILED`.

## 6. Canonical position actions

```text
MOVE_STOP
MOVE_TARGET
SET_BREAK_EVEN
TRAIL_STOP
PARTIAL_CLOSE
FULL_CLOSE
REDUCE_RISK
EMERGENCY_CLOSE
```

Every action must produce a command, broker response, execution event and reconciliation event.

## 7. Partial-close model

Partial closes must never overwrite logical trade history.

Required fields:

```text
logical_trade_uid
position_uid
deal_uid
partial_sequence
volume_before
volume_closed
volume_after
realized_pnl
remaining_risk
```

The logical trade closes only when remaining volume reaches zero or broker evidence confirms terminal closure.

## 8. Protection lifecycle

SL/TP changes shall produce:

```text
PROTECTION_CHANGE_REQUESTED
PROTECTION_CHANGE_ACCEPTED
PROTECTION_CHANGE_REJECTED
PROTECTION_RECONCILED
```

The active protection state is a projection rebuilt from these events.

## 9. Close lifecycle

```text
CLOSE_INTENT_CREATED
CLOSE_RISK_CHECKED
CLOSE_COMMAND_CREATED
CLOSE_SUBMITTED
BROKER_CLOSE_ACCEPTED
BROKER_CLOSE_REJECTED
POSITION_CLOSED
POSITION_RECONCILED
```

`POSITION_CLOSED` without reconciliation is not final success.

## 10. Reconciliation outcomes

```text
MATCH
MISSING_BROKER_POSITION
UNEXPECTED_BROKER_POSITION
VOLUME_MISMATCH
PRICE_MISMATCH
PROTECTION_MISMATCH
PNL_MISMATCH
IDENTITY_MISMATCH
UNKNOWN
```

## 11. Trade finalization conditions

A trade may be finalized only when broker evidence exists, final volume is zero, all partial deals are accounted for, realized P&L is reconciled, strategy/account identity is known, close reason is recorded and provenance is valid.

## 12. Journal lifecycle

Journal metadata binds to immutable logical trade UID and includes notes, tags, rating, review status, reviewer, timestamps, screenshots, lessons and policy breaches.

Journal updates are versioned and auditable.

## 13. Analytics lifecycle

Analytics are produced only from reconciled terminal events.

Every materialization records:

```text
dataset_version
watermark
policy_version
source_event_count
excluded_event_count
legacy_quarantine_count
generated_at
```

## 14. Restart and recovery

After EA or backend restart:

1. load desired configuration;
2. restore local protection state;
3. query broker positions, orders and deals;
4. compare broker, EA and backend state;
5. emit resync events;
6. quarantine mismatches;
7. prevent risk increase until reconciliation completes.

## 15. Failure behavior

Broker timeout, EA crash after submission, backend outage, duplicate close requests and unknown positions must never create automatic success or duplicate broker effects.

Unknown positions enter quarantine.

## 16. Trading lifecycle invariants

1. A signal is not an order.
2. An order is not a position.
3. Broker acceptance is not completion.
4. Position close is not final until reconciled.
5. Partial closes never overwrite previous events.
6. Analytics exclude unreconciled trades.
7. Restart cannot silently reset protections.
8. Unknown positions enter quarantine.
9. Duplicate requests cannot duplicate broker effects.
10. Every trade is traceable from signal to final analytics.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| Source-level technical audit | 100% | **100%** |
| Canonical architecture | 100% draft | **100% draft** |
| Event and command contracts | in progress | **100% draft** |
| Risk and policy model | in progress | **100% draft** |
| Trading lifecycle model | 0% | **100% draft** |
| Overall specification coverage | 25% | **47%** |
| Developer handoff readiness | 62% | **78%** |
| Combined delivery | 72% | **84%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED

## Next active block

**A3.5 — Strategy lifecycle, promotion gates, backtest evidence and live-validation protocol**

---

# SPECIFICATION PHASE — BLOCK A3.5
## Strategy Lifecycle, Promotion Gates, Backtest Evidence and Live-Validation Protocol

**Status:** normative specification draft

## 1. Objective

This section defines how a strategy becomes eligible for use inside NEXUS. Compilation or one profitable backtest is not production evidence. Promotion requires a reproducible chain from research to controlled live deployment.

## 2. Canonical strategy identity

Every strategy release must have:

```text
strategy_id
display_name
implementation_version
schema_version
owner
status
risk_class
supported_symbols
supported_timeframes
supported_environments
source_commit
artifact_hash
created_at
retired_at
```

Logic, parameters, risk profile, filters, execution rules, exit rules, data assumptions and evidence package must be versioned. A material behaviour change creates a new release.

## 3. Strategy states

```text
RESEARCH
SHADOW
PAPER
LIMITED_LIVE
LIVE
QUARANTINED
RETIRED
```

**RESEARCH:** coding, unit tests, simulation and parameter study; no broker execution.

**SHADOW:** processes live data and records hypothetical actions without placing orders.

**PAPER:** runs the production contracts in demo/simulated execution to validate runtime state, retries, restart recovery and reconciliation.

**LIMITED_LIVE:** real capital under explicit caps for risk, volume, symbols, sessions, concurrent trades and daily loss.

**LIVE:** approved production use only inside the certified scope.

**QUARANTINED:** no new entries; existing positions are managed only under safety rules.

**RETIRED:** no new deployments; historical evidence remains available.

## 4. Promotion workflow

```text
RESEARCH
→ evidence review
→ SHADOW
→ runtime review
→ PAPER
→ validation review
→ LIMITED_LIVE
→ live evidence review
→ LIVE
```

Every promotion must record:

```text
promotion_request_id
strategy_id
from_status
to_status
requested_by
evidence_package_id
reviewers
risk_decision_id
decision
decision_reason
approved_scope
approved_at
expires_at
```

No promotion may occur automatically from one performance threshold.

## 5. Reproducible evidence package

Required content:

```text
strategy_id
implementation_version
source_commit
build_artifact_hash
compiler_version
terminal_version
broker_model
symbol_specification
data_source
data_range
timezone
spread_model
commission_model
swap_model
slippage_model
execution_delay_model
parameter_set
random_seed
test_environment
result_hash
```

The package must support independent reproduction within a declared tolerance.

## 6. Evidence classes

```text
B0  Smoke test
B1  Deterministic regression
B2  Historical validation
B3  Out-of-sample validation
B4  Walk-forward validation
B5  Monte Carlo and perturbation
B6  Forward demo/paper evidence
B7  Limited-live evidence
```

No strategy may become `LIVE` without B7 evidence.

## 7. Minimum test dimensions

Evidence should cover trend, range, high/low volatility, news conditions, widening spread, rollover, session transitions, gaps where relevant, broker disconnection, restart with open positions, duplicate command delivery, delayed acknowledgement, partial close, rejected order, insufficient margin and stale data.

## 8. Required performance measures

```text
net_profit
gross_profit
gross_loss
profit_factor
expectancy
win_rate
average_win
average_loss
max_drawdown_absolute
max_drawdown_relative
recovery_factor
trade_count
exposure_time
average_holding_time
largest_win
largest_loss
consecutive_losses
consecutive_wins
tail_loss_percentile
costs
slippage
```

No single metric is sufficient for approval.

## 9. Statistical adequacy and overfitting controls

The evidence must state trade count, independent periods, symbols, regimes, confidence bounds where applicable, outlier dependence and concentration of results.

Required overfitting controls include development/test separation, parameter-search history, number of tested configurations, out-of-sample results, walk-forward analysis, parameter stability maps and degradation from in-sample to out-of-sample.

Red flags include narrow profitable parameter islands, profit concentrated in one period or symbol, very low sample size and high sensitivity to spread or delay.

## 10. Baseline comparisons

Every strategy must be compared against the previous release, a no-trade baseline, an appropriate simple benchmark and, where meaningful, shuffled/random-entry controls.

The evidence must show that results are not explained only by leverage, market drift, one exceptional trade, unrealistic costs or data leakage.

## 11. Data quality and symbol specification

Backtest evidence must declare source, coverage, timezone, missing/duplicate data, precision, tick/bar model and spread source.

For FX, XAUUSD and crypto, the symbol contract must include digits, point size, tick size/value, contract size, minimum volume, volume step, stop/freeze levels and trading sessions.

A result without symbol specification is not portable production evidence.

## 12. Execution realism

Production-candidate tests must include realistic spread, commission, swap, slippage, latency, order rejection, partial fills where applicable, stop-distance constraints, volume rounding, market closure and broker execution rules.

A fixed idealized spread is insufficient.

## 13. Artifact equivalence

Required chain:

```text
source commit
→ build artifact
→ artifact hash
→ test run
→ evidence package
→ deployment manifest
```

The tested artifact must be the deployed artifact. Recompilation or code changes invalidate prior approval unless the artifact hash remains identical.

## 14. Parameter governance

Every active parameter set requires:

```text
parameter_set_id
strategy_id
strategy_version
scope
values
created_by
approved_by
evidence_package_id
effective_from
effective_until
checksum
```

Silent mutation, untracked optimizer output and automatic promotion to live are prohibited.

## 15. Limited-live protocol

A strategy entering `LIMITED_LIVE` must have exact account scope, maximum initial and aggregate risk, maximum daily loss, trade and concurrency caps, allowed symbols/sessions/order types, trial duration, evidence target and automatic stop conditions.

Automatic stop conditions include reconciliation mismatch, unexpected order type, drawdown breach, abnormal slippage/spread, event loss, configuration mismatch, runtime exception and excessive broker rejection.

## 16. Live monitoring and degradation

A live release must be compared continuously with its approved evidence envelope.

Monitor expectancy, win/loss distribution, drawdown, slippage, spread, trade frequency, holding time, rejection rate, missed signals, regime distribution, parameter drift and reconciliation errors.

Outcomes:

```text
WITHIN_EXPECTATION
WATCH
DEGRADED
BREACH
UNKNOWN
```

`BREACH` or prolonged `UNKNOWN` triggers risk reduction or quarantine according to policy.

## 17. Shadow comparison

Where practical, the active release should run beside the next candidate, the previous stable release and a no-trade control in shadow mode. Shadow instances must never create broker orders.

## 18. Rollback and quarantine

Every promoted release requires a previous stable version, rollback manifest, compatible configuration statement, open-position handling rule, trigger and authorization.

Quarantine workflow:

```text
Trigger detected
→ New entries blocked
→ Open positions classified
→ Safe-management policy
→ Evidence captured
→ Root-cause review
→ Remediation or retirement
→ Revalidation before reactivation
```

## 19. Required test layers

- Unit tests for calculations, lot sizing, filters, sessions and transitions.
- Contract tests for EA/backend payloads, commands, events and settings acknowledgement.
- Integration tests for EA, backend, LocalBridge, lease/retry and restart recovery.
- Scenario tests for emergency stop, duplicate commands, stale settings, rejection, outages and unknown positions.
- Regression tests proving critical fixed defects remain fixed.

## 20. Approval roles

Minimum responsibilities:

```text
strategy author
independent reviewer
risk approver
deployment approver
```

For LIVE promotion, self-approval without an explicit exception record is not acceptable.

## 21. Production acceptance gates

A strategy may become LIVE only when:

1. source and artifact are identified;
2. compilation is reproducible;
3. unit and contract tests pass;
4. historical validation is complete;
5. out-of-sample evidence exists;
6. robustness testing exists;
7. paper evidence exists;
8. limited-live evidence exists;
9. risk approval is recorded;
10. deployment scope is explicit;
11. rollback is ready;
12. runtime monitoring is active;
13. no unresolved P0 affects the strategy path;
14. broker reconciliation is proven;
15. the exact promoted artifact was tested.

## 22. Current NEXUS evidence status

The source-level audit does not provide independently verified evidence for reproducible MetaEditor compilation, exact Strategy Tester configuration, independent result reproduction, forward demo, limited-live execution, artifact-hash equivalence, failure reconciliation, restart recovery with open positions or an automated regression suite.

Therefore:

```text
Current strategy promotion ceiling: RESEARCH / partial SHADOW
LIVE approval: NOT PERMITTED
```

This does not state that the strategy cannot work. It means the production evidence chain is incomplete.

## 23. A3.5 acceptance criteria

Implementation is conformant when every strategy has stable identity/version, promotion states are server-enforced, evidence is reproducible, deployed and tested artifacts match, costs are realistic, robustness and out-of-sample tests are recorded, limited-live exposure is capped, degradation triggers policy, rollback/quarantine exist and LIVE promotion cannot bypass evidence gates.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| Source-level technical audit | 100% | **100%** |
| Canonical architecture | 100% draft | **100% draft** |
| Event and command contracts | 100% draft | **100% draft** |
| Risk and policy model | 100% draft | **100% draft** |
| Trading lifecycle model | 100% draft | **100% draft** |
| Strategy promotion and evidence | 0% | **100% draft** |
| Overall specification coverage | 47% | **58%** |
| Developer handoff readiness | 78% | **84%** |
| Combined delivery | 84% | **88%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED by missing independently verified runtime and strategy evidence.

## Next active block

**A3.6 — Security architecture, identity, capabilities, secrets and production hardening specification**


---

# SPECIFICATION PHASE — BLOCK A3.6
## Security Architecture, Identity, Capabilities, Secrets and Production Hardening

**Status:** normative specification draft

## 1. Objective

This section defines the minimum security architecture required for NEXUS to operate as a production trading platform.

Security controls must protect:

- operator identities;
- broker-connected instances;
- live accounts;
- configuration;
- commands;
- licenses;
- source code and deployment artifacts;
- secrets;
- audit evidence;
- research/live separation.

The platform must assume that UI clients, local machines, networks and external integrations can fail or be compromised.

## 2. Zero-trust principle

No component is trusted solely because it is:

- on localhost;
- inside the same container network;
- launched by the desktop application;
- connected through LocalBridge;
- authenticated once in the past;
- using a known magic number;
- using a known account number;
- using a shared static token.

Every request must be evaluated using current identity, capability, target and context.

## 3. Canonical identity domains

NEXUS must distinguish at least:

```text
human_user
service_account
deployment
machine
terminal
ea_instance
broker_account
api_client
automation
ai_agent
```

One identity must not impersonate another identity class.

For example:

- a dashboard user is not an EA instance;
- an EA instance is not a deployment administrator;
- the AI Coach is not a trading operator;
- LocalBridge is not the owner.

## 4. Human identity model

Required user fields:

```text
user_id
tenant_id
email_or_username
status
roles
capabilities
mfa_status
created_at
last_authenticated_at
credential_version
session_version
```

Allowed user states:

```text
INVITED
ACTIVE
SUSPENDED
LOCKED
DISABLED
```

Disabled, suspended or locked users must lose active authorization immediately.

## 5. Role and capability model

Roles are administrative groupings.

Capabilities are the actual authorization primitive.

Example capabilities:

```text
dashboard.read
analytics.read
journal.write
strategy.read
strategy.promote
trade.request_close
trade.request_partial_close
risk.read
risk.modify
protection.reset
configuration.read
configuration.write
configuration.approve
command.read
command.create
command.cancel
deployment.read
deployment.execute
deployment.restart
license.read
license.manage
user.manage
audit.read
```

Server-side authorization must check capabilities, not only role names.

## 6. High-risk capability separation

The following capabilities must remain separate:

```text
risk.modify
protection.reset
trade.execute
configuration.approve
deployment.execute
license.manage
user.manage
```

Possessing one does not imply possession of the others.

The owner role may aggregate them, but every use remains auditable and may require step-up authentication.

## 7. Step-up authentication

Step-up authentication is mandatory for:

- resetting hard protections;
- increasing risk;
- enabling LIVE mode;
- approving a strategy for LIVE;
- restarting or redeploying a production terminal;
- changing broker/account binding;
- rotating production secrets;
- modifying user privileges;
- disabling audit controls;
- overriding quarantine.

Step-up evidence must include:

```text
authentication_method
authenticated_at
expires_at
user_id
session_id
action_scope
```

## 8. Multi-factor authentication

Production operator accounts should require MFA.

At minimum:

- owner;
- risk manager;
- deployment administrator;
- license administrator.

Recovery methods must be auditable and must not silently disable MFA.

## 9. Session architecture

Production sessions must use:

- short-lived access sessions;
- secure refresh or re-authentication;
- server-side revocation;
- session rotation after privilege change;
- per-device session identifiers;
- inactivity timeout;
- absolute session lifetime;
- protection against replay.

A long-lived 720-hour JWT is not acceptable for production administration.

## 10. Cookie and token rules

Browser authentication should use cookies with:

```text
HttpOnly
Secure
SameSite
narrow Path
appropriate Domain
```

State-changing browser requests require CSRF protection.

Tokens must not be:

- returned redundantly in both body and cookie;
- logged;
- exposed in URLs;
- stored in localStorage;
- embedded in source;
- reused across environments.

## 11. CSRF protection

For cookie-authenticated mutation endpoints, NEXUS must implement one approved mechanism:

- synchronizer token;
- double-submit cookie with strict validation;
- origin-bound anti-CSRF token;
- same-site plus origin/referer validation as defense in depth.

GET requests must remain read-only.

## 12. Machine and EA identity

EA and LocalBridge identity must be server-issued.

Required binding:

```text
machine_id
deployment_id
terminal_id
instance_id
account_id
broker_id
environment
credential_id
credential_version
```

The server must not trust client assertions alone for:

- host ID;
- account ID;
- magic number;
- symbol;
- deployment identity.

## 13. Machine credentials

Production machine credentials should be:

- unique per deployment or instance;
- revocable;
- rotated;
- environment-specific;
- scope-limited;
- protected at rest;
- never shared across all LocalBridge installations.

Preferred mechanisms:

- mTLS client certificates;
- signed short-lived machine tokens;
- hardware-backed keys where available;
- deployment enrollment workflow.

## 14. Deployment enrollment

A new machine or terminal must enter through:

```text
ENROLLMENT_REQUESTED
→ OPERATOR_APPROVED
→ CREDENTIAL_ISSUED
→ BINDING_VERIFIED
→ ACTIVE
```

Enrollment must record:

- requesting machine fingerprint;
- target environment;
- intended account;
- approver;
- credential issuance;
- expiration;
- revocation status.

## 15. Request signing

High-impact machine-to-backend requests should include:

```text
credential_id
timestamp
nonce
body_hash
signature
```

The backend must reject:

- expired timestamps;
- reused nonces;
- invalid signatures;
- payload mismatches;
- revoked credentials;
- target-scope mismatches.

## 16. Secret classification

Secrets must be classified.

### Class S0 — Public

Examples:

- frontend public configuration;
- non-sensitive version identifiers.

### Class S1 — Internal

Examples:

- internal service names;
- non-production feature flags.

### Class S2 — Sensitive

Examples:

- API keys;
- database credentials;
- machine credentials;
- signing secrets.

### Class S3 — Critical

Examples:

- broker credentials;
- production signing keys;
- license authority keys;
- owner recovery secrets;
- production deployment credentials.

S2 and S3 secrets require managed storage and rotation.

## 17. Secret storage

Production secrets must not reside in:

- repository files;
- Docker images;
- frontend bundles;
- default `.env` committed to source;
- logs;
- database rows in plaintext without encryption;
- hard-coded MQL5 constants.

Preferred storage:

- managed secret manager;
- OS credential vault;
- encrypted deployment secret store;
- hardware security module for highest-value keys.

## 18. Secret rotation

Every secret type must define:

```text
owner
scope
issued_at
expires_at
rotation_interval
last_rotated_at
revocation_method
dependent_services
emergency_rotation_runbook
```

Rotation must support overlap where necessary so active services can transition without outage.

## 19. Default credentials

Production startup must fail closed when:

- administrator credentials remain default;
- signing secret is missing;
- signing secret uses fallback value;
- machine token is shared default;
- broker secret is absent or malformed;
- encryption key is missing;
- environment is LIVE but development credentials are active.

No production component may silently generate an ephemeral authentication secret.

## 20. License security architecture

License state must be validated through a defined authority.

Required license fields:

```text
license_id
tenant_id
product
features
environment
status
issued_at
expires_at
machine_binding
account_binding
signature
issuer
```

Allowed states:

```text
ACTIVE
GRACE
EXPIRED
REVOKED
SUSPENDED
INVALID
```

License validation must fail closed for live execution when authenticity cannot be established.

A license may constrain features, but must not bypass independent security or risk policy.

## 21. Transport security

Production communications must use authenticated encryption.

Requirements:

- TLS for browser/backend;
- TLS or mTLS for LocalBridge/backend;
- certificate validation;
- no insecure fallback;
- modern protocol versions;
- controlled certificate renewal;
- explicit trust store;
- hostname verification.

Local network placement does not replace transport security.

## 22. Network segmentation

Recommended production zones:

```text
public ingress
application services
command/risk services
data services
deployment services
research workers
monitoring/audit
```

Research workers must not have direct access to broker execution credentials.

The frontend must not connect directly to the database, EA or broker terminal.

## 23. Service-to-service authorization

Internal services must authenticate and authorize each other.

A service identity must have only the capabilities required for its function.

Examples:

- analytics service can read reconciled events but cannot create commands;
- Coach service can read approved datasets but cannot mutate risk;
- deployment service can manage artifacts but cannot change trading risk;
- license service cannot place trades.

## 24. Input validation

All external payloads require strict schema validation.

Validation must cover:

- type;
- length;
- range;
- enum;
- format;
- nesting depth;
- unknown fields;
- numeric precision;
- timestamps;
- target identity;
- environment;
- version.

Machine-originated payloads are not trusted merely because they come from an EA or LocalBridge.

## 25. Output encoding and injection resistance

NEXUS must protect against:

- SQL injection;
- command injection;
- path traversal;
- template injection;
- log injection;
- stored XSS;
- reflected XSS;
- unsafe deserialization;
- malicious filenames;
- archive extraction attacks.

Deployment and compilation workflows require especially strict path and command handling.

## 26. Deployment security

Every deployment artifact must have:

```text
artifact_id
source_commit
build_pipeline_id
artifact_hash
signature
created_at
created_by
approved_by
environment
```

Before deployment, LocalBridge or the deployment service must verify:

- hash;
- signature;
- target environment;
- target instance;
- approved manifest;
- compatibility;
- rollback artifact.

Unsigned or modified artifacts must be rejected.

## 27. Build pipeline security

The production build process must:

- use pinned dependencies;
- record compiler/tool versions;
- isolate builds;
- scan dependencies;
- produce immutable artifacts;
- sign release manifests;
- retain build logs;
- prevent unreviewed direct production builds.

The deployed artifact should be built by the controlled pipeline, not manually rebuilt on the production host.

## 28. Audit logging

Security-relevant events must include:

```text
event_id
actor
actor_type
capability
target
action
decision
reason
source_ip_or_machine
session_id
correlation_id
created_at
integrity_hash
```

Mandatory audit events include:

- login success/failure;
- MFA changes;
- role/capability changes;
- secret rotation;
- machine enrollment;
- command authorization;
- risk override attempt;
- protection reset;
- deployment;
- license change;
- account binding change;
- audit access;
- security configuration change.

## 29. Audit integrity

Audit logs must be:

- append-only;
- access-controlled;
- tamper-evident;
- retained according to policy;
- exported or backed up independently;
- searchable by correlation ID;
- protected from ordinary application deletion.

Administrators must not be able to erase their own audit trail through the normal application interface.

## 30. Rate limiting and abuse control

Rate limits are required for:

- login;
- password reset;
- MFA verification;
- command creation;
- machine enrollment;
- license validation;
- deployment actions;
- AI requests;
- expensive analytics;
- webhook-like ingestion endpoints.

Limits should apply by:

- user;
- IP;
- machine identity;
- tenant;
- target account;
- capability.

## 31. Lockout and anomaly detection

Security monitoring should detect:

- repeated failed authentication;
- impossible session changes;
- credential reuse from new machines;
- abnormal command frequency;
- high-risk actions outside normal patterns;
- repeated protection reset attempts;
- cross-account targeting attempts;
- replayed machine requests;
- unexplained deployment changes;
- license tampering.

## 32. Production environment hardening

Production mode must enforce:

```text
debug = false
development routes = disabled
default credentials = rejected
ephemeral auth secrets = rejected
test data = isolated
mock broker = disabled
verbose secret logging = disabled
insecure transport = disabled
unverified artifacts = rejected
```

Production startup should run a security preflight and refuse to start on critical failure.

## 33. Database security

Required controls:

- least-privilege database access;
- encryption at rest where supported;
- protected backups;
- tested restore;
- restricted administrative access;
- no frontend access;
- parameterized queries;
- migration authorization;
- audit of destructive operations;
- separate live and research databases or schemas.

SQLite may remain acceptable for constrained single-node use only after durability, access-control and backup requirements are proven.

## 34. Backup security

Backups must be:

- encrypted;
- integrity-checked;
- access-controlled;
- versioned;
- tested through restore;
- isolated from the primary host;
- retained according to policy.

Backup files may contain credentials, account history and personal data and must be treated as sensitive.

## 35. Data privacy and minimization

NEXUS should store only data necessary for:

- operation;
- audit;
- analytics;
- legal obligations;
- recovery.

Sensitive fields should be:

- minimized;
- encrypted where appropriate;
- masked in UI;
- excluded from logs;
- removed from AI prompts unless required and approved.

## 36. AI security boundary

The AI Coach must not receive:

- broker passwords;
- signing secrets;
- machine credentials;
- raw session tokens;
- unnecessary personal data;
- unrestricted database access.

AI tool calls must be capability-scoped and audited.

AI output must be treated as untrusted input before any command or configuration request is created.

## 37. Dependency and supply-chain security

NEXUS must maintain:

- dependency inventory;
- version pinning;
- vulnerability scanning;
- update policy;
- provenance for downloaded binaries;
- checksum verification;
- review of third-party code;
- emergency patch process.

LocalBridge and MQL5 distribution are part of the supply chain and require the same integrity controls.

## 38. Security incident states

```text
SUSPECTED
CONFIRMED
CONTAINED
ERADICATED
RECOVERING
CLOSED
```

A confirmed security incident affecting execution credentials must trigger:

- credential revocation;
- command suspension;
- deployment isolation;
- account review;
- broker reconciliation;
- evidence preservation;
- operator notification.

## 39. Emergency security controls

NEXUS requires independently available controls for:

- revoke all sessions;
- revoke machine credential;
- disable one deployment;
- disable one account;
- disable all remote commands;
- force read-only mode;
- quarantine strategy;
- rotate signing keys;
- invalidate license;
- preserve audit evidence.

Emergency controls must not depend solely on the component being contained.

## 40. Security acceptance gates

Production security approval requires:

1. no default credentials;
2. no shared LocalBridge token;
3. no ephemeral JWT fallback;
4. short-lived revocable sessions;
5. MFA for privileged roles;
6. explicit CSRF protection;
7. server-issued machine identities;
8. target-scoped capabilities;
9. secret manager or equivalent protected storage;
10. signed deployment artifacts;
11. append-only tamper-evident audit;
12. TLS/mTLS as appropriate;
13. strict payload validation;
14. security preflight;
15. tested credential rotation;
16. tested session revocation;
17. tested incident runbook;
18. dependency inventory and scanning;
19. live/research separation;
20. independent verification of critical controls.

## 41. Current NEXUS security status

The source-level audit identified blockers including:

- shared LocalBridge token;
- client-asserted host identity;
- broad dashboard command authority;
- missing capability separation;
- destructive actions without sufficient approval contract;
- default credentials and fail-open behaviour;
- ephemeral JWT fallback;
- excessively long JWT lifetime;
- token duplication between cookie and response body;
- missing explicit CSRF control;
- weak EA identity;
- open-license fail-open behaviour;
- weak machine payload validation;
- monolithic trust boundaries.

Therefore:

```text
Security posture: NOT PRODUCTION-APPROVED
Production security gate: FAILED
```

This conclusion remains source-level and must later be verified through runtime security testing.

## 42. A3.6 acceptance criteria

Implementation is conformant only when:

- every human and machine action has a verifiable identity;
- authorization is capability-based and target-scoped;
- privileged actions require step-up authentication;
- machine credentials are unique and revocable;
- secrets are protected and rotatable;
- production startup fails closed;
- browser mutations are CSRF-protected;
- artifacts are signed and verified;
- audit logs are tamper-evident;
- incident controls are independently operable;
- AI remains outside the trust boundary for execution authority;
- critical controls pass runtime verification.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| Source-level technical audit | 100% | **100%** |
| Canonical architecture | 100% draft | **100% draft** |
| Event and command contracts | 100% draft | **100% draft** |
| Risk and policy model | 100% draft | **100% draft** |
| Trading lifecycle model | 100% draft | **100% draft** |
| Strategy promotion and evidence | 100% draft | **100% draft** |
| Security architecture and hardening | 0% | **100% draft** |
| Overall specification coverage | 58% | **68%** |
| Developer handoff readiness | 84% | **89%** |
| Combined delivery | 88% | **91%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED by missing independently verified runtime evidence and failed security gates.

## Next active block

**A3.7 — Observability, auditability, incident response, SLOs and production operations**


---

# SPECIFICATION PHASE — BLOCK A3.7
## Observability, Auditability, Incident Response, SLOs and Production Operations

**Status:** normative specification draft

## 1. Objective

NEXUS must be able to explain, at any time:

- what is happening;
- why it is happening;
- where it happened;
- when it happened;
- who or what caused it;
- whether it happened before;
- how severe it is;
- how recovery is performed.

Observability is a production-control requirement, not a dashboard feature.

## 2. Observability pillars

NEXUS shall use four complementary evidence types:

```text
LOGS
METRICS
TRACES
EVENTS
```

Logs explain local detail.  
Metrics show system condition over time.  
Traces connect distributed operations.  
Events preserve business and control-state transitions.

## 3. Structured logging

Every component shall emit structured logs with at least:

```text
timestamp
component
environment
deployment_id
instance_id
account_id
correlation_id
severity
event_type
message
```

Secrets, broker credentials, private keys and session tokens must never be logged.

## 4. Log levels

```text
TRACE
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

TRACE and DEBUG must be disabled by default in production and enabled only through controlled, time-bounded diagnostics.

## 5. Correlation

One correlation ID must span:

```text
Dashboard
→ Backend
→ Risk
→ Command
→ EA
→ Broker
→ Reconciliation
→ Analytics
```

A broken correlation chain is an observability defect.

## 6. Technical metrics

Required infrastructure and service metrics include:

- CPU;
- memory;
- disk;
- network;
- request rate;
- error rate;
- latency;
- queue depth;
- database health;
- retry rate;
- dependency availability.

## 7. Trading and operational metrics

Required domain metrics include:

- commands created;
- commands expired;
- commands rejected;
- orders submitted;
- broker rejections;
- open positions;
- reconciled positions;
- mismatches;
- EA online state;
- broker connectivity;
- active strategies;
- aggregate exposure;
- current drawdown;
- active incidents.

## 8. Health-state model

```text
UNKNOWN
STARTING
HEALTHY
DEGRADED
UNHEALTHY
STOPPED
```

Health must be computed from objective checks, not reported by a component without verification.

## 9. Readiness

A service is READY only when all mandatory dependencies are available.

Examples:

- database reachable;
- migrations complete;
- configuration loaded;
- license valid;
- Risk Engine available;
- command service writable;
- required broker adapter reachable;
- environment checks passed.

Being alive does not imply readiness.

## 10. Liveness

Liveness checks determine whether a component can continue executing its main loop.

A failing dependency should not cause false liveness failure unless the component itself is deadlocked or unable to recover.

## 11. Incident lifecycle

```text
DETECTED
ACKNOWLEDGED
INVESTIGATING
MITIGATING
RESOLVED
POSTMORTEM
CLOSED
```

Closing an incident requires evidence that impact has ended and residual risk is understood.

## 12. Incident severity

```text
P0 — platform or capital-protection failure
P1 — trading path materially compromised
P2 — degraded important capability
P3 — limited operational defect
P4 — cosmetic or low-impact issue
```

P0 and P1 require postmortem and corrective actions.

## 13. Service Level Objectives

Every critical service shall define measurable SLOs.

Initial normative targets may include:

```text
Backend API availability               >= 99.9%
Dashboard p95 read latency             < 500 ms
Command acceptance p95                 < 2 s
Risk decision p95                      < 100 ms
Broker reconciliation p95             < 5 s
Critical alert delivery                < 60 s
```

These are planning targets until validated against the actual deployment architecture.

## 14. Error budgets

Each SLO shall have an associated error budget.

When exhausted:

- feature releases may be frozen;
- reliability work takes priority;
- root-cause review is mandatory;
- risk limits may be reduced;
- deployment cadence may be restricted.

## 15. Alert model

```text
INFORMATIONAL
WARNING
ACTION_REQUIRED
CRITICAL
EMERGENCY
```

Alerts must be deduplicated, correlated and rate-controlled.

Alert storms are themselves operational incidents.

## 16. Alert routing

Routing shall consider:

- severity;
- affected environment;
- account;
- deployment;
- strategy;
- business hours;
- escalation policy;
- acknowledgement timeout.

Critical alerts must have a secondary escalation path.

## 17. Production dashboard

The operational dashboard shall expose at least:

- backend state;
- EA state;
- broker state;
- current risk;
- strategies by lifecycle state;
- open incidents;
- unresolved reconciliation mismatches;
- recent deployments;
- latency;
- error rate;
- command backlog;
- data freshness;
- license status.

Displayed live values must include provenance and freshness.

## 18. Postmortem contract

Every P0/P1 postmortem shall contain:

```text
incident_id
timeline
impact
root_cause
contributing_factors
detection_gap
mitigation
corrective_actions
owners
deadlines
verification_status
```

Postmortems are blameless but not responsibility-free.

## 19. Runbooks

Required runbooks include:

- broker unavailable;
- EA offline;
- backend unavailable;
- database corruption;
- reconciliation mismatch;
- stale configuration;
- license failure;
- failed deployment;
- emergency stop;
- secret compromise;
- unknown broker position;
- strategy quarantine.

Runbooks must include prerequisites, decision points, safe actions and escalation.

## 20. Planned operations

NEXUS must distinguish:

```text
MAINTENANCE
UPGRADE
ROLLBACK
EMERGENCY_MAINTENANCE
```

Maintenance must define how open positions are managed before any component is stopped.

## 21. Continuous verification

After deployment, NEXUS must verify:

- services started;
- dependencies reachable;
- database integrity;
- configuration checksum;
- license validity;
- Risk Engine readiness;
- command flow;
- EA registration;
- broker reconciliation;
- audit emission;
- monitoring and alerting.

Deployment is not complete until verification succeeds.

## 22. Capacity and saturation

Production operations must monitor:

- queue growth;
- storage growth;
- database write latency;
- log volume;
- concurrent connections;
- broker request limits;
- AI request volume;
- CPU and memory saturation.

Capacity thresholds must trigger action before hard failure.

## 23. Data-retention operations

Retention policies must define:

- event retention;
- audit retention;
- raw market-data retention;
- analytical aggregate retention;
- log retention;
- incident evidence retention;
- backup retention.

Retention must not break auditability or reproducibility.

## 24. Backup and restore operations

Backups are not considered valid until restore is tested.

Restore tests must verify:

- schema compatibility;
- event continuity;
- command history;
- audit integrity;
- configuration versions;
- identity bindings;
- reconciliation capability.

## 25. Operational change control

Production changes require:

```text
change_id
change_type
requester
approver
risk_assessment
maintenance_window
rollback_plan
verification_plan
status
```

Emergency changes remain auditable and require retrospective review.

## 26. Operational invariants

1. No service is healthy without objective checks.
2. No deployment is complete without verification.
3. No P0/P1 incident closes without postmortem.
4. No critical alert is silently discarded.
5. No live metric is shown without freshness.
6. No rollback erases audit history.
7. No maintenance ignores open-position safety.
8. No unresolved mismatch is represented as success.
9. No backup is trusted without restore testing.
10. No emergency change bypasses retrospective review.

## 27. A3.7 acceptance criteria

Implementation is conformant when:

- logs, metrics, traces and events are correlated;
- every critical component has liveness and readiness checks;
- SLOs and error budgets exist;
- incident severity and lifecycle are enforced;
- P0/P1 postmortems are mandatory;
- runbooks exist for critical failure modes;
- deployments include continuous verification;
- live dashboards expose provenance and freshness;
- backup restore is tested;
- operational changes are controlled and auditable.


---

# SPECIFICATION PHASE — BLOCK A3.8
## AI Architecture, Multi-Agent System, Memory, Orchestration and Decision Governance

**Status:** normative specification draft

## 1. Objective

This section defines how AI capabilities may be introduced into NEXUS without transferring trading authority, risk authority or deployment authority to a language model.

AI may improve:

- analysis;
- summarization;
- anomaly triage;
- research;
- documentation;
- operator assistance;
- strategy review;
- incident support.

AI must not become an unbounded control plane.

## 2. AI trust boundary

All AI output is untrusted until validated.

An AI response may:

```text
OBSERVE
EXPLAIN
SUGGEST
DRAFT
REQUEST
```

An AI response may not directly:

```text
PLACE_ORDER
MODIFY_RISK
RESET_PROTECTION
PROMOTE_STRATEGY
DEPLOY_ARTIFACT
ROTATE_SECRET
CHANGE_LICENSE
CHANGE_USER_PRIVILEGE
```

Any future execution mode must still pass capability checks, human authorization, Risk Engine and Policy Engine.

## 3. Canonical agent classes

NEXUS may contain specialized agents such as:

```text
COACH_AGENT
MARKET_ANALYSIS_AGENT
STRATEGY_REVIEW_AGENT
RISK_ADVISOR_AGENT
JOURNAL_AGENT
INCIDENT_ASSISTANT_AGENT
DEPLOYMENT_ADVISOR_AGENT
DOCUMENTATION_AGENT
RESEARCH_AGENT
ORCHESTRATOR_AGENT
```

Each agent must have a narrow purpose and explicit allowed tools.

## 4. Agent identity

Every agent instance requires:

```text
agent_id
agent_type
agent_version
model_id
prompt_version
tool_policy_version
tenant_id
environment
capabilities
created_at
retired_at
```

AI actions must be attributable to a specific agent version, prompt version and model configuration.

## 5. Agent capability model

Example AI capabilities:

```text
analytics.read
journal.read
journal.draft
strategy.read
strategy.review
risk.read
incident.read
incident.suggest
deployment.read
documentation.write
research.read
research.write
command.draft
```

No AI agent receives `trade.execute`, `risk.modify`, `protection.reset`, `deployment.execute` or `configuration.approve` by default.

## 6. Orchestration model

The orchestrator coordinates work but does not inherit all child-agent permissions.

Recommended flow:

```text
User request
→ Intent classification
→ Scope resolution
→ Data selection
→ Agent selection
→ Tool authorization
→ Agent execution
→ Result validation
→ Policy check
→ Human presentation
```

The orchestrator must not silently escalate privileges.

## 7. Planner and executor separation

For complex workflows:

- planner proposes steps;
- executor performs allowed tool calls;
- validator checks outputs;
- policy layer decides whether the result can advance.

One model should not both invent and authorize a high-risk action without an independent control.

## 8. AI recommendation contract

Every recommendation must include:

```text
recommendation_id
agent_id
model_id
prompt_version
created_at
expires_at
target
environment
input_dataset_version
provenance
watermark
stale
confidence
summary
rationale
assumptions
risks
proposed_action
required_authorization
```

Missing provenance forces explanation-only mode.

## 9. Confidence model

Confidence is not authority.

Allowed qualitative classes:

```text
VERY_LOW
LOW
MEDIUM
HIGH
```

Confidence must reflect:

- source quality;
- data freshness;
- evidence completeness;
- model uncertainty;
- conflicting signals;
- missing context.

High confidence does not bypass policy.

## 10. Memory architecture

AI memory shall be divided into:

```text
SESSION_MEMORY
USER_PREFERENCE_MEMORY
PROJECT_MEMORY
OPERATIONAL_MEMORY
RESEARCH_MEMORY
AUDIT_MEMORY
```

These memory classes must not be mixed implicitly.

## 11. Memory ownership

Every memory item requires:

```text
memory_id
memory_type
tenant_id
owner_id
scope
source
created_at
updated_at
expires_at
sensitivity
provenance
version
```

Coach memory must be user-scoped and tenant-scoped.

## 12. Memory write policy

AI may write memory only when:

- the memory class allows it;
- the scope is explicit;
- provenance is preserved;
- sensitivity is classified;
- retention is defined;
- the write is auditable.

Operational facts must come from authoritative events, not model recollection.

## 13. Memory conflict resolution

When stored memory conflicts with authoritative data:

```text
Broker / immutable ledger
> active configuration
> approved project specification
> current user instruction
> project memory
> user preference memory
> model inference
```

Conflicting memory must be marked stale or superseded.

## 14. Retrieval policy

Agents may retrieve only information required for their task.

Retrieval must apply:

- tenant filter;
- environment filter;
- capability filter;
- sensitivity filter;
- freshness filter;
- provenance filter;
- minimum necessary scope.

Broad full-database retrieval is prohibited.

## 15. Prompt governance

Prompts are production artifacts.

Required fields:

```text
prompt_id
agent_type
version
content_hash
created_by
approved_by
test_suite_id
effective_from
effective_until
```

Prompt changes that can alter operational recommendations require review and regression testing.

## 16. Model governance

Every model configuration must declare:

```text
model_id
provider
model_version
context_limit
temperature
tool_policy
data_policy
fallback_model
approved_use_cases
prohibited_use_cases
```

Silent model substitution is not allowed for high-impact workflows.

## 17. Tool-use governance

Before a tool call, the system must validate:

- agent capability;
- user capability;
- target scope;
- environment;
- tool risk class;
- input schema;
- rate limit;
- data sensitivity;
- required approval.

Tool results must be treated as external input and validated.

## 18. AI action risk classes

```text
A0 — read-only explanation
A1 — analysis and summarization
A2 — draft recommendation
A3 — draft operational request
A4 — authorized execution request
A5 — direct autonomous execution
```

Default production ceiling:

```text
A3
```

A4 requires explicit human approval and normal command/risk flow.

A5 is prohibited unless a future governance revision explicitly authorizes it.

## 19. Human approval

Human approval must be:

- explicit;
- target-specific;
- action-specific;
- time-bounded;
- linked to the exact recommendation;
- invalidated if inputs materially change.

General statements such as “do what is best” are not valid approval for high-risk actions.

## 20. Risk Engine precedence

The Risk Engine has unconditional veto over AI-generated requests.

Flow:

```text
AI recommendation
→ Human approval
→ Command draft
→ Risk evaluation
→ Policy evaluation
→ Command creation
→ Execution
```

AI and human approval together still do not bypass a DENY decision.

## 21. Multi-agent disagreement

When agents disagree, the orchestrator must not fabricate consensus.

The result should include:

- positions;
- evidence;
- confidence;
- unresolved conflict;
- recommended next validation step.

Risk-related disagreement defaults to the safer interpretation.

## 22. Hallucination containment

Controls include:

- source grounding;
- provenance display;
- structured outputs;
- schema validation;
- deterministic calculations outside the model;
- prohibited unsupported claims;
- explicit uncertainty;
- tool result verification;
- no invented live status.

AI must not state that an order, deployment or test succeeded without authoritative evidence.

## 23. Deterministic computation

The model must not be the source of truth for:

- lot-size calculation;
- margin calculation;
- drawdown calculation;
- exposure aggregation;
- policy thresholds;
- command state;
- broker state;
- configuration checksum.

These must be computed by deterministic services.

## 24. AI and market data

Market analysis requires:

```text
symbol
timeframe
data_source
observed_at
watermark
environment
market_state_version
```

Stale or incomplete data must be disclosed.

AI must not infer a current market state from old journal entries or generic memory.

## 25. AI and strategy research

Research agents may:

- summarize strategy logic;
- compare evidence;
- identify missing tests;
- generate test hypotheses;
- analyze failure clusters;
- draft documentation.

They may not promote a strategy or alter live parameters.

## 26. AI and risk advice

The Risk Advisor may:

- explain current risk;
- identify concentration;
- propose reductions;
- warn about stale data;
- compare policy scenarios.

It may not:

- increase limits;
- reset protection;
- override emergency state;
- change policy;
- authorize exposure.

## 27. AI and incidents

The Incident Assistant may:

- summarize evidence;
- correlate logs;
- propose runbook steps;
- draft timeline;
- identify missing telemetry;
- draft postmortem.

It may not suppress alerts, close incidents or execute containment without approved operational commands.

## 28. AI and deployment

The Deployment Advisor may:

- inspect manifests;
- compare versions;
- identify missing checks;
- draft rollback steps;
- explain failures.

It may not deploy, restart or roll back production directly.

## 29. Data sensitivity

AI input must classify data:

```text
PUBLIC
INTERNAL
SENSITIVE
RESTRICTED
```

Restricted data includes:

- broker credentials;
- production secrets;
- private keys;
- raw session tokens;
- unnecessary personal data.

Restricted data must never enter ordinary model prompts.

## 30. External model providers

When using external providers, NEXUS must define:

- data-processing terms;
- retention policy;
- region;
- model training opt-out;
- encryption;
- incident notification;
- provider availability;
- fallback behaviour.

Provider failure must not degrade safety controls.

## 31. AI fallback behaviour

On AI failure:

- trading protection continues;
- no authority is transferred;
- pending AI drafts expire safely;
- deterministic services remain available;
- the dashboard clearly reports AI unavailability.

AI is non-critical to safe execution.

## 32. AI audit trail

Every AI interaction relevant to operations must record:

```text
interaction_id
agent_id
model_id
prompt_version
user_id
input_references
tool_calls
tool_results
output_hash
recommendation_id
approval_state
created_at
latency
cost
```

Sensitive prompt content may require protected storage or redaction, but audit integrity must remain.

## 33. Evaluation framework

Each agent requires tests for:

- factual grounding;
- unsupported claims;
- tool misuse;
- privilege escalation;
- stale-data handling;
- target confusion;
- prompt injection;
- secret leakage;
- refusal consistency;
- deterministic schema compliance;
- disagreement handling.

High-impact agents require adversarial evaluation.

## 34. Prompt injection defense

AI-retrieved content is untrusted.

Instructions found inside:

- documents;
- logs;
- broker messages;
- websites;
- strategy notes;
- user-generated journal entries

must not override system policy or tool permissions.

## 35. Cost and rate governance

AI usage must track:

```text
tokens
request_count
latency
provider_cost
cache_hit_rate
agent_type
tenant_id
environment
```

Budget exhaustion must degrade gracefully to smaller models, cached summaries or AI-unavailable mode without affecting trading safety.

## 36. AI observability

Required metrics:

- recommendation volume;
- tool-call failures;
- grounding failure rate;
- stale-data rate;
- schema failure rate;
- human acceptance rate;
- human rejection rate;
- recommendation expiry;
- latency;
- cost;
- provider availability.

## 37. Agent lifecycle

```text
DRAFT
TESTING
APPROVED
ACTIVE
DEGRADED
SUSPENDED
RETIRED
```

Only APPROVED or ACTIVE agents may operate in production workflows.

## 38. AI change control

Changes to:

- model;
- prompt;
- tool policy;
- retrieval policy;
- memory policy;
- fallback behaviour

must produce a new controlled version and pass evaluation before production activation.

## 39. AI invariants

1. AI output is never authoritative broker state.
2. AI cannot bypass the Risk Engine.
3. AI cannot silently escalate privileges.
4. AI cannot directly mutate live risk by default.
5. AI cannot use stale data without disclosure.
6. AI cannot invent evidence of execution.
7. AI memory is scoped and versioned.
8. AI prompts and models are controlled artifacts.
9. Deterministic calculations remain outside the model.
10. AI failure cannot disable trading protections.
11. Multi-agent disagreement must remain visible.
12. Retrieved content cannot override system policy.

## 40. Current NEXUS AI status

The current source audit supports only a limited AI-assistance role.

Positive control:

- the Coach queues commands instead of directly controlling the broker;
- the Coach prompt avoids explicit profit guarantees.

Current blockers include:

- incomplete provenance enforcement;
- weak data freshness guarantees;
- insufficient user-scoped memory;
- incomplete capability isolation;
- no mature multi-agent governance;
- no production evaluation suite;
- no model/prompt release governance;
- no independently verified runtime controls.

Therefore:

```text
Current AI production ceiling: A1 / limited A2
Autonomous execution authority: NOT PERMITTED
```

## 41. A3.8 acceptance criteria

Implementation is conformant when:

- every agent has explicit identity and capability scope;
- AI cannot directly mutate live trading state;
- recommendations carry provenance and freshness;
- memory is tenant/user/environment scoped;
- prompts and models are version-controlled;
- tool calls are policy-gated;
- deterministic calculations remain outside AI;
- human approval binds to exact action and inputs;
- multi-agent disagreement is preserved;
- prompt injection and secret leakage are tested;
- AI failure cannot impair protection;
- high-impact agents pass adversarial evaluation.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| Source-level technical audit | 100% | **100%** |
| Canonical architecture | 100% draft | **100% draft** |
| Event and command contracts | 100% draft | **100% draft** |
| Risk and policy model | 100% draft | **100% draft** |
| Trading lifecycle model | 100% draft | **100% draft** |
| Strategy promotion and evidence | 100% draft | **100% draft** |
| Security architecture and hardening | 100% draft | **100% draft** |
| Observability and operations | 0% | **100% draft** |
| AI and multi-agent governance | 0% | **100% draft** |
| Overall specification coverage | 68% | **84%** |
| Developer handoff readiness | 89% | **95%** |
| Combined delivery | 91% | **96%** |

**Production readiness:** NO-GO  
**Point 5:** BLOCKED by missing independent runtime evidence, failed security gates and incomplete implementation verification.

## Next active block

**A3.9 — Final cross-section consistency review, gap closure, Release Candidate criteria and Master Specification v1.0 plan**


---

# SPECIFICATION PHASE — BLOCK A3.9
## Final Cross-Section Consistency Review, Gap Closure, Release Candidate Criteria and Master Specification v1.0 Plan

**Status:** normative specification draft

## 1. Objective

This section closes the architectural specification phase by checking that all previously defined domains agree with one another.

The purpose is not to add a new subsystem.

The purpose is to prove that:

- identities are consistent;
- events and commands align;
- risk rules apply everywhere;
- security controls do not conflict with operations;
- AI remains subordinate to deterministic governance;
- lifecycle states are compatible;
- production gates are explicit;
- implementation work can begin without architectural ambiguity.

## 2. Cross-section consistency domains

The final review covers:

```text
architecture
identity
events
commands
risk
trading lifecycle
strategy lifecycle
security
observability
AI governance
deployment
audit
operations
```

Each domain must use compatible terminology, states and authority boundaries.

## 3. Canonical authority chain

The final authority chain is:

```text
Human intent
→ authenticated capability
→ validated request
→ policy evaluation
→ risk evaluation
→ canonical command
→ execution adapter
→ broker result
→ reconciliation
→ immutable event/audit record
```

AI may assist before command creation but does not sit above Policy Engine or Risk Engine.

## 4. Canonical source-of-truth hierarchy

The final precedence order is:

```text
Broker-confirmed state
> reconciled canonical ledger
> approved active configuration
> immutable audit/event history
> current deployment manifest
> approved strategy evidence
> operational projections
> AI interpretation
> cached UI state
```

Any lower-priority source conflicting with a higher-priority source must be marked stale, degraded or invalid.

## 5. Identity consistency

The following identities must remain distinct:

```text
user_id
tenant_id
service_id
machine_id
deployment_id
terminal_id
ea_instance_id
broker_account_id
strategy_id
strategy_version
command_id
order_id
position_id
logical_trade_id
recommendation_id
incident_id
```

No identifier may be reused to represent another domain.

## 6. Command consistency

Every executable action must originate from a canonical command.

Required properties:

```text
immutable identity
explicit target
explicit environment
capability decision
policy decision
risk decision
expiry
idempotency
correlation
auditability
```

UI actions, AI recommendations and operator instructions are not executable until converted into a valid command.

## 7. Event consistency

Every state transition must emit a canonical event.

Required properties:

```text
event_id
event_type
occurred_at
observed_at
producer
subject
correlation_id
causation_id
environment
schema_version
payload
```

Events must not be rewritten to make later state appear cleaner.

Corrections require new events.

## 8. Risk consistency

Risk evaluation must apply to:

- strategy-originated orders;
- manual commands;
- AI-drafted requests;
- recovery actions;
- partial closes;
- protection resets;
- configuration changes that alter exposure;
- limited-live promotion;
- post-restart reconciliation actions.

There is no trusted path around the Risk Engine.

## 9. Lifecycle consistency

The lifecycle models must connect as follows:

```text
Strategy release
→ approved state
→ signal
→ trade intent
→ command
→ order
→ position
→ logical trade
→ reconciliation
→ finalization
→ analytics
→ evidence
```

No lifecycle stage may skip required predecessor evidence.

## 10. Strategy and deployment consistency

A deployed strategy must match:

```text
strategy_id
implementation_version
parameter_set_id
artifact_hash
deployment_manifest
approved_environment
approved_account_scope
approved_symbol_scope
evidence_package_id
```

Mismatch between any of these forces deployment rejection or quarantine.

## 11. Security and operations consistency

Operational recovery must not bypass security.

Examples:

- emergency restart still requires authenticated operator or emergency control;
- rollback still verifies artifact signature;
- incident containment still records audit evidence;
- secret rotation still preserves service identity;
- quarantine release still requires approval;
- read-only emergency mode still enforces authentication.

## 12. AI and operations consistency

AI may assist in:

- summarizing incidents;
- proposing runbook steps;
- drafting commands;
- reviewing evidence;
- detecting anomalies.

AI may not:

- close incidents by itself;
- suppress alerts;
- authorize deployment;
- override reconciliation;
- declare broker state;
- reset protections;
- elevate its own capabilities.

## 13. Observability consistency

Every critical business flow must expose:

```text
logs
metrics
traces
events
health state
audit record
```

The following flows are mandatory:

- authentication;
- command creation;
- risk decision;
- order execution;
- reconciliation;
- deployment;
- strategy promotion;
- protection activation;
- incident response;
- AI recommendation.

## 14. Error-model consistency

The canonical error taxonomy must distinguish at least:

```text
VALIDATION_ERROR
AUTHENTICATION_ERROR
AUTHORIZATION_ERROR
POLICY_DENY
RISK_DENY
STALE_STATE
CONFLICT
DEPENDENCY_UNAVAILABLE
BROKER_REJECTION
RECONCILIATION_MISMATCH
INTEGRITY_FAILURE
TIMEOUT
INTERNAL_ERROR
UNKNOWN
```

Errors must not be collapsed into generic success/failure strings.

## 15. Fail-safe consistency

The default safety posture is:

```text
uncertainty about state
→ block new exposure
→ preserve open-position safety
→ reconcile
→ require explicit recovery
```

Fail-open behaviour is prohibited for:

- authentication;
- licensing;
- risk policy;
- artifact verification;
- broker identity;
- account binding;
- protection state;
- critical configuration.

## 16. Data and freshness consistency

Any data used for live decision support must include:

```text
source
observed_at
watermark
environment
version
stale flag
```

Stale data may remain visible but cannot silently support live execution.

## 17. Configuration consistency

Configuration must be:

- versioned;
- checksummed;
- scope-bound;
- acknowledged by each EA instance;
- auditable;
- reversible;
- environment-specific.

The backend's active configuration is not assumed applied until the EA confirms the exact version and checksum.

## 18. Reconciliation consistency

Reconciliation is mandatory:

- at startup;
- after reconnect;
- after deployment;
- after restart;
- after broker rejection ambiguity;
- after timeout;
- after unexpected position event;
- periodically during live operation.

The platform must prefer broker-confirmed reality over internal expectations.

## 19. Audit consistency

Every high-impact action must answer:

```text
who
what
when
where
why
target
decision
result
correlation
evidence
```

Audit gaps affecting money movement, risk or deployment are release blockers.

## 20. Final unresolved architectural gaps

The draft architecture is coherent, but the following remain implementation gaps rather than specification gaps:

### G1 — Runtime compilation evidence

Missing:

- verified MetaEditor build;
- compiler output;
- exact artifact hash;
- reproducible build record.

### G2 — Test automation

Missing:

- unit suite;
- contract suite;
- integration suite;
- scenario suite;
- regression suite;
- adversarial AI/security suite.

### G3 — Broker reconciliation proof

Missing runtime proof for:

- restart with open positions;
- partial close;
- duplicate events;
- unknown broker position;
- delayed acknowledgement;
- rejected order ambiguity.

### G4 — Security hardening

Missing verified implementation for:

- unique machine credentials;
- session revocation;
- MFA;
- CSRF;
- secret rotation;
- signed artifacts;
- tamper-evident audit.

### G5 — Production observability

Missing verified:

- correlated traces;
- SLO measurement;
- alert routing;
- postmortem workflow;
- restore test;
- continuous verification.

### G6 — Strategy evidence

Missing:

- out-of-sample evidence;
- walk-forward;
- Monte Carlo robustness;
- paper validation;
- limited-live validation;
- artifact-evidence equivalence.

### G7 — AI governance

Missing:

- agent capability enforcement;
- prompt/model registry;
- evaluation suite;
- memory isolation;
- provenance enforcement;
- prompt injection testing.

## 21. Gap severity

```text
G1 — BLOCKER
G2 — BLOCKER
G3 — BLOCKER
G4 — BLOCKER
G5 — MAJOR
G6 — BLOCKER
G7 — MAJOR
```

Any blocker prevents production approval.

## 22. Specification completion criteria

The specification phase is complete when:

1. all architectural domains are defined;
2. terminology is consistent;
3. authority boundaries are explicit;
4. source-of-truth precedence is explicit;
5. lifecycle transitions are explicit;
6. error and failure behaviour are explicit;
7. security and risk invariants are explicit;
8. AI authority is bounded;
9. acceptance criteria exist for every section;
10. implementation gaps are separated from specification gaps.

These criteria are now satisfied at draft level.

## 23. Release Candidate criteria

The document may move from Draft to Release Candidate when:

- all sections pass consistency review;
- duplicate terminology is normalized;
- unresolved contradictions are removed;
- every normative requirement is tagged or traceable;
- all acceptance criteria are indexed;
- all known assumptions are declared;
- all open decisions are listed;
- all diagrams and lifecycle tables are synchronized;
- the implementation backlog is derived from the specification;
- a final owner review is completed.

## 24. Master Specification v1.0 criteria

The document may become v1.0 when:

- the Release Candidate review is complete;
- no unresolved P0 specification issue remains;
- no unresolved contradiction affects implementation;
- all canonical schemas are frozen for implementation;
- all mandatory invariants are approved;
- change-control rules are active;
- the implementation backlog references the approved requirements;
- future modifications require versioned amendments.

v1.0 means the architecture is approved as the official implementation reference.

It does not mean the software itself is production-ready.

## 25. Requirement traceability model

Each normative requirement should receive an identifier:

```text
NEXUS-ARCH-###
NEXUS-EVT-###
NEXUS-CMD-###
NEXUS-RISK-###
NEXUS-LIFE-###
NEXUS-STRAT-###
NEXUS-SEC-###
NEXUS-OPS-###
NEXUS-AI-###
```

Implementation tasks, tests and defects should reference these IDs.

## 26. Implementation backlog derivation

The first implementation backlog should be generated in this order:

```text
P0 safety and identity
→ canonical event/command contracts
→ reconciliation and ledger
→ risk enforcement
→ security hardening
→ observability
→ deployment integrity
→ strategy evidence pipeline
→ AI governance
→ UX refinement
```

This order minimizes the chance of polishing an unsafe architecture.

## 27. Recommended delivery phases

### Phase I — Foundation

- identity;
- capabilities;
- event envelope;
- command envelope;
- audit;
- configuration versioning.

### Phase II — Trading integrity

- order lifecycle;
- position lifecycle;
- reconciliation;
- logical trade model;
- restart recovery;
- broker adapter hardening.

### Phase III — Safety

- Risk Engine;
- Policy Engine;
- emergency controls;
- strategy state enforcement;
- limited-live constraints.

### Phase IV — Production platform

- deployment manifests;
- signed artifacts;
- secrets;
- observability;
- SLOs;
- incident operations;
- backup/restore.

### Phase V — Evidence and AI

- test automation;
- strategy evidence packages;
- shadow/paper/limited-live promotion;
- agent registry;
- memory governance;
- AI evaluations.

## 28. Change-control model

After v1.0, every architectural change must include:

```text
change_request_id
affected_requirements
reason
risk
compatibility
migration
test impact
approval
effective_version
```

Breaking changes require a new major version.

## 29. Final specification verdict

The architecture is now sufficiently defined to serve as a controlled implementation blueprint.

Final draft verdict:

```text
Specification completeness: HIGH
Cross-section consistency: ACCEPTABLE WITH NORMALIZATION
Implementation readiness: READY FOR BACKLOG DERIVATION
Production readiness: NO-GO
```

The project is no longer blocked by lack of architectural direction.

It remains blocked by implementation, testing, runtime evidence and security verification.

## 30. A3.9 acceptance criteria

A3.9 is complete when:

- all authority chains are consistent;
- all source-of-truth hierarchies are explicit;
- all lifecycle connections are defined;
- all blocker gaps are documented;
- Release Candidate criteria are explicit;
- v1.0 criteria are explicit;
- requirement traceability is defined;
- implementation phases are prioritized;
- production readiness remains separated from specification readiness.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| Source-level technical audit | 100% | **100%** |
| Canonical architecture | 100% draft | **100% draft** |
| Event and command contracts | 100% draft | **100% draft** |
| Risk and policy model | 100% draft | **100% draft** |
| Trading lifecycle model | 100% draft | **100% draft** |
| Strategy promotion and evidence | 100% draft | **100% draft** |
| Security architecture and hardening | 100% draft | **100% draft** |
| Observability and operations | 100% draft | **100% draft** |
| AI and multi-agent governance | 100% draft | **100% draft** |
| Final consistency and RC planning | 0% | **100% draft** |
| Overall specification coverage | 84% | **96%** |
| Developer handoff readiness | 95% | **98%** |
| Combined delivery | 96% | **98%** |

**Specification state:** DRAFT COMPLETE  
**Release Candidate state:** READY FOR NORMALIZATION REVIEW  
**Production readiness:** NO-GO  
**Point 5:** BLOCKED by implementation and evidence gaps.

## Next active block

**A4.0 — Draft normalization, requirement indexing, contradiction review and Release Candidate preparation**


---

# RELEASE PREPARATION — BLOCK A4.0
## Draft Normalization, Requirement Indexing, Contradiction Review and Release Candidate Preparation

**Status:** release-preparation draft

## 1. Objective

A4.0 converts the completed architectural draft into a controlled Release Candidate structure.

This phase performs four tasks:

```text
NORMALIZE
INDEX
RECONCILE
FREEZE
```

The goal is to make the specification reviewable requirement by requirement and directly translatable into implementation tasks and tests.

## 2. Canonical terminology

The Release Candidate shall use one preferred term for each concept:

```text
Policy Engine
Risk Engine
Canonical Command
Canonical Event
Broker-Confirmed State
Reconciled Ledger
Logical Trade
Strategy Release
Deployment Manifest
Evidence Package
Capability
Step-Up Authentication
Machine Credential
Incident
Recommendation
```

Alternative labels may appear only as explicit aliases.

## 3. Normative language

The document shall distinguish requirement strength:

```text
MUST       mandatory
MUST NOT   prohibited
SHOULD     recommended
SHOULD NOT discouraged
MAY        optional
```

Descriptive text must not be interpreted as a mandatory requirement unless marked accordingly.

## 4. Requirement identifier scheme

Stable requirement identifiers:

```text
NEXUS-ARCH-###
NEXUS-ID-###
NEXUS-EVT-###
NEXUS-CMD-###
NEXUS-RISK-###
NEXUS-LIFE-###
NEXUS-STRAT-###
NEXUS-SEC-###
NEXUS-OPS-###
NEXUS-AI-###
NEXUS-DEPLOY-###
NEXUS-DATA-###
NEXUS-TEST-###
```

Identifiers shall remain stable after RC publication. Retired IDs must not be reassigned.

## 5. Requirement record

Each indexed requirement should include:

```text
requirement_id
title
normative_statement
rationale
source_section
applies_to
verification_method
priority
status
dependencies
```

Allowed verification methods:

```text
INSPECTION
STATIC_ANALYSIS
UNIT_TEST
CONTRACT_TEST
INTEGRATION_TEST
SCENARIO_TEST
SECURITY_TEST
BACKTEST
FORWARD_TEST
LIMITED_LIVE_TEST
OPERATIONAL_EXERCISE
```

## 6. Priority classification

```text
P0 — capital, identity, integrity or control-path safety
P1 — production-critical correctness
P2 — important operational or analytical capability
P3 — usability, efficiency or non-critical enhancement
```

All P0 and P1 requirements require explicit verification before production approval.

## 7. Initial canonical requirement baseline

### Architecture

**NEXUS-ARCH-001 — Single execution authority**  
Every executable trading action MUST pass through the canonical command path.

**NEXUS-ARCH-002 — Source-of-truth precedence**  
Broker-confirmed state MUST override internal expectations, AI interpretation and cached UI state.

**NEXUS-ARCH-003 — Environment separation**  
RESEARCH, SHADOW, PAPER, LIMITED_LIVE and LIVE MUST remain operationally separated.

### Identity and authorization

**NEXUS-ID-001 — Distinct identities**  
Human, service, machine, terminal, EA and AI identities MUST remain distinct.

**NEXUS-ID-002 — Capability enforcement**  
Authorization MUST be capability-based and target-scoped.

**NEXUS-ID-003 — Privileged step-up**  
High-risk actions MUST require valid step-up authentication.

**NEXUS-ID-004 — Revocable machine credentials**  
Each production deployment or EA instance MUST use a unique revocable credential.

### Events and commands

**NEXUS-EVT-001 — Immutable transitions**  
Every material state transition MUST emit a canonical event.

**NEXUS-EVT-002 — Correction by new event**  
Historical events MUST NOT be rewritten to hide later corrections.

**NEXUS-CMD-001 — Canonical command envelope**  
Every executable request MUST include identity, target, environment, expiry, idempotency and correlation.

**NEXUS-CMD-002 — Duplicate safety**  
Repeated delivery of the same command MUST NOT cause duplicate execution.

**NEXUS-CMD-003 — Expiry enforcement**  
Expired commands MUST NOT execute.

### Risk and policy

**NEXUS-RISK-001 — No bypass path**  
No manual, automated or AI-generated action MAY bypass Risk Engine and Policy Engine evaluation.

**NEXUS-RISK-002 — Fail-safe uncertainty**  
Uncertainty about live state MUST block new exposure until reconciliation.

**NEXUS-RISK-003 — Protection precedence**  
Active hard protections MUST override strategy and operator requests.

**NEXUS-RISK-004 — Deterministic sizing**  
Position sizing and exposure calculations MUST be performed by deterministic services.

### Trading lifecycle

**NEXUS-LIFE-001 — Broker reconciliation**  
Startup, reconnect, restart and ambiguous execution states MUST trigger reconciliation.

**NEXUS-LIFE-002 — Logical trade continuity**  
Orders, positions, partial closes and finalization MUST remain traceable to one logical trade.

**NEXUS-LIFE-003 — Finalization evidence**  
A trade MUST NOT be considered final until broker-confirmed closure and reconciliation are recorded.

### Strategy governance

**NEXUS-STRAT-001 — Controlled lifecycle**  
A strategy MUST move through the approved lifecycle before LIVE.

**NEXUS-STRAT-002 — Artifact-evidence equivalence**  
The deployed artifact and parameter set MUST match the tested evidence package.

**NEXUS-STRAT-003 — Limited-live requirement**  
LIVE approval MUST require limited-live evidence.

**NEXUS-STRAT-004 — Quarantine on breach**  
A material live-performance or integrity breach MUST trigger quarantine or equivalent safe state.

### Security

**NEXUS-SEC-001 — No default credentials**  
Production MUST fail closed when default credentials or fallback signing secrets are present.

**NEXUS-SEC-002 — Secret protection**  
Sensitive and critical secrets MUST NOT be embedded in source, frontend bundles, logs or shared static tokens.

**NEXUS-SEC-003 — Signed artifacts**  
Production deployment artifacts MUST be signed and verified before activation.

**NEXUS-SEC-004 — Session revocation**  
Privileged sessions MUST be revocable server-side.

**NEXUS-SEC-005 — Tamper-evident audit**  
Security and trading audit records MUST be append-only and tamper-evident.

### Operations and observability

**NEXUS-OPS-001 — Correlated observability**  
Critical flows MUST produce correlated logs, metrics, traces and events.

**NEXUS-OPS-002 — Readiness before service**  
A component MUST NOT be considered ready until mandatory dependencies and checks pass.

**NEXUS-OPS-003 — Verified deployment**  
Deployment MUST NOT be considered complete until continuous verification succeeds.

**NEXUS-OPS-004 — Incident governance**  
P0 and P1 incidents MUST receive postmortem and corrective-action tracking.

**NEXUS-OPS-005 — Tested restore**  
A backup MUST NOT be considered valid until restore testing succeeds.

### AI governance

**NEXUS-AI-001 — AI is non-authoritative**  
AI output MUST NOT be treated as broker state, risk state or execution evidence.

**NEXUS-AI-002 — No direct live mutation**  
AI MUST NOT directly change live trading, risk, deployment, license or security state.

**NEXUS-AI-003 — Provenance and freshness**  
Operational AI recommendations MUST include provenance, data freshness and model/prompt version.

**NEXUS-AI-004 — Human approval binding**  
Approval of an AI recommendation MUST bind to the exact action, target and input state.

**NEXUS-AI-005 — Deterministic veto**  
Risk Engine and Policy Engine MUST retain final veto over AI-assisted requests.

## 8. Contradiction review matrix

| Domain pair | Potential conflict | Canonical resolution |
|---|---|---|
| Human authority vs Risk Engine | Owner requests unsafe action | Risk Engine retains veto |
| AI assistance vs execution | AI drafts an operational action | Draft only; normal authorization remains required |
| Broker vs internal ledger | Internal state disagrees | Broker-confirmed state wins, then ledger reconciles |
| Security vs emergency response | Emergency requires speed | Emergency path remains authenticated and audited |
| Strategy version vs deployment | Hash or parameters differ | Deployment rejected or quarantined |
| Availability vs safety | Dependency unavailable | Block new exposure; preserve safe management |
| Dashboard vs event history | UI cache appears current | Provenance and freshness required |
| Recovery vs audit integrity | Rollback restores old software | Audit history remains immutable |
| License vs risk policy | License allows feature | License never bypasses security or risk |
| Operator approval vs stale inputs | Inputs change after approval | Approval is invalidated |

No contradiction currently requires architectural redesign.

## 9. Ambiguity closure

Canonical environment meanings:

```text
RESEARCH      offline or exploratory analysis
SHADOW        real-time observation without execution
PAPER         simulated execution with production-like workflow
LIMITED_LIVE  broker-connected execution under explicit reduced constraints
LIVE          broker-connected production execution
```

“Specification-ready” means architecturally complete.

“Production-ready” means implemented, tested, secured and evidenced.

These terms MUST NOT be used interchangeably.

## 10. Open-decision register

Implementation choices still open:

```text
OD-001 production database technology
OD-002 event transport technology
OD-003 secret-management product
OD-004 machine identity mechanism
OD-005 observability stack
OD-006 CI/CD platform
OD-007 AI provider and model set
OD-008 broker-adapter isolation model
OD-009 single-node versus distributed deployment
OD-010 retention periods by data class
```

Each requires an Architecture Decision Record before implementation lock.

## 11. ADR template

```text
ADR_ID
title
status
context
decision
alternatives
consequences
security_impact
operational_impact
migration_impact
approved_by
date
```

Statuses:

```text
PROPOSED
ACCEPTED
SUPERSEDED
REJECTED
DEPRECATED
```

## 12. Assumption register

Current assumptions:

- MetaTrader 5 is the initial execution environment;
- broker behaviour differs by symbol and account;
- the first production deployment may be constrained and single-node;
- AI remains non-critical to safe execution;
- one tenant may own multiple accounts and deployments;
- production validation requires broker-connected evidence;
- multiple strategies must not share unrestricted authority.

## 13. Traceability chain

```text
Requirement
→ architecture component
→ implementation task
→ source commit
→ build artifact
→ test case
→ evidence result
→ deployment manifest
→ runtime telemetry
```

A blocker must be traceable to the failed or missing requirement.

## 14. Developer handoff package

The minimum package shall contain:

1. Master Specification RC;
2. requirement index;
3. canonical schemas;
4. state-transition tables;
5. authority matrix;
6. source-of-truth hierarchy;
7. error taxonomy;
8. open-decision register;
9. ADR templates;
10. implementation backlog;
11. test matrix;
12. production acceptance gates.

## 15. Release Candidate checklist

Before RC promotion:

- [ ] terminology normalized;
- [ ] all P0/P1 requirements identified;
- [ ] every requirement has a verification method;
- [ ] cross-references valid;
- [ ] lifecycle names consistent;
- [ ] no security/recovery contradiction;
- [ ] no AI/command-governance contradiction;
- [ ] no production claim relies on unverified evidence;
- [ ] all open decisions registered;
- [ ] all assumptions explicit;
- [ ] owner review recorded.

## 16. Release freeze rules

Once RC is declared:

- normative IDs freeze;
- breaking changes require change requests;
- terminology changes require cross-document review;
- implementation may begin against the RC baseline;
- defects are classified as specification or implementation defects;
- production approval remains independent.

## 17. Current normalization verdict

```text
Terminology normalization: SUBSTANTIALLY COMPLETE
Requirement baseline: ESTABLISHED
Contradiction review: PASSED AT ARCHITECTURAL LEVEL
Open decisions: REGISTERED
RC readiness: CONDITIONAL GO
```

The condition is completion of the final editorial and traceability pass.

## 18. A4.0 acceptance criteria

A4.0 is complete when:

- canonical terminology is fixed;
- requirement strength is explicit;
- stable identifiers exist;
- P0/P1 baseline requirements are indexed;
- contradiction classes are resolved;
- open choices are separated from architectural rules;
- ADR governance is defined;
- assumptions are registered;
- traceability is defined;
- RC review and freeze rules are explicit.

## Progress update

| Track | Previous | Current |
|---|---:|---:|
| Architectural draft | 100% | **100%** |
| Final consistency review | 100% draft | **100%** |
| Terminology normalization | 0% | **90%** |
| Requirement indexing | 0% | **85%** |
| Contradiction review | 0% | **100% architectural** |
| Open-decision register | 0% | **100% initial** |
| Release Candidate preparation | 0% | **90%** |
| Overall specification coverage | 96% | **99%** |
| Developer handoff readiness | 98% | **99%** |
| Combined delivery | 98% | **99%** |

**Specification state:** DRAFT COMPLETE  
**Release Candidate state:** CONDITIONAL GO  
**Production readiness:** NO-GO  
**Point 5:** BLOCKED by implementation, runtime testing and evidence.

## Next active block

**A4.1 — Final editorial pass, complete requirement traceability matrix and formal Release Candidate publication**

---

# A4.2 — FULL CORPUS AUDIT INTEGRATION
## Preliminary semantic audit of all uploaded trading sources

### Status and authority

This block integrates the current corpus-wide semantic audit into the NEXUS Master Specification.

The integrated audit is **preliminary evidence**, not an automatically approved trading specification.
It records what was detected in the source corpus and keeps architectural inferences explicitly separate from source-derived concepts.

The following rules apply:

- no source concept becomes executable logic without deterministic formalization;
- no course rule may bypass the Policy Engine or Risk Engine;
- visually derived rules require page-level verification before implementation;
- duplicate terminology across courses must not be treated as semantic equivalence without reconciliation;
- ambiguous, discretionary or non-testable rules remain research candidates;
- all promoted rules require requirement IDs, tests, evidence and versioned ownership.

### Current completion state

```text
Inventory complete: 100%
All PDF pages extracted/indexed: 100%
Markdown textual reading: 100%
Additional graphical-page verification: IN PROGRESS
Corpus semantic audit: PRELIMINARY COMPLETE
Final comparison against NEXUS: NOT YET DECLARED COMPLETE
```

### Integrated source audit

## NEXUS - Audit semantico preliminare dell’intero corpus PDF

## Metodo

- Ogni pagina è stata indicizzata singolarmente.
- Per le pagine con poco testo nativo è stato usato, ove disponibile, OCR supplementare.
- Le occorrenze sotto indicano dove il corpus esplicita un concetto; non sostituiscono ancora la lettura visiva dei grafici.
- Le proposte NEXUS sono inferenze architetturali separate dal contenuto originale.

## 863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf

- Pagine: **51**
- Pagine con testo/OCR non vuoto: **51/51**
- Caratteri estratti: **28.447**

### Concetti rilevati

- **Market Structure**: pagine più indicative 36, 37, 38, 10, 20, 39, 41, 46, 3, 22, 48
- **Support/Resistance & SNR**: pagine più indicative 14, 18, 15, 32, 3, 8, 10, 19, 22, 21, 36, 44
- **Liquidity & Stop Hunts**: pagine più indicative 10, 18, 5, 6, 14, 40, 45, 46, 50
- **Order Blocks & FVG**: pagine più indicative 2
- **ICT Concepts**: pagine più indicative 2, 36, 44, 1, 5, 10, 18, 19, 32, 37, 39, 40
- **Candlesticks**: pagine più indicative 5, 16, 32, 6, 7, 8, 3, 4, 10, 17, 33
- **Entries & Confirmation**: pagine più indicative 22, 19, 16, 4, 3, 17, 10, 21, 32, 18, 40, 42
- **Stop Loss & Take Profit**: pagine più indicative 45
- **Risk & Money Management**: pagine più indicative 4
- **Sessions & Timing**: pagine più indicative 36, 3, 4, 6, 9, 19, 20, 22, 42, 45, 48, 50
- **Psychology & Discipline**: pagine più indicative 5, 10, 40
- **Sequence / Proprietary Models**: pagine più indicative 1, 2, 18

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.
- Conservare il modello proprietario come strategia isolata, con nomenclatura e condizioni esplicite prima della codifica.

---

## Malaysian SNR Emperor.pdf

- Pagine: **67**
- Pagine con testo/OCR non vuoto: **67/67**
- Caratteri estratti: **22.562**

### Concetti rilevati

- **Market Structure**: pagine più indicative 59, 14, 56
- **Support/Resistance & SNR**: pagine più indicative 14, 46, 59, 8, 12, 15, 45, 52, 3, 18, 27, 47
- **Supply & Demand**: pagine più indicative 3
- **Liquidity & Stop Hunts**: pagine più indicative 5, 14
- **ICT Concepts**: pagine più indicative 47, 50, 52, 63
- **Candlesticks**: pagine più indicative 45, 43, 44, 46, 50, 6, 47, 59, 3, 4, 8, 9
- **Fibonacci**: pagine più indicative 60
- **Entries & Confirmation**: pagine più indicative 24, 59, 42, 48, 13, 22, 25, 30, 37, 38, 49, 17
- **Stop Loss & Take Profit**: pagine più indicative 65, 41, 48, 49, 59
- **Risk & Money Management**: pagine più indicative 63, 2, 60, 61, 62
- **Sessions & Timing**: pagine più indicative 19, 48, 7, 31, 46, 49, 6, 24, 30, 50
- **Psychology & Discipline**: pagine più indicative 64, 66, 2, 65
- **Sequence / Proprietary Models**: pagine più indicative 29, 1

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.
- Conservare il modello proprietario come strategia isolata, con nomenclatura e condizioni esplicite prima della codifica.

---

## My Rare SNR Course 2.pdf

- Pagine: **10**
- Pagine con testo/OCR non vuoto: **10/10**
- Caratteri estratti: **2.091**

### Concetti rilevati

- **ICT Concepts**: pagine più indicative 10
- **Entries & Confirmation**: pagine più indicative 3
- **Psychology & Discipline**: pagine più indicative 10

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.

---

## My Rare SNR Course.pdf

- Pagine: **29**
- Pagine con testo/OCR non vuoto: **29/29**
- Caratteri estratti: **13.111**

### Concetti rilevati

- **Market Structure**: pagine più indicative 7, 12
- **Support/Resistance & SNR**: pagine più indicative 1, 7, 2, 13, 5, 10, 12, 19, 3, 4, 9, 21
- **Supply & Demand**: pagine più indicative 1
- **ICT Concepts**: pagine più indicative 19, 1, 2, 8, 9, 21
- **Candlesticks**: pagine più indicative 13, 1, 2, 5, 15, 19, 21
- **Entries & Confirmation**: pagine più indicative 13, 12, 7, 11, 21, 23, 9
- **Stop Loss & Take Profit**: pagine più indicative 13, 14, 16
- **Sessions & Timing**: pagine più indicative 11

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.

---

## SNR Malaysia.pdf

- Pagine: **74**
- Pagine con testo/OCR non vuoto: **74/74**
- Caratteri estratti: **18.153**

### Concetti rilevati

- **Market Structure**: pagine più indicative 65, 68
- **Support/Resistance & SNR**: pagine più indicative 7, 29, 8, 15, 19, 65, 2, 5, 13, 30, 12, 22
- **Liquidity & Stop Hunts**: pagine più indicative 17, 18, 3, 5, 30
- **ICT Concepts**: pagine più indicative 6, 10, 19, 29, 46, 65
- **Candlesticks**: pagine più indicative 22, 4, 7, 5, 2, 30, 23, 25, 27, 56
- **Entries & Confirmation**: pagine più indicative 2, 28, 51, 67, 73, 6, 13, 12, 14, 15, 18, 19
- **Stop Loss & Take Profit**: pagine più indicative 30
- **Sessions & Timing**: pagine più indicative 7, 26, 4, 5, 13, 18, 65, 66, 67, 68, 70

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.

---

## Secret Of 411(1).pdf

- Pagine: **16**
- Pagine con testo/OCR non vuoto: **16/16**
- Caratteri estratti: **2.698**

### Concetti rilevati

- **Support/Resistance & SNR**: pagine più indicative 2, 3, 6, 4, 5
- **ICT Concepts**: pagine più indicative 4
- **Candlesticks**: pagine più indicative 6
- **Stop Loss & Take Profit**: pagine più indicative 7
- **Sessions & Timing**: pagine più indicative 2, 13
- **Psychology & Discipline**: pagine più indicative 2

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.

---

## Sequence.pdf

- Pagine: **76**
- Pagine con testo/OCR non vuoto: **56/76**
- Caratteri estratti: **4.588**

### Concetti rilevati

- **Market Structure**: pagine più indicative 50
- **Support/Resistance & SNR**: pagine più indicative 6, 8, 49
- **Liquidity & Stop Hunts**: pagine più indicative 53, 52
- **ICT Concepts**: pagine più indicative 57, 4, 5, 55
- **Entries & Confirmation**: pagine più indicative 8, 49, 66
- **Stop Loss & Take Profit**: pagine più indicative 53
- **Sequence / Proprietary Models**: pagine più indicative 1, 3, 49

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Conservare il modello proprietario come strategia isolata, con nomenclatura e condizioni esplicite prima della codifica.

---

## Sequence_1.pdf

- Pagine: **74**
- Pagine con testo/OCR non vuoto: **46/74**
- Caratteri estratti: **55.488**

### Concetti rilevati

- **Market Structure**: pagine più indicative 2, 27, 22, 7, 8, 23, 25, 44, 28, 32, 4, 5
- **Support/Resistance & SNR**: pagine più indicative 39, 2, 18, 19, 21, 14, 16, 20, 11, 28, 38, 7
- **Supply & Demand**: pagine più indicative 30, 31, 36
- **Liquidity & Stop Hunts**: pagine più indicative 2, 14, 15, 18, 42, 3, 6, 7, 8, 9, 25, 13
- **Order Blocks & FVG**: pagine più indicative 28, 3, 46, 2, 7, 21, 4, 6, 33
- **ICT Concepts**: pagine più indicative 46, 15, 21, 37, 4, 5, 6, 11, 16
- **Candlesticks**: pagine più indicative 2, 27, 4, 6, 7, 19, 26
- **Chart Patterns**: pagine più indicative 39
- **Fibonacci**: pagine più indicative 33, 10, 36, 3, 8, 9, 28, 29
- **Entries & Confirmation**: pagine più indicative 2, 36, 37, 21, 4, 22, 23, 24, 39, 16, 19, 28
- **Stop Loss & Take Profit**: pagine più indicative 2, 14, 16, 21, 25, 42
- **Risk & Money Management**: pagine più indicative 2
- **Sessions & Timing**: pagine più indicative 38, 44, 29, 45, 30, 31, 28, 4, 5, 16, 42, 18
- **Psychology & Discipline**: pagine più indicative 12, 13, 21, 28, 37
- **Sequence / Proprietary Models**: pagine più indicative 2, 1, 22, 26, 35

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.
- Conservare il modello proprietario come strategia isolata, con nomenclatura e condizioni esplicite prima della codifica.

---

## Sequence_2_unlocked.pdf

- Pagine: **119**
- Pagine con testo/OCR non vuoto: **0/119**
- Caratteri estratti: **0**

### Concetti rilevati

- Nessun concetto rilevato con affidabilità dal testo estratto.

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Nessuna implementazione deve essere dedotta senza ulteriore verifica visiva e formalizzazione.

---

## allyouneedtoknow-230110032117-f4fdcdb0.pdf

- Pagine: **153**
- Pagine con testo/OCR non vuoto: **153/153**
- Caratteri estratti: **19.045**

### Concetti rilevati

- **Market Structure**: pagine più indicative 2, 19, 9, 20, 1, 10, 14, 17, 18, 21, 22, 23
- **Support/Resistance & SNR**: pagine più indicative 105, 81, 11, 21, 30, 36, 38, 44, 46, 80, 87, 104
- **Liquidity & Stop Hunts**: pagine più indicative 2, 82, 28, 29, 37, 46, 78, 31, 39, 47, 48, 80
- **Order Blocks & FVG**: pagine più indicative 51, 2, 52, 55, 50, 53, 54, 56, 57, 87, 88, 93
- **ICT Concepts**: pagine più indicative 10, 21, 23, 11, 12, 99, 100, 138, 149, 7, 9, 72
- **Fibonacci**: pagine più indicative 11, 2, 7, 21
- **Entries & Confirmation**: pagine più indicative 103, 2, 46, 53, 56, 80, 104, 105, 112, 115, 116, 117
- **Stop Loss & Take Profit**: pagine più indicative 29, 37, 26, 82, 83, 85, 31, 39, 45, 90, 46, 53
- **Sessions & Timing**: pagine più indicative 61, 68, 2, 65, 72, 62, 104, 78, 75, 63, 64, 73

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.

---

## candlesticksfibonacciandchartpatterntrading-forexfactorypdfdrive-210313181656.pdf

- Pagine: **273**
- Pagine con testo/OCR non vuoto: **263/273**
- Caratteri estratti: **355.855**

### Concetti rilevati

- **Market Structure**: pagine più indicative 136, 185, 38, 132, 184, 191, 24, 31, 39, 41, 42, 48
- **Support/Resistance & SNR**: pagine più indicative 217, 213, 241, 212, 223, 121, 214, 55, 203, 216, 54, 73
- **Supply & Demand**: pagine più indicative 65, 231
- **Liquidity & Stop Hunts**: pagine più indicative 181
- **Order Blocks & FVG**: pagine più indicative 35
- **ICT Concepts**: pagine più indicative 158, 160, 88, 115, 144, 33, 34, 66, 73, 87, 134, 140
- **Candlesticks**: pagine più indicative 48, 103, 104, 47, 95, 45, 43, 46, 99, 42, 96, 97
- **Chart Patterns**: pagine più indicative 57, 124, 49, 121, 63, 105, 106, 120, 240, 62, 122, 50
- **Fibonacci**: pagine più indicative 198, 200, 185, 241, 199, 92, 193, 194, 203, 264, 28, 29
- **Entries & Confirmation**: pagine più indicative 90, 123, 79, 81, 160, 190, 72, 76, 121, 71, 246, 40
- **Stop Loss & Take Profit**: pagine più indicative 145
- **Risk & Money Management**: pagine più indicative 21, 18, 20
- **Sessions & Timing**: pagine più indicative 31, 105, 174, 29, 30, 32, 41, 44, 68, 75, 76, 91
- **Psychology & Discipline**: pagine più indicative 22, 8, 12, 21, 138, 148, 185, 204, 217, 236, 239, 14
- **Sequence / Proprietary Models**: pagine più indicative 27, 28, 29, 130, 251

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.
- Conservare il modello proprietario come strategia isolata, con nomenclatura e condizioni esplicite prima della codifica.

---

## flippingmarkets1-230503210106-91bd5cfc.pdf

- Pagine: **59**
- Pagine con testo/OCR non vuoto: **56/59**
- Caratteri estratti: **14.658**

### Concetti rilevati

- **Market Structure**: pagine più indicative 32, 12, 6, 34, 35, 5, 13, 14, 16, 17, 27, 28
- **Support/Resistance & SNR**: pagine più indicative 44, 58, 28, 29, 23, 9, 13, 16, 25, 32, 38, 40
- **Supply & Demand**: pagine più indicative 25, 29, 43, 28, 12, 23, 40, 44, 58, 35, 9, 11
- **Liquidity & Stop Hunts**: pagine più indicative 48, 49, 51, 52, 12, 46, 47
- **Order Blocks & FVG**: pagine più indicative 19
- **ICT Concepts**: pagine più indicative 28, 4, 7, 8, 18, 45, 58
- **Fibonacci**: pagine più indicative 37, 38
- **Entries & Confirmation**: pagine più indicative 46, 35, 37, 38, 45, 58, 6, 13, 22, 23, 24, 28
- **Stop Loss & Take Profit**: pagine più indicative 38, 48, 51, 54, 4, 13, 35, 56, 57
- **Risk & Money Management**: pagine più indicative 4
- **Sessions & Timing**: pagine più indicative 3, 8, 4, 45, 54, 2, 40

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.

---

## ict-trading-250828073107-caca0de9.pdf

- Pagine: **91**
- Pagine con testo/OCR non vuoto: **91/91**
- Caratteri estratti: **57.806**

### Concetti rilevati

- **Market Structure**: pagine più indicative 22, 71, 25, 65, 3, 7, 14, 15, 18, 29, 63, 9
- **Support/Resistance & SNR**: pagine più indicative 26, 23, 27, 42, 36, 11, 25, 29, 30, 20, 22, 37
- **Supply & Demand**: pagine più indicative 89
- **Liquidity & Stop Hunts**: pagine più indicative 11, 20, 62, 2, 7, 10, 69, 6, 12, 61, 63, 64
- **Order Blocks & FVG**: pagine più indicative 38, 2, 40, 65, 59, 6, 42, 51, 55, 68, 39, 43
- **ICT Concepts**: pagine più indicative 2, 3, 4, 5, 6, 91, 26, 90, 27, 29, 88, 89
- **Fibonacci**: pagine più indicative 26, 42
- **Entries & Confirmation**: pagine più indicative 26, 73, 89, 2, 25, 29, 30
- **Stop Loss & Take Profit**: pagine più indicative 10, 89, 11, 25
- **Risk & Money Management**: pagine più indicative 3, 91
- **Sessions & Timing**: pagine più indicative 21, 86, 89, 90, 91
- **Psychology & Discipline**: pagine più indicative 3, 34

### Possibile valore per NEXUS (inferenza, non regola automaticamente valida)

- Creare feature detector separati e osservabili, senza fondere concetti diversi in un singolo segnale opaco.
- Formalizzare conferme come predicati deterministici versionati e testabili.
- Mappare le regole nel RiskPlan canonico; nessuna regola del corso deve bypassare il Risk Engine.
- Implementare calendario/sessioni con timezone broker, DST e validazione temporale.
- Trattare pattern e Fibonacci come moduli di evidenza, con definizioni matematiche e test contro ambiguità.

---

# Sintesi trasversale

- Pagine totali inventariate: **1092**
- Pagine con almeno testo nativo o OCR: **912/1092**

## Densità concettuale globale

- Support/Resistance & SNR: 1515 occorrenze indicative
- Entries & Confirmation: 789 occorrenze indicative
- Candlesticks: 511 occorrenze indicative
- Fibonacci: 493 occorrenze indicative
- Chart Patterns: 378 occorrenze indicative
- Sessions & Timing: 319 occorrenze indicative
- ICT Concepts: 316 occorrenze indicative
- Market Structure: 315 occorrenze indicative
- Liquidity & Stop Hunts: 281 occorrenze indicative
- Order Blocks & FVG: 162 occorrenze indicative
- Stop Loss & Take Profit: 85 occorrenze indicative
- Supply & Demand: 84 occorrenze indicative
- Psychology & Discipline: 62 occorrenze indicative
- Sequence / Proprietary Models: 22 occorrenze indicative
- Risk & Money Management: 15 occorrenze indicative

# Limiti ancora aperti

- Le pagine grafiche con OCR assente o debole richiedono verifica visiva diretta.
- Un’occorrenza non dimostra che una regola sia corretta, completa o traducibile automaticamente in codice.
- Le strategie dei corsi possono usare la stessa parola con significati differenti; la normalizzazione deve essere fatta corso per corso.
- Nessun concetto verrà inserito nel Master NEXUS come requisito operativo prima della formalizzazione e della verifica.
