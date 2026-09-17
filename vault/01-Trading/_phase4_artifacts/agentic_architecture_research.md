# Survey: Open-Source Quant / Algo / Agentic Trading System Architectures

Research date: 2026-09-17
Purpose: survey validated open-source architectural patterns (observation -> feature extraction -> research -> decision -> risk -> execution -> memory -> feedback -> audit) before finalizing NEXUS's research-architecture redesign. All facts below are drawn from official repos/docs/papers linked in Sources; no anecdotal profitability claims are used as evidence. Star/commit counts are point-in-time snapshots (Sep 2026) and only indicate activity level, not architectural quality.

---

## 1. Gordon (general-liquidity/gordon)

**What it is:** An open-source, MIT-licensed "agent harness" for financial markets (crypto, equities, options, futures) — an LLM-driven trading agent wrapped in a deny-first safety/permission system. Note: disambiguate from unrelated forks/mirrors (`gonome/gordoncli` is a mirror) and from `TauricResearch/TradingAgents` / other "trading-agents" repos, which are separate projects.

**Source:** https://github.com/general-liquidity/gordon

**Architecture / separation of concerns:**
- **Observation/ingestion:** CCXT adapters (Binance, Coinbase, Kraken, Hyperliquid, etc.), equity/options brokers (Alpaca, tastytrade, Interactive Brokers), external data (Finnhub, SEC/EDGAR, Yahoo, Nansen, Arkham, Birdeye, DexScreener, Glassnode).
- **Feature extraction:** "100 indicator operations and 87 advanced-analysis operations behind two typed dispatchers" (technical indicators, market structure, regime detection, statistical tests, fundamentals, on-chain analytics) — explicitly exposed as a separate typed tool surface, not embedded in agent prompts.
- **Research/signal generation:** A dedicated **Researcher** agent, restricted to a "read-only, time-boxed surface," does multi-timeframe analysis, playbook strategies, and backtesting. It cannot place trades.
- **Decision-making:** Gordon (orchestrator) "routes, supervises, and synthesizes; never trades directly." Its output is a structured, human-inspectable **plan**, not a direct order — "The model proposes. The harness disposes."
- **Risk management:** A deterministic, non-LLM **permission engine**: deny-first policy, a 16-dimension risk classifier (8 base + 8 conditional), an immutable "trading constitution" (size/leverage/loss/drawdown/concentration ceilings), 8 distinct trade-halt types, and kill switches at firm/gateway/venue/instrument/account/trader/client/strategy granularity.
- **Execution:** A separate **Executor** agent holds execution tools only, "cannot bypass the safety plane," dispatches through paper/live adapters with bounded rules for reductions/protective recovery.
- **Memory/state:** LibSQL + vector memory for canonical state; 5-stage context-compaction at 70/80/90/94/99% pressure; loop-detection safeguards (identical-call, alternating-cycle).
- **Feedback loop:** 22 "proactive radar producers" with health tracking; 14 lifecycle hooks around tools/approvals/orders/sessions/compaction/subagents.
- **Audit/logging:** HMAC-chained decision log (SQLite) recording orders, risk decisions, portfolio snapshots, and the agent's reasoning trace together — an immutable, cryptographically chained audit trail, not just a log file.

**Backtest-vs-live parity / leakage:** Explicit self-aware caveat: "A backtest is not an edge. Robustness checks reduce self-deception; they do not create live alpha." Provides historical replay, walk-forward, Monte Carlo, optimization, impact and fee modeling, and overfitting checks. Notes real limits to parity: IBKR "paper versus live is not observable from the local gateway," and CCXT sandbox fidelity "must be verified" per exchange — i.e., it documents where parity *cannot* be guaranteed rather than claiming false confidence.

**License / maintenance:** MIT. Actively maintained (CI/CD, ~1,374 commits on main at time of review). Project self-describes as "young software."

---

## 2. OpenAlgo (marketcalls/openalgo)

**What it is:** A self-hosted, Python (Flask) + React algo-trading platform unifying 36 broker integrations behind one REST API, with visual strategy building, hosted Python strategy execution, and options analytics — positioned as a full trading OS, not just a broker bridge.

