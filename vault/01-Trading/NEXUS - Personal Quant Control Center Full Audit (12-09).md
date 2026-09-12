---
status: active
tags: [trading, nexus, frontend, backend, audit, personal-quant-control-center, research-lab, data-provenance]
date: 2026-09-12
scope: web-only
baseline_commit: 0a7f94cc7383a4813fa54e748b7a7625a26f156f
---

# NEXUS — Personal Quant Control Center Full Audit (12-09)

> Audit statico completo del frontend e backend web. Baseline: `main` @ `0a7f94cc7383a4813fa54e748b7a7625a26f156f`. Nessun codice applicativo, route, contratto API o file MQL5 è stato modificato.

## A. Executive Summary

1. NEXUS possiede già un control plane privato credibile: sessione cookie, CSRF, comandi target-scoped con lease/ACK, stato EA, rischio, ledger e diagnostica.
2. L'architettura web è un monolite FastAPI + SQLite e una SPA React/CRA; è riusabile senza rewrite, ma `Dashboard.jsx` centralizza troppo fetching e composizione.
3. Il dato live principale arriva dai push EA e dal ledger; WR, PF, analytics e leaderboard sono derivati, non osservati direttamente.
4. Il Live Chart non è live: l'OHLC è sempre sintetico; solo i marker dei trade derivano dal ledger.
5. La correlazione è sempre demo/vuota; molti stati vuoti sono correttamente marcati `demo`, ma alcune UI trasformano assenza in `0`, riducendo la chiarezza.
6. Il nuovo funnel quantitativo `GENERATED → ... → BROKER_REJECT` esiste in note/log di ricerca, non nello storage o nelle API web.
7. Il Research Lab ha motori, job, manifest, risultati JSON/CSV e validazione MT5 già riusabili, ma manca un modello unico di esperimento/hypothesis/validity.
8. Il vault è un asset maturo (224 note trading pre-audit su 271 Markdown totali), con strategy notes, audit, decisioni, failure memory e metodologia, ma non è indicizzato dal backend.
9. CI, readiness e deployment manifest esistono, ma non sono aggregati nella UI e il backend non espone commit/branch/build/deploy corrente.
10. Sicurezza buona per un pannello personale, con gap: frontend senza step-up UI e alcune mutation protette solo da `require_user` invece di `require_mutation`.
11. La suite backend non è verde: 206 test passati, 1 skipped, 7 falliti per drift registry/adapter e checksum manifest.
12. Performance: il dashboard polla 10 endpoint ogni 5 secondi; solo Landing3D è lazy-loaded; main bundle ~362 kB gzip.
13. Mobile shell è valida, ma tabelle research/analytics, chart, widget Coach e form densi richiedono viste compatte dedicate.
14. Capacità attuale complessiva: **51/100**; obiettivo realistico senza rewrite: **85/100**.
15. Strategia consigliata: consolidare verità/provenienza e osservabilità prima del redesign visuale, poi introdurre Research Lab e Knowledge Browser incrementalmente.

## Metodo, perimetro e classificazioni

- Ispezionati: `frontend/src`, contratti frontend, CSS/Tailwind/package, `server/app.py`, moduli backtest/analytics/jobs/policy/validation/retention/security/command contract, CI, Render, manifest, `vault`, `knowledge`, `results`, JSON/CSV.
- Escluso intenzionalmente: modifica o redesign MQL5; i riferimenti al motore servono solo a valutare il confine web.
- **REAL LIVE DATA**: osservazione recente inviata da EA/bridge o evento terminale persistito.
- **DERIVED DATA**: calcolo riproducibile su dati osservati/persistiti.
- **CACHED DATA**: snapshot/proiezione persistita, potenzialmente stale.
- **DEMO DATA**: risposta vuota o dimostrativa esplicitamente marcata demo.
- **MOCK DATA**: contenuto hardcoded solo UI/test.
- **FALLBACK DATA**: sostituto usato quando la fonte primaria non è disponibile.
- **UNKNOWN SOURCE**: provenienza non abbastanza esplicita per una rappresentazione “reale”.

## B. Architecture Map

```text
Browser /app (React 18 + CRA + Tailwind + Radix)
  ├─ AuthProvider ── axios withCredentials + CSRF header
  ├─ BrowserRouter basename=/app
  ├─ Dashboard shell
  │   ├─ Sidebar / BottomNav / CommandPalette / PageHeader
  │   ├─ global polling: 10 GET ogni 5s quando tab visibile
  │   ├─ StrategyHub drawer / TradeHub drawer
  │   └─ route section components
  └─ LiveChartPage separata
          │ HTTPS /api/*
          ▼
FastAPI app (server/app.py, versione 5.4.0-security-remediation)
  ├─ sessione JWT in cookie httpOnly + CSRF + origin allow-list
  ├─ EA/LocalBridge machine auth: X-Nexus-Token
  ├─ control plane: commands, settings, risk, licenses
  ├─ data plane: EA status, status history, trade/event ledger
  ├─ analytics: ledger_analytics + aggregazioni sincrone
  ├─ research: backtest.py + sweep.py + JobRunner
  ├─ AI Coach: Anthropic API + SQLite kv/memory
  └─ SQLite /data/nexus.db + file JSON/CSV/repo Markdown
```

### Frontend architecture

| Area | Implementazione attuale | Valutazione |
|---|---|---|
| Routing | `App.js`, `BrowserRouter basename="/app"`, 18 route incluse landing/login/root e wildcard | Chiaro; solo Landing3D lazy |
| Auth | `AuthProvider`, `/auth/me`, `/auth/login`, `/auth/logout`; route protette via `Protected` | Buona base privata |
| Layout shell | `Dashboard.jsx`: header, sidebar, bottom nav, banners, palette, widget, drawers | Riusabile ma troppo centralizzato |
| Sidebar | 5 gruppi Control/Research/Intelligence/Knowledge/System; 17 route | IA transitoria, route preservabili |
| Bottom nav | Home, Coach, Journal, Risk, More; mobile only | Funzionale, non allineata al target research-first |
| Command palette | navigazione + azioni EA; Ctrl/Cmd+K | Utile; catalogo route incompleto (chart/bridge/chain assenti) e conferme locali duplicate dal backend |
| State | `useState` locale + Context per auth/theme/drawers; React Query installato ma non usato | Sufficiente ora, inefficiente per cache/request dedupe |
| Polling | `useVisiblePolling`: stop su tab hidden, in-flight guard | Buona primitiva; fetch globale eccessivo |
| API client | Axios base URL, cookie, CSRF interceptor, redirect 401, formatter errori | Solido; error handling non uniforme nelle pagine |
| Error handling | `Promise.allSettled` globale + banner risorse parziali; molte pagine hanno `try/catch` locali | Parziale; alcuni catch convertono errori in demo/empty |
| Theme | dark default, light toggle, token HSL, Inter + JetBrains Mono | Già vicino al quant terminal |
| Responsive | sidebar drawer/swipe, bottom nav, grid breakpoints, overflow tabelle | Shell buona; contenuti densi solo adattati, non riprogettati |

