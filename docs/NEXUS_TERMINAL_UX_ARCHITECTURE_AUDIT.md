# NEXUS Quant Research & Market Intelligence Terminal

## Product / UX / UI Architecture Audit

**Requested baseline:** `707a94593e462639c0403e2b992a304b7cf3d316`

**Audited branch:** `main`

**Audited HEAD:** `b9414e601332d341080eac5525684df06ce4c389`

**Audit date:** 2026-09-18

**Scope:** product architecture, information architecture, frontend UX/UI, frontend-to-backend data dependencies, and a safe migration plan.
**Explicit non-scope:** no UI implementation, route/API changes, dependency additions, feature deletion, strategy/execution changes, or MQL5 changes.

---

## Executive conclusion

NEXUS already has three valuable but weakly integrated products inside one shell: an operational EA control surface, a broad backtest/analytics toolkit, and a repository-backed knowledge browser. The research backend has meanwhile moved to a materially better ontology—`MARKET STATE → EVENT → SETUP → TRIGGER → OUTCOME → PROBABILITY → EDGE → STRATEGY`—but the product UI still starts from strategies, pages, and files rather than from research entities and evidence.

The correct next move is not a visual reskin. It is an information-architecture migration to five primary workspaces: **Overview, Market, Research, Execution, Library**. Existing routes should initially remain as compatibility routes and be mounted inside those workspaces through tabs/panels. Settings, licenses, calculator, and calendar should become secondary utilities. AI Coach should evolve from a destination into a contextual side assistant, while retaining its current route during migration.

The largest blocker is data productization, not frontend rendering. Phase 5/5.5/6 already provides versioned JSON schemas and research artifacts for hypotheses, experiments, evidence grades, multiple testing, leakage, datasets, events, outcomes, edge components, and the H006 true-holdout result, but these are not exposed through stable authenticated APIs or a canonical graph/read model. Likewise, the current live API exposes EA-centric regime/structure telemetry, not the same versioned Market State/Event model used by research. A Galaxy can be valuable only after those canonical entities and relations exist; rendering raw files as nodes would create an attractive but epistemically misleading graph.

---

## 1. Current feature inventory

### 1.1 Application shell and cross-cutting capabilities

| Capability | Current implementation | Data/API | Maturity | Utility in terminal | Recommendation |
|---|---|---|---|---|---|
| Routing | `App.js`, React Router under `/app`; 19 explicit routes plus fallback | None | Production | Essential | KEEP routes during migration; add workspace shells later without breaking deep links |
| Authentication | `AuthProvider`; `/auth/me`, `/auth/login`, `/auth/logout`; protected route wrapper | Real session/cookie backend | Production | Essential/private terminal boundary | KEEP; do not couple IA work to auth changes |
| Main shell | `Dashboard.jsx` owns sidebar, header, bottom nav, global drawers, polling and most shared data | Ten polling requests every 5s | Production but over-centralized | Essential | KEEP shell behavior; later split data domains and workspace layouts |
| Sidebar | 18 destinations in 5 groups plus account, theme, bridge state | EA health/status passed from shell | Production | Useful but overloaded | REPLACE presentation incrementally with 5 primary workspaces + Utilities |
| Mobile bottom nav | Home, Coach, Journal, Risk, More | Route navigation | Partial alignment | Monitoring useful | MOVE to Overview, Market, Research status, Execution, More |
| Command palette | Navigation plus EA commands; keyboard shortcut | Uses shell command handler | Production/high-risk controls guarded | High | KEEP; regroup commands by workspace and retain confirmations |
| Theme | Dark-first token system with light mode toggle | Local state | Production | High | KEEP tokens; reduce ambient effects and hardcoded page colors |
| Provenance | `DataProvenanceBadge`: LIVE, RESEARCH, DERIVED, CACHED, DEMO, UNAVAILABLE | Per-page inference | Good foundation | Critical | KEEP and extend to entity/evidence provenance |
| Polling | `useVisiblePolling`; shell 5s, chart 5s, bridge 5s, commands 1.5s, auxiliary widgets | Multiple endpoints | Functional, request-heavy | High | KEEP helper short-term; move to domain queries and event-driven updates later |
| Global strategy drawer | `StrategyHubProvider`, `StrategyDrawer` | Strategy overview, risk manual, coach action | Production | Useful | MERGE into Strategy entity detail + Execution configuration context |
| Global trade drawer | `TradeHubProvider`, `TradeLifecycleDrawer` | Uses trade objects already fetched | Production | High | KEEP; make it the canonical execution lifecycle inspector |
| Setup wizard | License/setup onboarding | License endpoint/local state | Legacy/public-product oriented | Low for private terminal | MOVE to Utilities; DEPRECATE candidate after private deployment review |
| Notifications | Coach notifications and proactive alert widget | Coach endpoints/polling | Partial | Useful if evidence-backed | MOVE to global attention center; distinguish operational alerts from AI suggestions |
| PDF tearsheet | Header download action | `/api/report/tearsheet.pdf` via raw `fetch` | Partial; same-origin bug risk because it bypasses `api.js` | Medium | KEEP feature; route through shared API client in a later implementation phase |

### 1.2 Functional inventory by current destination

