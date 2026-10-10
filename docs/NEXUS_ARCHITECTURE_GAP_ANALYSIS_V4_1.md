# NEXUS MASTERPLAN V4.1 — Architecture Gap Analysis & Performance Review

Estende [NEXUS_MASTERPLAN_V4_GAP_ANALYSIS.md](NEXUS_MASTERPLAN_V4_GAP_ANALYSIS.md) (reparti) con l'infrastruttura (sito/backend/CI/Render) censita in V4.1, e aggiunge la revisione sistematica delle performance richiesta dalla task (sez.17).

## Cosa V4.1 ha scoperto che V4 non copriva

| Area | Scoperta |
|---|---|
| Frontend | SPA React matura (40+ pagine), già con auth solida e un hook di polling riusabile — **molto più costruito di quanto V4 lasciasse intuire** ("server/static/dashboard.html exists" era una sottostima) |
| Backend | `app.py` è un singolo file da 7.898 righe/241 route — un rischio strutturale reale non visibile dal census per-reparto di V4 |
| CI/Deploy | Safe Deploy V1 è ancora più rigoroso di quanto V4 avesse notato — doppio livello di protezione (`classify_deploy_risk.py` + `evaluate_auto_approval.py`), test di regressione negativo sul preflight di sicurezza |
| Render/dati | Rischio reale non precedentemente documentato: disco da 1GB condiviso tra DB, cache storico Dukascopy e backup; backup solo manuale, stesso disco del primario |
| Contratti | 64 file schema (non solo gli ~15 citati episodicamente in V4) — il confine di validazione è più esteso e più maturo di quanto apparisse |

## Performance Optimization Review (sez.17 della task, sistematica)

Per ciascuno dei 18 item richiesti: trovato con evidenza, o non verificabile in questa sessione (mai inventato).

