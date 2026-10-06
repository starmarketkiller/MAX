# NEXUS External Trading Audit — Wave 2

EXTERNAL_TRADING_SYSTEMS_REUSE_AUDIT_V1 — WAVE 2

Status: ANALYSIS COMPLETE FOR SECOND WAVE — no implementation authorized

## Executive result

The second wave changes priorities in a useful way:

1. NautilusTrader is the strongest architecture reference for deterministic research/live parity, event-driven execution, adapter boundaries, persistence, message bus, and supply-chain security.
2. FinRL-X is more relevant than classic FinRL. Its most reusable idea is not RL itself but the contract-preserving modular pipeline: strategy layers transform a canonical portfolio representation while keeping execution separated.
3. TensorTrade is useful mainly as an RL research sandbox and as a warning about cost sensitivity: its own published BTC experiment shows commission can turn a positive zero-cost result into a loss.
4. TradeOS MCP is not a reusable trading engine. It is mainly a thin MCP bridge to a hosted TradeOS endpoint. Its value for NEXUS is the integration pattern: HTTP MCP, OAuth, stdio fallback, tool packaging and Claude plugin workflow.
5. ai-hedge-fund has surprisingly useful governance ideas despite being educational: paper/backtest separation, approval before paper action, kill switch, persistent hash-chained session ledger, and fund mandates. It should not be copied as a trading-decision architecture.
6. Kronos remains research-only. The small/base open models are feasible enough to benchmark, but the published fine-tuning path expects GPU-oriented training. It should enter only as an incremental predictive component after current Unified Market Intelligence Phase 1.
7. LEAN remains benchmark/cross-validation infrastructure, not a migration target.

────────

## 1. NautilusTrader

### What is materially interesting

- Rust-native deterministic event-driven engine.
- Same strategy/execution-algorithm code can run in backtest and live.
- Explicit acknowledgement that live still differs through venue, timing, persistence and reconciliation.
- Python as control plane; compiled engine for critical runtime.
- Cache + message bus as first-class composition primitives.
- Modular venue/data adapters.
- Optional Redis-backed state persistence.
- Very mature order semantics.
- Strong supply-chain/security posture: dependency vetting, lockfiles/checksums, SBOM, signed artifacts, hardened CI, secret scanning, CodeQL, cargo audit/deny/vet, pinned GitHub Actions.

### NEXUS comparison

NEXUS already has the correct high-level separation:
Market Intelligence -> deterministic Risk -> Execution.
It also already has MT5 as the actual execution environment, so replacing the engine would create enormous migration risk.

What NEXUS does not yet appear to have at the same maturity:

- a single explicit event-domain contract shared between research and execution;
- formal reconciliation semantics for state divergence after restart/external activity;
- adapter conformance tests;
- supply-chain/security controls at Nautilus maturity;
- explicit message-bus/cache contracts as independent architectural surfaces.

### Decision

ADAPT_PATTERN — HIGH PRIORITY

Do not import Nautilus as core. Extract these patterns:

1. EVENT_CONTRACT_V1
2. EXECUTION_STATE_RECONCILIATION_V1
3. ADAPTER_CONFORMANCE_TEST_V1
4. DEPENDENCY_SUPPLY_CHAIN_POLICY_V1
5. explicit BACKTEST_LIVE_DIFFERENCE_REGISTRY

### Claude implementation gate

Claude should compare these ideas against:

- existing NEXUS WebBridge/LocalBridge/event/state modules;
- Trade Ledger;
- Position Coordinator;
- execution/risk modules;
- deployment/security docs.

Only create missing abstractions.

────────

## 2. FinRL-X

### Important correction

Classic FinRL is now explicitly positioned by its maintainers as the older educational/research framework. The production-oriented successor is FinRL-X / FinRL-Trading.

### Most valuable architecture idea

FinRL-X uses a weight-centric contract:
Selection -> Allocation -> Timing -> Risk Overlay -> canonical target weights -> backtest/execution.

The key idea is not the exact "weights" representation. The key idea is:

> every stage transforms a stable canonical decision object while preserving the interface contract.

### NEXUS translation

For NEXUS, copying portfolio weights literally would be wrong for XAUUSD/MT5 entry logic.

But the architectural equivalent is powerful:

MarketState
-> MarketView
-> TradeIntent
-> RiskAdjustedIntent
-> ExecutionPlan

Each object should have a versioned schema and downstream code should not need to know how upstream intelligence was produced.

This matches the Unified Market Intelligence direction extremely well.

### Other useful patterns