| Current destination | Primary component(s) | Functionality | API dependencies | Data availability / truth | Overlap | Maturity | New-paradigm utility |
|---|---|---|---|---|---|---|---|
| Overview | `HomePage`, `HealthScoreCard`, `SystemObservabilityPanel` | Status strip, account KPIs, latest research funnel, market telemetry, positions/actions, research links, system health, commands, equity history, why-no-trade, quick strategy toggles | Shell status/history/settings/health; `/research/certificates/latest`; health/ready/bridge inside observability | Mixed LIVE/CACHED/DERIVED/RESEARCH/DEMO with explicit badges | Risk, Analytics, Strategies, Bridge, Research | Broad but crowded | High; should become exception-oriented four-domain summary |
| Live Chart | `LiveChartPage` | OHLC chart, trade/shadow markers, visual zones, symbol/TF/layers, marker detail | `/chart/ohlc`, `/chart/markers` | OHLC may be synthetic/demo and is labeled; markers depend on ledger/EA visual objects | Overview Market Intelligence, Analytics | Functional; visually isolated and hardcoded light surface | Very high; core of Market workspace |
| Risk | `RiskCenterPage` in `Dashboard.jsx` | Risk budget, drawdown/floating loss/daily target, protection status | Shell `/ea/status`, `/settings`, `/ea/health` | LIVE/CACHED depending EA; missing values mostly explicit | Overview core metrics, Calculator, Optimizer risk config | Functional | High; belongs to Execution workspace and Overview attention state |
| MT5 Bridge | `LocalBridgePage` | Worker/host state, commands to local worker | `/local_bridge/status`, `/local_bridge/enqueue` | Real bridge state, cached/polled | Sidebar bridge card, System Observability, EA controls | Production operational tool | High; Execution/Systems subview |
| Backtest | `BacktestPage` plus seven submodules | Integrity certificates, run, optimizer, management/multi-TF reports, strategy library, CSV analysis, creator/locked profiles | Backtest catalog/run/jobs/library/analysis/profile endpoints; research certificate endpoints | Mixed: real computed jobs, stored libraries, imported CSV, research certificates; some defaults/fallback catalogs | Optimizer route, Strategy Diagnostics, What-if, Analytics, Knowledge | Feature-rich but monolithic (7 tabs) | High; should be split into Research workflow stages, not another mega-page |
| Optimizer | `OptimizerPage` | Live per-strategy leaderboard, adaptive/manual risk multiplier config | `/strategies/leaderboard`, `/strategies/risk_config`, `/strategies/risk_manual` | Operational/derived from live strategy stats and config; not the same as backtest optimizer | Backtest AI Optimize, Strategies, Risk | Functional but naming is misleading | High in Execution as allocation/risk tuning; rename conceptually, preserve route |
| Strategy Diagnostics | `StrategyAnalyticsPage` | Shadow diagnostics, health distribution, blockers, EA trade performance, uploaded strategy stats, metadata and Markdown report | `/analytics/shadow`, `/analytics/strategy_performance`, `/analytics/strategy_meta`, `/analytics/strategy_stats/*`, coach action | Mixed LIVE/CACHED/DERIVED/uploaded; broad provenance | Analytics, Strategies, Backtest Analysis, Journal | High breadth, 1,010-line page, fragmented models | High; divide between Research evidence and Execution diagnostics |
| What-if | `WhatIfPage` | Counterfactual filters and metric deltas | `/analytics/whatif` | Derived from ledger; subject to available trade sample | Analytics, Backtest | Functional | High as Research analysis tool; should attach to a hypothesis/experiment/dataset context |
| Chain | `StrategyChainPage` | Configure chain/cascade bridges and gates | `/strategy_chain/config` GET/PUT | Real mutable execution configuration | Strategies, Settings | Specialized operational tool | Medium/high in Execution advanced configuration; not primary navigation |
| Strategies | `StrategiesPage`, `StrategyDrawer` | Enable/disable live engines, family filters, status and per-strategy detail/risk override | Shell settings; `/strategies/{name}/overview`; coach action; risk manual | Real applied/draft config plus derived stats | Optimizer, Strategy Diagnostics, Backtest Library | Production but conflates executable engines with research knowledge | High if separated into Execution Engines vs Library Strategies |
| Analytics | `AnalyticsPage` | Summary, trades, heatmap, by-reason analysis, risk strip, P&L calendar, correlation placeholder | Shell `/analytics/summary`, `/trades`, `/heatmap`, `/by_reason`, `/calendar`, `/correlation` | DERIVED; correlation currently unavailable rather than fabricated | Overview, Journal, Strategy Diagnostics, What-if | Useful operational analytics | High; split by research vs execution questions |
| AI Coach | `CoachPage` and coach components | Chat, history, quick insights, daily brief, memory, notifications, proposed/apply actions | `/coach/*` | AI-generated with backend context; actions have explicit boundary/confirmation path | Global coach widget, notifications, strategy drawers | Functional but destination-centric | High as contextual assistant; MOVE to side panel, retain full-page history route |
| Knowledge | `KnowledgePage`, safe Markdown renderer | Search/filter repository reports and strategy DB, detail, exact strategy/phase relations | `/knowledge`, `/knowledge/{id}` | CACHED metadata over real versioned Markdown/JSON; not a canonical graph | Journal, Backtest reports, strategy database | Good Phase 4 browser, file-centric | High as Raw Evidence layer; insufficient as canonical Library |
| Journal | `JournalPage` | Trade list, tags/notes/ratings, resync, filters | `/analytics/trades`, `/journal/tags`, `/trades/{ticket}/tag`, `/command` | Real/derived ledger and operator annotations | Analytics, trade drawer, Knowledge | Production | High; Library/Execution record, secondary navigation |
| Calendar | `CalendarPage` | Upcoming macro events and news-filter explanation | `/calendar/upcoming` | Explicit DEMO/generated; not a live economic feed | Overview attention, EA news block | Demo | Medium only after real source; MOVE to Market utility and label unavailable/demo |
| Calculator | `RiskCalculator` | Position sizing and SL/risk calculation using optional EA balance | `/ea/status` | UI-derived calculation; balance live/cached if available | Risk | Mature utility | Medium; MOVE to Utilities or Risk drawer |
| Settings | `SettingsPage` in `Dashboard.jsx` | Settings editor, schema/history, validation, save | Shell settings; `/settings/history`; `/settings` | Real mutable configuration with audit history | Strategies, Chain, Risk configuration | Production/high impact | Essential secondary utility; keep outside primary research IA |
| Licenses | `LicensesPage`, `LicenseBanner` | Create/list/activate/deactivate/delete licenses and view summary | `/license/*` | Real administrative data | Setup wizard | Production but external-product oriented | Low for personal terminal; MOVE to Admin/Utilities, DEPRECATE candidate only after product decision |
| Login | `Login` | Authentication, status-oriented presentation | Auth provider `/auth/login` | Real | Landing | Production | Required; visual language should become sober workstation access |
| Landing | `Landing3D/*` | Public cinematic 3D marketing experience | No terminal data | Decorative/static | Login; Three.js/GPU stack | Mature standalone marketing surface | Low inside private terminal; keep code-split and product-separate |

### 1.3 Backtest destination sub-inventory

The single `/backtest` route currently contains seven products:

1. **Integrity** — certificates, verdict, funnel and gate reasons.
2. **Run** — local/server backtest configuration, metrics and charts.
3. **AI Optimize** — queued grid/parameter optimization and profile promotion.
4. **Management Report** — management and multi-timeframe reports.
5. **Library** — stored strategy/symbol result matrix and locked profiles.
6. **Analisi Reale** — CSV analysis and persisted last analysis.
7. **Creator** — saved setups, per-strategy and multi-TF optimization, profile promotion.

This is the clearest current example of navigation compression creating internal complexity. These tools should survive, but become workflow steps and contextual tools in Research rather than seven peer tabs behind a generic Backtest label.

---

## 2. Current route map

All application routes are under React Router basename `/app`.

| Route | Protected | Current destination | Proposed ownership |
|---|---:|---|---|
| `/` | Conditional root | Overview/Home | Overview |
| `/landing` | No | 3D marketing landing | Public surface, outside terminal |
| `/login` | No | Login | Access surface, outside terminal |
| `/chart` | Yes | Live Chart | Market / Chart |
| `/risk` | Yes | Risk Center | Execution / Risk |
| `/local-bridge` | Yes | MT5 Bridge | Execution / Systems |
| `/backtest` | Yes | Backtest Lab + Integrity | Research / Experiments & Validation |
| `/optimizer` | Yes | Live risk optimizer/leaderboard | Execution / Allocation; not Research optimizer |
| `/strategy-analytics` | Yes | Strategy diagnostics | Split into Research diagnostics and Execution quality |
| `/whatif` | Yes | Counterfactual analytics | Research / Analysis |
| `/chain` | Yes | Strategy chain configuration | Execution / Advanced |
| `/strategies` | Yes | Live engine enablement | Execution / Engines; canonical strategies belong in Library |
| `/analytics` | Yes | Ledger analytics | Execution / Performance, with links from Research where relevant |
| `/coach` | Yes | AI Coach | Contextual assistant + retained full history route |
| `/knowledge` | Yes | Repository Knowledge Browser | Library / Raw Evidence |
| `/journal` | Yes | Trade Journal | Library / Journal and Execution / Trades |
| `/calendar` | Yes | Demo economic calendar | Market / Calendar utility |
| `/risk-calc` | Yes | Risk calculator | Utility / Risk calculator |
| `/settings` | Yes | Settings | Utility / System settings |
| `/licenses` | Yes | License administration | Utility / Administration |
| `*` | No | Redirect to `/` | Shell behavior |