### Route → page → component → endpoint → source dati

| Route | Page/section | Componenti principali | Endpoint consumati | Origine |
|---|---|---|---|---|
| `/` | Overview | `Dashboard` → `HomePage`, `HealthScoreCard` | `/ea/status`, `/ea/history`, `/settings`, `/ea/health`; comandi/settings | EA push current-state; KV equity history/settings; ledger-derived PF health |
| `/chart` | Live Chart | `LiveChartPage` | `/chart/ohlc`, `/chart/markers` | **OHLC sintetico**; marker dal ledger |
| `/risk` | Risk | `Dashboard` → `RiskCenterPage` | global `/ea/status`, `/settings`, `/ea/health` | EA telemetry + settings KV + derived health |
| `/local-bridge` | MT5 Bridge | `LocalBridgePage` | `/local_bridge/status`, `/local_bridge/enqueue` | SQLite `bridge_hosts`, `bridge_commands` |
| `/backtest` | Backtest suite | `Backtest` + Run/Optimizer/Reports/Library/Real Analysis/Creator | `/backtest/*`, `/jobs/*` indirettamente/alias | Dukascopy/Yahoo/Stooq con fallback synthetic; SQLite jobs; KV/library/seeds/import |
| `/optimizer` | Live Optimizer | `OptimizerPage` | `/strategies/leaderboard`, risk config/manual | ledger-derived strategy metrics + KV risk config |
| `/strategy-analytics` | Strategy Analytics | `StrategyAnalyticsPage` | strategy stats latest/symbols/markdown/upload, `/analytics/shadow`, `/analytics/strategy_performance`, meta | EA stats snapshots; shadow table; ledger-derived performance; manual upload |
| `/whatif` | What-if | `WhatIfPage` | global summary/by_reason + POST `/analytics/whatif` | counterfactual derived from ledger |
| `/chain` | Chain | `StrategyChainPage` | GET/PUT `/strategy_chain/config` | KV settings/config |
| `/strategies` | Strategies | `StrategiesPage`, shared `StrategyDrawer` | global settings/status; drawer overview + mutations | settings/registry + ledger-derived overview |
| `/analytics` | Analytics | `AnalyticsPage`, trade drawer | summary/trades/heatmap/by_reason/calendar/correlation | ledger-derived; correlation always demo |
| `/coach` | AI Coach | `Coach`, `MessageList`, memory panel | history, insights, daily brief, chat, memory, notifications, apply action | ledger/status-derived prompt + Anthropic; KV/SQLite memory |
| `/journal` | Journal | `JournalPage` | `/analytics/trades`, `/journal/tags`, trade tag, deprecated `/command` resync | ledger + journal_meta; command queue |
| `/calendar` | Calendar | `CalendarPage` | `/calendar/upcoming` alias | backend hardcoded/synthetic calendar payload |
| `/risk-calc` | Risk Calculator | `RiskCalc` | `/ea/status` once | EA balance/symbol, calculations local derived |
| `/settings` | Settings | inline `SettingsPage` | global `/settings`; `/settings/history`; POST `/settings` | KV settings/history |
| `/licenses` | Licenses | `LicensesPage` | license list/create/update/delete; global license summary banner | SQLite licenses/events |
| `/login` | Login | `Login` | `/auth/login` | credential check; ticker è mock visuale |
| `/landing` | Public landing | lazy `Landing3D` | nessuno | contenuto statico/3D |
| `*` | Fallback | `Navigate` | nessuno | redirect `/` |

## C. Current Capability Matrix

| Capability | Score | Stato | Evidenza sintetica |
|---|---:|---|---|
| Control Center | 68 | PARTIAL | Stato, comandi, rischio, settings e bridge esistono; manca selector esplicito multi-instance e audit operativo integrato |
| Live Trading | 58 | PARTIAL | Telemetria/posizioni reali, ma chart prezzo sintetico e nessuno stream/event timeline completo |
| Research | 63 | PARTIAL | Motore, optimizer, library, CSV analysis, jobs e corpus ampio; modello esperimento frammentato |
| Quant Integrity | 35 | PARTIAL | Ledger/provenance e validity tooling esistono; funnel decisionale non entra nel web; test registry rossi |
| Strategy Intelligence | 54 | PARTIAL | Leaderboard, stats, shadow e diagnostics; assenti matrix unificata e memoria causale |
| Learning | 32 | PARTIAL | Coach/memory e artefatti knowledge; nessun learning engine versionato/closed-loop |
| Knowledge/Vault | 18 | MISSING UI | Corpus ricchissimo, zero index/API/browser frontend |
| System Observability | 46 | PARTIAL | `/health`, `/ready`, bridge status, manifest; niente GitHub/CI/Render/data-feed panel |
| Security | 67 | PARTIAL | Buon hardening backend; step-up non cablato in UI e mutation auth incoerente |
| Mobile | 57 | PARTIAL | Shell e nav valide; research/chart/tabelle/dialog densi |
| UX | 61 | PARTIAL | Dark cockpit, metric mono e colori; troppe card/glow e gerarchia data truth non uniforme |
| **Totale semplice** | **51/100** | **PARTIAL** | Base robusta, integrazione e verità UI ancora incomplete |

## D. Data Truth Matrix

### KPI e pannelli principali

