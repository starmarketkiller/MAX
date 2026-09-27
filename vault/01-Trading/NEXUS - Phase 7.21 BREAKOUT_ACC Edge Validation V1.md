# NEXUS - Phase 7.21 — BREAKOUT_ACC EDGE_VALIDATION_V1

**Baseline:** `7e2c764` (Phase 7.20, shortlist). Nessun lavoro concorrente rilevato (fetch eseguito prima e dopo). Nessuna optimization/TP-SL sweep/risk sizing/compounding/martingala/regime filter/eliminazione SELL/promozione live in questa fase. Un solo run MT5 nuovo (finestra forward OOS, vedi punto 2), lanciato SOLO dopo aver congelato baseline/costi/execution/temporale/statistica.

**Obiettivo**: determinare se BREAKOUT_ACC_INTENDED_D1_V1 possiede un edge economico reale e trasferibile, distinguendo rigorosamente evidenza già esplorata (usata per scoprire l'asimmetria BUY/SELL) da nuova evidenza indipendente.

---

## 1. Hypothesis congelata

**H1** (primaria): expectancy netta positiva dopo costi realistici. **H2** (secondaria): BUY più robusto di SELL — dichiarata esplicitamente **post-hoc** (scoperta guardando l'intero campione in Phase 7.9I/J) e quindi richiedente evidenza nuova e indipendente, non una ri-conferma sugli stessi 75 eventi. Nessuna modifica alla strategia per favorire BUY.

## 2. DATA_EXPOSURE_MAP

Il run MT5 sorgente (r002/r003) copre 2019.02.04–2026.08.14, ma l'**ultimo segnale generato** è del 2026.06.09 (verificato riga per riga sul trace raw, 67 righe — zero righe oltre quella data, non censura: la strategia semplicemente non ha più generato segnali in quella finestra). **Nessun vero holdout storico esiste** nel campione già raccolto — l'intero popolamento (75 eventi) è stato usato sia per il mechanism discovery sia per scegliere BUY vs SELL. **Unica opzione genuinamente untouched**: il periodo forward 2026.08.15–2026.09.27 (mai attraversato da nessuna versione dell'EA). Non investigata la disponibilità di dati pre-2019 (fuori scope tempo/beneficio — nessuna evidenza nel progetto suggerisce qualità comparabile prima di quella soglia). Eseguito un run MT5 isolato (selettore 9, stessa identità canonica/config-fingerprint di r002) su questa finestra — risultato al punto 9.

## 3. Baseline economica (47/75 eventi OPENED, unico sottoinsieme con P&L reale)

Net P&L = `realized_pnl` (deal profit) + `realized_swap` + `realized_commission` (tutti campi reali già nel dataset). **ALL** (n=47): expectancy netta **+$13.66/trade**, PF **1.62**, WR 30%, DD max $319.69, recovery factor 2.01, 11 perdite consecutive massime, ~6.7 trade/anno. **BUY** (n=36): +$26.51/trade, PF 2.33, WR 39%, +0.79R/trade. **SELL** (n=11): **-$28.38/trade, PF 0.00 (ZERO vittorie su 11 trade)**, -0.92R/trade. BUY-only non presentato come strategia validata (resta ipotesi H2).

## 4. Cost stress (3 scenari preregistrati)

COST_BASE (dati reali, nessuna assunzione aggiuntiva): +$13.66/trade. COST_MODERATE (+$0.5/trade assunto): +$13.16. COST_STRESS (+$2/trade assunto): +$11.66. **Sopravvive ai 3 livelli** — ma nota: commissione osservata SEMPRE $0.00 su tutti i 47 eventi e slippage segnale→fill SEMPRE 0.0 (artefatto noto del motore Tester in Research Mode, non evidenza di slippage reale zero — per questo i due scenari stressati aggiungono un costo assunto, dichiarato, non misurato).

## 5. Execution realism

Funnel: 67 segnali generati dal trace live → 56 passano gli execution gates (11 BLOCKED) → 47 aperti+riempiti (9 SENT_REJECTED dal broker). Blocked/rejected NON scartati: la loro "qualità del segnale" (movimento forward 60 barre aggiustato per direzione) è **praticamente identica** a quella eseguita (71% favorevole vs 71%/71% eseguibile) — i gate non selezionano per qualità, sono vincoli operativi. **Gap enorme fra segnale e realizzato**: 71% di movimento direzionale favorevole a 60 barre diventa solo **30% di win rate reale** — la gran parte del vantaggio direzionale viene perso perché lo SL interrompe il trade prima che il drift favorevole si materializzi (coerente con l'esempio esaminato: MFE=$221 ma uscita a SL per -$10.84).

## 6. Visual Audit (campione stratificato, 8 eventi)

2 winner, 2 loser, 2 random, 1 blocked, 1 broker-reject. Stage A eseguito con mascheramento **strutturale** (l'oggetto passato alla review non contiene campi di esito) — dichiarato esplicitamente il limite: l'operatore (questa sessione) ha già letto il dataset completo in fasi precedenti dello stesso lavoro, quindi non è un vero mascheramento di memoria/operatore, solo di dati. Nessuna regola operativa derivata dalle osservazioni visive in questa fase.

## 7. Robustezza temporale — **scoperta chiave**

5/8 anni con P&L netto positivo. **Concentrazione estrema**: i primi 5 trade (10.6% del campione) spiegano il **133.7%** del profitto netto totale — rimuovendo SOLO i primi 5 trade, il netto totale passa da **+$642.13 a -$216.17**: l'edge **sparisce completamente e si inverte**. Dichiarato esplicitamente, non nascosto (punto 12 del task).

## 8. Incertezza statistica (bootstrap per-trade, 10.000 iterazioni, seed dichiarato)

**ALL: CI 95% [-$7.15, +$36.37] — INCLUDE LO ZERO** (l'expectancy aggregata NON è statisticamente distinguibile da zero con questo campione). **BUY: CI [+$1.21, +$53.55] — esclude lo zero, ma debolmente** (limite inferiore vicino a zero). **SELL: CI [-$41.30, -$20.58] — esclude lo zero sul lato negativo**, evidenza statistica di una gamba perdente, non solo "più debole" di BUY.

## 9. OOS forward — risultato del nuovo run MT5

Finestra 2026.08.15–2026.09.27 (~6 settimane), run isolato selettore 9. **1 solo segnale generato, 1 trade aperto (BUY), uscito a SL il 2026.08.31 per -$110.30 (-1.071R)**. Campione sotto la soglia minima dichiarata (5 trade) → **`INSUFFICIENT_OOS_SAMPLE`** (non `FAILED`, esito esplicitamente ammesso). L'unica osservazione forward disponibile è una perdita, ma n=1 non permette nessuna conclusione.

## 10. Minimum Viable Capital

| Capitale | Rischio %/trade (SL medio) | Margin % | Eseguibile |
|---|---|---|---|
| 300€ | 9.5% | 7.22% | Sì (ma rischio alterato materialmente) |
| 500€ | 5.7% | 4.33% | Sì (al limite) |
| **1.000€** | **2.9%** | 2.16% | Sì — **MINIMUM_VIABLE_CAPITAL** |
| 2.500€ | 1.1% | 0.87% | Sì |
| 10.000€ | 0.3% | 0.22% | Sì (riferimento) |

Soglia dichiarata: rischio medio a lotto minimo ≤5% del capitale. Sotto i 500€ il lotto minimo (0.01) altera materialmente il profilo di rischio rispetto a quanto misurato in questo dataset (sempre a 0.01 lotto fisso). Nessun position sizing proposto.

## 11. Gate finale

**`EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION`**. Check: (1) expectancy netta positiva ALL — **PASS**; (2) cost survival 3 scenari — **PASS**; (3) execution non collassa il segnale — **PASS**; (4) nessuna concentrazione estrema — **FAIL** (top-5 = 133.7% del netto); (5) evidenza indipendente disponibile e di supporto — **FAIL** (OOS insufficiente, l'unico trade forward è una perdita). Non significa live-ready.

## 12. Configurazione forward congelata (non eseguita)

Poiché nessun vero holdout esiste e il campione forward è insufficiente: congelata una configurazione (stesso selettore 9, stessa identità canonica, ENTRAMBE le direzioni — **non eliminare SELL**, vietato dal punto 12 del task) con regole esplicite: nessuna modifica alla strategia, nessun tuning osservando i risultati, ogni evento registrato con Audit Packet, nessuna promozione live prima di ≥5 trade chiusi forward. Nessun deploy in questa fase.

## Deliverables

`build_data_exposure_map.py`, `build_baseline_economics.py`, `build_cost_stress.py`, `build_execution_realism.py`, `build_visual_audit_sample.py`, `build_temporal_robustness.py`, `build_statistical_uncertainty.py`, `build_oos_forward_analysis.py`, `build_minimum_viable_capital.py`, `build_breakoutacc_decision_card.py`, `build_frozen_forward_config.py` + i rispettivi JSON, `nxs_breakoutacc_dataset_loader.py` (helper condiviso), config Tester forward (`nxs_breakoutacc_forward_oos.ini`), trace forward reale committato (`nexus_trades_forward_oos.csv`), verificatore indipendente (`verify_phase_7_21.py`, VERIFY OK), 43/43 test propri, questo vault report.

## Vincoli preservati

Nessuna modifica a `MQL5/` (usata esclusivamente l'implementazione canonica già esistente, nessuna istrumentazione necessaria — il logging standard `NXS_LogTradeCSV` già cattura P&L netto reale). Nessun parameter sweep, TP/SL optimization, risk sizing aggressivo, compounding, martingala, regime filter optimization, eliminazione di SELL, aumento del rischio sui setup migliori, promozione live.

## Regressione

(compilata dopo l'esecuzione della suite completa)

---

```
7.20: SHORTLIST EDGE VALIDATION (BREAKOUT_ACC, ORDER_BLOCK)
7.21: BREAKOUT_ACC EDGE_VALIDATION_V1 - COMPLETATO
  H2 (BUY>SELL) dichiarata post-hoc, richiede evidenza indipendente
  DATA_EXPOSURE_MAP: nessun vero holdout storico - solo forward
    2026.08.15-2026.09.27 genuinamente untouched
  baseline (47 trade reali): ALL +$13.66/trade PF 1.62 WR 30%
    BUY +$26.51/trade PF 2.33 | SELL -$28.38/trade PF 0.00 (0/11 vinti)
  costi: sopravvive a COST_BASE/MODERATE/STRESS
  execution: gap enorme segnale(71% favorevole)->realizzato(30% WR) -
    lo SL interrompe il drift favorevole prima che si materializzi
  CONCENTRAZIONE ESTREMA: rimuovendo i primi 5/47 trade il netto
    passa da +$642 a -$216 - l'edge dipende quasi interamente da
    pochissimi eventi
  incertezza statistica: ALL non esclude lo zero (CI95 include 0);
    BUY lo esclude debolmente; SELL esclude lo zero sul NEGATIVO
  OOS forward (nuovo run MT5, 6 settimane): 1 solo trade, PERDENTE
    (-$110.30) - INSUFFICIENT_OOS_SAMPLE, non FAILED
  MINIMUM_VIABLE_CAPITAL: 1.000 EUR (soglia rischio 5%/trade a lotto min)
DECISIONE: EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION
  (PASS: expectancy positiva, cost survival, execution survival)
  (FAIL: concentrazione estrema, evidenza indipendente insufficiente)
CONFIG FORWARD CONGELATA (non eseguita): stesso selettore, ENTRAMBE le
  direzioni, nessun tuning, ogni evento con Audit Packet, servono
  >=5 trade chiusi forward prima di una nuova lettura del gate
PROSSIMO: nessuna promozione live. Accumulare campione forward (mesi,
  non settimane, data la cadenza storica 9-16 segnali/anno) prima di
  ri-valutare il gate - CONDITIONAL_EDGE + EXIT/RISK OPTIMIZATION solo
  se e quando il gate passa
```