**Migration constraint:** do not rename or remove these routes in the first IA phase. New workspace navigation can point to new parent routes later, while the old routes remain aliases/deep links until telemetry and tests show they are safe to retire.

---

## 3. API and data dependency map

### 3.1 Shared shell request topology

`Dashboard.jsx` issues the following batch every five seconds while visible:

```text
/ea/status                 -> live/cached EA, account, market and position telemetry
/ea/history                -> equity/status history
/settings                  -> operator and EA configuration
/analytics/summary         -> ledger-derived KPIs
/analytics/trades          -> recent trade ledger
/analytics/heatmap         -> derived temporal performance
/analytics/by_reason       -> derived reason aggregation
/analytics/calendar        -> derived P&L calendar
/analytics/correlation     -> currently unavailable/placeholder where no real data exists
/ea/health                 -> derived telemetry-health checks
```

This batch runs on every `Dashboard` section, even when a page needs only a subset. Live Chart bypasses the shell and performs its own polling. System Observability adds health/readiness/bridge polling. Several banners and coach widgets add more independent polls.

### 3.2 Endpoint families and current consumers

| Domain | Existing backend endpoints | Current consumer | Status for target terminal |
|---|---|---|---|
| Auth | `/auth/login`, `/logout`, `/me`, `/stepup` | Auth provider, privileged actions | **Supported now** |
| EA telemetry | `/ea/status`, `/ea/history`, `/ea/health`, EA push/settings/ack/visual objects | Overview, Risk, Sidebar, Chart | **Supported now**, but schema is EA-centric rather than canonical Market State |
| Commands | `/dashboard/command`, `/command/{id}`, EA command contract/ack | Overview, palette, Journal, drawers | **Supported now** with lifecycle and confirmations |
| LocalBridge | status, hosts, heartbeat, poll, enqueue, ack, maintenance, manifest | Bridge page, observability | **Supported now** |
| Settings | settings/state/schema/validate/history; dashboard settings | Settings, Strategies, Backtest, Risk | **Supported now** |
| Strategy runtime | strategies CRUD, leaderboard, overview, risk config/manual, registry/resolve | Strategies, Optimizer, drawers, backtest catalog | **Supported now**, but semantic entity is executable engine/configuration |
| Ledger analytics | trades, summary, heatmap, by_reason, calendar, shadow, strategy performance/meta/stats | Analytics, Journal, Diagnostics, Overview | **Supported now**, derived from ledger/EA uploads |
| Research certificates | list/latest/detail/funnel and bridge ingest | Backtest Integrity, Overview | **Supported now** for run integrity, not hypothesis/edge knowledge |
| Backtest/jobs | run, optimize, creator, reports, library, import/analyze, locked profile, jobs | Backtest modules | **Supported now**, uneven schemas and mixed sync/async flows |
| Knowledge | `/knowledge`, `/knowledge/{id}` | Knowledge Browser | **Supported now** for file/strategy metadata and lazy content |
| Chart | `/chart/ohlc`, `/chart/markers`, EA visual objects | Live Chart | **Supported now**, with synthetic fallback explicitly marked |
| Journal | tags and trade tagging | Journal | **Supported now** |
| Calendar | `/calendar/upcoming`, `/calendar` | Calendar | **Demo/generated**, not operational market intelligence |
| Coach | chat/history/memory/brief/insights/alerts/actions/notifications | Coach page, widget, bell | **Supported now**, page context is ad hoc/local rather than canonical entity context |
| Licenses/admin | license CRUD/summary/events; retention/backup/audit | Licenses, banners; some admin endpoints unused by UI | **Supported now**, secondary/private-terminal relevance |
| Phase 5 Market State | Versioned scripts, schemas and local artifacts | No frontend consumer | **Data/artifacts exist; no product API** |
| Event Registry | Schema and research build pipeline | No frontend consumer | **Schema/artifacts exist; no product API** |
| Hypothesis Registry | `phase5_5/hypothesis_registry_v1.json` | No frontend consumer; may appear only as raw Knowledge file if indexed | **Structured source exists; no stable API/UI** |
| Experiment Registry | `phase5_5/experiment_registry_v1.json` | No frontend consumer | **Structured source exists; no stable API/UI** |
| Evidence/multiple testing/leakage/holdout | Phase 5.5 and Phase 6 JSON and Markdown artifacts | No dedicated UI | **Structured source exists; H006 holdout is `BORDERLINE` and remains E2; no stable API/UI** |
| Edge components | Schemas/records and Phase 5 results | No dedicated UI | **Artifacts exist; canonical read model/API missing** |
| Knowledge graph | Entity/relation schemas are documented | None | **Not implemented as a graph store/read model** |
| Live intelligence stream | No SSE/WebSocket product endpoint | None | **Missing** |

### 3.3 Data reality boundary

The target product must preserve four different truths:

- **Operational truth:** live/cached EA, bridge, positions, commands, fills and ledger.
- **Research truth:** immutable/versioned datasets, experiments, hypotheses, outcomes and evidence grades.
- **Knowledge truth:** canonical entities and claims derived from research, with provenance and contradictions.
- **Document truth:** raw reports and notes, useful as evidence but not equivalent to validated knowledge.

The current UI handles operational provenance reasonably well, but mostly collapses the last three into “Research” or a list of files. The new architecture must never promote a Markdown conclusion or a promising metric directly into canonical edge status.

---

## 4. UX pain points

### 4.1 Information architecture

1. **Eighteen sidebar destinations have equal navigational weight.** The user must remember implementation boundaries rather than follow a research or operational workflow.
2. **Strategy is overloaded.** It means executable EA switch, backtest candidate, analytics row, strategy-database record, and sometimes a setup/event bundle.
3. **Backtest is a mega-page.** Seven internal tools represent different lifecycle stages but are exposed as tabs under one technical noun.
4. **Research and execution are interleaved.** The live risk optimizer lives under Research, while strategy diagnostics combines research evidence, uploaded artifacts and real execution performance.
5. **Knowledge is file-first.** Search is useful, but reports, negative tests, canonical strategies and architecture documents appear in one flat evidence stream.
6. **Overview is comprehensive rather than decisive.** It contains system status, six KPIs, research funnel, market intelligence, positions, research links, observability, health, commands, equity, why-no-trade and strategy toggles.

