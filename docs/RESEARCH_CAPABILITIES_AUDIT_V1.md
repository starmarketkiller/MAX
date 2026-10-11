# NEXUS Research Capabilities Audit V1

Data: 2026-10-11. Base: `main` @ `ba6c223`. Ricognizione in sola lettura: nessun codice modificato, nessun backtest, nessun download, nessun servizio acquistato.

**Come leggere le evidenze.** "Eseguito qui" significa che ho lanciato il comando in questo container Linux (4 CPU, 15 GB RAM, Python 3.13, numpy 2.5.4, pandas 3.0.5). Il PC Windows con MT5 e la cache dati non sono raggiungibili da qui: ciò che sta solo lì è classificato in base agli artifact versionati (manifest, hash, report), non verificato di persona.

**Limiti di questo ambiente.** `datafeed.dukascopy.com` è bloccato dalla policy di rete del container (connessione resettata dal proxy). `scipy` non è installato.

---

## A. Research Asset Inventory

### A.1 Dati storici

#### Fisicamente presenti nel repository

| Dataset | Posizione | Provider / origine | Strumento e TF | Copertura | Bid/ask, spread, volume | Righe / dimensione | Qualità e provenienza |
|---|---|---|---|---|---|---|---|
| MARKET_STATE_V1 barre | `server/research_datasets/market_state_v1/xauusd_h4_bars.csv` | Dukascopy, H4 costruite dai tick | XAUUSD H4, UTC, griglia 00/04/…/20 | 2019-02-03 → 2022-02-03 | OHLC su BID, `avg_spread`, `n_ticks` | 4.809 / 412 KB | sha256 `4f4a248d…` **verificato qui** e uguale al manifest. Classificato `DISCOVERY_REUSE`: già esposto, non è un holdout |
| MARKET_STATE_V1 feature | `server/research_datasets/market_state_v1/market_state_dataset_v1.csv` | derivato dal precedente | H4 | idem | — | 4.809 / 2,2 MB | sha256 `886c4834…` **verificato qui**. 26 feature causali (vedi A.2) |
| Export MT5 H4 | `server/research_scripts/nxs_h4_gold_29-08.csv` | broker XM, export MT5 | GOLD H4, ora server | 2025-01-02 → 2026-08-24 | OHLC + tick_volume, niente spread | 2.534 / 136 KB | provenienza dichiarata, niente hash |
| Export MT5 H4 + indicatori | `server/research_scripts/nxs_h4_gold_indicators_29-08.csv` | idem | H4 + SAR, EMA9, EMA21, ATR14 di MT5 | idem | — | 2.534 | prime barre con `DBL_MAX` (warm-up MT5) |
| Export MT5 M15 | `server/research_scripts/nxs_m15_gold_29-08.csv` | idem | GOLD M15 | 2025-10-15 → 2026-08-24 | OHLC, niente volume né spread | 20.164 / 960 KB | solo 10 mesi |
| Export MT5 D1 | `server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv` | idem | GOLD D1 | 2019-01-02 → 2026-08-19 | OHLC + tick_volume | 1.971 | — |
| Eventi strutturali EA | `results/structural_dataset_v1/structural_events.csv` | EA, `SNXSSweepExt` (Research Mode) | eventi M5…D1 | 2026-01-02 → 2026-08-24 | — | 8.118 eventi: 4.045 SWEEP, 3.741 INVALIDATE, 269 TRUE_BREAK, 63 RETEST | 8 mesi, sorgente unica |
| Trade e segnali ricostruiti | `results/cost_calibration_67_rerun/*_trades.csv`, `server/research_scripts/phase7/**/raw_data/*.csv` | Strategy Tester MT5 | per strategia | varia | fill reali | decine di file < 7 MB | vedi sezione C |

Altri CSV nel repository: 115 in totale, tutti sotto 7 MB. Il più grande è `phase7_18/nxs_tsi_realtrace_diag_prefix_curated.csv` (6,4 MB, trace diagnostico TSI).

#### Solo sul PC Windows (gitignored)

Nel repository ci sono manifest e hash, non i dati.