- Pydantic/type-safe configuration.
- no-lookahead semantics documented as core requirement.
- multi-benchmark backtesting.
- transaction costs integrated into evaluation.
- paper/dry-run before execution.
- explicit portfolio-level risk overlay.

### Decision

ADAPT_PATTERN — VERY HIGH PRIORITY

Potential NEXUS task:
CANONICAL_DECISION_CONTRACT_PIPELINE_V1

Do not add RL because FinRL has RL.
Do not add Alpaca or stock-specific data architecture to NEXUS core.

────────

## 3. TensorTrade

### Useful facts

TensorTrade is a composable RL environment:
Observer -> Agent -> ActionScheme -> Portfolio
with a RewardScheme and data/exchange/broker simulation.

The most useful part for NEXUS is its explicit separation between:

- observation;
- action space;
- reward;
- execution simulation.

### Critical research lesson

TensorTrade's own current README reports a BTC/USD experiment where:

- zero commission result is positive;
- 0.1% commission turns the agent result materially negative.

This is exactly why NEXUS should never treat an ML/RL result as edge before realistic cost gates.

### Decision

BENCHMARK_ONLY / OPTIONAL_EXPERIMENT

Potential future use:

- standardized RL environment adapter;
- compare reward designs;
- investigate whether position-management can be learned in simulation.

But only after:

- robust supervised/contextual edge work;
- transaction-cost model;
- walk-forward/OOS protocol;
- independent holdout.

Do not make RL a near-term priority.

────────

## 4. TradeOS MCP

### What it actually is

The public repo is mainly:

- an npm MCP bridge;
- HTTP MCP endpoint access;
- OAuth;
- stdio fallback;
- registry packaging;
- Claude Code plugin/skill integration.

The actual trading intelligence lives behind the hosted TradeOS service endpoint.

### Value for NEXUS

Very useful as a reference for how to package NEXUS capabilities for external agents.

Pattern:
Claude/Cursor/other MCP client -> authenticated MCP facade -> bounded tools -> NEXUS

Possible future tool groups:

- nexus.research.*
- nexus.backtest.*
- nexus.market_state.*
- nexus.strategy_registry.*
- nexus.revenue.*
- nexus.status.*

Never expose:

- raw broker credentials;
- unrestricted shell;
- direct live-order tool;
- arbitrary risk-setting mutation.

### Strong design pattern

Support both:

1. remote authenticated HTTP MCP;
2. local stdio bridge.

That would fit NEXUS very well:

- cloud Jarvis/Claude/Codex can use HTTP;
- local agents can use stdio/LocalBridge.

### Decision

ADAPT_PATTERN — HIGH PRIORITY

Task candidate:
NEXUS_MCP_FACADE_V1

But it must sit on top of Global Orchestrator/permissions, not beside it.

────────

## 5. ai-hedge-fund

### What is useful

The project explicitly says it is educational and does not execute real trades.

Still, its current paper/backtest UX contains several useful governance patterns:

- fund/mandate definitions;
- paper ledger;
- exact approval step before simulated action;
- kill switch;
- session history;
- hash-chained persistent ledger;
- backtest results stored separately.

### NEXUS relevance

The useful piece is mandate + ledger + kill-switch, not "famous investor agents debating".

Possible NEXUS translation:
TRADING_MANDATE_V1

- allowed instruments;
- max risk;
- permitted sessions;
- strategy/component set;
- live/paper/shadow mode;
- approval policy;
- kill conditions.

This could also generalize beyond trading:
Revenue experiments and agents can have mandates too.

### Decision

ADAPT_PATTERN — MEDIUM/HIGH

Avoid copying:

- persona-based investor agents as evidence;
- LLM consensus as risk control.

────────

## 6. Kronos

### Actual model structure

Kronos tokenizes OHLCV/K-line data into hierarchical discrete tokens and runs an autoregressive Transformer.

Open models include approximately:

- mini: 4.1M parameters;
- small: 24.7M;
- base: 102.3M;
while the large model is not open in the listed model zoo.

### Practical consequence

Inference experiments with mini/small may be feasible on modest hardware, but:

- latency must be measured;
- training distribution differs from XAUUSD;
- its examples are not proof of XAU edge;
- the official fine-tuning pipeline is designed for multi-GPU torchrun.

### Proper NEXUS experiment

Not "forecast gold and trade it."

Instead:
Kronos output -> RESEARCH_ONLY predictive feature
then ask whether it adds incremental value conditional on the canonical Market Intelligence state.

Examples:

- expected return feature;
- directional probability;
- forecast dispersion / uncertainty proxy;
- predicted volatility/path shape.