### 4.2 Data and interaction architecture

1. **Shell over-fetching:** ten endpoints every five seconds on almost every dashboard route.
2. **Duplicate polling:** bridge, health, coach, notifications, license and chart operate independently.
3. **Mixed ownership:** `Dashboard.jsx` is an 819-line shell containing settings and risk pages plus data orchestration and command execution.
4. **Local joins:** pages combine unrelated payloads client-side without a domain read model.
5. **Context loss:** moving from a certificate to a report, strategy, experiment or trade does not preserve a canonical selected entity.
6. **No URL-addressable substate:** Backtest tabs and many detail drawers are local state, limiting deep links and explainable workflows.
7. **Research artifacts are not queryable entities:** versioned JSON exists, but only general file metadata is indexed.

### 4.3 Visual system

1. The token foundation, Inter/JetBrains Mono pairing and tabular numbers are reusable.
2. Ambient radial glows, grid/noise, glass blur, hover lift, glowing active rails and multiple pulse effects produce a “cockpit/cyber” tone rather than an institutional workstation.
3. Cards are the default container for nearly every concept, flattening hierarchy into many equivalent boxes.
4. Semantic color exists but decorative gold/sky/purple effects compete with status meaning.
5. `LiveChartPage` is a fixed, hardcoded white full-screen surface and visually breaks dark mode and the shared shell.
6. Remote Google Font imports add an external runtime dependency and possible privacy/offline inconsistency.
7. Several large pages use very small uppercase labels and dense cards while other pages use large marketing-style headers; density is inconsistent.
8. Animation classes run broadly; motion should be reserved for state changes, loading, alerts and real event activity.

### 4.4 Mobile

1. The current bottom nav prioritizes Coach and Journal over Market and Research status.
2. Full feature access relies on opening the large sidebar through “More”.
3. Wide diagnostics/backtest tables depend on horizontal scroll rather than mobile-specific summaries.
4. Live Chart works as a dedicated full-screen view but lacks the future interpreted-state stack.
5. A graph/Galaxy cannot simply shrink; it requires a list/neighborhood alternative.

---

## 5. Features to KEEP

- Auth/session/CSRF boundaries and protected routes.
- EA status, positions, commands, confirmations and command lifecycle polling.
- LocalBridge status and host/command tooling.
- Trade lifecycle drawer and Journal annotations.
- Lightweight Charts implementation and real marker/visual overlays.
- Research certificate integrity funnel and verdict handling.
- Backtest engines, job model, strategy library, imports and reports.
- Data provenance badge and missing-value discipline.
- System observability and readiness indicators.
- Strategy registry/contracts as identifiers for executable engines.
- Knowledge Browser as the **Raw Evidence** browser.
- Theme tokens, dark/light support, Inter for UI and JetBrains Mono/tabular figures.
- Command palette as a professional keyboard-first affordance.
- Safe Markdown rendering without arbitrary HTML.
- Phase 5/5.5/6 registries, schemas, evidence grading, true-holdout results and methodological artifacts as source material for future canonical APIs.

---

## 6. Features to MERGE

| Consolidation | Existing features | Result |
|---|---|---|
| Market workspace | Live Chart + Overview Market Intelligence + Calendar + chart markers/visuals | One interpreted market surface with chart, state and event timeline |
| Research workspace | Backtest tabs + What-if + research portions of Strategy Diagnostics + research certificates | Hypothesis/experiment-centered workflow |
| Execution workspace | Strategies runtime controls + live Optimizer + Risk + Bridge + positions + execution portions of Diagnostics + Chain | One operational workspace from signal to fill and risk |
| Performance view | Analytics + Journal trade list + real trade performance | Shared execution/performance read model; Journal remains annotation mode |
| System status | Sidebar bridge card + Overview observability + health card | One compact global status/attention surface with drill-down |
| Strategy details | Strategy drawer + Strategy Analytics rows + strategy DB detail + backtest library row | One entity inspector with separate Research Evidence and Runtime Configuration tabs |
| Alerts | Notification bell + proactive coach widget + risk/bridge attention states | One evidence-backed attention center |

Merge means shared workspace and entity context, not deleting underlying components or endpoints.

---

## 7. Features to MOVE

- **AI Coach:** from primary page to right-side contextual assistant; keep `/coach` for full conversation history and memory management.
- **Calendar:** into Market as a secondary calendar panel; it remains visibly DEMO until a real feed exists.
- **Risk Calculator:** into Execution/Risk as a drawer or utility.
- **Settings, Licenses:** into a Utilities/Admin menu.
- **Strategy Chain:** into Execution/Advanced.
- **Live Optimizer:** from Research to Execution/Allocation because it changes runtime risk multipliers.
- **Strategy toggles:** from Intelligence to Execution/Engines.
- **Knowledge file browser:** into Library/Raw Evidence.
- **Journal:** accessible from both Execution/Trades and Library/Journal, backed by one view.
- **Landing:** remain a separate public/marketing surface; do not let its visual system dictate the terminal.

---

## 8. Features to DEPRECATE candidates

No code should be removed in the next phase. Candidates require usage and product-owner confirmation:

1. **Public 3D landing inside the same deployment** — retain if external acquisition still matters; otherwise isolate from the private terminal build.
2. **Setup wizard and license marketing prompts** — likely irrelevant for a single-user private workstation.
3. **Standalone `/optimizer` label** — preserve route but deprecate the name; it is runtime risk allocation, not hypothesis optimization.
4. **Standalone AI Coach primary navigation item** — deprecate only after the contextual assistant reaches feature parity.
5. **Flat “Knowledge” file list as the top-level knowledge model** — retain as Raw Evidence, deprecate only its role as the canonical library.
6. **Demo economic calendar as an operational feature** — keep clearly labeled for layout/testing; do not surface as trusted intelligence.
7. **Duplicate legacy dashboard endpoints** (`/api/dashboard/*`) where the frontend uses newer domain endpoints — inventory consumers before any backend deprecation.

---

## 9. Missing product capabilities

### P0 — required before the new Research/Library experience is truthful

- Canonical authenticated read APIs for hypotheses, experiments, datasets, evidence, edge components and decision cards.
- Explicit evidence-grade computation/read model, including the reason a grade is capped.
- Stable identifiers and links across certificate `run_id`, experiment, hypothesis, dataset, code build and raw artifacts.
- Canonical entity/relation store or materialized graph read model.
- Contradiction/refutation representation; negative tests must remain first-class evidence.
- Market State and Event APIs aligned with the Phase 5 schema rather than only EA presentation fields.

### P1 — required for professional workspaces

- Research queue/status model: planned, running, blocked, completed, invalidated.
- Experiment compare view with baseline, DeltaP, DeltaE, intervals, multiple-testing and leakage checks.
- Signal-to-fill/execution quality read model linking signals, orders, fills, positions and exits.
- Attention model that ranks exceptions across Market, Research, Execution and Risk.
- Context contract for the AI assistant: route, selected entity, visible dataset, filters and permissions.
- URL-addressable workspace subviews and selected entity IDs.

