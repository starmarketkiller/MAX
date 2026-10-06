# NEXUS External Trading Audit — Wave 3

EXTERNAL_TRADING_SYSTEMS_REUSE_AUDIT_V1 — WAVE 3

MT5 / MQL5 / MCP / Skills / Backtest Automation

Status: ANALYSIS COMPLETE — no implementation authorized

## Executive result

Wave 3 is the most directly relevant to NEXUS so far because these repositories sit close to the actual MT5/MQL5 execution layer.

The strongest findings are:

1. vincentwongso/mt5-trading-mcp — best reference for safe AI↔MT5 tool exposure: read vs mutating tools, preflight, human consent, idempotency, append-only audit, subscriptions/resources, local-first operation, Pydantic schemas.
2. psyb0t/mt5-httpapi — strongest reference for automated MT5 infrastructure: multi-terminal isolation, REST/MCP, Strategy Tester jobs, compile automation, optimization jobs, report/log retrieval, multi-VM scaling, binary supply-chain verification.
3. mnemox-ai/tradememory-protocol — highly relevant for a future memory/governance layer: outcome-weighted trade memory, local-first recall, policy brake/proxy before broker, hash-chained audit, idempotent forwarding, fail-closed behavior.
4. EA31337/EA31337-classes — mature reusable MQL4/MQL5 abstraction layer, especially useful as a comparison target for NEXUS indicator/account/symbol/order wrappers and cross-version compatibility.
5. BerryUIKI/RegimeForgeEA — unusually rigorous research repository. Its value is not the strategy but the scientific workflow: closed-bar signals, proxy-vs-broker distinction, negative evidence retention, training/validation/holdout separation, cost sensitivity, broker-native validation before live.
6. RicardoBarato/ea-auto-backtest-engine — practical reference for automated compile/test/report collection, public/private artifact boundaries, tester/live flags, sanitized configs and reproducible run folders.
7. nawfdev/mq5_skills — direct evidence that a reusable MQL5 coding Skill can package canonical patterns, eval cases and response contracts for Claude/ChatGPT/Mistral. Useful conceptually, but its hardcoded strategy/risk heuristics must not become NEXUS scientific truth.
8. sumedhkumar/mt5-trading-mcp — broad feature reference: MCP + REST + WebSocket quote stream + MT5 Python client + skill packaging. Useful for tool-surface comparison, but less safe by design because it exposes direct mutating tools without a NEXUS-style deterministic authority boundary.
9. toki-plus/ai-trader-for-mt5 — architecture-only reference that independently converges on the same idea as NEXUS: AI in an analysis layer, structured state, signal lifecycle, deterministic tooling/risk, execution separated from model output.

────────

## 1. vincentwongso/mt5-trading-mcp

### What is strong

- 12 read-only tools vs 4 mutating tools.
- Mutating path: preflight -> consent -> idempotency -> audit.
- Subscribable resources for account/positions/quotes.
- Local-first, no cloud/telemetry.
- Single MT5 adapter as terminal connection owner.
- Pydantic schemas as source of truth.
- Transparent reconnect/reinit.
- Explicit threat model for prompt injection.
- Tool scoping by role.
- Rate limits and symbol allow/deny support.
- Append-only audit JSONL.
- Chart screenshots through a tiny MQL5 bridge EA.

### Critical limitation

The consent gate is opt-in and mutating calls can auto-execute when unarmed. For NEXUS this is unacceptable as a default.

### NEXUS decision

ADAPT_PATTERN — VERY HIGH PRIORITY

Reuse patterns:

- READ_TOOL / MUTATING_TOOL capability classes
- preflight
- idempotency_key
- approval fingerprint / exact terms
- append-only audit
- subscription/change events
- schema-first tool definitions
- prompt-injection threat model
- role-scoped tool exposure

Do not expose direct place_order authority to generic agents.

### Candidate NEXUS task

MT5_CAPABILITY_GATEWAY_HARDENING_V1

