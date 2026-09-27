# NEXUS - Phase 7.22 — ORDER_BLOCK EDGE_VALIDATION_V1

**Baseline:** `d8f365e` (Phase 7.21, BREAKOUT_ACC). Nessun lavoro concorrente rilevato. **BREAKOUT_ACC resta congelata** nella sua configurazione forward (Phase 7.21, non toccata). **TSI non toccata.** Nessuna optimization/TP-SL sweep/risk sizing/compounding/martingala/eliminazione BUY-SELL post-hoc/modifica della geometria della zona in questa fase.

**Obiettivo**: determinare se ORDER_BLOCK post-fix (V2, TF-guarded) possiede un edge economico reale e trasferibile, usando esclusivamente l'implementazione canonica già validata causalmente (Phase 7.14) — la prima misurazione economica in assoluto per questa identità implementativa (mai fatta prima).

---

## 1. Identità e perimetro congelati

`NXS_Strat_OrderBlock()` V2 (guardia TF-scoped, Phase 7.14/7.15), TF canonico D1, selettore 15 isolato. OB_MIT tenuto **separato** (disabilitato in tutti i run di questa fase — nessun dato economico OB_MIT prodotto o dedotto). Tutta l'evidenza pre-fix (phase2_baseline, phase_partB, trace diagnostico Phase 7.14) marcata esplicitamente **non riutilizzabile** — nessun vecchio PF/WR usato come baseline.

## 2. Scoperta metodologica importante durante l'esecuzione

Un primo tentativo di run di discovery (2019.02–2026.06, ~7.4 anni, stessa finestra di BREAKOUT_ACC) è stato **interrotto** dopo aver osservato un ritmo di elaborazione di ~2%/5min (proiezione ~4 ore) — non pratico, sostituito con la finestra già nota di Phase 7.14 (2023.10.02–2026.06.30, ~2.9 anni). Al completamento (2h22min), l'estrazione ha rivelato che **`NEXUS_trades.csv` è un log persistente mai azzerato fra sessioni**: conteneva GIÀ 13 trade ORDER_BLOCK reali (2024.04.08–2026.08.24), quasi certamente prodotti dal run diagnostico originale di Phase 7.14 (stessa finestra, stesso meccanismo di logging attivo di default) **settimane prima di questa fase**. Il certificato ufficiale di quella run precedente (trovato senza suffisso `_rXXX`, period_end=2026.08.24) conferma GENERATED=25/BLOCKED=13/OPENED=12 — sostanzialmente coerente con i 13 trade nel CSV (scarto di 1, non risolto, dichiarato esplicitamente). I certificati prodotti dai run di QUESTA fase erano incoerenti (GENERATED=2) — anomalia dichiarata, non nascosta: il CSV riga-per-riga resta la fonte di verità (MT5 = ground truth), non il certificato. **Conseguenza pratica**: i dati erano già sufficienti — il run pluriennale non era a posteriori necessario. Un secondo bug (minore) scoperto e corretto nella stessa fase: `entry_lots` letto per errore dalla riga OPEN (sempre 0.00 per costruzione di `NXS_LogTradeCSV`) invece che dalla riga CLOSE — non influiva su P&L/PF/WR, solo sul calcolo del margine.

## 3. DATA_EXPOSURE_MAP

I 13 trade (2023.10.02–2026.08.24) sono stati **guardati per una domanda diversa** (integrità del fix, Phase 7.13/7.14/7.16 su segnali/zone, mai su P&L) — trattati come baseline economica descrittiva di prima misurazione, mai come conferma indipendente. **Unica finestra genuinamente untouched**: 2026.08.25–2026.09.27 (~1 mese, i dati esistenti coprivano già fino al 24/08) — eseguito un run MT5 dedicato per questa finestra.

## 4. Baseline economica (13 trade reali, fill/P&L netto reali)

**ALL**: expectancy netta **+$38.26/trade** (+0.72R), PF **1.86**, WR 46%, payoff ratio 2.17, DD max $331, recovery factor 1.50, 3 perdite consecutive massime, ~5.5 trade/anno, holding medio 20.6 giorni. **BUY** (n=12): +$48.64/trade, PF 2.19, WR 50%. **SELL** (n=1, unico trade): -$86.30, perdente — campione troppo piccolo per qualunque conclusione propria, non eliminato nonostante la performance negativa (vietato dal task).

