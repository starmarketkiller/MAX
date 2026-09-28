# NEXUS - Phase 7.25 — LIQ_SWEEP EDGE_VALIDATION_V1

**Baseline:** `c9e429f` (Phase 7.24, Canonical Dataset Adjudication). BREAKOUT_ACC (7.21), ORDER_BLOCK (7.22), il Run Isolation Harness (7.23) e l'adjudication (7.24) restano **congelati** (diff zero verificato dal verificatore). Nessuna optimization, nessun tuning, nessun deploy.

**Obiettivo**: determinare se la versione canonica MT5 di LIQ_SWEEP (42 trade chiusi + 1 ancora aperto, dataset riconciliato in Phase 7.24) possiede un edge economico reale, robusto e trasferibile — usando MT5 come ground truth, senza inseguire la parity Python.

---

## 1. DATA_EXPOSURE_MAP

Il dataset dei 42 trade è già stato **visto** in Phase 7.24 (net P&L aggregato +$1.076,30 già calcolato e riportato) — **non trattato come blind/OOS** per quel numero specifico. È invece genuinamente **untouched** per ogni statistica più fine costruita in questa fase: expectancy per direzione, concentrazione, CI bootstrap, cost stress, robustezza temporale, path anatomy, visual audit, MVC. La finestra **2026.07.01–2026.09.27** è l'unico vero holdout mai attraversato — popolata con un nuovo run MT5 dedicato in questa stessa fase (punto 10).

## 2. Baseline economica (42 trade chiusi)

**ALL**: expectancy netta **+$25,63/trade**, PF **1,48**, WR 55%, payoff ratio, DD max, 8 anni... **BUY** (n=39): +$26,78/trade, PF 1,54, WR 56%. **SELL** (n=3, campione minimo, conservato per intero): +$10,60/trade, PF 1,11, WR 33% — nessun lato eliminato.

## 3. Profit concentration

Top 1 = 29,0% del netto; **top 3 = 80,8%**; **top 5 = 127,4%** (rimuovendo i primi 5 il risultato diventa **negativo**, -$294,60); top 10% (4 trade) = 104,3%. **L'edge sopravvive alla rimozione dei primi 3 trade (+$207,10) ma NON dei primi 5** — concentrazione elevata ma meno estrema di ORDER_BLOCK (che non sopravvive nemmeno ai primi 3).

## 4. Statistical uncertainty

Bootstrap IID (10.000 iter.) **e** block bootstrap (blocchi da 5 eventi consecutivi, sensitivity alla serial dependence — i gap fra entry vanno da 1 a 109 giorni, mediana 14). **ALL: CI95 IID [-23,87, +73,39] e BLOCK [-14,05, +78,96] — ENTRAMBI includono lo zero** (non distinguibile dal caso). Interessante divergenza per **BUY**: IID include lo zero, ma il BLOCK bootstrap lo esclude [+10,06, +87,62] — riportato onestamente come disaccordo fra i due metodi, non usato per scegliere il risultato che conferma l'edge.

## 5. Cost stress

Sopravvive a COST_BASE (+$25,63) / COST_MODERATE (+$25,13) / COST_STRESS (+$23,63) — impatto dei costi assunti minimo.

## 6. Execution realism