| UI field/panel | Classe | Endpoint | Backend function | Storage/source originale | Nota di verità |
|---|---|---|---|---|---|
| Balance, equity | REAL LIVE DATA se `online=true`; CACHED se offline | `/ea/status` | `ea_status_dash` → `_primary_ea` | ultimo payload `ea_status`, scritto da `/ea/push` | Auto-dichiarato dall'EA; primary scelto implicitamente |
| Floating P&L, daily P&L | REAL LIVE/CACHED | `/ea/status` | idem | payload EA | Non broker-independent |
| Drawdown % | REAL LIVE/CACHED | `/ea/status` | idem | campo EA | Definizione dipende dal producer EA |
| Positions | REAL LIVE/CACHED | `/ea/status` | idem | array payload EA | Non ricostruite dal ledger |
| Trades today, streak | REAL LIVE/CACHED | `/ea/status` | idem | payload EA | Stato runtime EA |
| Regime/session/HTF/velocity | REAL LIVE/CACHED | `/ea/status` | idem | payload EA | Classificazioni prodotte dal motore |
| Structure, BOS, CHOCH, swings | REAL LIVE/CACHED | `/ea/status` | idem | payload EA | UI non mostra definizione/versione algoritmo |
| Reaction, active levels | REAL LIVE/CACHED | `/ea/status` | idem | payload EA | Stato corrente; nessuna history strutturata web |
| Equity chart | CACHED DATA | `/ea/history` | `ea_history` | KV `equity_history`, max 300 punti | Cache append da push; perdita semantica su restart/retention |
| WR, PF, P&L storico | DERIVED DATA | `/analytics/summary` | `analytics_summary` | eventi terminali via `ledger_analytics.authoritative_trades` | Valido solo rispetto a copertura/provenienza ledger |
| Strategy stats live | REAL LIVE/CACHED | `/analytics/strategy_stats/latest` | `_all_strategy_stats` | `strategy_stats`, push EA o upload manuale | Fonte `ea_push` e upload possono convivere; badge fonte necessario |
| Strategy performance/leaderboard | DERIVED DATA | `/analytics/strategy_performance`, `/strategies/leaderboard` | aggregazioni ledger | trade events + balance corrente | DD% usa balance corrente; non una curva capitalizzata storica completa |
| Heatmap/calendar/reasons | DERIVED DATA | `/analytics/heatmap`, `/calendar`, `/by_reason` | aggregazioni sincrone | ledger | Empty viene marcato demo |
| Correlation | DEMO DATA | `/analytics/correlation` | risposta costante | nessuna | Sempre `matrix: []`, `demo: true` |
| Health/bridge state | DERIVED + REAL LIVE | `/ea/health` | `_compute_ea_health` | telemetry EA + PF ledger | Score di telemetria, non garanzia di sicurezza; policy versionata |
| Live chart candles | DEMO/MOCK DATA | `/chart/ohlc` | `chart_ohlc` | generatore matematico hardcoded | **Sempre sintetico**, non deve chiamarsi live market data |
| Live chart trade markers | DERIVED DATA | `/chart/markers` | `chart_markers` | ledger terminale | `demo=true` se vuoto, ma vuoto non significa necessariamente demo |
| Calendar macro | FALLBACK/DEMO DATA | `/calendar`/`upcoming` | `calendar` | eventi sintetici backend | Test impongono label/provenienza demo |
| Backtest results | DERIVED/SIMULATED; possibile FALLBACK | `/backtest/run` e suite | `backtest.run_backtest` | Dukascopy/Yahoo/Stooq; fallback synthetic | `data_source` va reso prominente su ogni risultato |
| Strategy library | MIXED/UNKNOWN senza badge per riga | `/backtest/strategy_library` | `_library_rows` | recipe seed → sweep KV → import KV | Priorità sorgenti implicita; serve provenance row-level |
| Optimizer jobs | DERIVED/SIMULATED + CACHED | `/backtest/optimize*`, `/jobs/*` | JobRunner/backtest | SQLite `compute_jobs`, manifest JSON | Buona base, UI non espone manifest/hash/build in modo uniforme |
| What-if | DERIVED DATA | `/analytics/whatif` | filtro/ricalcolo | ledger | Controfattuale descrittivo, non causalità |
| Coach reply | DERIVED AI OUTPUT | `/coach/chat` | Anthropic call | prompt da status/analytics + session KV | Non dato osservato; provider può essere non configurato |
| Coach insights/brief | DERIVED DATA | quick insights/daily brief | regole backend | status + analytics + health | Alcuni errori vengono ignorati per comporre output parziale |
| Login ticker | MOCK DATA | nessuno | frontend | array hardcoded | Solo decorazione, commentato esplicitamente |

### Regole UI consigliate per la verità

- Ogni card deve mostrare `LIVE`, `CACHED`, `DERIVED`, `SIMULATED`, `SYNTHETIC`, `IMPORTED` o `UNKNOWN` vicino al valore, non solo a livello pagina.
- `0` non deve sostituire `null/no data`; usare `—` e spiegazione.
- Mostrare `observed_at`, age/staleness, account/symbol/magic e source instance.
- Per backtest/library: source dataset, finestra, engine version, params hash, RAW/RECIPE e validity certificate obbligatori.
- Vietare semanticamente “Live Chart” finché candles=`SYNTHETIC_DATA`; mantenere route, cambiare in futuro label/stato o fonte.

## Inventario pagine e decisione

| Pagina | Scopo/dati | Utilità target | Decisione | Demo/mock/fallback |
|---|---|---|---|---|
| Overview | Mission control EA, KPI, market/structure/reaction, posizioni, health, gate “why no trade” | Alta | Mantenere e rifocalizzare | banner demo quando offline; valori possono diventare zero |
| Live Chart | OHLC + marker/visual context | Alta solo con feed reale | Mantenere route; sostituire sorgente in fase futura | OHLC sempre synthetic |
| Risk | Limiti, protezioni, health | Alta | Mantenere; fondere con policy/apply state | Derivato da telemetry/settings |
| MT5 Bridge | Host/worker status e azioni | Alta | Mantenere sotto System/Control | Reale SQLite, se worker connesso |
| Calendar | Eventi macro | Media | Fondere in Live Trading/Overview o deprecare pagina autonoma | Synthetic demo |
| Strategies | Enable/disable registry | Alta | Evolvere in Strategy Matrix | Registry drift attuale |
| Optimizer | Risk scaling live per strategia | Media/alta | Separare da Experiment Queue; mantenere funzione | Empty demo; metriche derived |
| Strategy Analytics | Funnel EA stats, shadow, performance, CSV upload | Alta | Fondere nel Research Lab/Strategy Matrix | Fonti miste EA/upload/ledger |
| Backtest | Suite research completa | Molto alta | Mantenere, spezzare in Research Lab views | Possibile synthetic fallback |
| Chain | Config relazioni e smart reverse | Media | Mantenere come advanced setting/experiment | KV config, non demo |
| Analytics | Ledger KPIs, heatmap, calendar, reasons, correlation | Alta | Mantenere; separare truth/empty | Correlation demo |
| Journal | Annotazione trade | Alta | Fondere con Strategy/Failure Memory links | Ledger reale; resync usa alias deprecated |
| What-if | Esclusioni controfattuali | Media | Mantenere come experiment tool | Derived, no causal claim |
| AI Coach | Chat, brief, memory, azioni | Media | Rinominare Learning Engine solo dopo governance | AI derived; provider optional |
| Risk Calculator | Sizing locale | Alta | Mantenere utility | Balance live opzionale, resto derived local |
| Settings | Parametri e history | Alta | Mantenere; mostra desired vs applied | UI non usa `/settings/state` |
| Licenses | Vendita/distribuzione EA | Bassa nel pannello personale | Separare in Admin/Commercial, futura deprecazione dal core IA | Reale DB |
| Login | Accesso privato | Essenziale | Mantenere e semplificare | Ticker mock visuale |
| Landing | Marketing pubblico 3D | Bassa/negativa per pannello privato | Separare dal prodotto privato | Statico/decorativo |
| Setup Wizard | Onboarding profilo/licenza | Bassa nel personal center | Separare da first-run operativo personale | Flusso commerciale |

## Backend API Audit

Il censimento statico rileva **152 decorator di route** in `server/app.py` (inclusi metodi multipli/alias sulla stessa funzione e le route SPA). Le tabelle seguenti coprono l'intero spazio per famiglia, separando consumer web, machine API, admin/ops, alias e route non consumate; per il redesign è più utile mantenere il gruppo canonico che ripetere 152 righe quasi identiche.

### Endpoint consumati dal frontend corrente