Target architecture:
Agent -> NEXUS capability gateway -> deterministic policy/risk -> approval -> MT5 adapter

────────

## 2. psyb0t/mt5-httpapi

### What is strong

This repo solves a different problem: running the real Windows MT5 terminal as infrastructure.

Key patterns:

- real Windows MT5 in isolated VM(s)
- multiple brokers/accounts/terminal clones
- nginx routing
- REST + MCP
- dedicated live vs backtest terminal mode
- Strategy Tester jobs submitted over API
- build .ini and .set from structured JSON
- compile MQL5 without manual MetaEditor interaction
- optimization job support
- reports/logs/artifacts downloadable by job id
- queue and serialized tester lock
- restart recovery marks orphaned jobs failed
- retention policy
- path traversal rejection
- bearer auth
- vendored binary manifest with SHA-256, upstream URL and signature state
- CI verifies binaries before tests

### Important MT5-specific insight

A live terminal and Strategy Tester cannot safely share the same portable data directory. The project structurally separates mode: live from mode: backtest.

This is directly relevant to NEXUS automation.

### NEXUS decision

ADAPT_PATTERN — VERY HIGH PRIORITY

Likely reusable design:

- MT5_TESTER_JOB_V1
- MT5_COMPILE_JOB_V1
- MT5_ARTIFACT_MANIFEST_V1
- isolated terminal profiles
- job queue + restart recovery
- structured .set/.ini generation
- report/log collection
- explicit live/tester resource isolation

Do not import the whole VM stack yet unless NEXUS actually needs Linux-hosted multi-terminal orchestration.

### Candidate NEXUS tasks

- MT5_AUTOMATED_TESTER_CONTROL_PLANE_V1
- MT5_RUN_ARTIFACT_CONTRACT_V1
- MT5_TERMINAL_ISOLATION_POLICY_V1

────────

## 3. mnemox-ai/tradememory-protocol

### What is strong

This is not just "memory for LLMs". It introduces a policy layer between agent and broker.

Patterns:

- sync real fills into local memory
- recall losses before future orders
- local SQLite
- outcome-weighted memory
- pre-trade legitimacy checks
- strategy performance and reflection
- policy proxy/brake in front of broker MCP
- fail-closed behavior for unknown/un-evaluable orders
- exact approval terms/fingerprint
- idempotent forwarding
- protective stop cannot silently be removed
- full halt command
- append-only / hash-chained audit
- daily Merkle roots
- records both actions and non-actions

### NEXUS relevance

Very high for:

- future episodic trading memory
- deterministic pre-trade brake
- immutable audit chain
- post-trade learning
- decision provenance
- "do not forget prior failure in similar context"

### Scientific caution

Its "outcome-weighted memory" is useful as operational context, but must not become statistical evidence by itself. Historical losses recalled by similarity can bias decisions and create path dependence.

### NEXUS decision

ADAPT_PATTERN — HIGH PRIORITY

Candidate capabilities:

- TRADE_EPISODIC_MEMORY_V1
- TRADE_DECISION_RECORD_V1
- HASH_CHAIN_AUDIT_V1
- PRE_TRADE_BRAKE_V1
- POST_TRADE_OUTCOME_LINKER_V1

Memory must inform/review; deterministic risk remains authoritative.

────────

## 4. EA31337 Framework

### What is strong

- mature MQL4/MQL5 common abstraction
- account/symbol/order/chart/indicator wrappers
- indicator family abstraction
- data structures
- profiler
- cross-version compatibility

### NEXUS relevance

The main question is not whether to import the library.

The useful question is:

> Does NEXUS already have wrappers that reinvent these concepts inconsistently across dozens of strategies?

If yes, EA31337 can be used as a design benchmark for:

- indicator lifecycle abstraction
- symbol metadata normalization
- account state access
- order wrappers
- timing/profiling

### NEXUS decision

BENCHMARK / SELECTIVE PATTERN REUSE

Do not replace working NEXUS primitives just for style.

### Candidate task