### P2 — enables the Galaxy and live intelligence

- Graph query endpoint with bounded neighborhood expansion.
- Explain Path endpoint returning an ordered, evidence-backed path—not a frontend-inferred narrative.
- Append-only product event stream via SSE or WebSocket.
- Event retention/replay cursor and client reconnection semantics.
- Aggregated graph layout hints and evidence weights; raw files remain evidence leaves, not primary nodes.

---

## 10. Proposed navigation

### Primary navigation

```text
NEXUS
├── Overview
├── Market
│   ├── State & Chart
│   ├── Events & Timeline
│   └── Calendar (secondary; DEMO until real)
├── Research
│   ├── Hypotheses
│   ├── Experiments
│   ├── Edge Discovery
│   ├── Validation
│   └── Tools (Backtest, What-if, Reports)
├── Execution
│   ├── Live
│   ├── Engines
│   ├── Signal-to-Fill
│   ├── Risk
│   └── MT5 / Bridge
└── Library
    ├── Canonical Knowledge
    ├── Market Ideas
    ├── Events & Setups
    ├── Edge Components
    ├── Strategies
    ├── Failure Memory
    ├── Raw Evidence
    └── Journal

Utilities
├── Calculator
├── Settings
├── Licenses / Admin
├── System status
└── Command palette
```

### Corrections to the proposed target

1. Put **Risk** inside Execution but surface its status in Overview; it is not an independent product domain.
2. Put **Calendar** under Market utilities, not Library; the current implementation is demo and must not receive primary weight.
3. Distinguish **Execution Engines** from canonical **Strategies**. The former are mutable EA configurations; the latter are knowledge entities with evidence lineage.
4. Add **Validation** explicitly under Research because E0–E6 progression is a product workflow, not merely a backtest output.
5. Keep **System status** globally visible but not as a sixth primary workspace.

---

## 11. Proposed Overview

The Overview should answer four questions in one screen: What is NEXUS doing? What changed? What needs attention? Can the system act safely?

```text
┌──────────────────────────────────────────────────────────────────────┐
│ NEXUS · XAUUSD · LONDON · data 4s ago       [System READY] [⌘K] [AI]│
├─────────────────┬─────────────────┬─────────────────┬────────────────┤
│ MARKET          │ RESEARCH        │ EXECUTION       │ RISK           │
│ State: Trend ↑  │ H006 · E2       │ EA LIVE         │ Within limits  │
│ Vol: Expanding  │ Holdout BORDER. │ 1 open position │ DD 2.1 / 8.0%  │
│ 2 new events    │ Next: E3        │ Bridge LIVE     │ No active block│
├─────────────────┴─────────────────┴─────────────────┴────────────────┤
│ ATTENTION                                                             │
│ ! H006 remains E2: borderline holdout, CI overlap, side asymmetry    │
│ ! Event calendar is DEMO                                              │
├───────────────────────────────────────┬───────────────────────────────┤
│ Recent real activity                  │ Current context               │
│ 10:41 EVENT_DETECTED · RECLAIM        │ Market → Event → H006        │
│ 10:38 EVIDENCE_UPDATED · H006         │ [Open Explain Path]          │
└───────────────────────────────────────┴───────────────────────────────┘
```

Rules:

- Four domain summaries, not twenty equivalent widgets.
- Show exceptions before historical charts.
- Latest activity must be backend events or explicitly unavailable—never animation-as-status.
- Account KPIs remain accessible in Execution, with only the most decision-relevant risk metric on Overview.
- Every research status includes evidence grade and next blocking condition.

**Already supported:** EA/bridge/risk/positions, latest research certificate, health/readiness.

**New endpoints/data:** active hypothesis/experiment, canonical Market State, attention aggregation, product activity stream.
**UI-only:** four-domain layout, progressive disclosure, workspace deep links.

---

## 12. Proposed Market workspace

```text
┌──────────────────────────────────────────────────────────────────────┐
│ MARKET · XAUUSD · H4       [State] [Events] [Timeline] [Calendar]    │
├─────────────────────────────────────────────┬────────────────────────┤
│                                             │ CURRENT MARKET STATE   │
│                PRICE CHART                  │ Regime       TRENDING  │
│      event markers + causal state bands     │ Volatility   EXPANDING │
│                                             │ Dir. eff.    0.61      │
│                                             │ Momentum     POSITIVE  │
│                                             │ Location     UPPER 30% │
│                                             │ Structure    HH/HL      │
├─────────────────────────────────────────────┴────────────────────────┤
│ EVENT TIMELINE                                                       │
│ 08:00 SWEEP_LOW  →  12:00 RECLAIM  →  setup candidate               │
│ [detector v1] [observation point] [causal provenance] [inspect]      │
└──────────────────────────────────────────────────────────────────────┘
```

Design principles:

- The chart is evidence context, not the entire product.
- Show a compact interpreted Market State Vector with version and observation timestamp.
- Limit default state dimensions to regime, volatility, directional efficiency, momentum, location and structure.
- Events are discrete and causal; outcomes must never leak into event labels.
- The timeline connects state transitions and events; indicators are available only on demand.
- Use the current `lightweight-charts` foundation; do not introduce WebGL for the chart.

**Already supported:** OHLC, trade/shadow markers, visual zones, EA regime/structure/reaction fields.

**New endpoint/data:** versioned current/historical Market State, Event Registry query, detector/provenance metadata, state-transition timeline.
**UI-only:** split chart/state layout, timeline, layer controls and saved views.

---

## 13. Proposed Research workspace

The primary object is a **Hypothesis or Edge Component**, not a strategy and not a backtest file.

```text
┌──────────────────────────────────────────────────────────────────────┐
│ RESEARCH / H006 — LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT               │
│ Status: BORDERLINE           Evidence: E2 INTERNAL_VALIDATION        │
├───────────────────────────┬──────────────────────────────────────────┤
│ HYPOTHESIS                │ EVIDENCE LADDER                          │
│ Claim                     │ E0 ● Observation                         │
│ Dataset + version         │ E1 ● Discovery                           │
│ Observation point         │ E2 ● Internal validation  ← current      │
│ Primary outcome           │ E3 ○ True holdout        ← not attained  │
│ Frozen assumptions        │ E4 ○ Cross-source                        │
│                           │ E5 ○ Execution validated                 │
│                           │ E6 ○ Forward/demo                        │
├───────────────────────────┴──────────────────────────────────────────┤
│ RESULT                                                              │
│ n       Baseline P    Event P    DeltaP    DeltaE    CI / posterior │
│ 115     available     available  +0.0572   +0.277    CI overlap     │
├──────────────────────────────────────┬───────────────────────────────┤
│ INTEGRITY                            │ FAILURE / BLOCKERS             │
│ Multiple testing: prior BH pass      │ Materiality threshold not met  │
│ Holdout: temporally untouched        │ Bootstrap CI includes zero     │
│ Reproducibility: pass                │ BUY/SELL consistency failed    │
├──────────────────────────────────────┴───────────────────────────────┤
│ [Explain Path] [Open experiment] [Raw evidence] [Compare baseline]   │
└──────────────────────────────────────────────────────────────────────┘
```