## 5. Concentrazione del profitto

Stesso pattern già visto in BREAKOUT_ACC: **estrema**. Il solo trade migliore spiega il 57% del netto totale; i primi 3/13 spiegano il 143% (rimuovendoli il risultato diventa negativo, -$215); i primi 5/13 il 197%. Dichiarato esplicitamente.

## 6. Cost stress

Sopravvive a COST_BASE (+$38.26)/COST_MODERATE (+$37.76)/COST_STRESS (+$36.26) — impatto dei costi assunti minimo rispetto all'ampiezza tipica dei movimenti (SL/TP nell'ordine di decine/centinaia di $ su GOLD).

## 7. Execution realism

Funnel aggregato (certificato base, non per-evento come BREAKOUT_ACC): 25 segnali generati → 13 bloccati (52%) → 12 tentativi d'ordine → 12 aperti, 0 rifiuti broker. Nessun proxy di qualità del segnale bloccato disponibile in questa fase (gap dichiarato, a differenza di BREAKOUT_ACC che aveva un dataset per-evento dedicato).

## 8. Visual Audit (6 eventi: 2 winner, 2 loser, 2 random)

Stage A con mascheramento strutturale (nessun campo di esito nell'oggetto di review), stesso limite dichiarato di Phase 7.21 (mascheramento di dati, non di operatore/memoria). Nessuna regola operativa derivata.

## 9. Robustezza temporale

2024: -$33.20 (4 trade, WR 25%) — anno negativo. 2025: +$317.20 (5 trade, WR 60%). 2026 (parziale): +$213.40 (4 trade, WR 50%). Solo 3 "anni" nello stesso campione continuo (non regimi indipendenti verificati).

## 10. Incertezza statistica (bootstrap, 10.000 iterazioni, seed dichiarato)

**ALL: CI 95% [-$42.39, +$118.82] — INCLUDE LO ZERO** (non distinguibile dal caso con questo campione). **BUY: CI [-$38.04, +$131.85] — include lo zero.** **SELL: CI degenere (n=1)** — esclude lo zero per costruzione (nessuna varianza), non un segnale statistico reale.

## 11. OOS forward — nuovo run MT5 dedicato

Finestra 2026.08.25–2026.09.27, genuinamente mai attraversata. **Risultato: 0 segnali generati, 0 trade.** `INSUFFICIENT_OOS_SAMPLE` (non `FAILED`, esito esplicitamente ammesso). Il certificato del run mostra VERDICT=FAIL/MISSING_TELEMETRY — artefatto noto del meccanismo quando zero eventi si verificano, confermato indipendentemente dal CSV grezzo (0 righe) come genuino silenzio del segnale, non un errore del run.

## 12. Minimum Viable Capital

Leva reale osservata nel certificato: **1:500** (non 1:100 come richiesto nell'ini — stessa leva già usata nell'ini originale di Phase 7.14, usata qui il valore reale osservato).

| Capitale | Rischio %/trade (SL medio) | Margin % |
|---|---|---|
| 300€ | 22.6% | 2.23% |
| 500€ | 13.5% | 1.34% |
| 1.000€ | 6.8% | 0.67% |
| **2.500€** | **2.7%** | 0.27% | **← MINIMUM_VIABLE_CAPITAL** |
| 10.000€ | 0.7% | 0.07% |

Soglia: rischio medio a lotto minimo ≤5%. Il SL medio più ampio di BREAKOUT_ACC (holding multi-settimana) spinge il MVC a **2.500€**, più alto dei 1.000€ trovati per BREAKOUT_ACC.

## 13. Relazione con OB_MIT

Mantenuto separato per costruzione (selettore 15 isolato in tutti i run) — nessun dato economico OB_MIT prodotto, nessuna performance ORDER_BLOCK usata come proxy per OB_MIT.

## 14. Gate finale

**`EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION`** — stessa categoria di BREAKOUT_ACC (Phase 7.21). Check: (1) expectancy netta positiva — **PASS**; (2) cost survival — **PASS**; (3) execution non collassa — **PASS**; (4) nessuna concentrazione estrema — **FAIL** (top-5 = 197% del netto); (5) evidenza indipendente sufficiente — **FAIL** (0 trade forward). Non significa live-ready. Congelata una configurazione forward (entrambe le direzioni, nessun tuning) — non eseguita.

## Confronto con BREAKOUT_ACC (Phase 7.21)

| | BREAKOUT_ACC | ORDER_BLOCK |
|---|---|---|
| N trade | 47 | 13 |
| Net exp/trade | +$13.66 | +$38.26 |
| PF | 1.62 | 1.86 |
| CI95 ALL include zero? | Sì | Sì |
| Concentrazione top-5 | 133.7% | 196.8% |
| OOS forward | 1 trade, perdente | 0 trade |
| MVC | 1.000€ | 2.500€ |
| Decisione | REQUIRES_FORWARD_VALIDATION | REQUIRES_FORWARD_VALIDATION |

Entrambe le candidate mostrano lo stesso pattern: expectancy nominalmente positiva ma statisticamente non distinguibile da zero, concentrata in pochissimi trade, campione OOS insufficiente. Nessuna delle due è ancora un edge dimostrato.

## Deliverables

`build_identity_and_perimeter.py`, `build_orderblock_data_exposure_map.py`, `build_canonical_economic_dataset.py`, `build_orderblock_baseline_economics.py`, `build_orderblock_cost_stress.py`, `build_orderblock_execution_realism.py`, `build_orderblock_visual_audit_sample.py`, `build_orderblock_temporal_robustness.py`, `build_orderblock_statistical_uncertainty.py`, `build_orderblock_oos_forward_analysis.py`, `build_orderblock_minimum_viable_capital.py`, `build_orderblock_decision_card.py`, `build_orderblock_frozen_forward_config.py` + i rispettivi JSON, `nxs_orderblock_dataset_loader.py`, trace reali committate (`nexus_trades_discovery.csv`, `nexus_trades_forward_oos.csv`), certificati MT5 (base + run di questa fase), verificatore indipendente (`verify_phase_7_22.py`, VERIFY OK), 28/28 test propri, questo vault report.

## Vincoli preservati

Nessuna modifica a `MQL5/`, BREAKOUT_ACC (Phase 7.21, verificato diff zero), TSI (Phase 7.18, verificato diff zero), registry, Product Platform. Nessuna optimization, TP/SL sweep, risk sizing, compounding, martingala, eliminazione BUY/SELL post-hoc, modifica geometria zona, promozione live.

## Regressione

(compilata dopo l'esecuzione della suite completa)

---

```
7.21: BREAKOUT_ACC EDGE_VALIDATION_V1 - EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION (congelata)
7.22: ORDER_BLOCK EDGE_VALIDATION_V1 - COMPLETATO
  scoperta: NEXUS_trades.csv (log persistente) conteneva GIA' 13 trade
    reali da un run precedente (Phase 7.14) - run pluriennale di questa
    fase non a posteriori necessario, dichiarato per la prossima volta
  bug trovato e corretto nella stessa fase: entry_lots letto dalla riga
    sbagliata (OPEN invece di CLOSE) - non influiva su P&L/PF/WR
  baseline (13 trade reali): ALL +$38.26/trade PF 1.86 WR 46%
    BUY (12) +$48.64/trade PF 2.19 | SELL (1, unico) -$86.30
  concentrazione ESTREMA: top-5/13 = 197% del netto (rimuovendo i
    primi 3 il risultato e' gia' negativo)
  incertezza statistica: CI95 ALL include lo zero (non distinguibile
    dal caso)
  OOS forward (nuovo run MT5, ~1 mese): 0 segnali, 0 trade -
    INSUFFICIENT_OOS_SAMPLE
  MINIMUM_VIABLE_CAPITAL: 2.500 EUR (leva reale 1:500, SL medio piu'
    ampio di BREAKOUT_ACC)
DECISIONE: EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION
  (PASS: expectancy positiva, cost survival, execution survival)
  (FAIL: concentrazione estrema, evidenza indipendente insufficiente)
  STESSA CATEGORIA DI BREAKOUT_ACC - nessuna delle due e' ancora edge
CONFIG FORWARD CONGELATA (non eseguita): selettore 15, ENTRAMBE le
  direzioni, nessun tuning, servono >=5 trade chiusi forward
PROSSIMO: nessuna promozione live. BREAKOUT_ACC e ORDER_BLOCK restano
  entrambe in accumulo forward passivo (mesi, cadenza bassa per
  entrambe) - valutare se procedere alla candidata successiva
  (LIQ_SWEEP/FVG_CONT, Phase 7.20) nel frattempo, come suggerito
  dall'utente
```
