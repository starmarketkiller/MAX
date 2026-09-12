# NEXUS — Decision/Gate/Execution Trace v1

Roadmap 95/99, QUANTITATIVE INTEGRITY. Obiettivo: ogni segnale deve poter essere seguito causalmente da generazione ad apertura o blocco.

## Stato: implementato e testato su 2 strategie, funnel riconciliato

**Non un sistema isolato**: estende `NXS_GateTelemetry` (già esistente in `NXS_Execution.mqh`, già agganciato al punto causale corretto dentro `NXS_CommonExposurePreflight`) invece di duplicarlo, e aggiunge gli stessi call site su ogni altro gate reale nei 4 execution path.

## Architettura

Nuovo file `MQL5/Include/NEXUS_v1/NXS_Trace.mqh`, incluso subito dopo `NXS_Defines.mqh` (usa `SNXSSignal`, deve essere disponibile ovunque un gate possa bloccare/aprire un segnale).

**Campo aggiunto a `SNXSSignal`** (`NXS_Defines.mqh`): `long trace_id` — identità stabile assegnata UNA VOLTA subito dopo `NXS_CollectAllSignals()`, portata invariata attraverso qualunque path fino allo stato terminale.

**Stati**: `GENERATED → BLOCKED(reason)` oppure `GENERATED → OPEN_ATTEMPT → OPENED(position_id)` oppure `GENERATED → OPEN_ATTEMPT → BROKER_REJECT(reason)`.

**Gate enum canonico** (richiesto + 2 estensioni dichiarate): `PROFILE_DISABLED, TF_GATE, OPEN_POSITION, COOLDOWN, PROTECTIONS, RISKSHIELD, SPREAD, NEWS, HTF, VELOCITY, SCORE, EXPOSURE, MARGIN, INVALID_STOPS, BROKER_REJECT, UNKNOWN_STRATEGY, OPENED` + `LICENSE, STATE_UNCERTAIN` (gate reali già esistenti in `NXS_CommonExposurePreflight` senza un bucket canonico corrispondente — enumerati a parte invece di forzarli dentro PROTECTIONS in modo fuorviante).

**Overhead minimo / Live Mode invariato**: `g_nxsTraceActive` impostato in `OnInit()` a `NXS_IsResearchMode()` — zero Print aggiuntivi quando l'EA gira in Live. `NXS_IsResearchMode()` non è chiamabile da dentro `NXS_Trace.mqh` (definita molto più tardi nella catena di include) — il flag viene impostato dal chiamante dopo che tutti gli include sono risolti.

## Punto causale singolo per GENERATED

Emesso una sola volta, subito dopo `NXS_CollectAllSignals()` in `NEXUS_EA_v2.mq5`, PRIMA che qualunque path (DataCollection/Institutional/StrategyProfiles/Legacy) veda l'array `all[]`. Tutti e 4 consumano lo stesso array prodotto da questa unica chiamata — garantisce che ogni segnale con `dir!=DIR_NONE` abbia già un `trace_id` e una riga GENERATED prima di qualunque gate.

## `NXS_OpenTrade` come choke point condiviso

`NXS_OpenTrade()` è chiamata da TUTTI e 3 i path a ordine reale (Institutional, StrategyProfiles, Legacy via `NXS_TryExecuteRC`). Instrumentarla una sola volta copre tutti e 3: `NXS_Trace_OpenAttempt` in testa, `NXS_Trace_Blocked` a ognuno dei suoi ~13 gate interni (unknown_strategy, ruin_frozen, profile_disabled, regime_veto, wrong_tf, dashboard_disabled, bar_dir_cap, setup_matrix_cap, post_sl_cooldown, exhaustion, elliott, invalid_sl_distance, lot_calc_zero, strategy_risk_disabled, virtsl_hardSL_invalid, virtsl_offline_risk_over_cap), `NXS_Trace_Opened`/`NXS_Trace_BrokerReject` all'esito finale.

`NXS_CommonExposurePreflight` (chiamata da `NXS_OpenTrade` + 5 altri call site: grid/pyramid/profit-reclaim/SLReclaim/inst-manage) ha ricevuto un **out-parameter** `ENUM_NXS_GATE_REASON &gateOut`, impostato dal codice a ogni `return false` — scelta deliberata invece di string-matching su `reason` a posteriori: `NXS_RS_BlockEntry`/`EQUITY_BREAKER`/`CLUSTER_CAP` formattano `reason` con un wording che può cambiare, string-matching sarebbe fragile esattamente dove serve più precisione (RISKSHIELD).

## Path coperti in dettaglio

| Path | Copertura |
|---|---|
| DataCollectionMode | Completa: cap `InpDataCollectionMaxOpen`→EXPOSURE, OPEN_POSITION, `NXS_PreFlight`→SPREAD/MARGIN/INVALID_STOPS, OPEN_ATTEMPT/OPENED/BROKER_REJECT |
| StrategyProfiles | Completa: overlap-only, OPEN_POSITION, TF-bar-throttle→TF_GATE, SL/TP invalido, poi `NXS_OpenTrade` (vedi sopra) |
| Institutional | Solo tramite `NXS_OpenTrade` (choke point condiviso) — il proprio pre-check di aggregazione (`NXS_Institutional_Decide`, che fonde più segnali in UNA decisione) **non instrumentato**: non ha un `trace_id` naturale 1:1 essendo una decisione di GRUPPO, non un singolo segnale |
| Legacy (best-per-bar / `NXS_TryExecuteRC`) | Solo tramite `NXS_OpenTrade` — i propri pre-check (cooldown x2, MTF, velocity, il proprio HTF/NEWS/PROTECTIONS/SCORE dentro `NXS_TryExecuteRC` stesso) **non instrumentati** |

