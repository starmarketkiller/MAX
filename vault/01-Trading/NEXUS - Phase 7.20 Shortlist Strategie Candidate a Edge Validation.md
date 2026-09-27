# NEXUS - Phase 7.20 — Shortlist Strategie Candidate a Edge Validation

**Baseline:** `8dce300` (Phase 7.18/7.19 concluse). Nessun lavoro concorrente rilevato (fetch eseguito prima e dopo). Nessun parameter sweep, nessuna TP/SL optimization, nessun risk sizing, nessun compounding, nessun portfolio testing, nessuna promozione live in questa fase. Nessuna modifica a `MQL5/`.

**Obiettivo**: chiudere il ciclo di integrity work su BREAKOUT_ACC/ORDER_BLOCK/TSI e costruire, usando l'intero census (Phase 7.11, 83 strategie) e tutta l'evidenza disponibile fino a Phase 7.19, una shortlist rigorosa delle strategie che meritano una vera fase di validazione economica — senza promuovere nulla automaticamente solo perché "ripulito".

---

## 1. Universo e metodo

Unite in un solo record per strategia: il census completo (83 righe), l'audit statico del difetto CROSS_TIMEFRAME_STATE_CONTAMINATION (Phase 7.10, 20 candidate controllate), la priority queue dello stesso difetto (Phase 7.12) e **l'unico dataset multi-strategia a tick reali del progetto** (`knowledge/backtest_database.json`, campagna "sweep37 ROUND CORRENTE" — 7 strategie con PF riportato). Nessun nuovo dato generato. Valutate in profondità su 16 criteri indipendenti **9 strategie**: le 5 esplicitamente richieste (BREAKOUT_ACC, ORDER_BLOCK, TSI, ADX_RSI, SAR) più le uniche altre 4 con evidenza quantitativa reale nel corpus (LIQ_SWEEP, FVG_CONT, BOLLINGER, MACD). Le restanti 74 sono classificate con **regole esplicite e verificabili** (stato difetto + evidenza disponibile), non narrate singolarmente — la matrice resta comunque completa (83/83 righe). **Il PF storico non è mai usato da solo per classificare** (campo dichiarato e verificato).

## 2. Scoperta rilevante durante la costruzione dell'universo

`ADX_RSI` e `SAR` (letti direttamente dal sorgente in questa fase, non fra i 20 candidati di Phase 7.10): entrambe **stateless** (nessuno stato persistente fra barre, quindi non a rischio di corruzione cumulativa come TSI/ORDER_BLOCK) ma **senza alcuna guardia TF**. Per ADX_RSI trovato un problema strutturale non documentato altrove: mescola `g_adx`/`g_rsi` (TF fisso, calcolati dal motore indicatori) con `e50`/`price` (TF variabile via `NXS_EffTF()`) — un possibile disallineamento cross-TF di tipo diverso da quello già fissato 3 volte in questa sessione, **mai quantificato**. Non investigato oltre in questa fase (fuori scope, nessuna modifica MQL5 autorizzata).

## 3. Matrice completa (83/83)

| Categoria | N |
|---|---|
| READY_FOR_EDGE_VALIDATION | 2 |
| PROMISING_BUT_NEEDS_INTEGRITY_WORK | 2 |
| INSUFFICIENT_EVIDENCE | 59 |
| GENUINE_NO_EDGE_CANDIDATE | 0 |
| DO_NOT_USE_YET | 20 |

**GENUINE_NO_EDGE_CANDIDATE = 0 è un risultato atteso, non un'omissione**: nessuna strategia del corpus ha oggi evidenza sufficientemente pulita e controllata da poter affermare "nessun edge" con onestà — anche ADX_RSI/SAR (le più deboli sulla carta) hanno un'integrità mai verificata che impedisce una conclusione negativa definitiva.

**Tier A (9, dive-dive)**: BREAKOUT_ACC (READY), ORDER_BLOCK (READY), TSI (INSUFFICIENT_EVIDENCE — campione post-fix di soli 8 eventi/8 mesi, PF pre-fix già debole 0.76), ADX_RSI (DO_NOT_USE_YET — integrità irrisolta + PF 0.82 debole), SAR (DO_NOT_USE_YET — integrità irrisolta + evidenza "ambigua"), LIQ_SWEEP (PROMISING — miglior PF del corpus, 1.04, ma integrità mai controllata), FVG_CONT (PROMISING — PF 0.96 + segnale A/B non validato su MT5), BOLLINGER e MACD (DO_NOT_USE_YET — SUSPECT/non auditate + PF 0.79 entrambe).

