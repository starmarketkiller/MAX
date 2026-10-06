# Unified Market Intelligence — Shadow Phase 1 — Preregistration

**Stato:** `FROZEN_NOT_EXECUTED`. Nessun codice scritto, nessun dato di outcome osservato, nessun backtest eseguito, nessuna modifica a MQL5/live/risk/execution. Questo documento congela il protocollo PRIMA di qualunque risultato — Codex implementa ed esegue esattamente questo, senza modificare feature/soglie/split strada facendo.

**Fonti canoniche uniche:** `docs/UNIFIED_MARKET_INTELLIGENCE_FOUNDATION_V1_CANONICAL` (commit `c971e33`, gli 8 documenti), più i 3 artifact reali del pilot MACD appena chiuso da Codex (`b4e3edc`): `macd_decision_card_v1.json`, `macd_limitations_v1.json`, `regime_compatibility_diagnostic_v1.json` — usati **solo** come precedente/benchmark dichiarato, non per scegliere feature o condizioni di questo test (vincolo esplicito dell'utente, rispettato in ogni scelta sotto con motivazione non-di-performance).

**Struttura delle chiavi:** rispecchia deliberatamente lo schema già usato da Codex in `macd_preregistration_v1.json` (stesso schema_version/status/dataset/split_boundaries/outcomes/selection/test_family/decision_vocabulary/stage_separation/freeze_integrity), estesa dove serve per il confronto a 3 sistemi.

---

## 0. Research question primaria

Una rappresentazione `MARKET_REGIME(volatilità) + DIRECTIONAL_CONTEXT(HTF bias + 1 trend proxy) + COMPONENT deduplicati + TRIGGER` produce informazione incrementale misurabile rispetto a (A) un segnale/componente standalone e (B) `NXS_Institutional_Decide` legacy — misurata esclusivamente in shadow, mai in esecuzione live.

## 1. Precedente dichiarato (MACD Phase 1, solo come benchmark)

`DC-MACD-CONTEXTUAL-PHASE1-001`: `decision=WEAK`, `evidence_grade=E1`, nessuna delle 60 celle congelate ha superato BH q≤0.10; un'osservazione nominale (`LOW_VOL/SELL/1.0 ATR`, raw p=0.0225, bh_q=1.0) esplicitamente marcata `POST_HOC_OBSERVATION_NOT_CONFIRMED` con restrizione esplicita a non promuoverla né restringere la famiglia per salvarla. Dataset marcato `DISCOVERY_REUSE`, non `TRUE_HOLDOUT`. **Uso qui:** conferma che il problema "un singolo componente ha edge condizionale" è una domanda difficile e onestamente risposta con NO/WEAK anche con metodo rigoroso — non implica nulla su se un **insieme deduplicato** di evidenza faccia meglio. Nessuna feature di questo documento è stata scelta perché "ha funzionato" nel pilot MACD — vedi §4 per la giustificazione non-di-performance di ogni scelta.

`regime_compatibility_diagnostic_v1.json`: Phase 4/5.5 (H4, 5 stati) vs Phase 7.27 (D1, trend×vol_tercile) hanno **compatibilità solo PARZIALE**, `full_compatibility_possible=false` (timeframe e ontologia diversi), **tasso di accordo sulle facet comparabili = 41.1%** (quasi casuale per una classificazione a poche categorie) — numero concreto, non più solo "da riconciliare" come in `CONTEXT_REGIME_RECONCILIATION_V1.md`. Usato qui per decidere §4.1 (quale regime di volatilità congelare), con motivazione dichiarata, non di performance.

## 2. Sistemi da confrontare (A/B/C) — definizione congelata

- **A — standalone baseline**: un singolo componente MARKET_EVIDENCE (vedi §4.3) valutato da solo, stessa logica di generazione segnale già usata in `TRADING_EDGE_STATUS_RECONCILIATION_V1.md`, nessun contesto/regime applicato.
- **B — Institutional Engine legacy**: `NXS_Institutional_Decide` (`NXS_InstitutionalCore.mqh`), **ma alimentato SOLO con il set di componenti MVP di §4.3** (non con tutte le 83 strategie) — vincolo di equità congelato qui: confrontare "metodo di aggregazione" senza confondere la variabile con "quantità di informazione in input" diversa tra B e C. Pesi `InpCtxW_*` esistenti usati **invariati**, trattati esplicitamente come `UNVALIDATED_PRIOR` (non ricalibrati per questo test).
- **C — Unified Engine shadow**: `MARKET_REGIME(§4.1) + DIRECTIONAL_CONTEXT(§4.2) + COMPONENT deduplicati(§4.3) + TRIGGER(§4.4)`, combinati con l'aggregatore baseline di §6. Shadow puro: calcola e registra, non invia mai un ordine, non modifica `InpUseInstitutionalCore` né alcun flag live.

## 3. Dataset

`server/research_datasets/market_state_v1/market_state_dataset_v1.csv` (H4, Dukascopy, 4809 barre — già nel repo, commit `b4e3edc`), unito per data di calendario al layer D1 di Phase 7.27 con lo stesso crosswalk già usato da Codex (`regime_compatibility_diagnostic_v1.json`: 96.7% coverage, 72 righe H4 con regime mancante, 186 righe D1 trend-unknown — accettate come missing, non imputate, per `missing_data_policy_v1.md`). **Nessun nuovo dataset costruito.**

## 4. Feature set MVP — ogni scelta con motivazione NON di performance

### 4.1 MARKET_REGIME: volatilità

**Congelato:** `vol_tercile` di Phase 7.27 (D1, ATR14, tercili LOW/MED/HIGH) come dimensione **primaria e selettiva**. Il regime H4 di Phase 4/5.5 è loggato **in parallelo come diagnostico non-selettivo** (non entra nella formazione delle celle di §5) — separazione esplicita diagnostica/selezione, stessa disciplina anti-circolarità di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` §12-bis.
**Motivazione (non di performance):** il 41.1% di accordo (§1) rende insostenibile trattare i due sistemi come intercambiabili o fonderli; va scelto UNO come operativo e l'altro come controllo diagnostico, non il contrario, e Phase 7.27 è quello già usato come covariata di regime-matching nel precedente diretto (Phase 7.27 BUY-dominance, Phase F) di questo stesso progetto — continuità di infrastruttura, non risultato.

### 4.2 DIRECTIONAL_CONTEXT

- **HTF bias**: congelato come `price_above_htf_sma200` (Phase 7.27, D1) — stesso test del filtro EMA200 già embedded in MACD, usato qui come la versione research-dichiarata e causale. **Motivazione:** è il candidato di unificazione più pulito già identificato in `CONTEXT_REGIME_RECONCILIATION_V1.md` §2 — nessuna nuova formula introdotta.
- **1 trend proxy**: congelato `ema200_trend_filter`/rappresentazione momentum di MACD (già estratta come feature continua nel pilot Phase 1 di Codex, `macd_features.py`). **Motivazione esplicitamente non di performance:** riuso diretto dell'infrastruttura già costruita e chiusa (decisione `WEAK`, non promossa) — scegliere un proxy che ha appena fallito a dimostrare edge standalone è la prova che questa scelta non è guidata dal risultato. Gli altri 5 proxy (ADX_RSI/SAR a livello strategia; directional_efficiency/structure-break a livello contesto) restano esplicitamente fuori da questo round, per `CANONICAL_COMPONENT_CONTEXT_MODEL_V1.md` §5.

### 4.3 COMPONENT (MARKET_EVIDENCE), deduplicati

**Congelato: 2 componenti, non di più in questo round.**
1. `liquidity_sweep_detection` + `sweep_reversal_trigger` (LIQ_SWEEP) — `INDEPENDENT` per `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md`, nessun defect noto, nessuna primitiva condivisa con l'altro componente scelto.
2. `order_block_zone_location` + `order_block_retest_trigger` (ORDER_BLOCK) — `defect_status=REMEDIATED` (commit `17da794`), solo logica post-fix.

**Deduplicazione esplicita:** ORDER_BLOCK porta con sé due sotto-input condivisi con FVG_CONT (`external_h1_structure_trend`, `smc_reaction_confirmation`, `EXACT_SHARED_PRIMITIVE` da `UNIFIED_COMPONENT_CATALOG_V1.md`). **FVG_CONT è esplicitamente escluso da questo round MVP** proprio per evitare di dover risolvere la matematica della deduplicazione nel primo round — i due sotto-input condivisi vengono quindi trattati come parte di `DIRECTIONAL_CONTEXT`/`ELIGIBILITY_CONTROL` di ORDER_BLOCK stesso, non come evidenza MARKET_EVIDENCE aggiuntiva, e non duplicati nel conteggio di conviction (§6). FVG_CONT, ADX_RSI, BREAKOUT_ACC (oltre al suo ruolo di TRIGGER sotto) restano fuori — Phase 2, non autorizzata qui.

### 4.4 TRIGGER

Il TRIGGER osservabile causalmente è quello già incluso nei 2 componenti di §4.3 (`sweep_reversal_trigger`, `order_block_retest_trigger`) — **nessun TRIGGER aggiuntivo introdotto**. `breakout_acceptance_trigger` (BREAKOUT_ACC) resta un candidato per Phase 2, non incluso qui per mantenere il set deliberatamente piccolo (vincolo esplicito dell'utente).

### 4.5 ELIGIBILITY_CONTROL

Riusati **tali e quali**, nessuno ridisegnato: `delivery_candle_filter` (LIQ_SWEEP), RR-sanity già esistente. Nessun nuovo gate inventato per questo test.

## 5. Celle di analisi — Famiglia 1 (conditional edge di C)

**Congelato prima di guardare qualunque outcome:**
cella = componente (2) × direzione del trigger (BUY/SELL) × vol_tercile (LOW/MED/HIGH) × HTF-bias agreement (sì/no) × soglia outcome (stessa superficie multi-R di `outcome_schema.md`, stesso set già usato da `macd_evidence_record_v1.json` — riusato identico per comparabilità, non ridefinito).
Dimensione della famiglia: **2 × 2 × 3 × 2 × N_soglie** — N_soglie fissato al numero già usato nel pilot MACD (riuso esatto, non una nuova scelta). Correzione **BH-FDR su questa intera famiglia, dichiarata qui, non dopo aver visto i risultati**.

## 6. Famiglia 2 — Incremental value (C vs A, C vs B)

**Domanda diversa, famiglia statistica separata** (per non mescolare "il componente ha edge" con "il sistema aggregante aiuta"): confronto appaiato, stesse barre/stesso periodo, tra l'output di conviction di C e (a) il segnale standalone A, (b) la decisione di B — su una metrica di edge condizionale pre-dichiarata (stessa superficie outcome di §5). **2 confronti totali** (C-vs-A, C-vs-B), non per-cella — correzione triviale (α/2) dichiarata qui. Misura anche: stabilità per regime (stessa cella di §5, letta come breakdown descrittivo, non come test aggiuntivo), caratteristiche di drawdown/path, coverage/frequenza.

## 7. Split (TRUE_HOLDOUT vs DISCOVERY_REUSE — dichiarazione onesta)

**Questo round è dichiarato `DISCOVERY_REUSE`, non `TRUE_HOLDOUT`**, per lo stesso motivo onestamente dichiarato nel pilot MACD: le soglie di Phase 4/5.5 (split discovery [0,3366)) e la finestra D1 di Phase 7.27 sono già state toccate da analisi precedenti su questo stesso storico. **Non si finge un holdout che non esiste.** Split operativo congelato comunque: righe [3366, fine) usate come porzione di stima primaria (coerente con la convenzione già stabilita), righe [0,3366) riportate solo come diagnostica di stabilità, non come conferma. **Qualunque promozione futura a `SUPPORTED`/`VALIDATED` richiede un round successivo su dati genuinamente nuovi (barre H4 raccolte dopo la chiusura di questo test)** — stessa regola già imposta a MACD.

## 8. Costi

Riuso identico della convenzione già congelata nel pilot MACD e nel cost-calibrated re-evaluation (`ff9f0e5`): spread applicato una volta, slippage a entry e a stop di mercato, nessun slippage al target limite. **Nessun nuovo profilo di costo creato.**

## 9. Missing-data policy

Riuso di `missing_data_policy_v1.md` (Phase 4): righe con regime/HTF-bias mancante **escluse**, non imputate (72 righe H4, 186 righe D1-trend secondo il diagnostico già citato).

## 10. Dependence handling

Riuso del metodo già validato di Phase 6.5 (non del gate bloccato in Phase 7.4A, §0 di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md`): **3 metodi di Effective Sample Size dichiarati separatamente, mai fusi in un unico numero**, mai usati per condizionare il rigetto del test sulla stessa diagnostica. Overlap da crossover/finestre multi-barra dichiarato esplicitamente per ciascun componente (stessa cautela già applicata da Codex per MACD).