### Research object model

- **Hypothesis Registry:** claim, prior status, preregistration, dataset, outcome, allowed subgroups and stop condition.
- **Experiment:** immutable run specification, code/data versions, split, assumptions and artifacts.
- **Evidence:** result tied to hypothesis + experiment + dataset; supports or refutes.
- **Evidence Grade:** computed/capped by explicit requirements and blockers.
- **Edge Component:** promoted only when policy permits; remains distinct from Strategy.
- **Decision Card:** concise synthesis with unsupported assumptions visible.

### Workflow

```text
IDEA → REGISTERED → DISCOVERY → INTERNAL VALIDATION → TRUE HOLDOUT
     → CROSS-SOURCE → EXECUTION VALIDATION → FORWARD/DEMO
```

Backtest, What-if, optimizer and analysis become tools launched with the active hypothesis/dataset context. A run created without an active hypothesis may still exist, but is labeled exploratory and cannot silently advance evidence grade.

**Already supported:** Phase 5.5 registries and evidence ladder artifacts; Phase 6 H006 true-holdout artifacts (`BORDERLINE`, retained at E2); certificates/funnels; backtest jobs; What-if; reports.

**New endpoint/data:** hypothesis/experiment/evidence APIs, policy-driven grade/read model, comparison and blocker fields, immutable links to datasets/builds.
**UI-only:** ladder component, research header, result/integrity panels, contextual tool launcher.

---

## 14. Proposed Execution workspace

```text
┌──────────────────────────────────────────────────────────────────────┐
│ EXECUTION · EA LIVE · MT5 CONNECTED · XAUUSD                         │
│ [Live] [Engines] [Signal-to-Fill] [Risk] [Bridge] [Advanced]        │
├─────────────────────┬────────────────────────────────────────────────┤
│ POSITIONS           │ SIGNAL → GATE → ORDER → FILL → POSITION → EXIT│
│ #123 BUY 0.10       │   ✓       ✓       ✓      ✓        LIVE         │
│ P&L +$…             │ latency · slippage · reject/gate reason        │
├─────────────────────┴────────────────────────────────────────────────┤
│ RISK / PROTECTIONS                                                  │
│ Daily DD · Total DD · exposure · slots · ESL/DPT/Ruin               │
├──────────────────────────────────────┬───────────────────────────────┤
│ ENGINE CONFIGURATION                 │ SYSTEM                         │
│ enabled, applied/draft, allocation   │ Bridge, worker, command queue  │
└──────────────────────────────────────┴───────────────────────────────┘
```

Execution must preserve three layers:

1. **Intent:** setup/trigger/signal and the research entity that justified it.
2. **Decision:** gates, policy, operator or EA action.
3. **Broker reality:** order attempt, rejection, fill, position lifecycle and exit.

**Already supported:** EA/bridge state, positions, risk, commands, strategies, strategy chain, some lifecycle IDs and certificate funnel.

**Partial:** trade lifecycle and shadow diagnostics; current Research funnel must not be presented as live execution.

**New endpoint/data:** canonical signal-to-fill events, latency/slippage, rejection taxonomy and joins back to setup/hypothesis/build.
**UI-only:** workspace composition, tabs, compact lifecycle visualization.

---

## 15. Proposed Library

### Three layers

```text
RAW EVIDENCE                  DISTILLED KNOWLEDGE              CANONICAL GRAPH
reports                       decision cards                  Market State
backtests                     summaries                       Event
failed tests        ───────▶  findings             ───────▶   Setup
datasets                      failure patterns                Hypothesis
logs/artifacts                evidence assessments            Edge Component
notes                         conflicts                       Strategy
                                                             Experiment/Dataset
```

### Library views

- **Canonical Knowledge:** entities with status, evidence grade and latest decision.
- **Market Ideas:** proposed but not necessarily tested claims.
- **Events & Setups:** detector definitions and reusable market situations.
- **Edge Components:** supported, refuted, pending and execution-constrained components.
- **Strategies:** compositions of validated components plus execution/risk policy.
- **Failure Memory:** negative evidence, invalid assumptions, parity failures and operational failure patterns.
- **Raw Evidence:** the existing Knowledge Browser.
- **Journal:** operator annotations and trade observations.

Negative research remains visible but typed as `REFUTES`, `FAILURE_PATTERN`, `INVALIDATED_EXPERIMENT` or `INSUFFICIENT_EVIDENCE`. It must not have the same visual authority as an E5 edge.

**Already supported:** repository Markdown/JSON browser, strategy DB, evidence/failure documents and Phase 5 schemas.

**New endpoint/data:** normalized entities, relations, status policy, entity search and evidence rollups.
**UI-only:** layered navigation, entity cards, raw/canonical switch and relation-aware related content.

---

## 16. Knowledge Graph architecture

### Canonical entities

`MarketState`, `Event`, `Setup`, `Trigger`, `Hypothesis`, `EdgeComponent`, `Strategy`, `Experiment`, `Dataset`, `Evidence`, `FailurePattern`.

### Canonical relations

`SUPPORTS`, `REFUTES`, `TESTS`, `DERIVED_FROM`, `VALIDATED_BY`, `DEPENDS_ON`, `CONFLICTS_WITH`, `USES`.

### Required properties

Every entity and edge should carry:

- stable ID and schema version;
- label/type/status;
- source provenance and source IDs;
- created/observed timestamps;
- evidence grade where applicable;
- data/code version;
- confidence or relationship policy where meaningful;
- explicit `null` for unavailable fields;
- links to raw artifacts without embedding filesystem paths.

### Recommended storage path

Start with a **materialized graph read model in SQLite/PostgreSQL**, not a graph database. The current scale is small, relations are explicit, and operational simplicity matters. Use normalized entity and relation tables plus JSON metadata. Add a graph database only if multi-hop query volume/complexity proves relational recursive queries inadequate.

```text
Versioned research JSON/Markdown
            │ ingest/validate
            ▼
Canonical entity tables ── relation tables ── evidence links
            │
            ├── list/search/detail API
            ├── bounded neighborhood API
            └── Explain Path API
```

The ingestion process must be deterministic, schema-validated, idempotent and auditable. A source document is linked evidence; it is not automatically promoted to an entity or claim.

---

## 17. Intelligence Galaxy feasibility

### Product verdict

**Feasible, but only after the canonical graph exists.** It should be an alternate exploration mode inside Library, not the default navigation or the source of truth.

### Technology comparison

