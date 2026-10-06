# NEXUS External Trading Audit — Wave 1

EXTERNAL_TRADING_SYSTEMS_REUSE_AUDIT_V1

Status: IN_PROGRESS — architecture/reuse audit, no implementation authorized.

Purpose: identify reusable patterns/components from public AI/quant/trading systems and decide what NEXUS should reuse, adapt, benchmark, or reject.

## Decision classes

- ADOPT_PATTERN
- EVALUATE_CODE_REUSE
- BENCHMARK_AGAINST
- OPTIONAL_EXPERIMENT
- REJECT_FOR_CORE
- NEEDS_DEEP_AUDIT

## NEXUS invariants

1. LLM != live order authority.
2. Market intelligence stays separate from deterministic Risk/Execution.
3. Prefer Skill + Tool + Verifier unless a new Agent is justified by authority/context/failure isolation or parallelism.
4. Web/news/social are untrusted inputs.
5. New models/providers/frameworks enter EVALUATION/SHADOW first.
6. Point-in-time integrity, provenance, reproducibility and OOS/forward gates remain mandatory.
7. NEXUS remains canonical orchestration/state/audit layer.

## TradingAgents — TauricResearch

Observed: LangGraph multi-agent graph, parallel analysts, structured outputs, multi-provider abstraction including Ollama, persistent decision log, checkpoint/resume, date-grid backtesting, and recent point-in-time/look-ahead fixes.

Decision:

- ADOPT_PATTERN: checkpoint/resume, run isolation, point-in-time guards, structured role outputs, provider registry concepts.
- BENCHMARK_AGAINST: fan-out/fan-in quality/cost/latency.
- REJECT_FOR_CORE: direct LLM trader/portfolio authority as execution design.
- NEEDS_DEEP_AUDIT: LangGraph overlap with NEXUS Work Graph/Orchestrator.

Claude questions:

1. Map checkpoint/state ideas onto NEXUS without adding a second orchestrator.
2. Compare provider abstraction vs current router/capability graph.
3. Reuse point-in-time tests where applicable.
4. Evaluate decision-memory settlement as verified episodic memory, not research contamination.

## Microsoft RD-Agent / Qlib

Observed: R&D split into Research and Development, quant factor mining/model optimization, factor-model co-optimization, benchmark-driven evaluation, multi-provider backend.

Decision:

- ADOPT_PATTERN: R→D loop, experiment artifacts, benchmark-driven improvement, candidate registries.
- BENCHMARK_AGAINST: Edge Factory throughput/reproducibility.
- EVALUATE_CODE_REUSE: isolated research adapters/utilities only.
- OPTIONAL_EXPERIMENT: factor mining on NEXUS datasets after current Unified Market Intelligence Phase 1.
- REJECT_FOR_CORE: automatic promotion from research into live trading.

Claude questions:

1. Map R/D abstractions to Trading Research / Experiment / Coding / Reviewer.
2. Identify minimum reusable primitives.
3. Decide whether Qlib should be research-only adapter.
4. Audit license/dependency/runtime cost.

## QuantDinger

Observed: self-hosted AI Trading OS; AI research→strategy code→backtest→paper/live→monitoring; Agent Gateway + MCP; scoped tokens; paper-only default; audit logs; schedules/notifications.

Decision:

- ADOPT_PATTERN: scoped agent tokens, paper-only default, dual-gate live enablement, audit-log and approved-tool MCP concepts.
- BENCHMARK_AGAINST: Local Bridge/capability grants/execution approvals/control plane.
- EVALUATE_CODE_REUSE: MCP gateway patterns after overlap audit.
- REJECT_FOR_CORE: generic agent token becoming effective live authority without deterministic NEXUS risk gates.

Claude questions:

1. Compare Agent Gateway security with NEXUS HMAC/capability/approval boundaries.
2. Check whether MCP façade removes custom integration work.
3. Compare scheduler/notification architecture with NEXUS Automation/Event Bus plans.
4. Inspect credential isolation.

## HKUDS Vibe-Trading

Observed: natural-language research UX, MCP server with bounded tools, backtest/factor/market-data/web/document tools, shadow strategy tooling, swarm presets, local Ollama support.

