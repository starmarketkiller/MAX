# NEXUS - Phase 7.2: External Hypothesis Mining & Market Sequence Ontology

**Baseline:** `7737cb9` (Phase 7.1 Integrity & Provenance Patch, chiusa con `NO_SUPPORTED_CANDIDATE`, RECLAIM BOTH/BUY/SELL correttamente REFUTED_AT_DISCOVERY). Questa fase **non e' una discovery run**: nessun ΔP, nessun backtest, nessuna optimization, nessun accesso a development/validation/holdout NEXUS per confrontare idee.

**Conferma esplicita richiesta: NO NEXUS OUTCOME DATA USED FOR EDGE DISCOVERY IN PHASE 7.2.** Verificato: nessuno script di questa fase legge market_state_dataset/outcomes/validation/locked_validation/final_holdout di NEXUS. La failure memory e i risultati canonici (Phase 5/6/6.5/7.1) sono stati letti SOLO per evitare duplicazione (sec.33 esplicito), non per scegliere parametri.

---

## 1. Fonti e claim raccolti

**66 fonti distinte**, **115 raw claim** (target minimo 100, superato). Raccolti da 5 agenti di ricerca paralleli, uno per categoria di fonte, con retry per il batch community dopo un rate-limit di sessione e un blocco totale di Reddit nell'ambiente (mai forzato con contenuti fabbricati - vedi sec.7 sotto). Nessuna fonte supera il 3.5% del corpus (massimo osservato, ben sotto il tetto del 10%).

## 2. Categorie di fonte

| Categoria | Claim | Fonti |
|---|---|---|
| ACADEMIC (paper/preprint/quant blog) | 37 | ~26 |
| MQL5_EA | 25 | ~16 |
| COMMUNITY (ForexFactory/altri forum) | 25 | ~16 |
| OPEN_SOURCE_SCRIPTS (TradingView/GitHub) | 24 | ~13 |
| MARKET_STRUCTURE_DOC (broker/exchange) | 4 | 4 |

5 categorie richieste, tutte presenti con margine. **Limitazione dichiarata**: Reddit e' risultato completamente inaccessibile nell'ambiente di questa sessione (blocco a livello di dominio sia da WebFetch che dal browser, non un semplice 403) - il batch community si basa su ForexFactory e BabyPips, non su Reddit. Nessun claim fabbricato per compensare.

## 3. Market mechanisms emersi

**33 mechanism** derivati dal corpus (market_mechanism_registry_v1.json) - non una lista imposta a priori. Includono fenomeni di prezzo classici (BREAKOUT_ACCEPTANCE_CONTINUATION, BREAKOUT_FAILURE, VOLATILITY_COMPRESSION_TO_EXPANSION, LIQUIDITY_SWEEP, LEVEL_RECLAIM_REVERSAL, MEAN_REVERSION_BAND_TOUCH, VWAP_ACCEPTANCE_REJECTION, VALUE_AREA_ACCEPTANCE_REJECTION), fattori strutturali/statistici (ILLIQUIDITY_RISK_PREMIUM, TERM_STRUCTURE_ROLL_YIELD, VOLATILITY_CLUSTERING, FAT_TAIL_VOL_RETURN_ASYMMETRY), e 3 mechanism esplicitamente metodologici/risk-management (SIGNAL_OVERFITTING_METHODOLOGICAL_CAUTION, GRID_MARTINGALE_MEAN_REVERSION_ASSUMPTION, POSITION_HOLDING_TIME_RISK_GROWTH) - mantenuti per completezza e per il red-team, non fenomeni di prezzo puri.

## 4. Claim duplicati/normalizzati

Tutti i 115 claim mappati (0 non mappati) su 33 mechanism - nessun claim scartato in questa fase per duplicazione (la deduplicazione e' avvenuta a livello di CONCETTO, non di claim: piu' claim distinti da fonti diverse che descrivono lo stesso fenomeno confluiscono nello stesso mechanism, mantenendo tutte le fonti come provenance separata - sec.17). Il mechanism con piu' supporto (BREAKOUT_ACCEPTANCE_CONTINUATION) ha 18 claim da 17 fonti distinte (nessuna fonte duplicata sproporzionatamente).