| Option | Strengths | Risks | Recommendation |
|---|---|---|---|
| Cytoscape.js | Mature 2D graph model, filtering, compound nodes, layouts, accessibility easier than WebGL-only, deterministic interaction | Large bundles/layout cost at high node counts; custom aesthetics require work | **Preferred first implementation** for evidence exploration and Explain Path |
| react-force-graph-2d | Quick force-directed exploration, Canvas performance, React integration | Less semantic layout control; accessibility and precise inspection need parallel DOM UI | Viable prototype after canonical API |
| react-force-graph-3d / Three.js | Strong spatial spectacle, existing Three.js dependency | Navigation, occlusion, labels, motion sickness, mobile/GPU cost, accessibility, harder deterministic screenshots/tests | Do not use as primary; optional desktop experiment only |
| Custom Three.js | Maximum visual control | Highest maintenance and interaction cost; duplicates graph/layout/accessibility work | Not justified |
| SVG/D3 | Excellent control and accessibility for bounded graphs | DOM performance degrades with many nodes/edges | Good for Explain Path and small neighborhoods, not whole corpus |

### Recommended interaction model

- Default to 2D semantic graph with a synchronized accessible list/detail panel.
- Load a bounded initial neighborhood, not the entire corpus.
- Node size = count/weight of linked evidence, capped and logarithmically scaled.
- Halo = evidence grade, with explicit legend; no halo for entities without a grade.
- Color = entity family only; status uses shape/border/icon to avoid color overload.
- Edge thickness = relationship confidence only when such a measure is explicitly stored; otherwise constant.
- Search/focus, isolate neighborhood, type/grade/thread filters and evidence inspection are required.
- “Rotate” is not needed in 2D. If a 3D mode is later tested, it remains desktop-only and optional.

### Performance and accessibility constraints

- Server-side filtering and neighborhood pagination.
- Render labels only for focused/important nodes.
- Web Worker for layout above an agreed threshold.
- Keyboard traversal through the synchronized entity list.
- Textual equivalent for graph relations and Explain Path.
- Reduced-motion mode disables animated layout and pulses.
- Mobile uses list + mini-neighborhood, not a squeezed Galaxy.

---

## 18. Live event-stream architecture

### Transport recommendation

Use **Server-Sent Events first** for server-to-browser intelligence activity. The UI already uses authenticated same-origin HTTP and most requested activity is unidirectional. SSE is simpler to operate, reconnects naturally and works through standard HTTP infrastructure. Keep command mutations on existing authenticated REST endpoints. Move to WebSocket only if bidirectional low-latency collaboration or high-frequency streaming becomes a demonstrated need.

### Proposed event envelope

```json
{
  "event_id": "evt_01...",
  "sequence": 18422,
  "timestamp": "2026-09-18T10:41:22.481Z",
  "event_type": "EVIDENCE_UPDATED",
  "source_entity": {"type": "Experiment", "id": "EXP-P5-005"},
  "target_entity": {"type": "Hypothesis", "id": "H006"},
  "experiment_id": "EXP-P5-005",
  "run_id": "run_...",
  "provenance": "RESEARCH",
  "metadata": {
    "evidence_grade_before": "E1",
    "evidence_grade_after": "E2"
  }
}
```

Allowed initial event types:

- `DATASET_READ`
- `FEATURE_COMPUTED`
- `EVENT_DETECTED`
- `BASELINE_MATCHED`
- `HYPOTHESIS_TESTED`
- `EVIDENCE_UPDATED`
- `MT5_SIGNAL`
- `ORDER_SENT`
- `FILL_RECEIVED`

### Integrity rules

- Events are append-only and carry a monotonic sequence per stream.
- The client reconnects with `Last-Event-ID`/cursor and can request bounded replay.
- Heartbeats indicate connection health but never appear as research activity.
- An animation is emitted only for a stored backend event.
- The stream never represents hidden chain-of-thought or “AI thinking”.
- Sensitive metadata is filtered by event type and authorization.
- The Galaxy remains static when no event exists.

**Backend requirement:** new event ledger/read model and `/api/intelligence/events` SSE endpoint. Existing polling cannot truthfully synthesize this stream.

---

## 19. Explain Path design

Explain Path is a backend-supported evidence trace, not a visual animation inferred from filenames.

### Example

```text
EC-LIQUIDITY_SWEEP_RECLAIM
  └─ DERIVED_FROM → SWEEP + RECLAIM detectors v1
      └─ TESTS → EXP-P5-005 / Phase 5
          ├─ COMPARED_WITH → matched baseline v1
          ├─ SUPPORTS → DeltaP / DeltaE result
          ├─ VALIDATED_BY → multiple-testing BH pass
          ├─ CONFLICTS_WITH → Phase 5 validation contamination
          └─ TESTED_BY → H006 Phase 6 untouched temporal holdout
                    ├─ RESULT → DeltaP +0.0572; CI overlap
                    ├─ CONFLICTS_WITH → BUY/SELL consistency
                    └─ VERDICT → BORDERLINE; E2 retained
                              ↓
                    Evidence grade capped at E2
```

### UI behavior

- Select entity and target claim/grade.
- Backend returns ordered path nodes, relation types, evidence references and a human-readable reason code per step.
- UI highlights the path in graph and renders the same sequence as an accessible vertical evidence trail.
- Each step opens the underlying experiment, result or raw evidence.
- Conflicting/refuting paths are visible alongside supporting paths.
- The final grade explanation states both achieved requirements and unmet caps.

### Proposed read contract

```text
GET /api/knowledge/entities/{id}/explain?claim=evidence_grade
→ subject, conclusion, achieved_grade, capped_by[], paths[], evidence_refs[]
```

The initial implementation can support evidence-grade explanations only; general path search can follow later.

---

## 20. AI Assistant integration

### Target behavior

- Persistent right-side assistant on desktop; bottom sheet/full-screen panel on mobile.
- Context includes current route/workspace, selected canonical entity, selected experiment/run, active filters and visible evidence IDs.
- Suggested questions are generated from entity type and known blockers.
- Responses cite entity/evidence IDs and open relevant panels.
- Any proposed mutation remains a draft action through the existing guarded action boundary.

```text
┌──────────── workspace ─────────────┬──── contextual assistant ────┐
│ H006 · E2                          │ Context: H006 / EXP-P5-005   │
│ evidence and blockers              │ Why is this E2?              │
│                                    │ • true holdout not clean ... │
│                                    │ [Open evidence] [Explain]    │
└────────────────────────────────────┴──────────────────────────────┘
```

### Existing support

- Chat/history/memory/brief/insights and read-only action boundary exist.
- Chart writes a limited context object to local storage.

### Required changes later

- Formal page-context contract rather than ad hoc local storage.
- Retrieval by canonical entity/evidence ID.
- Citation payload and UI affordances.
- Permission-aware action proposals.
- Preserve `/coach` as full conversation/history workspace until the side assistant is complete.

---

## 21. Desktop and mobile behavior

### Desktop workstation

- Persistent compact primary rail; workspace-level tabs across the content header.
- Resizable main/inspector/assistant panels where density warrants it.
- Keyboard navigation, command palette and entity quick-open.
- Tables use sticky headers, column visibility and density controls rather than many cards.
- Details open in a consistent inspector, not a unique modal/drawer implementation per page.
- Minimum decorative chrome; borders and type establish hierarchy.

### Laptop

- Inspector and assistant are mutually collapsible.
- Workspace tabs may horizontally scroll, but primary content must not.
- Four-domain Overview becomes a 2×2 grid.