| Dataset | Path dichiarato | Copertura | Contenuto | Evidenza |
|---|---|---|---|---|
| Tick Dukascopy Phase 4 | (manifest non materializzato) | 2019-02-03 → 2022-02-03, 1.097 giorni | tick, mid o bid | `phase5_5/dataset_version_v1.json` (hash manifest `f84a12c7…`) |
| Tick Dukascopy Phase 6 (holdout H006, già consumato) | `server/research_scripts/phase6/data_cache_holdout/decoded/` | 2022-02-04 → 2023-02-03 | tick | `phase6/true_holdout_declaration.json` |
| **Tick Dukascopy Phase 7** | `server/research_scripts/phase7/data_cache_new_period/decoded/*.csv.gz` | **2023-02-04 → 2026-09-16, 1.321 giorni, 226.482.290 tick** | `epoch_ms, bid, ask, bid_vol, ask_vol` | `phase7/new_dataset_integrity_report_v1.json`: PASS_WITH_NOTES. 0 giorni mancanti, 0 duplicati, 0 timestamp non monotoni, 0 prezzi impossibili, 4 feriali a zero tick (festività) |
| Partizioni Phase 7 (logiche, sullo stesso manifest) | `phase7/partition_manifest_v1.json` | discovery 2023-02-04→2024-08-03 (61,4 M tick) · internal_validation 2024-08-04→2025-05-03 · locked_validation 2025-05-04→2026-02-03 · **final_holdout 2026-02-04→2026-09-16 SEALED** | — | `final_holdout_seal_v1.json`. Ledger accessi: zero record (`phase7_1_validation_access_evidence_v1.json`) |
| Cache M15 del backtester | `server/data_cache/` (oppure `/data/dukascopy` su Render) | sconosciuta | OHLC **mid**, niente bid/ask separati (`dukascopy_fetch.py:84`) | stato leggibile solo da `/api/dukascopy_status` |
| Cache M5 | `server/data_cache_m5/` (`fetch_dukascopy_history_m5.py`) | sconosciuta | OHLC | nessun manifest nel repository |
| Serie multi-TF Phase 7.13 | `phase7/phase7_13/multi_tf_dataset_v1.json` da `nxs_m15_gold_extended.csv` | 2023-10-02 → 2026-08-25 | M15/M30/H1/H4/D1 ricampionati da una sola serie M15 MT5 | provenienza dichiarata "non accertata oltre plausibilità" (`build_multi_tf_dataset.py`) |
| Tick reali del broker in MT5 | terminale XM | **GOLD: tick reali solo dal 2023-09-11** | tick broker | `results/cost_calibration_67_rerun/tick_history_audit_xmglobal7.csv` (primo tick 2023-09-11 21:17:51). Prima di quella data il Tester genera tick dalle barre |
| Simbolo custom con tick Dukascopy in MT5 | `MQL5/Scripts/NXS_ImportDukascopyCustomSymbol.mq5` + `convert_dukascopy_for_mt5_import.py` | quella importata | bid/ask Dukascopy dentro MT5 | usato in Phase 5 ("SAR vs XM") |

#### Solo scaricabili

| Fonte | Strumento | Come | Stato da qui |
|---|---|---|---|
| Dukascopy datafeed | XAUUSD e altri, tick | `phase7/phase7_dukascopy_downloader.py` (salva bid/ask/volumi), `server/dukascopy_fetch.py` (salva mid) | **BLOCKED** in questo container: host negato dal proxy |
| Stooq daily | XAUUSD D1 | `server/backtest.py:_fetch_stooq` | non provato |
| Yahoo | intraday breve (~60 giorni / 2 anni) | `server/sweep.py:fetch_yahoo` | non provato |
| **Dati sintetici** | — | `backtest.py:_synthetic`, `sweep.py:_synth`: fallback automatico se la rete manca. `/api/chart/ohlc` è sintetico | Etichettati `data_source="synthetic"`. **Rischio**: un run senza rete produce numeri su dati inventati se nessuno legge l'etichetta |

#### Fusi orari

Dukascopy e le barre di ricerca sono in UTC. Il server XM è GMT+3 in estate (misurato: `phase7_8i/raw_data_audit/nxs_volbrk_timezone_measure_immediately_before_run3.txt`, offset 10.800 s, con nota DST). Le H4 Python (griglia UTC) e quelle MT5 (griglia del server) non coincidono: in `results/cost_calibration_67_rerun/phase_e_macd_mismatch_attribution.json` la stessa barra H4 differisce di 2–33 $ in chiusura. Conversione all'ora italiana: non esiste codice (`Europe/Rome`/`zoneinfo` assenti).

### A.2 Indicatori e feature

| Tipo | Cosa c'è | Dove | Calcolabile offline? |
|---|---|---|---|
| Indicatori standard MT5 usati dall'EA | iMA (14 handle), iATR (6), iADX (5), iRSI (3), iSAR, iMACD, iIchimoku, iBands (2 ciascuno) | `MQL5/Include/NEXUS_v1/*.mqh` | serve il terminale, oppure export (`NXS_ExportH4Indicators.mq5`, `NXS_ExportMACDIndicators.mq5`) |
| Logica calcolata a mano nell'EA | 30 funzioni di struttura e livelli: sweep, FVG, OB, BOS/CHOCH, swing, zigzag, fib; TSI, PMAX, Hull ecc. dentro le strategie | `NXS_Structure*.mqh`, `NXS_Strategies*.mqh`, `NXS_LevelRegistry.mqh` | solo con repliche Python dedicate (vedi A.3) |
| Indicatori custom MQL5 | `NEXUS_VisualSuite_v2.mq5` (visuale), `NXS_SAR_Visual.mq5` | `MQL5/Indicators/` | no, solo visualizzazione |
| Indicatori Python | `sma`, `ema_series`, `atr_series`, `psar_series`, `adx_series`, `rsi_series`, MACD signal, `tsi_series` | `server/backtest.py:383-1165` | sì. In più `server/sweep.py` ha versioni proprie (`_ema`, `_rsi`, `_atr`, `_adx`, `_bb`, `_swings`): **duplicate** |
| Feature statistiche causali | 26 feature registrate, tutte `CAUSAL_SAFE`: direzione e efficienza del trend, persistenza, ATR e percentile, realized vol e accelerazione, compressione, distanze da massimi/minimi rolling, giornalieri e settimanali, ROC, momentum, autocorrelazione lag-1, variance ratio, mean reversion score, ora, sessione, giorno | `phase7/feature_registry_v2.json`, `phase5_5/feature_provenance_registry_v1.json`, `feature_redundancy_audit_v1.json` | sì, su H4 |
| Detector di eventi (Phase 5, H4) | BREAKOUT 724 (HIGH), COMPRESSION_RELEASE 482, DISPLACEMENT 188, FAILED_BREAKOUT 315, **PULLBACK 3.988 = 83% delle barre: PATHOLOGICAL, non ammesso**, RECLAIM 300, RETEST 337, SWEEP 500, VOLATILITY_EXPANSION 1.784 (HIGH) | `phase5/build_events.py`, `phase7/event_detector_health_v1.json` | sì, ma solo H4 e sul dataset 2019–2022 |
| Librerie quantitative | installate qui: numpy 2.5.4, pandas 3.0.5. Dichiarate: solo `pandas` in `requirements-dev.txt`. **`scipy` usato da 6 moduli del motore statistico ma non dichiarato da nessuna parte**. Assenti: statsmodels, scikit-learn, arch, TA-Lib, vectorbt, backtrader, matplotlib, pyarrow, MetaTrader5 | `server/requirements*.txt` | — |