| Endpoint | Metodo | Auth | Source | Consumer | Stato |
|---|---|---|---|---|---|
| `/api/auth/login`, `/logout`, `/me` | POST/POST/GET | credential/session | config + revocation KV | AuthProvider/Login | PRODUCTION |
| `/api/ea/status`, `/ea/history`, `/ea/health` | GET | user | EA snapshot/KV/ledger | shell, Overview, Risk, Calc | PRODUCTION/PARTIAL |
| `/api/dashboard/command`, `/command/{id}` | POST/GET | mutation/user | command queue/events | Dashboard/palette | PRODUCTION |
| `/api/command` | POST | mutation | alias queue | Journal resync | DEPRECATED |
| `/api/settings`, `/settings/history` | GET/POST | user/mutation | KV | Settings/shell/backtest | PRODUCTION |
| `/api/strategies/leaderboard`, `/risk_config`, `/risk_manual`, `/{name}/overview` | GET/POST | user/mutation | ledger + KV | Optimizer/drawer | PRODUCTION/PARTIAL |
| `/api/analytics/trades`, `/summary`, `/by_reason`, `/calendar`, `/heatmap` | GET | user | ledger scan | Dashboard/Analytics/Journal | PRODUCTION |
| `/api/analytics/correlation` | GET | user | none | Analytics | DEMO |
| `/api/analytics/whatif` | POST | user only | ledger scan | What-if | PARTIAL (read-compute POST, no CSRF) |
| `/api/analytics/shadow` | GET | user | shadow_trades | Strategy Analytics | PARTIAL |
| `/api/analytics/strategy_performance` | GET | user | ledger | Strategy Analytics | PRODUCTION |
| `/api/analytics/strategy_stats/*` | GET/POST | user | strategy_stats/manual upload | Strategy Analytics | PARTIAL |
| `/api/journal/tags`, `/trades/{ticket}/tag` | GET/POST | user/mutation | journal_meta | Journal | PRODUCTION |
| `/api/chart/ohlc`, `/chart/markers` | GET | user | synthetic/ledger | Live Chart | DEMO/PARTIAL |
| `/api/calendar/upcoming` | GET | user | alias synthetic calendar | Calendar | DEMO |
| `/api/local_bridge/status`, `/enqueue` | GET/POST | user/mutation | bridge tables | MT5 Bridge | PRODUCTION |
| `/api/strategy_chain/config` | GET/PUT | user/mutation | KV | Chain | PRODUCTION |
| `/api/license/*`, `/license/summary` | mixed | user/mutation | licenses/events | Licenses/banner | PRODUCTION, commercial |
| `/api/coach/chat`, history, insights, brief, memory, notifications | mixed | user/mutation | Anthropic + KV/tables | Coach/widgets | PARTIAL |
| `/api/coach/apply_action` | POST | mutation | command/settings | Coach/drawer | DEPRECATED |
| `/api/backtest/symbols|strategies|presets` | GET | user | registry/static config | Backtest | PRODUCTION |
| `/api/backtest/run`, creator, reports | POST/GET | user | backtest engine/datasets | Backtest tabs | PARTIAL |
| `/api/backtest/optimize*`, `/strategy_library/build`, job aliases | POST/GET | mixed | compute_jobs + engine | Backtest | PRODUCTION/PARTIAL |
| `/api/backtest/strategy_library`, analyze CSV/live diagnostic, locked profile | mixed | user/mutation | seed/KV/import/ledger/stats | Backtest | PARTIAL |

### Endpoint backend non mostrati o sottoutilizzati

| Gruppo endpoint | Potenziale | Stato |
|---|---|---|
| `/api/ready`, `/health`, `/dukascopy_status`, `/dukascopy_snapshot` | Backend/data-feed health | PRODUCTION, non consumato dalla SPA |
| `/api/settings/state`, `/settings/schema`, `/settings/validate` | desired vs applied e contract-driven forms | PRODUCTION, quasi unused |
| `/api/ea/command_contract` | conferme/effects server-driven | PRODUCTION, frontend mantiene duplicato locale |
| `/api/audit/operator` | audit trail azioni | PRODUCTION, non mostrato |
| `/api/admin/retention`, backup/drill | operabilità DB | PRODUCTION, non mostrato |
| `/api/jobs`, `/jobs/{id}`, cancel | Experiment Queue | PRODUCTION, nessuna pagina generale |
| `/api/meta/deprecations` | tech debt machine-readable | PRODUCTION, non mostrato |
| `/api/local_bridge/deployment_manifest`, hosts, maintenance | build/worker governance | PRODUCTION, parzialmente nascosto |
| `/api/downloads/*` | distribuzione worker/EA | PRODUCTION, commerciale/ops |
| `/api/analytics/journal_verdict`, `/strategy_diagnostic_live` | validity/strategy evidence | PRODUCTION, accesso solo dentro sub-tab |
| `/api/dashboard/*` legacy aggregate family | vecchia dashboard API | UNUSED/PARTIAL rispetto alla SPA nuova |

### Endpoint machine-facing

| Endpoint | Auth | Source/effect | Stato |
|---|---|---|---|
| `/api/ea/push` | bridge token | upsert current + append status history | PRODUCTION |
| `/api/ea/command`, `/ack` | bridge token | lease/ACK broker outcome | PRODUCTION |
| `/api/ea/settings`, `/settings/ack` | bridge token | desired/applied settings | PRODUCTION |
| `/api/ea/trade_history_sync`, `/trade_reason` | bridge token | trades + event ledger/reasons | PRODUCTION/PARTIAL provenance |
| `/api/ea/strategy_stats`, `/shadow_trades`, `/visual_objects` | bridge token | current projections/tables | PRODUCTION/PARTIAL history |
| `/api/local_bridge/heartbeat`, poll, ack | bridge token/enrollment | bridge status/queue | PRODUCTION |
| `/api/license/verify`, `/notify/telegram` | bridge token | license/notification | PRODUCTION/commercial |

### Duplicazioni, mismatch e costo API

- Comandi: `/dashboard/command` canonico; `/ea/command [POST]`, `/command` e `coach/apply_action` sono alias deprecati dichiarati.
- Registry: `/strategies/registry` e `/strategy-registry` sono alias equivalenti.
- Calendar: `/calendar` e `/calendar/upcoming` alias.
- Dashboard legacy: `/dashboard/overview|journal|strategy_stats|shadow_trades|trade_reasons|notifications|settings|locked_profiles` duplica molte API specialistiche e non è usata dal frontend attuale.
- Il poll globale ogni 5s esegue 10 chiamate anche su pagine che non ne usano gran parte: ~120 richieste/minuto/tab visibile.
- Analytics esegue scansioni sincrone fino a `ANALYTICS_MAX_ROWS=5000` ripetute in endpoint separati; summary, heatmap, reasons, calendar, PF health ricalcolano popolazioni sovrapposte.
- `Promise.allSettled` evita failure totale, ma non deduplica tra Dashboard, widget Coach, LicenseBanner e pagine con polling autonomo.
- Il frontend non usa React Query pur avendolo tra le dipendenze.