MQL5_COMMON_PRIMITIVES_DUPLICATION_AUDIT_V1

────────

## 5. RegimeForgeEA

### Why it matters

The most useful part is research discipline.

It explicitly:

- disables new entries by default
- distinguishes public proxy data from broker-native XAUUSD
- retains failed candidates as negative evidence
- uses closed-bar signals
- executes next-bar in Python backtests
- documents intrabar ambiguity
- separates training/validation/final holdout
- stops inspection after failure gates
- tests costs
- rejects apparent event-level effects if order-level execution removes them
- requires broker-native Strategy Tester validation before live

This is very close to the scientific direction NEXUS already adopted.

### NEXUS decision

BENCHMARK_AGAINST — HIGH PRIORITY

Not for strategy import.
Use it to audit our own Research Protocol and negative-evidence handling.

### Candidate task

RESEARCH_PROTOCOL_EXTERNAL_BENCHMARK_V1

Compare:

- preregistration
- holdout handling
- proxy-data caveats
- order-level conversion
- cost stress
- failed-candidate retention
- live enablement gate

────────

## 6. EA Auto Backtest Engine

### Useful patterns

- MetaEditor compile automation
- Strategy Tester automation
- run folders
- private artifact default
- redacted tester config
- live orders disabled by default
- tester orders explicitly enabled
- PowerShell + Python split
- safe .gitignore / public-private boundary

### NEXUS relevance

Useful as a simpler alternative/reference to mt5-httpapi.

### NEXUS decision

ADAPT_PATTERN — MEDIUM/HIGH

NEXUS should have:
compile -> test -> artifacts -> parse -> verify -> registry
as one deterministic workflow.

────────

## 7. mq5_skills

### Important finding

A public skill package already exists specifically for generating MQL5 EAs with:

- SKILL.md
- reference blueprints
- eval cases
- canonical MQL5 patterns
- output contract
- local validation
- compatibility with Claude, ChatGPT, Mistral and other models

This strongly supports the NEXUS Skill Factory direction.

### What to copy conceptually

- Skill package structure
- references folder
- eval cases
- canonical API patterns
- response contract
- repo validator
- skill versioning

### What NOT to copy as truth

Examples like:

- "risk always <=1%"
- "PF >1.5"
- "Sharpe >1"
- hardcoded martingale caps
- fixed demo duration

These may be sensible heuristics, but they are not universal scientific facts.

### NEXUS decision

ADAPT_PATTERN — VERY HIGH PRIORITY

Candidate:
MQL5_ENGINEERING_SKILL_V1

It should teach:

- NEXUS-specific coding conventions
- known MQL5 pitfalls
- handle lifecycle
- CopyBuffer
- new-bar/closed-bar rules
- time zone handling
- strategy identity/attribution rules
- risk/execution boundaries
- test requirements
- compile and regression commands
- forbidden patterns

This skill can be used by Codex, Claude, Ministral or future local models.

────────

## 8. sumedhkumar/metatrader-mcp-server

### Useful pieces

- MCP stdio/SSE/streamable HTTP
- REST API
- WebSocket tick stream
- Python MT5 client abstraction
- retries/backoff
- market/account/history/order APIs
- Claude skill packaging
- IDE/client compatibility

### NEXUS decision

TOOL-SURFACE BENCHMARK

Good reference for completeness of MT5 capabilities.

Not sufficient as NEXUS safety architecture because direct natural-language execution is a core use case in that project.

────────

## 9. toki-plus/ai-trader-for-mt5

### Important convergence

The architecture description independently argues:

- do not let LLM directly issue trades
- structured market/account/signal context
- deterministic tools
- strategy/risk separation
- signal lifecycle
- controlled execution
- logging and review

That is essentially the same direction NEXUS has converged on.

### NEXUS decision

ARCHITECTURAL CONFIRMATION / BENCHMARK ONLY

The full implementation is not public, so there is little code to reuse.

────────

## Wave 3 consolidated reuse matrix