Separazione a 3 livelli: **signal-level opportunity** (3.672 segnali generati) → **executable trade** (49 tentativi d'ordine, dopo i gate — 3.623 bloccati, quasi tutti per `OPEN_POSITION`: singola posizione alla volta) → **realized trade** (42 chiusi + 1 ancora aperto). Funnel riconciliato al 100% (Phase 7.24), nessun conteggio scartato. Gap dichiarato: nessuna telemetria per-evento sui segnali bloccati (solo conteggi aggregati).

## 7. Temporal robustness

**Scoperta rilevante**: 2023 (-$80,30, 4 trade), 2024 (+$145,50, 14 trade), **2025 (+$1.069,70, 16 trade — il 99% del netto totale!)**, 2026 parziale (-$58,60, 8 trade). **Solo 2 anni su 4 positivi**, e il risultato aggregato dipende quasi interamente da UN SOLO anno. Rolling window (10 trade) non sempre positivo (minimo -$34,20). Nessun regime indipendente verificato — un solo run continuo.

## 8. Visual Audit REALE (non solo JSON)

**Nota tecnica**: matplotlib è risultato bloccato nell'ambiente di esecuzione (policy di sicurezza — `DLL load failed while importing _image`). **Pivot**: rendering SVG puro-Python (zero dipendenze native), stesso contenuto informativo. Generati **38 chart reali** (candele OHLC macro D1/H4 + dettaglio M15, livelli entry/SL/TP, marker entry/exit) per 6 eventi stratificati (2 winner, 2 loser, 2 random) × 3 stage (A blind/troncato all'entry, B percorso rivelato senza P&L, C outcome completo) + 2 chart per un **matched non-event** (punto medio del gap più lungo fra due trade, 25 giorni, regola dichiarata prima di guardare il prezzo). **blocked/near-miss dichiarato GAP** (non fabbricato): MQL5 non logga telemetria per-evento dei segnali bloccati, e ricostruirla in Python reintrodurrebbe il rischio di fedeltà già segnalato in Phase 7.23. Mascheramento Stage A strutturale (verificato dal verificatore: nessun campo di esito esposto, chart troncato all'entry bar).

## 9. Outcome/path anatomy (MFE/MAE, descrittivo)

Ricostruito dalla serie M15 GOLD per tutti i 42 eventi. MFE medio 128,8 price units, MAE medio 76,0. **Asimmetria osservata**: l'escursione avversa media prima di un WINNER (36,3) è molto più piccola dell'escursione favorevole media prima di un LOSER (80,4) — **OBSERVATION**: i perdenti tendono a muoversi favorevolmente più a lungo prima di invertire, rispetto a quanto i vincenti si muovano contro prima di vincere. **HYPOTHESIS** (non testata, non implementata): possibile pattern di "falso movimento"/mancato follow-through dopo lo sweep — nessuna regola operativa derivata.

## 10. OOS/forward — nuovo run MT5 dedicato

Finestra **2026.07.01–2026.09.27**, genuinamente mai attraversata, harness di isolamento (Phase 7.23). **Risultato: 6 trade chiusi (sopra la soglia di 5 dichiarata prima del risultato) — `SAMPLE_SUFFICIENT_FOR_A_FIRST_READ`.** Net P&L **-$539,30 totali, -$89,88/trade, WR 17%** — **nettamente negativo**. Prima volta nel corpus (BREAKOUT_ACC=1 trade, ORDER_BLOCK=0 trade) che un campione OOS abbastanza grande da essere informativo va contro l'edge storico, non semplicemente "insufficiente". Non prova che l'edge sia falso (n=6 resta piccolo) — ma è un segnale reale, non ignorabile.

## 11. Minimum Viable Capital

Leva reale 1:500. **MINIMUM_VIABLE_CAPITAL = 2.500€** (stesso livello di ORDER_BLOCK — SL ampio, holding multi-giorno).

| Capitale | Rischio %/trade (SL medio) |
|---|---|
| 300€ | alto |
| 1.000€ | sopra soglia |
| **2.500€** | **≤5% ← MVC** |
| 10.000€ | basso |

## 12. Nessuna optimization

Nessun TP/SL sweep, filter tuning, BUY-only/SELL-only, compounding, martingala, regime filter post-hoc. Pattern osservati riportati come OBSERVATION → HYPOTHESIS, mai come regola applicata.

## 13. Decision Card finale

**`EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION`**

Check: (1) expectancy netta positiva — **PASS**; (2) cost survival — **PASS**; (3) execution non collassa — **PASS**; (4) nessuna concentrazione estrema — **FAIL** (top-5=127,4%, edge non sopravvive); (5) uncertainty compatibile con edge — **FAIL** (CI95 ALL include lo zero sia IID che block); (6) evidenza indipendente disponibile e supportiva — **FAIL** (OOS sufficiente MA negativo, non solo insufficiente). Non significa live-ready. Nessuna configurazione forward congelata proposta in questa fase (il segnale OOS negativo consiglia cautela maggiore, non un proseguimento automatico).

## 14. Confronto con BREAKOUT_ACC e ORDER_BLOCK

| | BREAKOUT_ACC (7.21) | ORDER_BLOCK (7.22) | LIQ_SWEEP (7.25) |
|---|---|---|---|
| N trade | 47 | 13 | **42** |
| Net exp/trade | +$13,66 | +$38,26 | +$25,63 |
| PF | 1,62 | 1,86 | 1,48 |
| Concentrazione top-5 | 133,7% | 196,8% | **127,4%** (meno estrema) |
| CI95 ALL include zero? | Sì | Sì | Sì (IID e block) |
| OOS forward | 1 trade, perdente | 0 trade | **6 trade, -$539,30 (WR 17%)** |
| MVC | 1.000€ | 2.500€ | 2.500€ |
| Provenance/riconciliazione | buona | 1 scarto irrisolto | **perfetta (harness dedicato, 0 residui)** |
| Decisione | REQUIRES_FORWARD_VALIDATION | REQUIRES_FORWARD_VALIDATION | REQUIRES_FORWARD_VALIDATION |

**LIQ_SWEEP aggiunge informazione, non ripete solo il pattern**: campione storico più ampio e con provenance nettamente superiore, concentrazione meno estrema — MA è l'unica delle tre ad avere un campione OOS abbastanza grande da essere informativo, e quella lettura è negativa. Combinato con la scoperta che il 99% del P&L storico proviene da un solo anno (2025), il quadro è **più cauto** per LIQ_SWEEP nonostante il dataset storico più pulito.

## Deliverables

`nxs_liq_sweep_edge_dataset_loader.py`, `nxs_liq_sweep_chart_utils.py` (rendering SVG), `build_liq_sweep_data_exposure_map.py`, `build_liq_sweep_baseline_economics.py`, `build_liq_sweep_concentration_analysis.py`, `build_liq_sweep_statistical_uncertainty.py`, `build_liq_sweep_cost_stress.py`, `build_liq_sweep_execution_realism.py`, `build_liq_sweep_temporal_robustness.py`, `build_liq_sweep_visual_audit.py` (+ 38 chart SVG in `charts/`), `build_liq_sweep_path_anatomy.py`, `launch_oos_forward_run.py` / `collect_oos_forward_run.py` + run reale isolato (`runs/liq_sweep_oos_forward/`), `build_liq_sweep_oos_forward_analysis.py`, `build_liq_sweep_minimum_viable_capital.py`, `build_liq_sweep_comparison_with_prior_strategies.py`, `build_liq_sweep_edge_decision_card.py` + i rispettivi JSON, `verify_phase_7_25.py` (VERIFY OK), `test_phase_7_25.py` (36/36), questo vault report.

**Nota tecnica sui nomi file**: i builder sono stati rinominati con prefisso `liq_sweep_` DOPO una prima stesura con nomi generici (`build_baseline_economics.py`, `build_decision_card.py`, ecc.) — la regressione completa (`pytest server/research_scripts/phase7/`, tutti i file in un unico processo) ha rivelato una collisione di nomi modulo con file OMONIMI in Phase 7.21/7.9i/7.13 (stesso nome file, cartella diversa): Python cachea i moduli in `sys.modules` per NOME, non per path completo, quindi un `import build_decision_card` in un file di test veniva silenziosamente soddisfatto dalla cache lasciata da un'altra fase caricata prima nello stesso processo pytest, producendo dati sbagliati (es. una decisione `DEFECT_CONFIRMED_MATERIAL_IMPACT` mai definita in questa fase). Rinominato con prefisso `liq_sweep_` — che ha subito creato una SECONDA collisione, questa volta con `build_liq_sweep_decision_card.py` di Phase 7.23 (stessa strategia, prefisso identico) — rinominato ulteriormente in `build_liq_sweep_edge_decision_card.py`. Scansione finale su tutte le fasi: 0 collisioni residue, regressione completa (781+ test) pulita.

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`, `contracts/`. BREAKOUT_ACC (7.21), ORDER_BLOCK (7.22), Run Isolation Harness (7.23), Adjudication (7.24) non toccate (diff zero verificato). Nessuna optimization, nessun risk sizing, nessun deploy.

## Regressione

Suite Phase 7.25: 36/36 pass. Suite Phase 7 completa: (compilata dopo l'esecuzione).

---

```
7.24: LIQ_SWEEP CANONICAL DATASET ADJUDICATION - READY_WITH_DOCUMENTED_LIMITATION
7.25: LIQ_SWEEP EDGE_VALIDATION_V1 - COMPLETATO

BASELINE (42 chiusi): ALL +$25,63/trade PF 1,48 WR 55%
  BUY (39) +$26,78/trade PF 1,54 | SELL (3, minimo) +$10,60/trade
CONCENTRAZIONE: top-5 = 127,4% (senza top-5: negativo) - MENO estrema
  di ORDER_BLOCK (196,8%, non sopravvive nemmeno ai primi 3)
INCERTEZZA: CI95 ALL include lo zero sia IID che BLOCK bootstrap
  (sensitivity a serial dependence testata, non solo assunta IID)
  nota: BUY diverge fra i due metodi (BLOCK esclude lo zero, IID no)
COST STRESS: sopravvive a BASE/MODERATE/STRESS
TEMPORAL: SCOPERTA - 99% del netto proviene da UN SOLO anno (2025 su
  4 anni) - solo 2/4 anni positivi
VISUAL AUDIT REALE: 38 chart SVG (pivot da matplotlib, bloccato
  dall'ambiente) - 6 eventi x 3 stage + control case - blocked/near-
  miss dichiarato GAP (non fabbricato)
PATH ANATOMY: asimmetria osservata (favorevole-pre-loser 80,4 >
  avverso-pre-winner 36,3) - OBSERVATION/HYPOTHESIS, nessuna regola
OOS FORWARD (nuovo run isolato, 2026.07.01-2026.09.27): 6 trade -
  PRIMA VOLTA campione sufficiente (>=5) nel corpus - risultato
  NEGATIVO (-$539,30, WR 17%)
MVC: 2.500 EUR (leva 1:500)

DECISIONE: EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION
  (PASS: expectancy positiva, cost survival, execution survival)
  (FAIL: concentrazione, CI include zero, OOS sufficiente ma negativo)
CONFRONTO: LIQ_SWEEP ha il dataset storico piu' pulito del corpus ma
  E' L'UNICA con OOS genuinamente informativo - e quella lettura va
  CONTRO l'edge storico, non solo "insufficiente" come le altre due
PROSSIMO: nessuna promozione. Serve accumulo forward ulteriore prima
  di qualunque conclusione - il segnale OOS negativo consiglia
  cautela maggiore rispetto a BREAKOUT_ACC/ORDER_BLOCK, non minore
```