## E. Missing Pieces (priorità)

### P0 — verità, integrità e sicurezza

1. Ingestion/storage/API del decision funnel con identità canoniche e vincoli di riconciliazione.
2. Correggere drift registry/adapter/test e checksum deployment manifest: oggi la CI locale è rossa.
3. Rendere impossibile presentare OHLC sintetico come “Live”.
4. Provenance e freshness per-card, con `null` distinto da zero/demo.
5. Collegare step-up frontend e uniformare tutte le mutation a `require_mutation`/CSRF.
6. Selector esplicito account/symbol/magic; evitare primary EA implicito in presenza di più istanze.

### P1 — Research Control Plane

1. Entità canonica Experiment/Run/Hypothesis/Validity/Artifact.
2. Experiment Queue basata su `compute_jobs`, con manifest, progress, cancel e output.
3. Research Lab che unisca backtest, optimizer, strategy stats, validity e corpus `results/knowledge`.
4. Certificato validità machine-readable collegato a run/build/dataset.
5. Strategy Matrix e failure memory per strategia.

### P2 — Knowledge e observability

1. Markdown index read-only per vault/docs con path allow-list, tag, links e search.
2. Endpoint `/api/system/info` aggregato: commit, branch, app/build, deploy, readiness, feed.
3. GitHub Actions/Render status tramite metadata build/deploy server-side senza token al browser.
4. Timeline operativa status/commands/events/notes.

### P3 — UX/performance/mobile

1. Route-level code splitting per le pagine pesanti.
2. Query cache/deduping e polling per dominio/visibilità/route.
3. Tabelle virtualizzate/responsive row-detail.
4. Riduzione card decorative/glow; densità terminale e status bar stabile.

## F. Recommended IA

Route attuali possono essere mantenute durante la migrazione; le label/aggregazioni cambiano senza big bang.

```text
CONTROL
  Overview
  Live Trading        -> route attuale /chart, dopo fonte reale
  Risk
  MT5 Bridge

RESEARCH
  Research Lab        -> hub che incorpora /backtest
  Experiment Queue    -> nuova vista su /jobs
  Backtests           -> tab/route esistente
  Test Validity       -> CSV + live diagnostic + certificate
  Hypothesis Tracker  -> vault/knowledge + run links

INTELLIGENCE
  Strategy Matrix     -> /strategies + /optimizer + perf
  Market Structure    -> structure/reaction history
  Learning Engine     -> Coach read-only + insights
  Strategy Memory     -> evidence/timeline per strategy
  Failure Memory      -> vault + structured issues

KNOWLEDGE
  Vault
  Research Notes
  Reports
  Findings

SYSTEM
  Backend Health
  MT5 Health
  Build & Deploy
  Data Feed Health
  Settings
  Advanced / Commercial (Licenses, downloads)
```

## G. Recommended Home Dashboard

1. **Persistent status bar**: environment, account, symbol, magic, EA build, backend build, commit, data age, bridge/feed state.
2. **Control strip**: balance, equity, open risk, daily P&L, DD, open positions, hard-limit state; ogni KPI con provenance.
3. **Execution funnel**: SCAN → SIGNAL → GATE → EXECUTE → POSITION → EXIT, conteggi finestra e principali `gate_reason`.
4. **Live trading table**: posizioni, last signals/decisions, broker rejects, command state; drill-down per identity.
5. **Risk & health**: protections, desired/applied settings, anomalies, stale sources.
6. **Research now**: experimenti running/queued/failed, latest validity, current hypothesis, latest build.
7. **Strategy matrix compact**: enabled, live PF/WR/DD/trades, validity, last signal, failure-memory flag.
8. **Knowledge feed**: note recenti, finding P0/P1, backlink al run/strategy.
9. **System footer**: backend/MT5/Render/GitHub/data feed con stato e timestamp.

## Research Lab Audit

| Campo target | Disponibilità attuale | Fonte | Readiness |
|---|---|---|---|
| strategy | Sì | registry, jobs, results, stats | EXISTS ma registry drift |
| selector | Sì/parziale | strategy registry/Backtest config | PARTIAL; nomenclatura non unica |
| source TF | Nei nuovi trace/log e alcuni result | vault/log/params | PARTIAL, non storage web |
| entry TF | Nei trace/log e backtest config | vault/log/params | PARTIAL |
| period | Backtest request/dataset | manifest params | EXISTS, non normalizzato ovunque |
| RAW / RECIPE | Concetto presente in recipe/library/note | seed recipe, results, vault | PARTIAL, non enum canonico UI |
| PF, WR, DD, trades | Sì | backtest result, ledger analytics, stats | EXISTS; fonti da separare |
| status | Job state + verdict/status metadata | compute_jobs, bt_verdict | EXISTS/PARTIAL |
| commit/build | App/engine version nei job; build trace nei log | manifest/trace | PARTIAL; commit assente |
| valid/invalid | CSV analyzer, validity note/template | bt_verdict + vault | PARTIAL; no certificate schema centrale |
| current hypothesis | Note vault e creator saved setup | Markdown/KV | MISSING come entità |

### Fonti riusabili già presenti

- `knowledge/`: evidence, strategy timelines/database, runs, artifacts, bugs, decisions, backtests, imports ledger e schema v1.
- `results/`: risultati best-per-strategy, CSV fase/optimization, `results/manifests/baseline_manifest.json`.
- `server/research_scripts/`: numerosi JSON/CSV/log di studi e replay.
- `server/seed_recipe.json`, `seed_library.json`, `seed_results.json`: seed utili ma da etichettare come seed, non produzione.
- SQLite: `compute_jobs`, `strategy_stats`, `trade_events`, `trades`, `ea_status_history`, KV library/profiles/analysis.
- Job metadata: `nexus_jobs.manifest` include schema/app/engine/requested_by/params hash/params.

La base dati per il Research Lab esiste, ma manca un catalogo unico che registri `artifact_id`, `run_id`, source path, dataset, engine/build, validity e hypothesis.

## Quantitative Integrity UI Readiness

### Stato attuale

| Campo/stato | Backend web schema | Frontend | Evidenza repo | Esito |
|---|---|---|---|---|
| `run_id` | No colonna/event contract | No | docs/vault/log | PARTIAL |
| `decision_id` | No | No | docs/vault/log | PARTIAL |
| `signal_id` | No | No | docs/vault/log | PARTIAL |
| `strategy` | Sì in trades/stats | Sì | diffuso | EXISTS |
| `source_tf`, `entry_tf` | Non canonici | No funnel | trace/backtest params | PARTIAL |
| `level_id` | No | No | trace | PARTIAL |
| `position_id` | Sì in trade events/trades/command ACK | drawer parziale | DB | PARTIAL |
| `pipeline_stage` | No | No | trace/log | MISSING web |
| `gate_reason` | reason/blocker frammentati | Why-no-trade snapshot | trace/stats | PARTIAL |
| `build` | app/engine version in job; EA version in health | health parziale | logs/manifests | PARTIAL |
| GENERATED/BLOCKED/OPEN_ATTEMPT/OPENED/BROKER_REJECT | Nessun enum/storage/API | Nessun funnel | trace v1 validato in note/log | MISSING web |