## 11. Minimum sample

**Soglia congelata: 30 osservazioni effettive indipendenti** (convenzione già stabilita in questo corpus — correzione LIQ_SWEEP n=6, riconfermata in `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` §11). Sotto soglia → `INSUFFICIENT_EVIDENCE`, categoria distinta da `FAIL`, non un punto basso della stessa scala.

## 12. Multiple-testing policy

**Due famiglie separate, ciascuna con il proprio piano BH-FDR/correzione dichiarato PRIMA dei risultati** (§5, §6) — mai un'unica famiglia indifferenziata, mai una soglia scelta dopo aver visto quale cella "sembra promettente".

## 13. Conviction / aggregatore — nessuna calibrazione su questa finestra

**Vincolo assoluto dell'utente, congelato qui letteralmente:** nessun peso calibrato usando l'outcome di questa stessa finestra. Se serve un aggregatore per produrre la "unified conviction" di C, si riusa **la sola struttura** già esistente in `NXS_Institutional_Decide` — il peso decrescente per contributi della stessa famiglia (`1/(n+1)`, `AUD0-INST-010`) — applicata ai 2 componenti deduplicati di §4.3, **senza i pesi `InpCtxW_*` esistenti** (quelli restano solo dentro il Sistema B per il confronto, non entrano in C). Questa struttura minima va trattata essa stessa come `UNVALIDATED_PRIOR`/baseline deterministica da battere, non come verità — esattamente come richiesto.