**Tier B (23, regola esplicita)**: 8 con `DEFECT_CONFIRMED_UNFIXED` (stesso difetto già fissato 3 volte, qui ancora aperto — BAR_UPDN, BB_SQUEEZE, PIVOT_WICK, PMAX, RANGE_FADE, SH_BMS_RTO, SH_BMS_RTO_V2, SILVER_BULLET); 4 con `SUSPECT_INTEGRITY_UNRESOLVED` (3COMMAS_BOT, ICHIMOKU_HULL_MACD, MACD_SMA200, RSI_DIV_PINE); 7 con `SAFE_INTEGRITY_BUT_NO_REAL_EVIDENCE` (LEVEL_CONFLUENCE/_M5, LEVEL_REACTION/_M5, WEEKLY_EXP, WICK_SWEEP_RECLAIM/_REV — integrità confermata pulita ma zero trade economico mai registrato); 4 wrapper (OB_MIT, IFVG, FVG_MIT, FVG_MIT_WINDOW — ereditano lo stato della strategia riusata).

**Tier C (59, bulk)**: nessuna evidenza quantitativa trovata in nessuna fonte + integrità mai auditata — la maggioranza (RESEARCH_ONLY) non è mai stata live su MQL5.

## 4. Shortlist (2, non 3-5)

**BREAKOUT_ACC** e **ORDER_BLOCK**. Deliberatamente non riempita a 3-5: TSI/ADX_RSI/SAR/LIQ_SWEEP/FVG_CONT sono stati valutati esplicitamente e non promossi, con ragioni specifiche (vedi matrice) — preferite 2 candidate genuinamente pronte a un numero artificialmente più alto.

- **BREAKOUT_ACC**: unica strategia con integrità certificata E un canonical event dataset già esistente a fill reali (75 eventi, Phase 7.9H/K) — pronta per gli Stadi 1-2 del protocollo SENZA nuovo lavoro MT5. Rischio principale: confidence bassa dichiarata dagli stessi autori, campione SELL troppo piccolo (15 eventi) da testare separatamente da BUY (60 eventi).
- **ORDER_BLOCK**: integrità certificata al livello più rigoroso del corpus (trace EA reale pre/post fix) ma **zero evidenza economica** per l'implementazione V2 canonica — candidata perché il gap è "serve un run", non "serve un altro audit".

**LIQ_SWEEP** e **FVG_CONT** segnalate esplicitamente come prossimi candidati più vicini (priorità 1 e 2 per un futuro audit di integrità dedicato, stesso schema già usato 3 volte in questa sessione).

## 5. Evidenza storica riutilizzabile vs non

Riusabile: solo `phase7_9k/breakout_acc_intended_d1_v2_dataset.json` (prodotto DOPO entrambi i fix di BREAKOUT_ACC). **Non riutilizzabile** come evidenza dell'implementazione canonica attuale: tutta l'evidenza pre-fix di ORDER_BLOCK/TSI (già classificata contaminata in Phase 7.14/7.17); il PF sweep37 di ADX_RSI/BOLLINGER/MACD/BJORGUM/LIQ_SWEEP/FVG_CONT (identità implementativa eseguita in quel run mai accertata per nessuna delle 6).

## 6. Gap principali prima dell'edge validation

BREAKOUT_ACC: benchmark esplicito mai calcolato, nessun vero holdout temporale. ORDER_BLOCK: serve un nuovo run MT5 reale (non Research Mode) preregistrato. **Gap trasversale più ricorrente**: nessuna strategia del corpus ha oggi un vero holdout OOS pronto — coerente con il gap "runtime_fingerprint assente" trovato in Phase 7.19 per un motivo diverso ma della stessa natura (infrastruttura di misurazione indietro rispetto alla logica di trading).

## 7. EDGE_VALIDATION_V1 (proposta di protocollo, non eseguito)