### Architettura proposta (non implementata)

- **Storage**: tabella append-only `decision_events` con PK evento, indice `(run_id, decision_id, sequence)`, unique idempotency key e campi canonici; payload raw separato. Non sovraccaricare `trade_events`, che descrive lifecycle di trade terminali.
- **Ingestion**: `POST /api/ea/decision-events` machine-auth, batch bounded, schema version, dedupe e validation fail-closed. Accettare gli enum sopra e timestamp producer/received.
- **Read API**:
  - `GET /api/integrity/funnel?window=&strategy=&run_id=` aggregato;
  - `GET /api/integrity/decisions/{decision_id}` timeline completa;
  - `GET /api/integrity/gates?window=&group_by=reason,strategy`;
  - `GET /api/integrity/runs` con build/source TF/entry TF/coverage/reconciliation.
- **Streaming**: iniziare con polling incrementale `after_event_id` ogni 2–5s e ETag; SSE solo dopo stabilità del contratto. Il volume di ricerca può usare batch/job, non WebSocket obbligatorio.
- **UI funnel**: conteggi e conversioni per stage; invarianti visibili (`GENERATED = BLOCKED + OPENED + in-flight`, ogni `OPENED` ha position_id, reject ha reason); click apre decision timeline.
- **Retention**: eventi decisione raw con finestra configurabile; aggregati giornalieri più lunghi; run con validity/audit protetti dalla potatura.

## Vault / Obsidian Audit

- Baseline pre-report: 271 file Markdown totali; 224 sotto `vault/01-Trading` (177 root, 39 strategie, 3 fonti, 3 TODO e 2 decisioni).
- Research notes/audit/report: `vault/01-Trading/*.md`.
- Strategy memory: `vault/01-Trading/Strategie/*.md` e `knowledge/strategy_timelines.json`.
- Failure memory: `NEXUS - Failure Memory ...` più `knowledge/bug_database.json`/`data_quality_issues.json`.
- Methodology/validity: Principles, Test Validity Certificate, Decision-Gate trace, audit e framework.
- Navigazione: frontmatter `status/tags`, wiki links `[[...]]`, MOC e link espliciti già presenti.

### Browser knowledge proposto

`repo markdown → backend read-only index → frontend knowledge browser` è la soluzione corretta e non richiede Obsidian Desktop.

- Allow-list radici `vault/01-Trading`, `docs`, eventualmente `knowledge`; mai path arbitrari dal client.
- Indice rebuild on startup + refresh incrementale per mtime; titolo, path, tags, status, date, headings, outbound links, backlinks, excerpt.
- Full-text search SQLite FTS5; filtri tag/status/type/strategy/date.
- Preview Markdown sanitizzata; nessun HTML raw o asset remoto automatico.
- API minime: `/knowledge/index`, `/knowledge/search`, `/knowledge/note/{id}`, `/knowledge/recent`, `/knowledge/backlinks/{id}`.
- Read-only nella prima fase. Editing resta Git-first per preservare auditabilità.

## GitHub / Build / Render Readiness

| Dato | Esiste | Dove | Gap UI/API |
|---|---|---|---|
| Current commit SHA/branch | Solo runtime Git locale/CI | `.git`, GitHub Actions | non baked/exposed |
| Frontend version | Sì, `2.0.0` | `frontend/package.json` | non mostrata |
| Backend version | Sì, `5.4.0-security-remediation` | `APP_VERSION`, FastAPI | indiretta; nessun system info endpoint |
| EA/worker version | EA payload + deployment manifest | `/ea/health`, deploy manifest | parziale |
| Build status | CI workflow | GitHub Actions | nessuna lettura dashboard |
| Deploy status | Render config, autoDeploy false | `render.yaml` | nessuna metadata release corrente |
| Health/readiness | Sì | `/api/health`, `/api/ready` | SPA usa solo `/ea/health` |
| Data feed health | Dukascopy status/snapshot | API dedicate | non mostrato |

### Minimo sicuro

- In CI/build iniettare variabili non segrete: `GIT_SHA`, `GIT_BRANCH`, `BUILD_ID`, `BUILD_TIME` e `RENDER_GIT_COMMIT` se disponibile.
- Esporre dal backend `/api/system/info` autenticato con soli metadati pubblicabili; nessun token GitHub/Render al browser.
- Per latest CI/deploy, preferire webhook/deploy metadata salvata server-side o API GitHub/Render chiamata dal backend con secret env; restituire solo stato/URL/timestamp.
- Aggregare `/ready`, EA health, bridge manifest e Dukascopy health; distinguere process liveness da readiness.
- Il `deploy/deployment-manifest.json` esiste ma oggi fallisce il test checksum: non mostrarlo come valido finché riconciliato.

## H. Backend Gaps

1. `decision_events` ingestion/read model e funnel aggregation.
2. Experiment/hypothesis/validity/artifact schema e API canoniche.
3. Knowledge index/search/note/backlink API read-only.
4. System info aggregato con git/build/deploy/feed/readiness.
5. OHLC/feed reale autenticato e provenance; eventuale cache candle.
6. Analytics snapshot/cache per evitare scansioni duplicate; query per account/instance/window.
7. Multi-instance selector e scope obbligatorio su read model, non solo commands.
8. Provenance row-level per strategy library/backtest/import/seed.
9. Mutation security uniforme e step-up contract consumabile.
10. Correlation engine oppure rimozione semantica del pannello demo.

## I. Frontend Gaps

1. `DataProvenanceBadge`, `FreshnessIndicator`, `SourceScope` e null/empty contract comuni.
2. `ExecutionFunnel`, `DecisionTimeline`, gate-reason drill-down.
3. Research Lab shell, Experiment Queue, Test Validity e Hypothesis Tracker.
4. Strategy Matrix/Memory/Failure Memory.
5. Knowledge Browser/search/preview/backlinks.
6. System Status page/status bar per backend/MT5/GitHub/Render/feed.
7. Step-up modal + retry sicuro e command contract-driven UI.
8. Route-level lazy imports e query cache/dedupe.
9. Mobile table-to-detail patterns e chart toolbar compatta.
10. Source/account/window filters globali coerenti e serializzabili in URL.

## J. Security Risks