| # | Item | Verdetto |
|---|---|---|
| 1 | Passaggi eliminabili | **Trovato**: duplicazione in `research_scripts/phase7` (manifest collection ripetuta manualmente) — già in [Architecture Review V4 #7](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#7-quick_win-consolidare-la-duplicazione-in-research_scriptsphase7) |
| 2 | LLM calls evitabili | **Parzialmente verificabile**: il Risk Gate di Trading è già deterministico (non-LLM) per design; `classify()` precede sempre `ministral_router.py` — il principio "deterministico prima dell'LLM" è già applicato dove verificato |
| 3 | Parallelismo sicuro | **Trovato, proposto**: `parallel_groups` in `NEXUS_WORKFLOW_DEFINITION_V1` per Trading (Scout/News/Sentiment/Charts eseguibili in parallelo) — non ancora implementato, verificare supporto in `multi_stage_executor.py` |
| 4 | Event-driven invece di polling | **Valutato**: `useVisiblePolling.js` già parsimonioso (si ferma su tab non visibile) — raccomandato mantenerlo, SSE come upgrade futuro non urgente (vedi [Visual Operations integration](NEXUS_VISUAL_OPERATIONS_SITE_INTEGRATION.md)) |
| 5 | Precomputazione report | **Non verificato in questa sessione** — nessuna evidenza raccolta né a favore né contro |
| 6 | Caching | `@tanstack/react-query` già fornisce caching lato frontend (trovato nel census, non approfondito oltre la presenza della libreria) |
| 7 | Riduzione serializzazioni | **Non verificato** — richiederebbe profiling reale, fuori scope di un census statico |
| 8 | Riduzione query | **Non verificato** — stesso motivo |
| 9 | Capability reuse | **Confermato ripetutamente**: ogni census di reparto in V4 ha trovato riuso dell'Orchestrator/capability esistenti, zero nuovi agenti |
| 10 | Task atomiche | **Già il pattern**: `TASK_MANIFEST_V1`/nodi di workflow sono già pensati come unità atomiche |
| 11 | Resource Governor P0–P4 | **Gap trovato**: la Queue reale usa `URGENT/HIGH/NORMAL/LOW`, non P0-P4 — mappatura esplicita necessaria (vedi [NEXUS_MASTERPLAN_V4.md §5](NEXUS_MASTERPLAN_V4.md)), non ancora fatta |
| 12 | Code logiche senza duplicare la queue | **Rispettato per design**: tutti i contratti proposti in V4.1 derivano da TaskQueue/EventLedger, mai una coda parallela |
| 13 | Recovery persistente | **Già reale**: `multi_stage_executor.py` gestisce ripresa da local-bridge offline (vedi [census V4 Jarvis](NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md)) |
| 14 | Verificatori leggeri per task a basso rischio | **Proposto**: i 4 livelli L0-L3 di [NEXUS_INDEPENDENT_REVIEW_V1.md](NEXUS_INDEPENDENT_REVIEW_V1.md) permettono di scegliere il livello minimo necessario invece di applicare sempre il massimo |
| 15 | Incremental frontend updates | **Già il pattern**: React + React Query fanno aggiornamenti incrementali per natura, nessuna azione necessaria |
| 16 | Lazy loading e reduced motion | **Non verificato** — nessuna evidenza raccolta sull'uso di `React.lazy()` o `prefers-reduced-motion` nel frontend esistente |
| 17 | Budget per esperimento | **Proposto**: `resource_budget`/`timeout` in `NEXUS_WORKFLOW_DEFINITION_V1` |
| 18 | Benchmark prima/dopo | **Proposto**: `metrics_vs_baseline` in `NEXUS_INDEPENDENT_REVIEW_V1`, con soglia dichiarata in anticipo — mai post-hoc |

**Disciplina rispettata**: dove non c'era evidenza raccolta in questa sessione (item 5, 7, 8, 16), il verdetto è "non verificato", mai un beneficio stimato senza base.

## Riconciliazione con Command Floor di Codex (scoperta a fine sessione)

**Scoperta dopo aver scritto la proposta del Visual Operations Center, non prima**: durante questa stessa sessione, Codex ha mergiato su `origin/main` (`d2c7eed`) un sistema di visualizzazione operativa — "Command Floor" — con la stessa identica filosofia della mia proposta, design diverso. Census dedicato read-only eseguito (`git show origin/main:<path>`, nessun file toccato).

| Aspetto | Command Floor (Codex, già reale) | La mia proposta V4.1 | Verdetto |
|---|---|---|---|
| Unità base | "Stazione" (`frontend/src/command/stations.js`, 119 su 7 reparti + Council) — skill/worker/gate/input/output per stazione | "Nodo" (`NEXUS_WORKFLOW_DEFINITION_V1.nodes`) — ruolo/capability/required | **Stesso concetto**, schema diverso |
| Dati live | `live.js` legge 9 endpoint reali esistenti, `classifyResponse()` fail-closed (`LIVE_VERIFIED` solo con validator esplicito — 2/9 oggi) | `NEXUS_VISUAL_WORKFLOW_STATE_V1` (proposto, non implementato) | **Già implementato da Codex**, con lo stesso rigore fail-closed che proponevo |
| Esecuzione reale | `floor_workflow.py` — un workflow reale (fashion handoff, 3/10 stazioni con evidenza, le altre dichiarate `NOT_RUN` esplicitamente), passa per l'Orchestrator esistente, si ferma a `WAITING_APPROVAL` | `MultiStageExecutor` + `NEXUS_WORKFLOW_DEFINITION_V1` (proposto) | **Stesso principio già applicato da Codex** su un caso reale, un solo task sul dispatcher esistente |
| Council | Room "Council" solo come label/dati statici nella UI (`stations.js`), **zero backend**, zero hit per "council" in `server/app.py`/`jarvis_v1/` | `NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md` (proposta V4) | **Nessuno dei due sistemi lo implementa** — gap reale confermato indipendentemente due volte, la mia proposta resta l'unica sul tavolo |
| Risultato task | `task_result_view.py` — proiezione reale sola-lettura di `TASK_MANIFEST_V1`/`result_packet`, mai rigenera lavoro mancante | `NEXUS_WORKFLOW_RUN_STATE_V1`/`DEPARTMENT_RESULT_PACKET_V1` (proposti) | **Concettualmente vicino**, scoped al multi-stage generico non per-reparto |
| Endpoint | `GET /api/jarvis/floor-workflow` (`app.py:1959`), riusa 9 endpoint preesistenti generici, nessun endpoint duplicato | Nessun endpoint nuovo proposto esplicitamente | Coerente |

**Conclusione onesta**: la parte "costruire un Visual Operations Center da zero" della mia proposta è **in gran parte già fatta, con un design migliore e più dettagliato del previsto** (119 stazioni reali, non un concetto astratto). Non è stato sprecato lavoro — i miei contratti JSON Schema restano utili come **proposta di formalizzazione** di `stations.js` (oggi JS ad hoc senza versioning esplicito) se Codex o l'utente lo ritengono utile, non come sostituzione. La **Milestone 2 della roadmap va riletta come "verificare/estendere Command Floor", non "costruire da zero"** — vedi [Roadmap](NEXUS_IMPLEMENTATION_ROADMAP_V4_1.md). Il gap sul Global Improvement Council **resta pienamente valido e ora ha un'evidenza più forte**: due sistemi costruiti indipendentemente, con la stessa visione, nessuno dei due ha ancora un Council funzionante.

## I 2 rischi infrastrutturali reali più significativi trovati in V4.1 (non in V4)

1. **Backup manuale, stesso disco del primario** — single point of failure reale, non ipotetico (vedi [Render Infrastructure Plan](NEXUS_RENDER_INFRASTRUCTURE_PLAN.md)).
2. **`app.py` a 7.898 righe/241 route in un solo file** — rischio di conflitto crescente con lavoro concorrente (Codex), non ancora un problema manifestato ma strutturalmente fragile.

Questi due si aggiungono alla Top 10 di V4 nella lista unificata del documento principale.
