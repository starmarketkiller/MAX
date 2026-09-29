# NEXUS TASK #0005 — Funding Priority & Opportunity Framework V1

**Baseline:** `942720e`. Prima NEXUS TASK di natura **architetturale/design** (non backfill di dati esistenti) dopo che il modello operativo base è stato validato su 4 cicli reali (#0001-#0004).

## Perché è diversa dalle precedenti

#0001/#0002 sono backfill di dati **già esistenti** — Ministral aveva una possibilità reale di successo. Qui non c'è nulla da "scoprire": è design di un framework nuovo. Il Router ha **correttamente riconosciuto l'assenza di capacità locale** (`required_capabilities=["business_framework_design", "priority_scoring_model_design"]`, nessun agente le dimostra) ed è escalato **immediatamente** a TIER3_CLAUDE, senza sprecare un tentativo locale — un comportamento diverso ma altrettanto corretto di quello dimostrato in #0002 (dove 6/7 sotto-task erano invece genuinamente derivabili in locale). `ROUTER_DIRECT_ESCALATION` con `CONTEXT_PACKET_V1` auto-generato, verificato funzionante.

## Design consegnato

- **`contracts/opportunity.schema.json`**: OPPORTUNITY_V1 — 11 dimensioni dichiarate (mai derivate da dati di mercato reali) + due assi di priorità **separati per costruzione**.
- **`contracts/opportunity-priority-queue.schema.json`**: due classifiche indipendenti + vista affiancata, con `funding_can_finance_technical` **dichiarato esplicitamente** (mai inferito da una correlazione statistica fra i punteggi).
- **`server/funding_v1/opportunity_scoring.py`**: motore deterministico, punti-per-livello-enum e pesi **espliciti e documentati** (sommano 1.0 su entrambi gli assi) — `time_to_cash` pesa di più nel funding (0.15, obiettivo dichiarato: cassa presto), `infrastructure_leverage` pesa di più nel technical (0.35, avanzamento del core NEXUS).
- **5 opportunity di esempio** radicate nel contesto reale di questo progetto, esplicitamente etichettate come illustrative (`provenance.dimension_estimation_method=ESTIMATED_BY_CLAUDE_NO_MARKET_DATA`), non decisioni di business già prese.

## Prova che i due assi sono genuinamente indipendenti

| Opportunity | Funding | Technical |
|---|---|---|
| Tool provenance/audit compliance | **81.2** | 43.8 |
| Abbonamento segnali trading | 75.2 | 18.0 |
| Backtest-as-a-Service | 60.2 | 59.0 |
| Consulenza metodologia Safety Net | 55.8 | 18.0 |
| Prodotto SaaS Orchestrator locale-first | 47.8 | **100.0** |

Esattamente il pattern richiesto: il prodotto SaaS Orchestrator è il più interessante tecnicamente (avanza direttamente il core NEXUS) ma il più lento a generare cassa; il tool di compliance è l'opposto. Test dedicato (`test_technical_and_funding_priority_are_genuinely_independent_axes`) verifica che i due ranking **non siano mai identici**.

**Nota di rigore inclusa deliberatamente**: l'opportunity "abbonamento segnali" ottiene un funding score alto (automazione/ricorrenza) ma `risk=VERY_HIGH` lo penalizza, e la descrizione dichiara esplicitamente che **nessuna strategia NEXUS ha oggi status EDGE_CONFIRMED** (Phase 7.27: la dominanza BUY è largamente spiegata dal regime, non da un edge) — non è azionabile oggi. Illustra perché il framework non va mai letto senza il campo risk e la descrizione completa.

## Bug reale trovato e corretto nel core dell'Orchestrator

Transizione `ESCALATION_REQUIRED → WAITING_APPROVAL` mancante nella macchina a stati — la prima escalation di questo Core risolta con un intero framework nuovo (non un singolo campo dato come in #0004) ha rivelato che questo percorso non era mai stato previsto. Aggiunta anche `ESCALATION_REQUIRED → COMPLETED` per il caso in cui la risoluzione non tocchi file reali.

## Decisione finale

**`FRAMEWORK_READY_AWAITING_ADOPTION`** — stato **WAITING_APPROVAL**, confidence HIGH. Introduce architettura canonica nuova: **non adottato automaticamente**, resta in attesa di una conferma esplicita dell'utente prima di essere considerato canone per Jarvis/futuri task.

## Deliverables

`contracts/opportunity.schema.json`, `contracts/opportunity-priority-queue.schema.json`, `server/funding_v1/` (opportunity_scoring.py, build_example_opportunities.py, build_opportunity_priority_queue.py, example_instances/opportunities_v1.json, opportunity_priority_queue_v1.json), `run_nexus_task_0005_funding_framework.py` + `run_nexus_task_0005_finalize.py`, `verify_nexus_task_0005.py`, fix a `core/task_queue.py`, `server/tests/test_funding_v1.py` (8 test), questo vault report.

## Regressione

`verify_nexus_task_0005.py`: PASSED (ricalcolo indipendente di ogni punteggio, schemi validati, assi confermati indipendenti). 47/47 test su tutta la suite Orchestrator+NEXUS TASK.