| Rischio | Severità | Evidenza/azione futura |
|---|---|---|
| Frontend non gestisce `STEPUP_REQUIRED`/header step-up | HIGH | Backend lo richiede per alcune azioni; UI può fallire senza recovery |
| Mutation con `Depends(require_user)` | HIGH | `/strategies` save, strategy stats upload, locked profile save, coach notification read/session delete e altri POST compute/read usano protezione incoerente; classificare e migrare quelle con side effect |
| Primary EA implicito | HIGH | primo online/most recent; rischio cross-instance visual/command se selector non esplicito |
| Bridge token condiviso fra istanze | MEDIUM/HIGH | noto in `NORMATIVE_CONFORMANCE`; preferire enrollment/credential per host/EA |
| Landing/marketing/licenze nello stesso prodotto | MEDIUM | aumenta superficie pubblica/commerciale del pannello privato |
| AI output può proporre azioni | MEDIUM | actions disabilitate in produzione, ma endpoint deprecated resta; mantenere draft + human confirm |
| Sessione 12h | MEDIUM | accettabile con step-up funzionante; elevata per workstation lasciata aperta |
| Cookie | Buono | httpOnly, Secure configurabile, SameSite=Lax, revocation list |
| CSRF/CORS | Buono ma incompleto | double-submit + origin allow-list su `require_mutation`; gap dove mutation usa `require_user` |
| Destructive actions | Buono backend | reason/confirm/target/TTL/ACK/audit; testi frontend duplicati e non contract-driven |

Parti ancora orientate a utenti esterni/vendita: Landing3D, license creation/lifecycle/banner, SetupWizard di licenza, downloads/worker distribution, pagine statiche legacy `server/static/*.html`. In futuro vanno separate in public/commercial admin, senza rimuoverle durante il redesign personale.

## UX / Visual System Audit

### Riusabile

- Dark default, token HSL e semantiche success/warning/destructive.
- JetBrains Mono/tabular numbers per metriche; Inter per testo.
- Sidebar responsive con drawer/swipe, bottom nav safe-area, sticky header.
- Shared cards/KPI/pill/section header, drawers trade/strategy, command palette.
- Recharts/lightweight-charts già presenti; focus visible e reduced-motion parziale.
- Provenance chips introdotte nel shell e health disclaimer backend.

### Da ridisegnare

- Ridurre `cockpit-card`, glow, gradient, hover-lift e animazioni sulle superfici dati: oggi competono con la gerarchia informativa.
- Definire una status bar stabile e una griglia densa; card solo per gruppi semantici, tabelle per evidenza ripetuta.
- Unificare colori: gold è primary/identity, green profit/healthy, red loss/block, amber stale/warning, blue info/derived, violet simulated.
- Rendere provenance/freshness una primitive UI, non chip manuali sparsi.
- Separare “dato osservato”, “interpretazione”, “azione”; il health score non deve sembrare risk certification.
- Aggiungere empty/error/stale states coerenti e non sostituire missing con zero.
- Ridurre motion; rispettare `prefers-reduced-motion` per tutte le animazioni, non solo loading.

## K. Performance Risks

| Rischio | Impatto | Evidenza |
|---|---|---|
| 10 richieste globali ogni 5s su ogni route Dashboard | HIGH | `fetchAll` in `Dashboard.jsx`; ~120 req/min/tab |
| Scansioni ledger duplicate e sincrone | HIGH | summary, PF health, heatmap, reasons, calendar, leaderboard/perf |
| Code splitting quasi assente | HIGH | solo Landing3D lazy; tutte le pagine dashboard nel main bundle |
| Main bundle grande | HIGH | build osservata: main ~361.9 kB gzip; chunk 3D ~287.7 kB gzip |
| Landing three.js | MEDIUM | correttamente lazy, ma superficie pubblica costosa e non core |
| React Query installato/non usato | MEDIUM | nessuna cache/dedupe centralizzata |
| Tabelle senza virtualizzazione | MEDIUM | analytics, library, creator, diagnostics possono crescere |
| Chart reload completo 5s | MEDIUM | 300 candles + markers, replace series; oggi sintetico |
| Multiple independent pollers | MEDIUM | Dashboard, chart, bridge, license, coach widgets, library jobs |
| `Dashboard.jsx`/pages >800–1000 linee | LOW runtime/HIGH maintenance | grandi rerender boundary e ownership opaca |

## Mobile Audit

| Area | Stato | Problema |
|---|---|---|
| Sidebar | Buono | drawer 288px, overlay, swipe; gruppi lunghi richiedono scroll |
| Bottom nav | Buono/partial | accesso rapido, ma Coach/Journal dominano rispetto a Live/Research |
| Overview | Partial | card stack leggibile, pagina molto lunga; header nasconde equity/balance sotto `md` |
| Tables | Partial/scarsa | overflow-x evita rottura, ma richiede pan orizzontale e perde contesto colonne |
| Live Chart | Scarsa | toolbar/layers/popover e canvas densi; assenza vista portrait dedicata |
| Backtest/Research | Scarsa | form e risultati estesi, tabs numerosi, tabelle larghe |
| Strategy Analytics | Scarsa | pagina 1003 linee, molti pannelli/tabelle in sequenza |
| Dialog/drawers | Partial | Radix/overlay e max-height buoni; azioni dense e tastiera iPhone da verificare |
| Command palette | Buono/partial | max width/height e keyboard nav; footer/shortcut non utile su touch |
| Coach widget | Rischio overlap | pannello assoluto `w-80` bottom-right sopra bottom nav su schermi stretti |
| Forms | Partial | input generalmente responsive; target touch e sticky action non uniformi |

## L. Technical Debt / Duplication

- `Dashboard.jsx` contiene shell, polling, commands, Settings/Risk subpages e routing-by-section.
- `StrategyAnalyticsPage.jsx` (1003 linee), `HomePage.jsx` (837) e `Dashboard.jsx` (832) concentrano responsabilità.
- Formatter/style helper duplicati: `cls/classNames`, metric/tone helpers, cards e badge locali oltre a `dashboard/shared.jsx` e `components/ui`.
- Trade drawer montato sia in `TradeHubProvider` sia direttamente in `Dashboard` per `selectedTrade`.
- API alias/legacy: command, dashboard family, calendar upcoming, registry route.
- Contratto command frontend hardcoded nonostante `/ea/command_contract`.
- Business logic frontend in `WhyNoTrade` ricostruisce gate da status/settings: può divergere dalla policy EA/backend.
- `DEFAULT_SETTINGS`/adapter frontend generati non sono allineati al registry corrente secondo i test.
- `@tanstack/react-query`, `cmdk`, `next-themes` e altre dipendenze risultano installate ma il flusso principale usa implementazioni custom; verificare dead dependency.
- `server/static/*.html` sono pagine legacy/publiche separate dalla SPA React e potenziale drift.
- CSS include font Google remoti: dipendenza runtime esterna e privacy/offline concern per terminale privato.
- UI usa testi “35 strategie” mentre registry corrente segnala 52 live/82 totali: copy stale.

### Test evidence

Comando: `python -m pytest server/tests -q --basetemp .pytest_tmp`.

- **206 passed, 1 skipped, 7 failed, 2 warnings**.
- 1 failure: checksum `deploy/deployment-manifest.json` non corrisponde al worker corrente.
- 6 failure: conteggi registry attesi 37/59 contro 52/82 correnti e adapter frontend/MQL non allineati.
- Nessuna correzione eseguita; la directory temporanea è stata rimossa.

## M. Migration Plan

### Phase 1 — Trust foundation