## 14. Decision vocabulary (congelato, stesso stile del pilot MACD)

- **SUPPORTED**: almeno una cella di Famiglia 1 supera BH q≤0.10 con ESS≥30 **e** il confronto corrispondente di Famiglia 2 (C vs A **e** C vs B) è positivo e non attribuibile a caso con lo stesso criterio.
- **WEAK**: evidenza nominale non confermata (stesso trattamento della cella MACD `POST_HOC_OBSERVATION_NOT_CONFIRMED`) — non promuovere, non restringere la famiglia per salvarla, non ri-testare sullo stesso dataset.
- **FAILED**: nessuna cella supera Famiglia 1 e il confronto di Famiglia 2 è non-positivo con campione sufficiente.
- **INSUFFICIENT_EVIDENCE**: ESS<30 nelle celle rilevanti — categoria distinta, non FAILED.

## 15. Stage separation (anti-circolarità, esplicita)

1. **Diagnostica**: ESS, confronto di compatibilità regime (già fatto da Codex, riusato), missingness.
2. **Selezione**: quali celle entrano nella Famiglia 1/2 — fissato da questo documento, non dal risultato.
3. **Test**: conditional edge (Famiglia 1) e incremental value (Famiglia 2) — calcolati solo sulle celle fissate allo stage 2.
Nessuno stage può essere ricalcolato dopo aver visto l'esito di uno stage successivo.

## 16. Safety

Shadow only. Nessuna modifica a MQL5/registry/risk/execution. `InpUseInstitutionalCore` e ogni altro flag live restano invariati. Nessun ordine, nessuna decisione di trading reale, nessun collegamento al runtime di produzione.

## 17. Freeze integrity

Questo documento, una volta approvato, è la specifica congelata. Qualunque deviazione (cambio di split, soglia, feature, famiglia) richiede una nuova preregistrazione esplicita, non una modifica silenziosa durante l'implementazione.

---

UNIFIED_MARKET_INTELLIGENCE_SHADOW_PHASE1_PREREG_READY_FOR_REVIEW