Compare against:

- naive persistence;
- simple momentum;
- volatility baseline;
- Unified Market Intelligence without Kronos.

### Decision

OPTIONAL_EXPERIMENT — NOT NOW

Candidate:
PREDICTIVE_MODEL_KRONOS_PILOT_V1
only after current Shadow Phase 1.

────────

## 7. LEAN

### Why it still matters

LEAN is a large, actively maintained Apache-2.0 algorithmic trading engine with:

- Python/C# algorithms;
- brokerage abstraction;
- modular algorithm framework;
- mature historical/live architecture.

### Best NEXUS use

Not replacement.

The strongest use is an independent truth source:
implement a tiny subset of one already-frozen strategy in LEAN and compare:

- timestamps;
- signals;
- positions;
- costs;
- outcomes.

If MT5 and LEAN disagree, investigate semantics rather than optimize.

### Decision

BENCHMARK_AGAINST — MEDIUM PRIORITY

Task:
CROSS_ENGINE_PARITY_HARNESS_V1
later, for high-value strategies only.

────────

## Consolidated reuse matrix

| System         | Reuse priority | What to take                                                                        | What not to take                      |
|----------------|----------------:|--------------------------------------------------------------------------------------|----------------------------------------|
| NautilusTrader | VERY HIGH       | event contracts, parity philosophy, reconciliation, adapters, security/supply-chain | engine migration                       |
| FinRL-X        | VERY HIGH       | stable canonical decision contract, modular risk overlay, no-lookahead, dry-run     | stock-specific stack / RL hype         |
| TradeOS MCP    | HIGH            | MCP facade, OAuth/HTTP + stdio patterns, external-agent tooling                     | hosted vendor intelligence dependency  |
| RD-Agent       | HIGH            | R->D research loop, benchmarked self-improvement                                    | automatic research->live promotion     |
| TradingAgents  | HIGH            | checkpoint, run state, parallel roles, provider abstraction                         | LLM trader authority                   |
| Vibe-Trading   | HIGH            | bounded tool/skill catalog, shadow workflows                                        | prompt-generated strategies as proof   |
| ai-hedge-fund  | MED/HIGH        | mandate, kill switch, approval, append-only/hash ledger                             | persona voting                         |
| LEAN           | MEDIUM          | independent parity/reference engine                                                 | migration from MT5                     |
| TensorTrade    | MEDIUM          | RL environment abstractions, cost-aware research lesson                            | near-term RL core                      |
| Kronos         | MEDIUM/LATER    | predictive component experiment                                                     | direct forecast->trade                 |

## New candidate NEXUS tasks

1. CANONICAL_DECISION_CONTRACT_PIPELINE_V1
2. EVENT_CONTRACT_V1
3. EXECUTION_STATE_RECONCILIATION_V1
4. ADAPTER_CONFORMANCE_TEST_V1
5. DEPENDENCY_SUPPLY_CHAIN_POLICY_V1
6. BACKTEST_LIVE_DIFFERENCE_REGISTRY_V1
7. NEXUS_MCP_FACADE_V1
8. AGENT_TRADING_MANDATE_V1
9. CROSS_ENGINE_PARITY_HARNESS_V1
10. PREDICTIVE_MODEL_KRONOS_PILOT_V1
11. RL_RESEARCH_SANDBOX_V1 — low priority
12. EXTERNAL_SYSTEM_REUSE_REGISTRY_V1

## Recommended order for Claude

### P0 — inspect now, no implementation

Claude should verify whether NEXUS already has equivalents of:

- canonical decision contracts;
- event-domain schema;
- durable state/reconciliation;
- adapter conformance testing;
- MCP capability exposure;
- mandate model;
- supply-chain controls.

### P1 — likely implementation candidates

Only if gaps are real:

1. Canonical Decision Contract Pipeline
2. MCP Facade
3. Event/Reconciliation contracts
4. Supply-chain policy
5. Mandate model

### P2 — research infrastructure

- Cross-engine LEAN/Nautilus parity harness.
- Kronos pilot.
- RL sandbox.

## Handoff rule

Claude must classify every candidate:
REUSE_EXISTING / EXTEND_EXISTING / ADAPT_PATTERN / IMPORT_COMPONENT / BENCHMARK_ONLY / REJECT

For any proposed implementation, it must name:

- exact NEXUS files/modules affected;
- why existing capability is insufficient;
- new dependency if any;
- security impact;
- rollback path;
- tests/evals;
- whether the change touches live trading.

No external framework should be added as a dependency by default.
