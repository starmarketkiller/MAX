# NEXUS TASK #0002 — Research Safety Net Auto-Backfill

**Baseline:** `0a6abca`. Prima NEXUS TASK a testare esplicitamente il confine fra "l'Orchestrator procede da solo" e "deve fermarsi e chiedere". Claude solo supervisore: inventario/classificazione dei campi e' un'ispezione FATTUALE di TIER0 (vedi `safety_net_classification.py` per il ragionamento completo), il calcolo e' deterministico o via ministral-3:3b, mai deciso/corretto manualmente da Claude.

## Investigazione (TIER0, prima di eseguire qualunque task)

Ispezionati Cross-Strategy Learning Packet, Failure Map, Experiment/Hypothesis Registry, Data Exposure Registry, Path Anatomy (Phase 7.9i/7.9k/7.25/7.26) per le 4 strategie. Trovati **3 casi concreti di dati gia' calcolati ma mai propagati**:

1. **BREAKOUT_ACC.execution_degradation**: bug di key-path nel builder originale (`build_cross_strategy_learning_packet.py` riga 96 cerca `signal_pct_favorable`, chiave mai esistita — il dato reale e' nidificato sotto `signal_edge.pct_favorable`). I `funnel_counts` grezzi esistono gia' in `execution_realism_v1.json`.
2. **BREAKOUT_ACC.favorable_before_loss / adverse_before_win**: `breakout_acc_path_anatomy_v2.json` ha gia' MFE/MAE per-evento — mai incrociato con l'esito vinto/perso del dataset economico per separare le medie condizionate.
3. **BREAKOUT_ACC/ORDER_BLOCK.temporal_concentration + exit_efficiency**: gia' calcolati e verificati in NEXUS TASK #0001, mai propagati nel Learning Packet.

**7 campi classificati DERIVABLE_NOW** (su 46 NOT_AVAILABLE totali nelle 4 strategie) — tutti gli altri **REQUIRES_NEW_DATA** con ragione strutturale verificata (nessuna pipeline di tagging regime/volatilita' per-trade esiste per nessuna strategia; nessun dato OHLC bar-level per ORDER_BLOCK/TSI; TSI non ha MAI avuto un dataset economico trade-per-trade — il suo filone di ricerca riguarda un difetto di contaminazione confermato, Phase 7.17/7.18). **0 campi REQUIRES_SCIENTIFIC_JUDGMENT o SOURCE_CONFLICT** — risultato onesto di questo giro, non un limite dell'impalcatura (pronta e testata comunque).

## Esecuzione (attraverso l'Orchestrator, non script manuale)

8 sotto-task reali: inventario (TIER0), funnel_rates BREAKOUT_ACC (TIER0), favorable/adverse_before (TIER0, join path-anatomy+esito), 4 narrative temporal_concentration/exit_efficiency (TIER2, ministral-3:3b).

**Risultato: 7/8 COMPLETED, 1 ESCALATION_REQUIRED genuina** — `ORDER_BLOCK.exit_efficiency` (13 eventi, rapporto 0.31): il worker locale, dopo 1 retry delimitato, ha ripetutamente omesso il numero chiave dalla narrativa (confermato con campionamento manuale: 2/3 tentativi indipendenti droppano il dato) — una vera **limitazione di affidabilita' locale su questo specifico caso**, non un bug. Il sistema ha correttamente **non forzato** una narrativa incompleta, ne' inventato il numero, ne' fatto scrivere la frase a Claude: ha escalato con un CONTEXT_PACKET_V1 gia' pronto per TIER3_CLAUDE. Il campo resta `NOT_AVAILABLE` nella proposta.

**3 bug reali trovati e corretti nell'harness di verifica** (mai nel contenuto): (1) controllo troppo rigido su virgola vs punto decimale ("0,14" italiano corretto rifiutato perche' cercavo solo "0.14"); (2) **allucinazione reale intercettata**: il modello ha copiato lo stile "~99%" dell'esempio nel prompt inventando "98%" per ORDER_BLOCK senza che nessuna formula sui dati desse quel numero — corretto con un controllo generale anti-allucinazione (ogni percentuale nella narrativa deve corrispondere a un calcolo plausibile sui dati di origine, non solo alla whitelist); (3) accettata anche la forma percentuale equivalente (31%) oltre a quella decimale (0.31).

## Deliverable prodotti (16/16 richiesti)

TASK_MANIFEST_V1 x9, inventario campi, tabella di classificazione (`safety_net_classification.py`), coverage report before/after per le 4 strategie, **proposta** di Learning Packet aggiornato (`proposed_patches/cross_strategy_learning_packets_v1_PROPOSED_UPDATE.json` — **file reale MAI toccato**), provenance map per i 6 campi completati, 1 escalation packet reale, 3 proposte di task future raggruppate (regime-tagging pipeline, bar-level path-anatomy ORDER_BLOCK/TSI, dataset economico pulito TSI — quest'ultima priorita' ALTA, sblocca 21 campi), verificatore indipendente, 11 test, RESULT_PACKET_V1, Event Ledger, questo vault report.

## Coverage (prima → dopo)

| Strategia | Prima | Dopo | Completati | Escalati | Rimangono REQUIRES_NEW_DATA |
|---|---|---|---|---|---|
| BREAKOUT_ACC | 64.3% | **82.1%** | 5/5 | 0 | 5 |
| ORDER_BLOCK | 53.6% | 57.1% | 1/2 | 1 | 11 |
| LIQ_SWEEP | 92.9% | 92.9% | 0/0 | 0 | 2 |
| TSI | 25.0% | 25.0% | 0/0 | 0 | 21 |

## Approval boundary — confermato di nuovo

Task finale (`TASK_NEXUS_0002_PROPOSE_PACKET_UPDATE`, `approval_required=REVIEW_REQUIRED`): termina in **WAITING_APPROVAL**, come atteso — nessuna scrittura del file reale, nessun push automatico.

## Decisione finale

**`SAFETY_NET_BACKFILL_COMPLETED_WITH_ESCALATIONS`**

Corretta: 6/7 campi derivabili completati con successo, 1 escalato genuinamente (non nascosto, non forzato). Premium calls/cost: **0**.

## Deliverables

`safety_net_classification.py`, `run_nexus_task_0002_safety_net_backfill.py`, `verify_nexus_task_0002.py`, `nexus_task_0002_result_v1.json`, `proposed_patches/cross_strategy_learning_packets_v1_PROPOSED_UPDATE.json` + `safety_net_backfill_provenance_map_v1.json`, 2 nuove azioni deterministiche in `core/deterministic_worker.py` (`safety_net_field_inventory`, `compute_percentage_rates`, `join_breakout_acc_path_anatomy_outcome_conditional_excursion`), `server/tests/test_nexus_task_0002.py` (11 test), questo vault report.

## Vincoli preservati

Nessun verdict/hypothesis/holdout toccato (verificato dal verificatore indipendente, hash Data Exposure Registry invariato). Nessuna modifica MQL5/Product-Platform. Nessun deploy, nessun nuovo backtest, nessuna chiamata premium automatica. File reale `cross_strategy_learning_packets_v1.json` intatto.

## Regressione

`verify_nexus_task_0002.py`: PASSED. 28/28 test (core + bake-off + questo). Suite completa `server/orchestrator_v1/`: nessuna regressione.