**Source:** https://github.com/marketcalls/openalgo · https://openalgo.in/

**Architecture / separation of concerns:**
- **Observation/ingestion:** Real-time WebSocket + ZeroMQ message bus normalizing market data (depth, quotes, LTP) across all 36 broker plugins into one schema; historical data stored separately in DuckDB ("Historify").
- **Feature extraction:** A dedicated Rust-backed indicator library (`openalgo.ta`, 127 indicators) plus built-in options analytics (IV smile, vol surface, Greeks, max pain) — consumed identically by the visual builder, Python host, and the AI agent module.
- **Research/signal generation:** Three parallel authoring surfaces: a no-code "Flow" drag-and-drop node builder, a hosted Python strategy editor with process isolation, and an LLM "AI Agent" that reads market data and proposes strategies.
- **Decision-making:** Flow condition nodes with explicit branching logic; for the AI Agent, **every generated order pauses for explicit human approval before execution** — an explicit human-in-the-loop gate between LLM output and order placement.
- **Risk management:** Smart order position sizing, automatic square-off schedules, configurable rate limiting (login/API/order/webhook), order-splitting/intelligent routing for large orders.
- **Execution:** One broker-agnostic REST contract (`/api/v1/`, 57 endpoints) shared by all 36 broker plugins; an "Action Center" offers both auto-mode (immediate) and semi-auto (manual approval) execution paths.
- **Memory/state:** Six separate operational data stores (main SQLite, logs, latency, health, sandbox SQLite, DuckDB historical) — state is partitioned by concern rather than one shared database.
- **Feedback loop:** Real-time PnL tracker, latency monitor (order round-trip time), traffic monitor (API usage/error stats), WebSocket reconnection/failover handling.
- **Audit/logging:** Full audit trail with timestamps in Action Center; live-streamed strategy logs; Argon2 password hashing + Fernet-encrypted broker tokens; manual IP-ban security dashboard.

**Backtest-vs-live parity / leakage:** "Analyzer Mode" is an isolated sandbox (separate database, simulated ₹1 Crore capital, its own margin/leverage/square-off rules) that runs the *same* strategy code against real market data without live order risk — a structurally separate environment rather than a flag on the live path, which reduces the chance that test and prod diverge silently. No explicit walk-forward/cross-validation tooling documented.

**License / maintenance:** AGPL-3.0. Actively maintained (~5,241 commits, 2.7k stars, regular issue/PR throughput).

---

## 3. Agentic Trading Lab / AgenticTrading (Open-Finance-Lab / SecureFinAI Lab)

**What it is:** An open-source research and education platform for LLM-powered trading agents, built around the **FinAgent Orchestration Framework** (published at NeurIPS 2025), spanning historical backtesting through live paper trading with full decision transparency and standardized leaderboards.

**Source:** https://github.com/Open-Finance-Lab/AgenticTrading

**Architecture / separation of concerns:**
- **Observation/ingestion:** Market data via Alpaca API; news/sentiment via an "Agentic FinSearch" module (Reddit/social sentiment planned).
- **Feature extraction / research-signal generation:** Embedded inside the agent decision pipeline rather than a separate pre-computed layer; agents work from customizable prompts and a community template library.
- **Decision-making:** LLM agents coordinated via an **Agent API v2**; the orchestration is explicitly **DAG-based multi-agent planning** (FinAgent framework), not a single monolithic call.
- **Risk management:** Per-order risk caps for live trading; an explicit **"review-only mode"** shows agent decisions before they execute; standardized risk-evaluation metrics; kill-switch support planned.
- **Execution:** One workflow spans backtest, paper, and live execution backends (v2), with Robinhood and Alpaca as live/paper brokers.
- **Memory/state:** Persistent agent state for scheduled/long-running agents; SQLite (`backtest.db`) for trade/position/portfolio records.
- **Feedback loop:** Standardized leaderboard comparisons across agents/models under identical market windows; Discord bot integration for monitoring.
- **Audit/logging:** Explicit design goal — "every run, decision, and reason" is logged and inspectable, i.e., reasoning traces are treated as first-class audit artifacts, not just final orders.