**Differenze Python/MQL5 documentate:**

- MACD/EMA200 Python vs MT5 su GOLD H4: valori diversi sulla stessa barra, a causa del feed (Dukascopy vs XM) e della griglia oraria. In un caso la condizione è diversa (MT5 SELL, Python none) (`phase_e_macd_mismatch_attribution.json`).
- ATR: Python usa Wilder (EMA α=1/14) che include TR_t; serve attenzione alla causalità (nota in vault su `phase5/build_events.py:99`).
- BREAKOUT_ACC: parità evento per evento 66 su ~80 (78–80%), residuo `FEED_BAR_DIFFERENCE` (`phase7_9c/breakout_acc_event_parity_matrix_v1.json`).
- Il registro strategie dichiara `research_parity`: **0 EXACT**, 32 APPROXIMATE, 6 PROXY, 45 NOT_IMPLEMENTED.

### A.3 Strategie

Fonte canonica: `contracts/strategy-registry.json` (83 identità), arricchita da `contracts/edge-validation-registry.json` (83 righe) e da `phase7/phase7_11/complete_strategy_census_v1.json`.

| Gruppo | N | Note |
|---|---|---|
| Nell'EA (`live_implementation`) | 53 | 28 ACTIVE, 22 DISABLED, 3 EXPERIMENTAL |
| Solo ricerca (`RESEARCH_ONLY`) | 30 | varianti _V2, _CHOCH_WINDOW, SCALP_*, CRT, CISD_TRUE, DARVAS_BOX, DONCHIAN_TURTLE, EMA_CROSS_BENCHMARK… |
| Con implementazione Python | 59 | parità quasi mai esatta (vedi sopra) |
| Funzioni `NXS_Strat_*` nell'EA | 55 | 58 `stratName` distinti |
| Nell'EA ma non nel registro | 2 | `OB_MIT_NXR`, `STRUCT_REACT_NXR` (wrapper NXR, codice morto: `InpNXR_Enable` è costante `false`) |
| Mai implementate per intero | 3 | CRT, FVG_MIT_WINDOW, `sig_breakout` Python orfano (`census_summary_v1.json`) |
| Lineage e duplicazioni | 12 | LIQ_VOID←FVG_CONT, LONDON_BO←BREAKOUT_ACC, RANGE_FADE←BOLLINGER, SH_BMS_RTO/SMS_BMS_RTO←OB_MIT, WEEKLY_EXP←BREAKOUT_ACC, CISD=THREE_BAR_DELIVERY_BREAK, cinque *_NXR. Enum `STRAT_STRUCT_REACT` condiviso da ~34 strategie (skill mql5-engineering §8) |
| Timeframe dichiarati | — | `*` 34, H4 19, D1 13, H1 7, M15 6, M30 2, M5 2 |
| Famiglie | — | SCALP 30, UNCLASSIFIED 13, LIQUIDITY 9, SMC 8, TREND 6, MOMENTUM 5, SESSION 5, AMD 3, VOLATILITY 3, PATTERN 1 |
| Altri sorgenti | — | `pinescript/` (10 strategie in Pine), `Grok3xAI.mq5` legacy (568 righe), branch `codex/create-mt5-expert-advisor-*` (EA alternativi, non in main) |

Stato di evidenza (`docs/TRADING_EDGE_STATUS_RECONCILIATION_V1.md` ed edge registry):