### Mobile

- Primary actions: Overview, Market, Research, Execution, More.
- Overview is attention-first; detailed analytics are summaries with drill-down.
- Market defaults to chart/state tabs rather than side-by-side layout.
- Research shows experiment status, grade, blockers and result summary; complex matrices scroll within bounded containers.
- Execution shows EA/bridge/risk and positions; destructive actions retain step-up/confirmation.
- Library uses search/list/detail navigation.
- Galaxy becomes search + entity list + one-hop neighborhood; no forced 3D.
- Assistant is a bottom sheet with current-context label.

---

## 22. Migration sequence in small safe phases

### Phase 0 — contracts and terminology, no visual redesign

- Freeze canonical vocabulary and IDs from Phase 5/5.5/6.
- Document the distinction between executable engine, setup, edge component and strategy.
- Define workspace route strategy while preserving every current route.
- Add data-contract fixtures and null/provenance tests.

### Phase 1 — navigation shell and visual restraint

- Introduce five primary workspace navigation items.
- Keep old pages mounted as workspace subviews and preserve direct URLs.
- Move utilities into a secondary menu.
- Remove decorative glow/blur/ambient grid incrementally through tokens.
- Normalize Live Chart into dark/light shared shell.

### Phase 2 — Overview and domain read models

- Build the four-domain Overview from existing endpoints first.
- Add a backend attention/readiness aggregation only where client composition is insufficient.
- Split shell polling by domain and route visibility.
- No graph yet.

### Phase 3 — Research entities

- Add read-only APIs for hypotheses, experiments, datasets, evidence and decision cards.
- Build Hypothesis/Experiment list-detail workspace and Evidence Ladder.
- Attach existing certificate, backtest, What-if and report tools contextually.
- Link raw artifacts without promoting them automatically.

### Phase 4 — Market and Execution workspaces

- Productize versioned Market State/Event read models.
- Merge chart/state/event timeline.
- Consolidate runtime strategies, allocation, risk, bridge and diagnostics into Execution.
- Add signal-to-fill schema/read API before showing live funnel counts.

### Phase 5 — Library canonical model

- Implement deterministic ingestion into entity/relation/evidence tables.
- Add canonical Library views, failure memory and relation-aware search.
- Keep existing Knowledge Browser as Raw Evidence.
- Add Explain Path for evidence grade.

### Phase 6 — Galaxy and live activity

- Prototype bounded 2D graph with Cytoscape.js or equivalent after graph API stability.
- Validate accessibility, mobile fallback and performance with real graph sizes.
- Add SSE event stream and only then enable real activity pulses.
- Consider optional 3D only if user testing demonstrates analytical value over 2D.

### Phase 7 — contextual AI and compatibility cleanup

- Add formal assistant context/citations and side panel.
- Retain full Coach route during rollout.
- Measure old-route usage and remove/deprecate only through a separate approved task.

---

## 23. Recommended visual system direction

### Reuse

- Current semantic CSS variables and light/dark themes.
- Inter UI type and JetBrains Mono/tabular numerics.
- Radix primitives, Tailwind tokens, accessibility focus ring.
- Existing success/warning/destructive semantics.
- Compact provenance badges and sober data tables.

### Change later

- Replace glass cards with mostly opaque surfaces.
- Reduce global radius from “soft dashboard” to a smaller workstation radius.
- Remove ambient body grid/noise and most background radial glows.
- Remove generic hover lift and decorative shadows.
- Reserve pulses for real live/attention state and respect reduced motion.
- Use one accent color for selection; semantic colors only for status/outcome.
- Prefer section rules, split panes and tables over nested card grids.
- Standardize page title, toolbar, tabs, inspector and empty/error states.
- Make data density selectable where tables are central.

---

## 24. Backend support matrix for the proposed product

| Capability | Existing backend | New endpoint | New source data | UI-only |
|---|---:|---:|---:|---:|
| Four-domain Overview | Partial | Optional aggregation | Active hypothesis/attention needed | Yes |
| Market chart | Yes | No | No | Yes |
| Canonical Market State | Research artifacts only | Yes | Runtime/state history needed | No |
| Event timeline | Research artifacts/EA visuals partial | Yes | Canonical event registry/history needed | No |
| Hypothesis workspace | JSON registry and Phase 6 holdout artifacts exist | Yes | No for historical Phase 5.5/6; future ingest needed | Yes |
| Experiment workspace | JSON registry exists | Yes | Future job lifecycle integration | Yes |
| Evidence Ladder | Rules/artifacts exist | Yes/read model | Grade policy and blockers must be canonical | Yes |
| Backtest/validation tools | Yes | Mostly no | No | Recomposition |
| Execution live/risk/bridge | Yes | Mostly no | No | Recomposition |
| Signal-to-fill quality | Partial telemetry | Yes | IDs, timestamps, reject/fill detail needed | No |
| Raw Evidence browser | Yes | No | No | Existing |
| Canonical Library | No | Yes | Ingestion/read model | Yes |
| Knowledge graph | No | Yes | Canonical entities/relations | Yes |
| Explain Path | No | Yes | Reason codes/grade caps | Yes |
| Live Galaxy pulses | No | SSE/WebSocket | Append-only event ledger | Yes |
| Contextual AI | Partial | Context/retrieval extensions | Entity links/citations | Yes |

---

## 25. Blockers and decisions required

1. **Canonical source of truth:** decide whether Phase 5/5.5/6 JSON remains generated source input or is ingested into the application database as immutable versions.
2. **Identifier governance:** align strategy registry IDs, hypothesis IDs, experiment IDs, edge component IDs, certificate `run_id` and live signal/order IDs.
3. **Market State parity:** decide how research Market State and live EA state are versioned and compared without pretending they are identical today.
4. **Execution telemetry:** the requested signal-to-fill view cannot be completed truthfully until all lifecycle stages and timestamps are emitted and joined.
5. **Graph promotion policy:** define who/what can promote raw evidence into canonical entities and evidence grades.
6. **Real-time transport:** confirm Render/proxy operational constraints and retention requirements before selecting SSE implementation details.
7. **Calendar source:** keep DEMO or fund/integrate a real source; do not visually upgrade it into apparent live intelligence.
8. **Private vs commercial product:** decide whether licensing, setup wizard and public landing remain inside the same information architecture.
9. **Bundle/performance budget:** the authenticated app already includes large analytical/UI dependencies; any graph library needs a lazy-loaded budget and real-node benchmark.

---

## 26. Final recommendation

Adopt the five-workspace IA, but sequence it behind a thin canonical research API. The first implementation should be deliberately unglamorous: navigation consolidation, a four-domain Overview, and read-only Hypothesis/Experiment/Evidence views backed by Phase 5.5/6 registries and artifacts. Do not build the Galaxy first. Build the knowledge model, Explain Path contract and event integrity first; then use a bounded, accessible 2D graph as an alternate lens. This preserves every existing operational feature while changing the product’s center of gravity from “EA dashboard” to “research and market-intelligence terminal.”