**Non coperto per scelta esplicita, dato il tempo disponibile**: i pre-check propri di Institutional e Legacy (mai esercitati da Research Mode in questa sessione — Research Mode usa sempre `InpUseStrategyProfiles=true`), e i 5 call site "secondari" di `NXS_CommonExposurePreflight` (grid/pyramid/profit-reclaim/SLReclaim/inst-manage add), che ricevono l'out-param solo per compilare, non trace attivo.

## Compile e test

Compilato: **0 errori**, 2 warning preesistenti invariati.

Test: 2 passate Research Mode isolate (Fast Smoke 2026.06.01-06.15, GOLD H4, leva 500), una per strategia:

| Strategia | selector | GENERATED | BLOCKED | OPENED | Trade reali (report MT5) |
|---|---|---|---|---|---|
| ADX_RSI | 1 | 118 | 117 (tutti OPEN_POSITION) | 1 | 1 ✓ |
| MACD | 3 | 483 | 481 (tutti OPEN_POSITION) | 2 | 2 ✓ |

**Funnel riconciliato in entrambi i casi**: GENERATED = BLOCKED + OPENED esattamente, e OPENED coincide col conteggio reale del report MT5. Zero segnali spariti.

### Esempio trace reale (ADX_RSI, un segnale completo)

```
[NXS_TRACE] run_id=GOLD_2026.06.01 00:00:00 decision_id=1 signal_id=1 strategy=ADX_RSI source_tf=PERIOD_D1 entry_tf=PERIOD_M15 level_id=- position_id=0 timestamp=2026.06.05 17:00:00 pipeline_stage=GENERATED gate_reason=NONE detail=ADXRSI bear (site) build=3.0.0
[NXS_TRACE] run_id=GOLD_2026.06.01 00:00:00 decision_id=1 signal_id=1 strategy=ADX_RSI source_tf=PERIOD_D1 entry_tf=PERIOD_M15 level_id=- position_id=0 timestamp=2026.06.05 17:00:00 pipeline_stage=OPEN_ATTEMPT gate_reason=NONE detail= build=3.0.0
[NXS_TRACE] run_id=GOLD_2026.06.01 00:00:00 decision_id=1 signal_id=1 strategy=ADX_RSI source_tf=PERIOD_D1 entry_tf=PERIOD_M15 level_id=- position_id=2 timestamp=2026.06.05 17:00:00 pipeline_stage=OPENED gate_reason=OPENED detail= build=3.0.0
[NXS_TRACE] run_id=GOLD_2026.06.01 00:00:00 decision_id=2 signal_id=2 strategy=ADX_RSI source_tf=PERIOD_D1 entry_tf=PERIOD_M15 level_id=- position_id=0 timestamp=2026.06.05 17:15:00 pipeline_stage=GENERATED gate_reason=NONE detail=ADXRSI bear (site) build=3.0.0
[NXS_TRACE] run_id=GOLD_2026.06.01 00:00:00 decision_id=2 signal_id=2 strategy=ADX_RSI source_tf=PERIOD_D1 entry_tf=PERIOD_M15 level_id=- position_id=0 timestamp=2026.06.05 17:15:00 pipeline_stage=BLOCKED gate_reason=OPEN_POSITION detail= build=3.0.0
```

`signal_id`/`decision_id` (coincidenti in v1 per i path 1:1) restano identici da GENERATED a OPENED — `position_id=2` è il ticket reale assegnato dal broker, leggibile direttamente dalla riga OPENED.

## File

`MQL5/Include/NEXUS_v1/NXS_Trace.mqh` (nuovo), `NXS_Defines.mqh` (+trace_id), `NXS_Execution.mqh` (NXS_OpenTrade + NXS_CommonExposurePreflight instrumentati), `NEXUS_EA_v2.mq5` (GENERATED, DataCollectionMode, StrategyProfiles), `NXS_GridRecovery.mqh`/`NXS_InstManage.mqh`/`NXS_ProfitReclaim.mqh`/`NXS_Pyramiding.mqh`/`NXS_SLReclaim.mqh` (solo firma aggiornata per compilare, trace non attivo). `server/research_scripts/trace_v1_test_adx_rsi_log.txt`, `trace_v1_test_macd_log.txt` (log delle 2 passate di test).

## Non coperto (dichiarato esplicitamente, non nascosto)

- Pre-check propri di Institutional (`NXS_Institutional_Decide`) e Legacy (`NXS_TryExecuteRC`'s own MTF/velocity/HTF/news/protections/score prima di chiamare NXS_OpenTrade) — mai esercitati da Research Mode in questa sessione, ma path realmente esistenti in Live se `InpUseStrategyProfiles=false`.
- I 5 call site secondari di `NXS_CommonExposurePreflight` (grid/pyramid/profit-reclaim/SLReclaim/inst-manage) — non sono segnali primari, fuori dai 4 path principali mappati.
- Institutional aggrega più segnali in una decisione sola: non ha un `signal_id` 1:1 naturale con l'attuale schema — richiederebbe un design a parte (`decision_id` di gruppo + lista di `signal_id` contribuenti), non implementato.