| Stato | Strategie |
|---|---|
| CANDIDATE (9) | ADX_RSI (confidenza ridotta dal regime, 7.27), EMA_PULLBACK, FVG_CONT (bypass SLReclaim non chiuso), ICHIMOKU, JUDAS_SWING, LIQ_SWEEP (OOS n=6 negativo), MALAYSIAN_SNR, STRUCT_REACT (debole), Z_SCORE_BREAKOUT (n=460) |
| BORDERLINE (4) | BOLLINGER, LONDON_BO, NY_REVERSAL, SAR |
| FORWARD_REQUIRED (2) | BREAKOUT_ACC, ORDER_BLOCK (fix validati causalmente, CI95 include zero, OOS 0–1 trade) |
| FAILED (3) | MACD, RSI_DIV, CRT |
| DEFECT_BLOCKED (9) | BB_SQUEEZE, SH_BMS_RTO, SILVER_BULLET, TSI (guardia TF presente in `NXS_Strategies.mqh:1370` e validata in 7.18 come FIX_CAUSALLY_VALIDATED, ma l'edge registry del 2026-10-06 la riporta ancora DEFECT_BLOCKED: discrepanza), BAR_UPDN, PIVOT_WICK, PMAX, RANGE_FADE, SH_BMS_RTO_V2: tutti CROSS_TIMEFRAME_STATE_CONTAMINATION |
| UNVALIDATED | 65 su 83 |

---

## B. Research Capability Matrix

| CAPACITÀ | COMPONENTE ESISTENTE | POSIZIONE | STATO | EVIDENZA | LIMITI | AZIONE NECESSARIA |
|---|---|---|---|---|---|---|
| Ingestione tick con bid/ask | Downloader Phase 7 | `phase7/phase7_dukascopy_downloader.py` | AVAILABLE_AND_VERIFIED (sul PC) | integrity report PASS, 226 M tick | non eseguibile qui (host bloccato); dati solo sul PC | nessuna per i dati esistenti |
| Ingestione M15/M5 per backtester | `dukascopy_fetch.py`, `fetch_dukascopy_history_m5.py` | `server/` | PARTIALLY_AVAILABLE | codice + endpoint di stato | salva **mid**, niente spread; su Render disco da 1 GB | usare i tick Phase 7 per lo spread |
| Validazione dati | integrity check, dataset version guard, manifest hash | `phase7/check_new_dataset_integrity.py`, `engine/dataset_version_guard.py` | AVAILABLE_AND_VERIFIED | hash MARKET_STATE_V1 ricontrollati qui | — | — |
| Barre H4 da tick | `build_h4_bars*.py` (Phase 5/6/7.1) | `phase5/`, `phase6/`, `phase7/phase7_1/` | AVAILABLE_AND_VERIFIED | `reproducibility_report_v1.json` (rebuild byte-identico) | **solo H4**, BID, griglia UTC | — |
| Barre M15/M5 da tick Phase 7 | — | — | MISSING | nessun builder M15 sul manifest 2023–2026 | — | builder M15 deterministico (stessa logica H4) |
| Feature causali | 26 feature + provenance + redundancy audit + leakage guard | `phase5/build_market_state.py`, `phase5_5/` | AVAILABLE_AND_VERIFIED | `leakage_guard_report_v1.json` | solo H4 | portarle sul periodo 2023–2026 (già fatto per H4 in 7.1) |
| Detector di eventi | 9 famiglie H4 + firing-rate guard | `phase5/build_events.py`, `engine/event_firing_rate_guard.py` | PARTIALLY_AVAILABLE | `event_detector_health_v1.json` | PULLBACK patologico, niente M15 | detector PULLBACK formalizzato |
| Eventi strutturali EA | sweep, true break, retest, invalidate | `NXS_StructuralResearchLog.mqh`, `results/structural_dataset_v1/` | AVAILABLE_AND_VERIFIED | 8.118 eventi esportati | 8 mesi, griglia server | — |
| Sequenze ed episodi | sequence episode engine, causality guard, detector contract, 20 sequenze, feasibility gate | `phase7/phase7_3/engine/`, `phase7_2/market_sequence_registry_v1.json`, `phase7_5/` | IMPLEMENTED_NOT_TESTED su dati reali | readiness gate tutto true con suite sintetica; 0 di 5 famiglie pronte (`NEEDS_DETECTOR_FORMALIZATION`) | trigger M15 "gap dichiarato" | formalizzare un detector |
| Event study con baseline abbinata | Baseline Engine v4, control reuse ledger, cross-split safety | `phase7/engine/` | IMPLEMENTED_NOT_TESTED in questo ambiente | 7.1 eseguito sul PC (NO_SUPPORTED_CANDIDATE) | i test 7.4A non si caricano senza `scipy` | dichiarare `scipy` |
| Inferenza con dipendenza seriale | block bootstrap, permutation test matched-pair, dependence validity gate | `phase6_5/`, `phase7/engine/` | PARTIALLY_AVAILABLE | 7.4 verdetto "PRIMARY INFERENCE METHOD NOT YET VALIDATED" / "BLOCKED - GATE REQUIRES REDESIGN" | metodo primario non validato | chiudere la 7.4 |
| Multiple testing | BH-FDR (gated, ungated, dependence-gated), ledger | `engine/multiple_testing_v2.py`, `phase5_5/multiple_testing_ledger_v1.json`, `phase7_26/multiple_testing_registry_v1.json` | AVAILABLE_AND_VERIFIED | usato in 7.1 e 7.27 | — | — |
| Preregistrazione e lifecycle | preregistration guard, candidate lifecycle, post-hoc quarantine, signature anti-duplicati | `phase7/engine/` | AVAILABLE_AND_VERIFIED | test passano qui | — | — |
| Accesso a holdout | validation access ledger (one-shot) | `engine/validation_access_ledger.py` | AVAILABLE_AND_VERIFIED | seal attivo | ledger su file gitignored del PC | — |
| Backtest Python | `run_backtest` (SL/TP ATR, costi, `bar_range` IS/OOS, profili) | `server/backtest.py:4683` | PARTIALLY_AVAILABLE | CI backend verde; endpoint `/api/backtest/*` | parità con EA mai esatta; fallback sintetico | non usarlo come prova finale |
| Ottimizzazione | grid, optimize per strategia e multi-TF, job asincroni | `backtest.py:5518`, `sweep.py`, `/api/backtest/optimize*`, `nexus_jobs.py` | IMPLEMENTED_NOT_TESTED su dati autentici | — | gira sul motore Python | — |
| Walk-forward | `walk_forward()` copiato in ≥5 script, `big3_1d_walkforward.py`, `full_catalog_walkforward_15-08.py` | `server/research_scripts/` | PARTIALLY_AVAILABLE | risultati di agosto | nessuna libreria unica, finestre ad hoc | estrarre una funzione unica |
| OOS e holdout | partition contract v2, holdout sigillato, OOS per strategia | `phase7/partition_contract_v2.json`, 7.21–7.25 | AVAILABLE_AND_VERIFIED | decision card 7.21/7.22/7.25 | OOS per strategia quasi esauriti (C.3) | — |
| Monte Carlo | portfolio Monte Carlo | `portfolio_montecarlo_25-08.py`, `_v3_` | DOCUMENTED_ONLY / ad hoc | script di agosto | non collegato a lifecycle | — |
| Stress sui costi | cost profiles, cost model audit, rerun | `backtest.py` (profili XAUUSD), `results/cost_model_audit/`, `results/cost_calibration_67_rerun/` | AVAILABLE_AND_VERIFIED | `classification.json`, rerun 15-09 | spread reale solo nei tick Phase 7 | — |
| MFE/MAE e path anatomy | path anatomy engine (signal e fill relative, censoring) | `phase7/phase7_26/nxs_path_anatomy_engine.py`, `phase7_9k/nxs_forward_path_v2.py`, `phase5/build_outcomes.py` (R e ATR) | AVAILABLE_AND_VERIFIED | test 7.9K/7.26 passano qui (salvo un test SVG) | D1 e H4, non M15 | — |
| Rischio/rendimento | metriche backtest, ledger analytics | `backtest.py`, `server/ledger_analytics.py` | AVAILABLE_AND_VERIFIED | CI | — | — |
| Baseline vs variante | matched baseline (eventi); per strategie solo confronti manuali pre/post fix | `engine/baseline_engine_v4.py`; 7.14/7.18 | PARTIALLY_AVAILABLE | decision card FIX_CAUSALLY_VALIDATED | nessun runner automatico | — |
| Parità EA/Python | repliche ORDER_BLOCK, TSI, BREAKOUT_ACC; matrici semantiche LIQ_SWEEP | `phase7_13/16/17`, `phase7_9c…9f`, `phase7_23` | PARTIALLY_AVAILABLE | 78–80% su BREAKOUT_ACC | per strategia, non generalizzato | — |
| Strategy Tester MT5 | `/config` manuale, certificati (`NXS_TestValidityCertificate.mqh`), compile via worker | `MQL5/`, `LocalBridge/nexus_local_worker.py` | PARTIALLY_AVAILABLE | molti run reali (7.8–7.25) | **manuale**, niente `run_tester`, niente coda | handler `run_tester` |
| Reporting e decision card | decision card per fase, evidence ledger, read model API | `phase6_6/`, `phase7_*/decision_card*.json`, `server/research_read_model.py`, `/api/research/*` | AVAILABLE_AND_VERIFIED | test backend in CI | — | — |
| Registro esperimenti | experiment, hypothesis, data exposure, failure map, priority queue | `phase7/phase7_26/*.json`, `/api/research/control-plane/*` | AVAILABLE_AND_VERIFIED | `test_research_control_plane_v2` in CI | 9 esperimenti backfillati | — |
| Visual audit | rendering SVG di eventi | `phase7_26/`, `/api/research/control-plane/visual-audits` | PARTIALLY_AVAILABLE | 1 test SVG fallisce qui | — | — |
| Calendario macro storico | — | — | MISSING | `/api/calendar` = `SYNTHETIC_DEMO` | — | fonte con licenza chiara |
| Calendario MT5 live | `NXS_NewsFilter.mqh` (`CalendarValueHistory`) | EA | PARTIALLY_AVAILABLE | codice | `InpUseNews=false` di default ("il backtest non ha news filter", `NXS_Inputs.mqh:459`); le funzioni Calendar di MQL5 non lavorano nel Strategy Tester (limite noto della piattaforma, non verificato qui) | — |
| Allineamento notizia/prezzo | — | — | MISSING | — | — | — |
| Conversione ora italiana | — | — | MISSING | nessun `zoneinfo` | — | — |

---

## C. Evidence Reuse Report

### C.1 Riutilizzabile senza ripetere il lavoro

- **Infrastruttura metodologica Phase 5–7**: feature causali, firing-rate guard, baseline v4, BH-FDR, preregistrazione, validation ledger, path anatomy. È la parte con il valore più alto e la meno legata a singole strategie.
- **Dataset tick 2023-02-04 → 2026-09-16** con integrità verificata e partizioni dichiarate prima di vedere i dati. Per una nuova ipotesi comportamentale la partizione `development_discovery` è usabile. `locked_validation` e `final_holdout` non risultano consumate nel ledger (vedi rischio in C.3).
- **MARKET_STATE_V1 (2019–2022)**: riusabile come terreno di sviluppo, già marcato `DISCOVERY_REUSE`.
- **Mappa dei difetti**: la classe CROSS_TIMEFRAME_STATE_CONTAMINATION (`phase7_10/cross_timeframe_state_contamination_failure_memory_v1.json`) e la failure map (`phase7_26/failure_map_v1.json`, 18 classi). Dicono già cosa non rifare.
- **Risultati negativi robusti**: CRT (griglia di 36 combinazioni, costi dominanti), MACD (2 anni su 3 negativi), RSI_DIV (−17,5 R su 6 anni), H006 sweep-reclaim (holdout vero BORDERLINE, ΔP 0,057 contro la soglia 0,15). Non vanno ripetuti.
- **Dataset canonico BREAKOUT_ACC V2** (`phase7_9k/breakout_acc_intended_d1_v2_dataset.json`): l'unico artifact economico classificato REUSABLE per l'implementazione attuale (`phase7_20/evidence_reusability_v1.json`).
- **Regime benchmark 7.27**: la dominanza BUY delle strategie è in gran parte spiegata dal regime di mercato. È un controllo da riapplicare a ogni nuova scoperta su oro 2019–2026.

### C.2 Non riutilizzabile come prova dell'implementazione attuale

- `knowledge/strategy_database.json`, `knowledge/backtest_database.json`, `vault/01-Trading/Strategie/*.md`: generazione di luglio, superati.
- Tutto ciò che riguarda ORDER_BLOCK e TSI prima dei fix (7.14 e 7.18): `HISTORICAL_CONTAMINATED` / `POSSIBLY_CONTAMINATED`.
- `results/phase2_*`, `phase_partA/B_*`, sweep37: pre-fix e pre-cost-model.
- Le 9 strategie DEFECT_BLOCKED: qualsiasi loro numero è inaffidabile finché il difetto non è corretto.
- Qualsiasi risultato con `data_source="synthetic"` o con test MT5 prima del 2023-09-11 dichiarato "real ticks".

### C.3 Rischi di affidabilità trovati in questa ricognizione

1. **Holdout sigillato già attraversato da un'altra via.** Il seal Phase 7 vale per la pipeline Python sui tick. Gli studi MT5 7.21–7.25 su ORDER_BLOCK (2023-10 → 2026-09), LIQ_SWEEP e BREAKOUT_ACC hanno però guardato prezzi e trade fino a fine settembre 2026, cioè dentro la finestra 2026-02-04 → 2026-09-16 (`phase7_26/data_exposure_registry_v1.json`). Per ipotesi vicine a quelle strategie (sweep, OB, breakout) la finestra non è più "mai vista".
2. **OOS per strategia esauriti**: BREAKOUT_ACC (1 trade), ORDER_BLOCK (0), LIQ_SWEEP (6) hanno consumato il loro OOS; un nuovo OOS richiede dati futuri.
3. **Riproducibilità**: dei test in `server/research_scripts` (non in CI), qui ne passano 752, 86 falliscono e 7 non si caricano. Cause: 70 file solo sul PC (`multi_tf_dataset_v1.json` ×39, `C:\…\NEXUS_trades.csv` ×19, `nxs_m15_gold_extended.csv` ×11, un trace ORDER_BLOCK), `scipy` mancante (5 moduli), alcuni test-snapshot ormai superati dal codice. I risultati delle fasi 7.9H, 7.13, 7.15–7.18 e 7.25 **non sono riproducibili da un clone del repository**.
4. **Gli artifact si riscrivono da soli.** Eseguendo i test, 4 file versionati in `phase7_9c/` sono stati rigenerati (stesso `canonical_sha256 73a8559c…`, cambiano timestamp e righe CSV). Li ho ripristinati con `git checkout`. Lanciare la suite di ricerca sporca il working tree.

---

## D. Infrastructure & Compute Map

| Carico | Dove gira | Dipendenze | Limiti documentati |
|---|---|---|---|
| Download tick Dukascopy | PC Windows (o qualunque host con accesso) | rete verso `datafeed.dukascopy.com` | bloccato in questo container; 226 M tick: dimensione non registrata nei manifest (stima: diversi GB compressi), comunque oltre il disco Render da 1 GB |
| Pipeline Phase 5–7 (feature, eventi, baseline, inferenza) | PC (dove stanno i tick) | numpy, pandas, **scipy non dichiarato** | — |
| Backtester Python e ottimizzazioni | Render (`/api/backtest/*`, job asincroni in `nexus_jobs`) o locale | Stooq/Yahoo/cache Dukascopy M15 | Render starter, disco persistente 1 GB su `/data` (`render.yaml`), job con rate limit (`JobRejected` → 429) |
| Strategy Tester MT5 | PC, `C:\MT5-Tester` (terminale separato) | MT5, junction `Include\NEXUS_v1`, `.set` manuali | manuale, nessuna coda, un run alla volta; tick reali XM dal 2023-09-11 |
| Compile EA | PC via worker (`handle_compile_ea`) | MetaEditor del terminale giusto | vietato sul LIVE_TERMINAL (`nexus_terminal_profiles.config.example.json`) |
| EA live/demo | PC, `C:\Program Files\MetaTrader 5` | conto XM | — |
| Read model e API ricerca | Render | artifact versionati | solo lettura |
| LLM locali | PC, Ollama (ministral-3:3b) | — | ragionamento scientifico BASIC (`orchestrator_v1/agent_capability_registry_v1.json`) |
| Database | SQLite (`/data/nexus.db` su Render) + JSON/CSV versionati | — | — |
| Persistenza artifact | git per JSON e CSV piccoli; dati pesanti gitignored sul PC | — | nessun backup documentato dei tick sul PC |

---

## Agenti, skill e automazioni (sezione 7)

| Componente | Dichiarato | Codice invocabile | Test superato | Automatizzato davvero |
|---|---|---|---|---|
| "Research Agent", "Strategy Analyst", "Backtest Agent", "Risk Analyst", "Optimization Agent" | stazioni del Command Floor (`frontend/src/command/stations.js`) | **no** (le stazioni hanno `tools: ["NON_CONNECTED"]`) | test frontend solo sulla rappresentazione | no |
| Registro agenti | 5 agenti: 2 Ministral locali, Claude, Codex, ChatGPT ("non connesso") | routing in `orchestrator_v1`, `jarvis_v1` | `test_orchestrator_v1_*` in CI | routing sì, ricerca no |
| Jarvis | Telegram/Web, approvazioni, task handoff, programming plan | `server/jarvis_v1/` | molti test in CI | nessuna rotta verso la pipeline di ricerca (grep su `research`/`backtest` in `local_operations.py` e `floor_workflow.py`: nessun risultato) |
| Dispatcher e coda | durable queue in-process su Render | `NEXUS_QUEUE_DISPATCHER_*` | `test_durable_queue_dispatcher_v1` | sì, per task Jarvis e revenue |
| Compute jobs | backtest e optimize asincroni | `nexus_jobs.py`, `_submit_compute_job` | `test_compute_jobs` | sì, su richiesta (motore Python) |
| Worker locale MT5 | ping, compile, restart, deploy, open chart, template | `LocalBridge/nexus_local_worker.py` | `test_command_contract`, identity guard | sì, ma senza Strategy Tester |
| Skill | `mql5-engineering` (convenzioni + verifier statico) | `.claude/skills/mql5-engineering/verifier.py` | eseguito in questa sessione | — |
| Job pianificati | revenue automation; nessun job di ricerca | `render.yaml` | — | nessuno per la ricerca |

---

## E. Gap Analysis: i cinque blocchi principali per lo studio XAUUSD

1. **Niente pipeline multi-timeframe causale H4→M15 sui tick autentici.** I builder esistono solo per H4. Le sequenze dichiarano M15 come "gap". Il detector PULLBACK esistente è patologico (83% delle barre).
2. **I dati autentici e il calcolo stanno solo sul PC.** Tick 2023–2026, ledger degli holdout e dataset multi-TF sono gitignored. Metà delle prove non si riproduce da un clone. Da qui Dukascopy non è raggiungibile.
3. **Indipendenza degli holdout compromessa per famiglie vicine a sweep, OB e breakout** (C.3.1), e OOS per strategia esauriti. Ogni nuova scoperta serve una regola di esposizione esplicita prima di partire.
4. **Il Strategy Tester non è automatizzabile** (niente `run_tester`, niente coda): il trasferimento scoperta → EA → verifica di fedeltà resta manuale, una run alla volta.
5. **Nessuna base macro.** Nessun calendario storico con actual/forecast/previous e orari di pubblicazione. Il calendario MT5 non funziona nel Tester. L'impatto delle notizie oggi non è studiabile.

Gap trasversali minori: `scipy` non dichiarato, inferenza 7.4 non validata, walk-forward copiato in più script, nessuna conversione oraria Italia/UTC/broker centralizzata.

---

## F. Reuse-First Roadmap: il percorso più breve per il Behavior Lab

1. **Rendere riproducibile l'ambiente (giorno 0).** Dichiarare `scipy` (con versione) nei requirements di ricerca. Scrivere un comando unico che sul PC verifichi i manifest Phase 7 e MARKET_STATE_V1. Isolare i test che riscrivono artifact.
2. **Barre M15 da tick, stesso metodo delle H4.** Riusare `phase7_1/build_h4_bars_p71.py` cambiando solo la durata della barra (BID, griglia UTC, buffer di lookback). Registrare hash e versione in `dataset_version_registry_v2.json`.
3. **Regola di esposizione prima di guardare.** Usare solo `development_discovery` (2023-02-04 → 2024-08-03) per esplorare. Dichiarare `internal_validation` per lo screening. Annotare in `data_exposure_registry` che la finestra 2026 è già stata vista via MT5.
4. **Detector formalizzati, uno alla volta.** Impulso H4: partire da DISPLACEMENT/VOLATILITY_EXPANSION, che hanno firing rate sano. Pullback: nuovo detector, perché quello esistente è patologico; deve passare `event_firing_rate_guard`. Conferma M15: definita solo con barre M15 chiuse dopo la chiusura della H4 che ha generato l'evento. Contratto: `phase7_3/sequence_detector_contract_v1.json`.
5. **Event study con il motore esistente.** Baseline v4 per gli abbinamenti, outcome R/ATR e path anatomy (MFE/MAE), BH-FDR sulla famiglia dichiarata, regime benchmark 7.27 come controllo. Niente backtest di strategia in questa fase.
6. **Solo dopo un esito SUPPORTED**: replica in MQL5 in Research Mode, export della trace e matrice di parità come in 7.9C/7.14. Poi un unico run in Tester su tick reali XM (dal 2023-09-11).

---

## G. First Experiment Readiness: H4 impulse → pullback → M15 confirmation

**Verdetto: NO, non oggi così com'è.**

**Singolo blocker più importante:** non esiste una serie M15 costruita in modo causale dagli stessi tick Dukascopy 2023–2026 da cui derivano le H4, né un detector formalizzato che leghi un evento H4 a una conferma M15 successiva alla sua chiusura.

Per questo l'esperimento non si può eseguire con dati autentici senza inventare un allineamento. Le alternative oggi disponibili hanno ciascuna un difetto:

- l'export MT5 M15 copre solo 10 mesi ed è su griglia server;
- `nxs_m15_gold_extended.csv` ha provenienza non accertata;
- la cache del backtester è in mid e non è nel repository.

Cosa è già pronto e va riusato: tick con bid/ask e integrità verificata (sul PC), builder H4, 26 feature causali, detector impulso (DISPLACEMENT, VOLATILITY_EXPANSION), baseline v4, BH-FDR, preregistrazione, validation ledger, path anatomy.

Verifiche preliminari, prima di lanciare qualsiasi cosa:

1. Sul PC, ricalcolare l'hash di `data_cache_new_period/manifest.json` e confrontarlo con `605249c6…` (`dataset_version_registry_v2.json`).
2. Verificare che `validation_access_log` sia ancora vuoto per `locked_validation` e `final_holdout`.
3. Installare `scipy` e far passare `phase7/phase7_4/test_*` e `phase7/phase7_3/test_phase7_3_synthetic_suite.py`.
4. Costruire le M15 e verificare che ogni H4 coincida con l'aggregazione delle sue 16 M15 (open, high, low, close identici).
5. Preregistrare ipotesi, finestra, orizzonte, outcome primario e famiglia FDR **prima** di calcolare un solo outcome.
6. Far passare il nuovo detector PULLBACK da `event_firing_rate_guard` (firing rate fuori dalla fascia patologica).

---

## Risposte alle 12 domande

1. **Comportamento storico dell'oro su H4 e M5/M15?** H4 sì: 2019–2022 nel repository, 2023–2026 sul PC dai tick, con feature causali. M15/M5 solo in modo parziale: export MT5 brevi, cache mid del backtester, tick grezzi senza builder M15.
2. **Rilevare automaticamente impulsi, pullback, inversioni, sweep e continuazioni?** In parte. Su H4 ci sono detector per breakout, displacement, sweep, reclaim, retest e failed breakout. Il pullback è patologico. L'EA esporta eventi strutturali sweep/break/retest su M5–D1, ma solo per gen–ago 2026. "Continuazione" e "inversione" esistono solo come sequenze non formalizzate.
3. **Usare e confrontare gli indicatori MT5?** Sì via export dal terminale (H4 e MACD già fatti). Il confronto ha mostrato differenze dovute a feed e griglia oraria, non al calcolo. Su larga scala serve il terminale.
4. **Confluenze tra prezzo, indicatori e timeframe?** Su un solo timeframe (H4) sì, con feature e baseline. Tra timeframe no: manca l'allineamento causale H4/M15.
5. **MFE/MAE e probabilità di continuazione dopo un evento?** Sì: path anatomy engine, outcome R/ATR di Phase 5 e probabilità di evento contro baseline con CI di Wilson e beta-binomiale (H006). Testato su D1/H4.
6. **Impatto storico delle notizie?** No. Non c'è un calendario storico e quello del backend è sintetico.
7. **Migliaia di eventi senza leakage?** Sì come metodo: preregistrazione, cross-split safety, ledger one-shot, dependence diagnostics, BH-FDR. Con due riserve: l'inferenza dipendenza-aware della 7.4 non è validata, e la finestra 2026 è già stata vista via MT5 per famiglie affini.
8. **Framework OOS e walk-forward?** OOS e holdout sì e rigorosi (partition contract v2). Walk-forward solo come funzioni copiate in script ad hoc, senza una libreria unica.
9. **Affidabilità dei risultati accumulati?** Alta per i negativi robusti (CRT, MACD, RSI_DIV, H006) e per l'infrastruttura. Bassa per tutto ciò che precede i fix di luglio–settembre. Media per i CANDIDATE, con campioni OOS piccoli o assenti. Nessuna strategia ha oggi un edge validato su OOS indipendente.
10. **Trasferire una strategia all'EA e verificarne la fedeltà in MT5?** Sì, ma a mano: il metodo esiste (repliche, trace diagnostiche, matrici di parità, certificati del Tester), con parità tipica del 78–80% per differenze di feed. I tick reali XM partono solo dal 2023-09-11. In alternativa si può usare il simbolo custom con tick Dukascopy.
11. **Cosa si può automatizzare già oggi?** Download e verifica tick (sul PC), build H4 e feature, event study sui detector sani, multiple testing, path anatomy, registri e read model, backtest Python asincroni, compile e deploy via worker. Non si possono automatizzare: Strategy Tester, conferma M15, notizie.
12. **Minimo sviluppo per avviare il Behavior Lab?** Quattro cose:
    1. dichiarare `scipy`;
    2. scrivere un builder M15 dai tick Phase 7 con controllo di coerenza H4/M15;
    3. formalizzare un detector pullback che passi il firing-rate guard, più la regola di conferma M15 post-chiusura H4;
    4. preregistrare il primo esperimento su `development_discovery`.

    Tutto il resto (baseline, FDR, path anatomy, registri) si riusa.