## 5. Contraddizioni piu' interessanti

**2 contradiction group formalizzati** (contradiction_registry_v1.json), entrambi con la variabile di stato mancante ipotizzata ma NON testata:

- **CG-0001**: sweep+reclaim->reversione (11 claim) vs sweep-senza-reclaim->continuazione (4 claim), stesso evento visibile (LIQUIDITY_SWEEP). Ipotesi di stato mancante: genuinita' del displacement/partecipazione prima dello sweep.
- **CG-0002**: breakout->accettazione (23 claim) vs breakout->fallimento (5 claim), esattamente l'esempio dato nella specifica della fase. Ipotesi di stato mancante: conferma di volume/volatilita' concorrente e regime di trend (efficiency).

## 6. Sequence families prodotte

**20 sequence** formalizzate (market_sequence_registry_v1.json), coerenti con lo schema STATE->EVENT_A->TRANSITION->EVENT_B->OUTCOME_FAMILY. Includono 1 famiglia FAILED_EVENT dedicata (BREAKOUT_FAILURE, SEQ-0004) e 1 famiglia NO_TRADE_INFORMATION dedicata (TREND_CHOP_REGIME_CLASSIFICATION, SEQ-0014, is_no_trade_information=true).

## 7. Idee che ripetono fallimenti noti

**SEQ-0010** (RECLAIM generico, BOTH/BUY/SELL senza filtri) = **DIRECT_REPEAT_OF_FAILED_IDEA**, esplicitamente bloccata (implementation_status=NOT_IMPLEMENTABLE_AS_DESCRIBED) con riferimento diretto al risultato REFUTED_AT_DISCOVERY di Phase 7.1. **SEQ-0009** (LIQUIDITY_SWEEP isolato), **SEQ-0011** (RECLAIM filtrato con 2 condizioni di stato indipendenti da CLAIM-0108/0109), **SEQ-0012** (sweep-senza-reclaim) = **RELATED_TO_PREVIOUS_FAILURE**, con motivazione dichiarata del perche' differiscono dalla forma gia' refutata - non semplici "filtri per salvare" l'idea, ma ipotesi genuinamente diverse su quando l'informazione esisterebbe.

## 8. Famiglie realmente nuove per NEXUS

**16 sequence su 20 (80%) sono NOVEL** rispetto a failure_memory_registry_v1.json e ai risultati canonici (Phase 5/6/6.5/7.1) - includono TREND_PERSISTENCE, MOMENTUM_DECAY_TO_MEAN_REVERSION, BREAKOUT_ACCEPTANCE/FAILURE (concettualmente vicine a detector Phase 5 mai promossi a evidence grade), VOLATILITY_COMPRESSION_TO_EXPANSION, CALENDAR_SCHEDULED_EVENT_DRIFT, GOLD_CALENDAR_DEMAND_SHOCK, SESSION_SIGN_REVERSAL, GAP_IMBALANCE_FVG_RESPONSE, TREND_CHOP_REGIME_CLASSIFICATION, MOMENTUM_BURST_CONTINUATION, MEAN_REVERSION_BAND_TOUCH, VALUE_AREA_ACCEPTANCE_REJECTION, VWAP_ACCEPTANCE_REJECTION, PAIRS_COINTEGRATION_MEAN_REVERSION, DUAL_MOVING_AVERAGE_MOMENTUM.

## 9. Dati/informazioni necessarie per testarle

Gap dichiarati esplicitamente (phase7_3_sequence_engine_input_contract_v1.json): (a) NEXUS oggi produce solo barre H4 - qualunque sequence con SETUP_TF/TRIGGER_TF piu' fine (es. M15/M5 per il displacement pre-sweep di SEQ-0011, o il price-discovery di apertura NY) richiede una nuova pipeline di costruzione barre; (b) VWAP di sessione e value area/profilo di volume non calcolati oggi (richiedono dati di volume/aggregazione per sessione); (c) session/clock model timezone-safe/DST-aware non ancora formalizzato (i bucket UTC fissi attuali non lo sono - session_clock_model_v1.json); (d) calendario macro (FOMC) e calendario culturale (festivita' gold-demand) esterni non integrati; (e) un secondo strumento cointegrato con XAUUSD non identificato.