**Backtest-vs-live parity / leakage:** Architecturally emphasizes a *single progression* — historical simulation -> live paper trading -> (optionally) live — in one workflow specifically to reduce the implementation gap between research and production. No explicit lookahead-bias detection tooling documented (unlike Freqtrade or TradingAgents below).

**License / maintenance:** OpenMDW-1.0. Actively developed (~1,688 commits, 80 open issues, recent NeurIPS 2025 paper backing the orchestration framework).

---

## 4. OpenAlice (TraderAlice/OpenAlice)

**What it is:** A file/Git-driven, local-first AI trading agent ("your one-person Wall Street") covering equities, crypto, commodities, forex, and macro — designed to plug into existing coding agents (Claude Code, Codex, OpenCode, etc.) as the "brain," with OpenAlice supplying market data, research workspaces, and brokerage connectivity.

**Source:** https://github.com/TraderAlice/OpenAlice

**Architecture / separation of concerns:**
- **Observation/ingestion:** Configurable data providers for market data, fundamentals, news, and quant tools; a UI lets a human inspect the same data the agent sees.
- **Feature extraction / research:** Distinct **workspace types** per research mode — Chat (general analysis), AutoQuant (quantitative experiments), Auto Prediction (prediction-market research) — each persisting "conversations, files, and Git history together."
- **Decision-making:** Connects to brokers via a "Unified Trading Account" abstraction to inspect holdings/orders/state before deciding.
- **Execution — the standout idea:** **"Trading as Git."** Agents stage proposed trading operations as commits with rationale attached; a human reviews and approves before anything executes. This turns the entire decision history into a version-controlled, diffable, revertible audit log by construction, rather than a bolted-on logging layer. (Currently beta; project explicitly warns to use simulator/paper accounts.)
- **Memory/state/feedback:** "Issues" carry instructions + a schedule for recurring work; "Tracked" links assets/topics/work products; an "Inbox" aggregates reports, questions, and updates — i.e., project-management primitives repurposed as the agent's working memory and feedback queue.
- **Audit/logging:** Workspaces *are* Git repositories; credentials are sealed at rest under `~/.openalice`.

**Backtest-vs-live parity / leakage:** No explicit backtesting engine or lookahead-prevention mechanism documented — the project's rigor is concentrated on the human-approval-before-execution gate and on the Git-based audit trail, not on statistical validation of signals.

**License / maintenance:** AGPL-3.0. Actively developed (~4,133 commits, ongoing issue/PR activity).

---

## 5. NautilusTrader (nautechsystems/nautilus_trader)

**What it is:** A "production-grade Rust-native engine for multi-asset, multi-venue trading systems," event-driven, designed explicitly so the *same* strategy code runs in backtest, paper, and live.

**Source:** https://github.com/nautechsystems/nautilus_trader

**Architecture / separation of concerns:**
- **Observation/ingestion:** Modular per-venue adapters (WebSocket/REST) normalize everything into one domain model (quote ticks, trade ticks, bars, order-book deltas, custom data), each at nanosecond timestamp resolution.
- **Feature extraction:** User-defined indicators exposed to Python strategies via PyO3 bindings over the Rust core.
- **Research/signal generation & decision-making:** Python "strategies" act as the **control plane** for logic/config/orchestration; the Rust core is the deterministic **event-sequencing kernel**. This split is the architectural core of the whole project.
- **Risk management:** Rich native order semantics used as risk primitives directly (IOC/FOK/GTC/GTD/DAY/AT_THE_OPEN/AT_THE_CLOSE, post-only, reduce-only, iceberg, OCO/OUO/OTO contingency orders) rather than a bolted-on risk layer re-implementing what the exchange already guarantees.
- **Execution:** Deterministic, asynchronous (tokio-based) event-driven execution engine — same engine object for backtest and live, only the data/adapter source changes.
- **Memory/state:** Optional Redis-backed persistence plus an in-memory cache for the message bus.
- **Feedback loop:** Nanosecond-resolution event stream is the same substrate used for both simulation and live monitoring, so live behavior can be compared directly against the simulated expectation.
- **Audit/logging:** Event-sourcing via the internal message bus; reconciliation behavior (matching internal state to venue truth after reconnects/restarts) is tracked as its own concern, separate from strategy logs.

