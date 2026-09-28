# NEXUS - Phase 7.27 — GOLD BUY-Dominance Benchmark Test

**Baseline:** `f4834cb` (Phase 7.26, Research Safety Net V1). Nessuna modifica MQL5/strategie. Nessuna optimization. Nessun nuovo backtest MT5 (tutto calcolato su serie di prezzo già esistenti). Nessun deploy.

**Obiettivo**: verificare se la dominanza BUY condivisa da BREAKOUT_ACC, ORDER_BLOCK e LIQ_SWEEP (candidate hypothesis nata dalla Cross-Strategy Synthesis, Phase 7.26) contiene informazione specifica delle strategie, o riflette principalmente il regime rialzista strutturale di XAUUSD nel periodo studiato.

---

## 1. Preregistrazione

Congelati **prima** di calcolare qualunque risultato: 3 strategie incluse (BREAKOUT_ACC 36 BUY, ORDER_BLOCK 12 BUY, LIQ_SWEEP 39 BUY — TSI escluso, nessun dataset economico), i 3 dataset di **discovery** (non holdout), 7 orizzonti fissi in barre D1 [1,3,5,10,20,40,60] con **h10 come orizzonte primario**, 8 metriche, 5 benchmark, matching rules (solo informazione causale/trailing), exclusion rules (nessun cherry-picking), seed dichiarati. Fonte di prezzo unica per tutte e 3 le strategie e i benchmark: la serie D1 già usata dal progetto per BREAKOUT_ACC (`phase7_9h/raw_data/nxs_d1_gold_phase79h.csv`, 2019.01.02–2026.08.19 — l'unica che copre l'intera finestra di tutte e 3).

## 2. Benchmark