## 10. Le 10-20 famiglie candidate per Phase 7.3

**8 sequence HIGH_RESEARCH_PRIORITY** (punteggio >=13/18, research_priority_queue_v1.json): BREAKOUT_FAILURE (18), BREAKOUT_ACCEPTANCE_CONTINUATION (18), MEAN_REVERSION_BAND_TOUCH_REGIME_DEPENDENT (17), TREND_PERSISTENCE (16), SWEEP_WITHOUT_RECLAIM_CONTINUATION (16), LIQUIDITY_SWEEP (15), TREND_CHOP_REGIME_CLASSIFICATION (15), VOLATILITY_COMPRESSION_TO_EXPANSION (14). **12 ulteriori in MEDIUM/LOW** completano la shortlist di 20 (il registro intero e' la shortlist - nessuna sequenza scartata dal report, solo classificata).

## 11. Perche' sono state prioritarizzate

Da **research_priority_scoring_rule_v1.json**, congelata PRIMA di leggere l'elenco finale (anti-selection rule, sec.22): 9 componenti (falsifiability, causal measurability, implementation clarity, sample availability, distinctiveness da fallimenti noti, source diversity, evidence transparency, parameter count, execution feasibility), ognuna derivata MECCANICAMENTE da campi gia' registrati (evidence_quality, parameter_overfit_risk, failure_memory_relation, categorie di source_diversity_matrix, implementation_status) - nessun punteggio scelto guardando quanto una sequenza sembrasse interessante. Prova diretta che la regola funziona: SEQ-0010 (RECLAIM generico) ottiene solo 7/18 (LOW) nonostante il forte precedente storico, perche' la componente distinctiveness lo penalizza meccanicamente a 0.

## 12. Cosa non sappiamo ancora

Se un qualunque mechanism/sequence di questo registro produca un effetto reale su XAUUSD - **nessun numero e' stato calcolato**. Non sappiamo se le 2 contraddizioni si risolvano con le variabili di stato ipotizzate (displacement/volume per CG-0001, conferma di volatilita'/regime per CG-0002) - sono domande formalizzate, non risposte. Non sappiamo se SEQ-0011 (RECLAIM filtrato) sia genuinamente diverso dalla forma refutata o solo un filtro che sembra diverso - resta un candidato ad alto rischio da trattare con scetticismo proporzionale. Non sappiamo quanto siano frequenti (firing rate reale) i mechanism senza un detector Phase 5 preesistente.

---

## Deliverables

`server/research_scripts/phase7/phase7_2/`:
- `schemas/external_claim_schema_v1.json`, `schemas/market_sequence_schema_v1.json`
- `raw/batch_1..5_*.json` (115 claim grezzi, 5 batch)
- `external_hypothesis_corpus_v1.json`, `source_registry_v1.json`
- `market_mechanism_registry_v1.json`, `mechanism_proxy_registry_v1.json`
- `market_sequence_registry_v1.json`, `contradiction_registry_v1.json`
- `session_clock_model_v1.json`
- `source_graph_v1.json`, `source_diversity_matrix_v1.json`, `failure_memory_crosscheck_v1.json`
- `research_priority_scoring_rule_v1.json`, `research_priority_queue_v1.json`
- `phase7_2_red_team_v1.json`, `phase7_2_research_journal_v1.jsonl`
- `phase7_3_sequence_engine_input_contract_v1.json`
- `external_source_quality_report_v1.json`
- `build_*.py` (5 script di assemblaggio, tutti deterministici e ri-eseguibili)

## Vincoli rispettati

Nessun edge calcolato sui dati NEXUS; nessun uso di development/validation/holdout per confrontare idee; nessun candidato creato per essere promosso; nessun backtest; nessuna parameter optimization; RECLAIM non riciclato senza motivazione indipendente; anti-selection rule rispettata (scoring congelato prima della shortlist); failure memory integrata; nessun Render deploy; commit/push su main.