**Backtest-vs-live parity / leakage — the most rigorous of the surveyed projects on this point:** Core design claim, stated directly in docs: *"The same strategy and execution-algorithm code can run across backtest and live systems, reducing deployment divergence."* Crucially, the project does **not** oversell this — it explicitly documents a "Backtest and live differences" section acknowledging *"Live execution still introduces venue, transport, timing, persistence, external-activity, and reconciliation behavior that a simulation may not reproduce."* This combination (share the code path, but document precisely where reality still diverges) is arguably the single most transferable idea in this survey. Determinism of the replay kernel is also the load-bearing anti-lookahead mechanism: strategies never receive data out of timestamp order because the same event kernel enforces ordering in both modes.

**License / maintenance:** LGPL-3.0-only. Very active (~21k+ commits, 29k+ stars, bi-weekly releases).

---

## 6. Freqtrade

**What it is:** A free, open-source Python crypto trading bot with integrated backtesting, hyperparameter optimization, and an adaptive-ML extension (FreqAI).

**Source:** https://github.com/freqtrade/freqtrade

**Architecture / separation of concerns:**
- **Observation/ingestion:** CCXT-based multi-exchange connectivity (Binance, Kraken, OKX, Gate, Bybit, etc.); dedicated `download-data`/`list-data` commands separate historical data acquisition from live operation.
- **Feature extraction:** TA-Lib indicator computation; FreqAI adds self-training adaptive-prediction models as a distinct, optional feature-generation layer on top of raw indicators.
- **Research/signal generation:** User-defined Strategy classes (buy/sell logic); `hyperopt` performs strategy parameter optimization against historical data as a separate offline step from live execution.
- **Decision-making / risk / execution:** Strategy signals plus built-in money-management (position sizing, leverage rules) drive order placement; **dry-run mode** is a first-class, explicitly recommended mode ("Always start by running a trading bot in Dry-Run and do not engage money before you understand how it works").
- **Memory/state:** SQLite persistence for trades/state across restarts.
- **Feedback loop:** Telegram bot (`/status`, `/profit`, `/performance`) and a WebUI dashboard for live monitoring.
- **Audit/logging:** Backtest result inspection tooling (`backtesting-show`, `backtesting-analysis`) kept separate from live logs.

**Backtest-vs-live parity / leakage — notable dedicated tooling:** Freqtrade ships **first-class, named commands specifically for bias detection**: `lookahead-analysis` ("explicitly detects potential forward-looking bias") and `recursive-analysis` ("identifies circular formula issues"). This is the only project surveyed that treats lookahead/leakage detection as a shipped, documented CLI feature rather than a design principle or caveat — worth studying directly for NEXUS's own audit tooling.

**License / maintenance:** GPL-3.0. Very active (~54k stars, ~32,900 commits).

---

## 7. Hummingbot

**What it is:** Open-source framework for building and deploying market-making / high-frequency crypto trading bots across 50+ centralized and decentralized venues.

**Source:** https://github.com/hummingbot/hummingbot