7 stadi sequenziali a cancello: 0 preregistrazione → 1 baseline edge (vs benchmark esplicito) → 2 costi (spread/slippage/commissioni/swap, con/senza fianco a fianco) → 3 OOS (campione temporalmente successivo, mai split retroattivo) → 4 execution realism (riusa ANTI_LEAKAGE_SPECIFICATION_V1/SOURCE_OF_TRUTH_HIERARCHY_V1 di Phase 7.19) → 5 minimum viable capital (solo stima preparatoria) → 6 demo forward readiness (fuori scope qui). Esclusioni esplicite dichiarate: nessun parameter sweep, nessun risk sizing aggressivo/compounding, nessun portfolio testing, nessuna promozione automatica, mai il solo PF storico per decidere un cancello.

## 8. Raccomandazione: quale validare per prima

**BREAKOUT_ACC** — unica strategia con dataset economico già pronto (Stadi 1-2 possono iniziare subito), gap residuo più piccolo (solo OOS) rispetto a ORDER_BLOCK (zero dati, serve un run intero). Raccomandazione esplicitamente limitata all'ORDINE di lavoro, non un'affermazione di edge già presente. Lato SELL (15 eventi) da NON includere nel primo giro.

## Deliverables

`build_strategy_universe.py` + `strategy_universe_v1.json`, `build_evaluation_matrix.py` + `evaluation_matrix_v1.json`, `build_shortlist.py` + `shortlist_v1.json`, `build_edge_validation_protocol.py` + `edge_validation_protocol_v1.json`, `build_recommended_first.py` + `recommended_first_v1.json`, `build_evidence_reusability.py` + `evidence_reusability_v1.json`, `build_edge_validation_gap_analysis.py` + `edge_validation_gap_analysis_v1.json`, `build_inclusion_exclusion_summary.py` + `inclusion_exclusion_summary_v1.json`, verificatore indipendente (`verify_phase_7_20.py`, VERIFY OK), 27/27 test propri (`test_phase_7_20.py`), questo vault report.

## Vincoli preservati

Nessuna modifica a `MQL5/`, registry, Product Platform. Nessun run Tester lanciato. Nessun parameter sweep, TP/SL optimization, risk sizing aggressivo, compounding, portfolio testing, promozione live. Nessun artifact storico cancellato o reinterpretato.

## Regressione

Prima esecuzione della suite completa: trovata una collisione di nome modulo Python fra `phase7_19/build_gap_analysis.py` e un `build_gap_analysis.py` di questa fase (stesso pattern gia' documentato e risolto in Phase 7.15 per `build_decision_card_v2.py` fra phase7_9k/phase7_14) - risolta rinominando il file DI QUESTA fase (non uno storico) in `build_edge_validation_gap_analysis.py` / `edge_validation_gap_analysis_v1.json`. Nessuna regressione reale, solo un difetto di isolamento test introdotto in questa sessione e corretto nella stessa sessione.

---

```
7.18/7.19: TSI FIX + EVENT AUDIT PACKET - CONCLUSI
7.20: SHORTLIST EDGE VALIDATION - COMPLETATO
  universo: 83 strategie (census 7.11), matrice 100% coperta
  scoperta: ADX_RSI/SAR stateless ma senza guardia TF + mescolamento
    TF fisso/variabile in ADX_RSI mai quantificato (non investigato,
    fuori scope)
  categorie: READY=2 PROMISING=2 INSUFFICIENT=59 NO_EDGE=0 DO_NOT_USE=20
  shortlist (2, non riempita a 3-5): BREAKOUT_ACC, ORDER_BLOCK
  TSI/ADX_RSI/SAR/LIQ_SWEEP/FVG_CONT valutate esplicitamente, NON
    promosse (ragioni specifiche per ciascuna, non solo "non ancora")
  prossimi candidati piu' vicini: LIQ_SWEEP (PF 1.04, il migliore del
    corpus) e FVG_CONT, entrambe bloccate solo su un audit di
    integrita' mai fatto
PROTOCOLLO: EDGE_VALIDATION_V1 proposto (7 stadi a cancello), NON eseguito
RACCOMANDATA PER PRIMA: BREAKOUT_ACC (dataset gia' pronto, gap minore)
PROSSIMO: blocco dichiarato dall'utente - baseline edge -> costi -> OOS
  -> execution -> minimum viable capital -> demo forward, a partire
  da BREAKOUT_ACC (solo BUY nel primo giro)
```