| External project                      | NEXUS value                                            | Decision                  |
|----------------------------------------|---------------------------------------------------------|----------------------------|
| vincentwongso/mt5-trading-mcp         | Safe MT5 capability gateway                             | ADAPT_PATTERN — VERY HIGH |
| psyb0t/mt5-httpapi                    | Automated tester/compile/multi-terminal control plane   | ADAPT_PATTERN — VERY HIGH |
| mnemox-ai/tradememory-protocol        | Memory, brake, hash-chain audit                         | ADAPT_PATTERN — HIGH      |
| nawfdev/mq5_skills                    | Skill packaging/evals for MQL5 engineering              | ADAPT_PATTERN — VERY HIGH |
| EA31337/EA31337-classes               | MQL common abstractions                                 | BENCHMARK / SELECTIVE     |
| BerryUIKI/RegimeForgeEA               | Research rigor                                          | BENCHMARK — HIGH          |
| RicardoBarato/ea-auto-backtest-engine | Compile/test/artifact workflow                          | ADAPT_PATTERN — MED/HIGH  |
| sumedhkumar/mt5-trading-mcp           | MT5 tool surface/streaming                              | BENCHMARK                 |
| toki-plus/ai-trader-for-mt5           | Architecture convergence                                | BENCHMARK ONLY            |

## New high-value NEXUS candidates

1. MT5_CAPABILITY_GATEWAY_HARDENING_V1
2. MT5_AUTOMATED_TESTER_CONTROL_PLANE_V1
3. MT5_RUN_ARTIFACT_CONTRACT_V1
4. MT5_TERMINAL_ISOLATION_POLICY_V1
5. MQL5_ENGINEERING_SKILL_V1
6. MQL5_COMMON_PRIMITIVES_DUPLICATION_AUDIT_V1
7. TRADE_DECISION_RECORD_V1
8. TRADE_EPISODIC_MEMORY_V1
9. PRE_TRADE_BRAKE_V1
10. HASH_CHAIN_AUDIT_V1
11. POST_TRADE_OUTCOME_LINKER_V1
12. RESEARCH_PROTOCOL_EXTERNAL_BENCHMARK_V1

## Recommended priority

### P0 — Claude gap audit now

Before implementation, compare the NEXUS repo against:

- MT5 capability gateway
- existing Local/Web Bridge
- compile/test automation
- tester scripts
- trade ledger
- approval/fingerprint/idempotency
- event bus
- memory/state
- current MQL5 shared includes
- audit/provenance
- GitHub/CI supply-chain controls

### P1 — likely high-value implementation if gaps are confirmed

1. MQL5_ENGINEERING_SKILL_V1
2. MT5_AUTOMATED_TESTER_CONTROL_PLANE_V1
3. MT5_CAPABILITY_GATEWAY_HARDENING_V1
4. MT5_RUN_ARTIFACT_CONTRACT_V1
5. TRADE_DECISION_RECORD_V1

### P2

- episodic trade memory
- hash-chain audit
- common primitive refactor
- terminal multi-instance/VM orchestration

## Critical architecture rule

Do not connect:
web/news/social/LLM -> MT5 mutating tool

The allowed architecture remains:

```
untrusted input
-> Market Intelligence / agent analysis
-> canonical TradeIntent
-> deterministic Risk Engine
-> Policy/Brake
-> approval when required
-> idempotent ExecutionPlan
-> MT5
-> Trade Decision Record
-> Outcome linker / audit / memory
```

## Claude handoff

Required review:
docs/EXTERNAL_TRADING_SYSTEMS_REUSE_AUDIT_V1_WAVE3_CLAUDE_REVIEW.md

For every candidate Claude must classify:
REUSE_EXISTING / EXTEND_EXISTING / ADAPT_PATTERN / IMPORT_COMPONENT / BENCHMARK_ONLY / REJECT

And provide:

- exact NEXUS files/modules already present
- gap
- external source/pattern
- dependency required?
- live-trading impact
- security implications
- tests
- migration/rollback
- priority

No implementation until this gap review is complete.