**Architecture / separation of concerns:**
- **Observation/ingestion & execution:** A single connector abstraction normalizes REST/WebSocket across CEX spot/perp, DEX spot/perp, and AMM pools — the same connector interface serves both data-in and orders-out.
- **Decision-making:** Three strategy tiers of increasing reusability: single-file **Scripts**, reusable **Controllers** (V2 strategy framework), and legacy V1 strategies.
- **Risk management:** Reusable **Executors** (position, DCA, grid, arbitrage, XEMM, TWAP) bake risk controls directly into the execution primitive — e.g., the position executor implements "triple-barrier" risk control (take-profit/stop-loss/time-limit) as one atomic unit rather than a separate risk-checking pass.
- **Memory/state:** State lives inside the Controller/Executor objects during a run.
- **Feedback loop / audit:** CLI/dashboard exposes trades, PnL, logs, and status; a "reported volumes" system aggregates trading metrics (originally tied to Hummingbot's liquidity-mining program).

**Backtest-vs-live parity / leakage:** Notable pattern — Controllers are designed to be "backtested, deployed, and tuned live while running" using the *same* controller object, similar in spirit to NautilusTrader's shared-code-path idea but at the strategy-component level rather than the whole engine. No explicit lookahead-bias tooling documented.

**License / maintenance:** Apache 2.0. Active (~20k stars, ~28k commits).

---

## 8. QuantConnect Lean

**What it is:** An event-driven, open-source, professional-grade algorithmic trading engine (C#/Python) with the most explicit, textbook version of pipeline separation surveyed here: the **Algorithm Framework**.

**Source:** https://github.com/QuantConnect/Lean · https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview

**Architecture / separation of concerns — the Algorithm Framework is five named, independently pluggable modules, each with a formal contract:**
1. **Universe Selection** — "a framework module that selects assets for your algorithm," decoupled from everything downstream.
2. **Alpha** — "a framework module that generates trading signals on the assets in your universe," producing `Insight` objects; has no knowledge of portfolio construction.
3. **Portfolio Construction** — "a framework module that determines position size targets based on the `Insight` objects it receives from the Alpha model," producing `PortfolioTarget` objects; independent of risk constraints.
4. **Risk Management** — "a framework module that manages market risks... This model adjusts the `PortfolioTarget` objects it receives from the Portfolio Construction model before they reach the Execution model" — i.e., risk is architecturally a *pure filter/transform* sitting between sizing and execution, never bypassable.
5. **Execution** — "a framework module that places trades to reach the target risk-adjusted portfolio based on the `PortfolioTarget` objects it receives from the Risk Management model" — mechanical order placement only, no strategy logic.

Each stage communicates only through a well-typed object (`Insight` -> `PortfolioTarget` -> adjusted `PortfolioTarget` -> orders), and modules "function independently without relying on other components' internal state" — this is the cleanest documented example of strict interface-based separation in the whole survey.

- **Feature extraction:** A first-class Indicators library, separate from the Algorithm Framework folders.
- **Memory/state:** Configuration and data modules hold algorithm state; brokerage state handled by the Brokerages module.
- **Audit/logging:** Dedicated Logging and Messaging modules, separate from strategy code.

**Backtest-vs-live parity:** Core design goal — the identical algorithm project (same Universe/Alpha/Portfolio/Risk/Execution code) is first backtested locally and then "started live trading locally" via the LEAN CLI with no code change, only a deployment-target switch.

**License / maintenance:** Apache 2.0. Very active (~13,355 commits, 21.7k stars, passing CI/regression pipelines).

---

## 9. TradingAgents (TauricResearch)

**What it is:** A multi-agent LLM trading framework that explicitly mirrors the org chart of a real trading firm, backed by a peer-reviewed paper. Included because it is the clearest example of role-based agent separation directly analogous to NEXUS's pipeline stages, and because its changelog documents real, dated lookahead-bias bugfixes — rare, concrete evidence of the failure mode NEXUS is trying to design around.

**Source:** https://github.com/TauricResearch/TradingAgents · paper: https://arxiv.org/pdf/2412.20138

**Architecture / separation of concerns:**
- **Observation/ingestion (Analyst Team, 4 roles):** Fundamentals Analyst ("evaluates company financials... identifying intrinsic values and potential red flags"), Sentiment Analyst (news/StockTwits/Reddit aggregation), News Analyst (macro/global events), Technical Analyst (MACD/RSI-style pattern detection). Each is a separate agent with a narrow, named mandate — no single agent both gathers data and decides.
- **Research/signal generation (Researcher Team):** Bullish and bearish researcher agents "critically assess the insights provided by the Analyst Team. Through structured debates, they balance potential gains against inherent risks" — an adversarial debate step is used deliberately as a bias-reduction mechanism before a decision is made.
- **Decision-making (Trader agent):** Synthesizes analyst + researcher output into "informed trading decisions, determining the timing and magnitude of trades" — decision-making is a distinct agent role from both research and risk.
- **Risk management & execution:** A Risk Management team continuously evaluates portfolio risk; a Portfolio Manager agent approves/rejects the Trader's proposal before it reaches (simulated) execution — decision and risk approval are two separate agents/checkpoints, not one.
- **Memory/feedback loop:** Persists decisions to a memory file, retrieves realized returns for the same ticker afterward, generates a **reflection**, and injects that reflection back into the Portfolio Manager's prompt on the next decision — an explicit, code-level feedback loop from outcome back into future decision context.
- **Audit/logging:** Built on LangGraph; checkpoints save full state after each graph node (resumable), with optional per-ticker SQLite persistence — the reasoning graph itself is the audit trail.

**Backtest-vs-live parity / leakage:** The changelog is unusually candid and directly useful: v0.4.0 shipped "look-ahead / point-in-time fixes across FRED macro, social sentiment"; v0.3.1 shipped "Alpha Vantage look-ahead filtering." The Market/Technical Analyst is designed to ground "exact price and indicator claims in a verified data snapshot," and company-identity resolution from ticker happens deterministically "before any agent runs" (avoiding an LLM hallucinating which company a ticker refers to as of a historical date). The project also explicitly disclaims profitability: results depend on "backbone language models, model temperature, trading periods, the quality of data, and other non-deterministic factors" and are "not intended as financial, investment, or trading advice" — flagged here as an explicit non-claim, not evidence of edge.

**License / maintenance:** Apache 2.0. Actively maintained (v0.4.0 released Aug 2026, i.e., within the last ~1 month of this review).

---

## Synthesis: Patterns Worth Adopting for NEXUS

These are patterns that recur across **multiple independent projects with no shared codebase or team**, which is what makes them validated-by-convergence rather than one team's house style:

1. **Decision and risk/execution must be separate, non-bypassable stages, connected by typed objects, not shared mutable state.**
   Seen in QuantConnect Lean (`Insight` -> `PortfolioTarget` -> adjusted `PortfolioTarget` -> order, each stage blind to the others' internals), Gordon (Researcher is read-only; only the Executor can place orders, and it "cannot bypass the safety plane"), TradingAgents (Trader proposes, Portfolio Manager/Risk team approves or rejects before execution), and Hummingbot (risk baked into the Executor primitive itself, e.g. triple-barrier). **This is the single most convergent pattern in the survey** — 4 of 9 unrelated projects independently arrived at "risk sits as a mandatory gate between decision and execution, not a check the decision-maker can skip."

2. **Human-approval-before-execution as a first-class mode, not an afterthought.** OpenAlgo's AI Agent pauses every generated order for explicit approval; OpenAlice's "Trading as Git" makes every trade a proposed commit a human must merge; Gordon's `ask` permission mode requires approval per trade; Agentic Trading Lab has an explicit "review-only mode." For LLM/agentic decision components specifically (as opposed to pure quant signal code), this is near-universal among the agentic (non-classic-quant) projects.

3. **Same code path for backtest and live, with divergence points explicitly documented rather than assumed away.** NautilusTrader states this as its core design principle and then documents exactly where parity still breaks (venue/transport/timing/reconciliation behavior a simulator can't reproduce). QuantConnect Lean achieves it by having one algorithm project deployable to either backtest or live via the CLI with no code change. Hummingbot achieves a lighter version of it at the Controller level. The lesson for NEXUS: don't just claim parity — enumerate and document the specific mechanisms (venue latency, partial fills, reconciliation) that a backtest cannot reproduce, the way NautilusTrader does.

4. **Lookahead/leakage prevention is best treated as tooling, not a design assumption.** Freqtrade ships dedicated `lookahead-analysis` and `recursive-analysis` commands as first-class CLI features. TradingAgents' changelog shows concrete, dated point-in-time bugfixes (FRED macro, Alpha Vantage) — i.e., even a well-designed system leaks data in ad-hoc integrations and needs ongoing, named defenses per data source, not one global check. NEXUS's audit/feedback stage should probably include an explicit, nameable leakage-detection pass per data source, mirrored on Freqtrade's approach.

5. **Immutable, structured audit trail as a design primitive, not a log file bolted on later.** Gordon's HMAC-chained decision log (order + risk decision + portfolio snapshot + reasoning trace, chained so entries can't be silently altered) and OpenAlice's "workspace is a Git repo" (every proposed action is a diffable, revertible commit with rationale) both treat the audit trail as a structural, tamper-evident part of the system rather than an appended log stream. TradingAgents' LangGraph checkpointing is a lighter version of the same idea (state after each reasoning node is itself resumable/inspectable).

6. **Deterministic, narrowly-scoped agent/module roles beat one monolithic decision-maker.** TradingAgents (4 analyst roles -> 2 debating researchers -> 1 trader -> risk team), Gordon (orchestrator / researcher / executor), and QuantConnect's 5-stage framework all independently converge on: no single component both gathers evidence, forms a signal, sizes a position, and executes. Each stage has a narrow mandate and a typed handoff to the next.

## Patterns to Avoid / Anti-Patterns

- **Claiming backtest-live parity without naming the exceptions.** Several smaller projects (OpenAlgo, Agentic Trading Lab, OpenAlice) describe "one workflow" spanning backtest to live but do not document *where* that parity actually breaks down. NautilusTrader's approach (claim parity, then explicitly list what still diverges) is the more trustworthy pattern — an unqualified parity claim is itself a yellow flag.
- **Embedding feature extraction inside the decision/agent prompt rather than as an independent, inspectable layer.** Agentic Trading Lab's docs describe feature/signal generation as happening "within the agent decision pipeline" rather than as a separable stage — this makes the feature layer harder to unit-test or audit independently of the LLM's reasoning, unlike e.g. QuantConnect's separate Indicators module or Gordon's typed indicator dispatchers.
- **Treating profitability marketing copy as architectural evidence.** Multiple Gordon/OpenAlice-style project pages use strong marketing language ("frontier trading agent," "one-person Wall Street"). None of the profitability-adjacent claims on these pages are backed by published, reproducible backtest results in the material reviewed — they are noted here only for their architectural ideas (deny-first harness, Trading-as-Git), and any implied edge/profitability claim from these projects should be treated as **unverifiable, no code/paper evidence**, distinct from the architecture itself which is real and inspectable in the repos.
- **One shared database for all state.** Only OpenAlgo explicitly partitions state into six separate stores by concern (main, logs, latency, health, sandbox, historical); most other projects use one database for everything, which risks coupling audit/log writes to the same failure domain as live trading state.

---

## Sources

- Gordon: https://github.com/general-liquidity/gordon
- OpenAlgo: https://github.com/marketcalls/openalgo · https://openalgo.in/
- Agentic Trading Lab (AgenticTrading / FinAgent Orchestration Framework): https://github.com/Open-Finance-Lab/AgenticTrading
- OpenAlice: https://github.com/TraderAlice/OpenAlice
- NautilusTrader: https://github.com/nautechsystems/nautilus_trader
- Freqtrade: https://github.com/freqtrade/freqtrade · https://github.com/freqtrade/freqtrade/blob/develop/LICENSE
- Hummingbot: https://github.com/hummingbot/hummingbot
- QuantConnect Lean: https://github.com/QuantConnect/Lean · https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview
- TradingAgents (TauricResearch): https://github.com/TauricResearch/TradingAgents · paper (arXiv): https://arxiv.org/pdf/2412.20138

Disambiguation notes for future reference:
- "Gordon" also matches unrelated repos in search (`gonome/gordoncli` is a mirror of the same project; other unrelated "Gordon" tools exist outside trading — none were used here).
- "AgenticTrading" as a bare name also matches several unrelated/personal forks (`Allan-Feng/AgenticTrading`, `bhardwajRahul/AgenticTrading`, etc.) and an unrelated Google ADK/A2A demo (`kweinmeister/agentic-trading`); the SecureFinAI Lab / Open-Finance-Lab repo is the one matching the "Agentic Trading Lab" research platform described in the task.
- "OpenAlice" also matches an unrelated/differently-scoped "File-driven AI trading agent engine" fork lineage (e.g. `2233admin/OpenAlice`); `TraderAlice/OpenAlice` is the canonical upstream used here.