Decision:

- ADOPT_PATTERN: explicit tool catalog, shadow tools, run/result API, free/local-first paths.
- BENCHMARK_AGAINST: Skill Factory / MCP compatibility.
- EVALUATE_CODE_REUSE: tool schemas/run-management patterns.
- REJECT_FOR_CORE: natural-language strategy generation as scientific validation.

Claude questions:

1. Can NEXUS expose safe capabilities via MCP without duplicating Orchestrator logic?
2. Which tool schemas map to Skill Capsules?
3. Compare shadow workflow to current research-run contracts.

## LEAN / QuantConnect

Observed: event-driven modular trading engine with research/backtest/optimization/live and pluggable components.

Decision:

- BENCHMARK_AGAINST: event model, transaction handling, data/broker abstraction, research/live separation.
- OPTIONAL_EXPERIMENT: independent validation of selected strategy logic.
- REJECT_FOR_CORE: migrating away from MT5 just to adopt LEAN.
- NEEDS_DEEP_AUDIT: narrow research adapter value vs maintenance cost.

## Kronos

Observed: open-source foundation model for financial candlestick/K-line sequences across many exchanges, with fine-tuning support.

Decision:

- OPTIONAL_EXPERIMENT only.
- Enter Component Registry as RESEARCH_ONLY.
- Require causal input semantics, preregistration, OOS/forward, cost and latency gates.
- No priority before Unified Market Intelligence Shadow Phase 1 closes.

## High-priority reusable patterns

A. Durable task state/checkpoint-resume.
B. Point-in-time data integrity.
C. R→D autonomous R&D loop.
D. Scoped Agent Gateway / MCP.
E. Paper/shadow-by-default as a capability property.
F. Tool/Skill catalogs with schema, permissions, verifier, telemetry, golden evals.
G. Cross-engine validation.
H. Foundation-model components as research-only candidates.

## Do NOT copy

- Swarm for its own sake.
- LLM voting treated as statistical evidence.
- Generic LLM Trader with direct order authority.
- Self-reflection that silently rewrites scientific rules.
- Live execution enabled by one model decision.
- Duplicate orchestration stacks.
- Model-generated strategy code promoted without preregistration/OOS/forward.
- RL/foundation models added only because they look sophisticated.

## Candidate backlog additions

- EXT-TRADING-001 External Trading Systems Reuse Registry
- EXT-TRADING-002 MCP Façade Feasibility Audit
- EXT-TRADING-003 Durable Work Graph / Checkpoint-Recovery Comparison
- EXT-TRADING-004 RD-Agent R→D Pattern Mapping for Edge Factory
- EXT-TRADING-005 Point-in-Time Integrity Pattern Audit
- EXT-TRADING-006 Skill Catalog / Tool Contract Comparison
- EXT-TRADING-007 Cross-Engine Validation Feasibility
- EXT-TRADING-008 Predictive Model Candidate Registry
- EXT-TRADING-009 External Framework License + Supply-Chain Audit
- EXT-TRADING-010 External Framework Golden Benchmark Suite

## Recommended order

1. No runtime changes now.
2. Claude performs deep code audit of TradingAgents, RD-Agent, QuantDinger and Vibe-Trading against existing NEXUS code.
3. Produce a reuse matrix: capability / NEXUS already has / external implementation / better? / integration cost / security impact / recommendation.
4. Only then promote selected items into implementation tasks.
5. LEAN/Nautilus/Kronos remain research/benchmark tracks until current Unified Market Intelligence Shadow Phase 1 is complete.

## Claude handoff gate

Do not implement until Claude has:

- inspected corresponding NEXUS modules first;
- proven functionality is not duplicate;
- identified exact files/interfaces to reuse or extend;
- documented dependency/security/license implications;
- classified each candidate as REUSE_EXISTING / ADAPT_PATTERN / IMPORT_COMPONENT / BENCHMARK_ONLY / REJECT.

Required output:
docs/EXTERNAL_TRADING_SYSTEMS_REUSE_AUDIT_V1_CLAUDE_REVIEW.md

Each final decision must include:
decision, why, NEXUS files affected, external source, dependency introduced?, security impact, expected benefit, test plan, rollback plan.