- Correggere test drift/manifest; stabilire baseline verde.
- Introdurre contract provenance/freshness/null e selector istanza.
- Collegare `/settings/state`, command contract e step-up UI.
- Smettere di presentare synthetic chart/calendar come live.
- Aggiungere `/system/info` minimo e status bar.

### Phase 2 — Quant integrity + observability

- Aggiungere decision event schema/ingestion/storage/read API.
- Costruire funnel e timeline senza sostituire le pagine attuali.
- Cache/snapshot analytics e polling route-aware.
- Esporre jobs, readiness, data feed, audit operator e build/deploy.

### Phase 3 — Research Lab + intelligence

- Canonicalizzare experiment/run/hypothesis/validity/artifact.
- Unificare Backtest/Optimizer/Strategy Analytics sotto Research Lab.
- Creare Strategy Matrix e memory views collegate a run/trade/note.
- Rendere ogni risultato source/build/dataset-validity aware.

### Phase 4 — Knowledge + visual/mobile consolidation

- Indicizzare vault/docs/knowledge read-only e aggiungere browser.
- Applicare IA definitiva preservando route con redirect/alias solo se approvati.
- Rifinire dark quant terminal, densità, table virtualization e mobile detail views.
- Separare public landing/commercial licenses dal personal control center.

## N. File-by-file Plan futuro

| File/area | Futuro intervento |
|---|---|
| `frontend/src/App.js` | lazy routes, eventuale system/knowledge/research routes preservando compatibilità |
| `frontend/src/pages/Dashboard.jsx` | estrarre shell, data orchestration e command controller |
| `frontend/src/components/Sidebar.jsx` | IA definitiva dopo approvazione audit |
| `frontend/src/components/BottomNav.jsx` | priorità Control/Research mobile |
| `frontend/src/components/CommandPalette.jsx` | catalogo route completo + command contract backend |
| `frontend/src/lib/api.js` | typed errors, step-up retry, ETag/cancel |
| `frontend/src/lib/useVisiblePolling.js` | jitter/backoff/incremental polling o query layer |
| `frontend/src/lib/auth.jsx` | session expiry/step-up state |
| `frontend/src/pages/dashboard/HomePage.jsx` | home data-first + funnel + provenance |
| `frontend/src/pages/LiveChartPage.jsx` | real feed, source/stale state, incremental update |
| `frontend/src/pages/dashboard/AnalyticsPage.jsx` | cached scoped queries; rimuovere demo correlation finché reale |
| `frontend/src/pages/dashboard/StrategyAnalyticsPage.jsx` | decomporre in validity/funnel/performance modules |
| `frontend/src/pages/Backtest.jsx`, `pages/backtest/*` | Research Lab tabs con experiment identity/manifest |
| `frontend/src/pages/dashboard/StrategiesPage.jsx`, `OptimizerPage.jsx` | Strategy Matrix |
| `frontend/src/pages/Coach.jsx` | Learning Engine read-only/governed |
| `frontend/src/index.css`, `tailwind.config.js` | token status/provenance, densità, motion/accessibility |
| `frontend/src/contracts/*` | generator unico e CI drift check |
| `server/app.py` | nuovi router aggregati; ridurre monolite gradualmente |
| `server/ledger_analytics.py` | scoped/cacheable snapshots e definitions |
| `server/nexus_jobs.py` | experiment linkage, progress più granulare, artifacts |
| `server/backtest.py` | provenance obbligatoria e nessun fallback silenzioso |
| `server/nexus_validation.py` | schema decision events/experiments/knowledge IDs |
| `server/nexus_security.py` | credential per-instance e policy mutation uniforme |
| `server/nexus_retention.py` | classi decision events/experiment artifacts |
| nuovo `server/routers/integrity.py` | ingestion/read funnel |
| nuovo `server/routers/knowledge.py` | vault index read-only |
| nuovo `server/routers/system.py` | build/deploy/readiness aggregation |
| nuovo `server/research_catalog.py` | catalogo run/artifact/validity |
| `.github/workflows/ci.yml` | generator check, frontend tests, metadata build artifact |
| `render.yaml`, `server/Dockerfile` | build metadata non segreta e release manifest valido |
| `vault/01-Trading/*`, `knowledge/*`, `results/*` | restano fonti; aggiungere ID/frontmatter gradualmente, mai bulk rewrite |

## O. DO NOT TOUCH durante il redesign

1. Contratto machine auth e fail-closed preflight (`nexus_security`, env LIVE, bridge token) senza migrazione/test dedicati.
2. Command lifecycle target-scoped, lease/ACK, TTL, retry, broker confirmation, reason e operator audit.
3. Append-only `trade_events`, hash chain, idempotency, trade identity/account scoping.
4. Distinzione desired/applied settings e locked profile versioning.
5. Registry canonico e generatori: prima correggere drift, poi cambiare insieme contract/test/adapters.
6. Risk caps/policy e destructive-action confirmation/step-up.
7. Retention, backup/restore drill e persistent Render disk paths.
8. Backtest validity/provenance: non uniformare risultati Python, MT5, import e synthetic come se fossero equivalenti.
9. MQL5 e pipeline trading durante il redesign web.
10. Route e API esistenti finché consumer e compatibilità non sono misurati; usare strangler/incremental migration.
11. Vault originale: indicizzarlo read-only; non rinominare/bulk-editare note o wiki links nella fase UI.
12. `server/static/app` build deployata: non editarla manualmente; deve essere prodotto della build frontend.

## Decisione raccomandata

Approvare un redesign solo dopo una **Phase 1 di trust foundation**. La SPA e il backend sono abbastanza maturi da evolvere senza rewrite; il maggiore rischio non è visuale ma epistemico: distinguere sempre ciò che il sistema ha osservato, derivato, simulato, importato o inventato come fallback. Il target realistico è **85/100 senza rewrite**, mantenendo FastAPI, SQLite, route e gran parte dei componenti, purché integrity telemetry, knowledge indexing, system observability e query orchestration vengano aggiunti come layer incrementali.

## Evidenze principali

- Frontend: `frontend/src/App.js`, `pages/Dashboard.jsx`, `pages/dashboard/*`, `pages/*`, `components/*`, `lib/*`, `contracts/*`, `hooks/*`, `index.css`, `tailwind.config.js`, `package.json`.
- Backend: `server/app.py`, `backtest.py`, `ledger_analytics.py`, `nexus_jobs.py`, `nexus_policy.py`, `nexus_validation.py`, `nexus_retention.py`, `nexus_security.py`, `command_contract.py`, `bt_verdict.py`, `strategy_registry.py`.
- Ops: `.github/workflows/ci.yml`, `render.yaml`, `server/Dockerfile`, `deploy/deployment-manifest.json`.
- Research/knowledge: `vault`, `knowledge`, `results`, `server/research_scripts`, `server/seed_*.json`.

[[MOC - Trading]] · [[NEXUS - Decision-Gate-Execution Trace v1 (12-09)]] · [[NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico) (12-09)]] · [[NEXUS EA - Test Validity Certificate (template e istanze 10-09)]]