5 costruiti: **RANDOM_TIMESTAMPS_MATCHED** (N barre casuali, seed dichiarato), **UNCONDITIONAL_LONG_EXPOSURE** (media sull'intera popolazione di barre, nessun campionamento), **PERIODIC_ENTRY_LONG** (intervalli fissi deterministici), **REGIME_MATCHED_RANDOM_LONG** (appaiato 1:1 per bucket trend×volatilità, l'unico realmente causale rispetto al regime), **BUY_AND_HOLD** (solo contesto macro, mai un confronto trade-per-trade). Regime classificato causalmente: trend = pendenza SMA50 trailing, volatilità = ATR14 trailing in terzili (bordi calcolati sull'intera distribuzione — limite dichiarato), anno, posizione vs SMA200. Tutti e 3 i BUY reali hanno trovato un match di regime (0 unmatched).

## 3-5. Risultati per strategia (tenute separate)

Analisi **primaria**: REGIME_MATCHED_RANDOM_LONG (design appaiato) @ h10, forward_return_price_units.

| Strategia | n | Direzione | Media diff. appaiata | CI95 | Significativo? |
|---|---|---|---|---|---|
| BREAKOUT_ACC | 36 | REAL_BETTER | +5,15 | [-43,08, +54,81] | No |
| ORDER_BLOCK | 10* | REAL_BETTER | +50,76 | [-24,05, +154,52] | No |
| LIQ_SWEEP | 39 | REAL_WORSE | -7,05 | [-73,04, +63,34] | No |

*ORDER_BLOCK: 2/12 eventi censurati a h10 (fine serie) — campione minimo dichiarato in preregistrazione.

**Nessuna delle 3 strategie batte significativamente il benchmark regime-matched all'orizzonte primario.** Su tutti i 7 orizzonti × 3 strategie (21 confronti regime-matched): solo **1 "significativo"** (ORDER_BLOCK, h1, il più corto, n=12) — e si **inverte di segno** entro h40/h60, pattern coerente con rumore campionario, non con un segnale robusto.

## 6. Risultato cross-strategy

**`NONE_BEATS_REGIME_MATCHED_BENCHMARK_SIGNIFICANTLY`**. 2/3 strategie mostrano direzione media favorevole ma nessuna in modo significativo; la concordanza direzionale **non** è stata trasformata automaticamente in edge.

## 7. Anti-leakage e data exposure

Tutti e 3 i dataset usati sono di **discovery** (già esposti in Phase 7.21/7.22/7.24-25) — nessun holdout consumato per questa prima verifica, come richiesto. Registrato in `GLOBAL_DATA_EXPOSURE_REGISTRY_V1` come nuovo record `BUY_DOMINANCE_BENCHMARK_V1_2019-2026`, `holdout_status=DERIVED_FROM_DISCOVERY_DATASETS`. Qualunque risultato positivo resta **`SUPPORTED_AS_HYPOTHESIS`**, mai promosso a edge.

## 8. Multiple testing

**84 confronti statistici totali** (3 strategie × 7 orizzonti × 4 benchmark statistici), **3 primari** (1 per strategia, REGIME_MATCHED @ h10) usati per la decisione — gli altri 81 sono **exploratory**, mai usati per scegliere il confronto più favorevole. L'unico risultato "significativo" (ORDER_BLOCK h1) non sopravvive nemmeno a una correzione Bonferroni minima sui soli confronti esplorativi.

## 9. Decisione finale

**`BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME`**

Nessuna delle 3 strategie mostra un effetto BUY statisticamente distinguibile dal semplice essere long GOLD in un regime di trend/volatilità comparabile, con questo campione. Non è un rigetto netto (2/3 direzioni restano nominalmente favorevoli) — ma il segnale di selezione specifico della strategia, se esiste, è troppo debole per emergere da questo test.

## 10. Aggiornamento Safety Net

Senza reinterpretare retroattivamente i verdict esistenti (verificato: H1_BREAKOUT_ACC/H_ORDER_BLOCK/H_LIQ_SWEEP restano `INCONCLUSIVE` come in Phase 7.26):

- **HYPOTHESIS_REGISTRY_V1**: +1 (`H_BUY_DOMINANCE_MARKET_REGIME_ARTIFACT`, stato `TESTING` — non `SUPPORTED`, perché i dataset restano di discovery).
- **EXPERIMENT_REGISTRY_V1**: +1 (`EXP_BUY_DOMINANCE_BENCHMARK_CROSS_STRATEGY`).
- **CROSS_STRATEGY_LEARNING_PACKET_V1**: aggiunta un'osservazione a BREAKOUT_ACC/ORDER_BLOCK/LIQ_SWEEP (non sostituiti i campi esistenti).
- **CROSS_STRATEGY_SYNTHESIS_V1**: aggiunto un nuovo finding OBSERVATION che risolve (senza cancellare) il CANDIDATE_HYPOTHESIS originale.
- **RESEARCH_PRIORITY_QUEUE_V1**: `BUY_BIAS_BENCHMARK_VS_BUY_AND_HOLD` marcato `COMPLETED_PHASE_7_27`; nuovo top priority = backfill temporal/exit-efficiency per BREAKOUT_ACC/ORDER_BLOCK.
- **GLOBAL_DATA_EXPOSURE_REGISTRY_V1**: +1 record (non nella lista esplicita del task ma necessario per evitare riferimenti orfani nell'experiment registry).

## Deliverables

`nxs_gold_d1_loader.py`, `nxs_regime_classifier.py`, `nxs_real_buy_events_loader.py`, `nxs_prereg_constants.py`, `nxs_benchmark_generators.py`, `nxs_outcome_metrics.py`, `build_preregistration.py`, `build_benchmark_samples.py`, `build_per_strategy_results.py`, `build_regime_controlled_analysis.py`, `build_cross_strategy_results.py`, `build_multiple_testing_accounting.py`, `build_buy_dominance_decision_card.py` + i rispettivi JSON, `verify_phase_7_27.py` (VERIFY OK, richiama anche il verificatore di Phase 7.26), `test_phase_7_27.py` (28/28), questo vault report. Aggiornamenti a Phase 7.26: `build_hypothesis_registry.py`, `build_experiment_registry.py`, `build_cross_strategy_learning_packet.py`, `build_cross_strategy_synthesis.py`, `build_research_priority_queue.py`, `build_data_exposure_registry.py`, `nxs_backfill_sources.py`.

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`, `contracts/`. Nessuna fase 7.9x-7.25 toccata (diff zero verificato). Solo Phase 7.26 aggiornata, autorizzata esplicitamente dal task (registry viventi). Nessuna optimization, nessun nuovo backtest MT5, nessun deploy.

## Regressione

Suite Phase 7.27: 28/28 pass. Suite Phase 7 completa: 844 passed, 7 failed (stessi 7 self-check di staleness pre-esistenti già noti da prima di questa fase — phase7_12, phase7_13, phase7_15 ×2, phase7_17, phase7_9h ×2 — nessun nuovo fallimento introdotto, `git diff` zero su tutti i file coinvolti). Effetto collaterale noto reintegrato: `phase7_9c/breakout_acc_{mt5,python}_event_stream_v1.json` (solo timestamp) revertito con `git checkout --` prima del commit.

---

```
7.26: NEXUS RESEARCH SAFETY NET V1 - COMPLETATO
7.27: GOLD BUY-DOMINANCE BENCHMARK TEST - COMPLETATO

PREREGISTRATO: 3 strategie (36+12+39 BUY), dataset di discovery (non
  holdout), serie D1 unica 2019-2026, orizzonti [1,3,5,10,20,40,60]
  barre (primario h10), 5 benchmark, seed dichiarati

PER STRATEGIA (primario: REGIME_MATCHED_RANDOM_LONG @ h10, appaiato):
  BREAKOUT_ACC (n=36): +5.15 CI95[-43.08,+54.81] - NON significativo
  ORDER_BLOCK  (n=10): +50.76 CI95[-24.05,+154.52] - NON significativo
  LIQ_SWEEP    (n=39): -7.05 CI95[-73.04,+63.34] - NON significativo

CROSS-STRATEGY: NONE_BEATS_REGIME_MATCHED_BENCHMARK_SIGNIFICANTLY
  84 confronti totali, 3 primari, 81 esplorativi - 1 solo "significativo"
  (ORDER_BLOCK h1, n=12) che si inverte di segno e non sopravvive a
  Bonferroni - concordanza NON trasformata in edge

DECISIONE: BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME
  (2/3 direzioni nominalmente favorevoli ma nessuna significativa)

SAFETY NET AGGIORNATO (non reinterpretato retroattivamente):
  +1 hypothesis (TESTING, non SUPPORTED - dataset di discovery)
  +1 experiment, +1 learning packet observation x3, +1 synthesis
  finding, priority queue: BUY_BIAS_BENCHMARK completato

PROSSIMO (Research Priority Queue): backfill temporal_concentration
  ed exit_efficiency per BREAKOUT_ACC/ORDER_BLOCK (costo zero, dati
  gia' esistenti) - poi tornare a testare strategie singole
  (LIQ_SWEEP forward passivo, FVG_CONT integrity audit)
```
