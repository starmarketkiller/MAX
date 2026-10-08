# NEXUS MASTERPLAN V4 — Reparto Jarvis & Automation

Vedi [NEXUS_MASTERPLAN_V4.md](NEXUS_MASTERPLAN_V4.md) per legenda di stato e provenienza. Fonte: census read-only di questa sessione — nessun file executor/dispatcher/bridge toccato.

**Sintesi**: il cervello centrale del sistema, sorprendentemente maturo. Executive State a 9 domini, esecuzione multi-stage reale, pianificazione/capability resolver tutti IMPLEMENTED e cablati in produzione. L'unico gap sistematico è lo stesso di tutti gli altri reparti: self-improvement locale quasi interamente PLANNED.

## Input
Richieste utente, eventi di sistema, dati da reparti, task da eseguire.

## Processo interno

| # | Step | Stato | Evidenza |
|---|---|---|---|
| 1 | Analisi richieste (NLP) | PARTIAL/dormiente-capace | Due percorsi reali: catena regex `classify()` in `service.py` (~90 pattern, sempre attiva); `ministral_router.py` (router cognitivo via Local Inference Gateway) — codice e test reali, ma **OFF di default** (`JARVIS_MINISTRAL_ROUTER_V1`) |
| 2 | Routing e classificazione | IMPLEMENTED | `service.py::_dispatch_classifier()`; short-circuit a prefisso rigido `/mistral`, `/task`, `/handoff`, `/jarvis`, `/new` (costruiti in questa sessione) prima della classificazione |
| 3 | Fast path o deep path | PARTIAL | `local_operations.py::is_complex_mistral_request()` — euristica reale (verbi operativi + soglia lunghezza/parole), ma un singolo gate regex, non un router tunato/appreso da metriche |
| 4 | Pianificazione task e agenti | IMPLEMENTED | `local_operations.py::build_execution_plan()` + `CapabilityResolver`/`SkillRegistry` — 2 skill reali registrate (`mql5-engineering`, `ui-ux-pro-max`), verifica di esistenza su disco, `AUTHORIZED`/`DENIED` fail-closed |
| 5 | Esecuzione multi-stage | IMPLEMENTED, sostanziale | `multi_stage_executor.py` (298 righe) — coordinatore durevole, crea record figli `TASK_MANIFEST_V1` reali, li interroga via Orchestrator/Queue canonici, costruisce `RESULT_PACKET_V1` solo quando ogni step è `VERIFIED` indipendentemente, gestisce timeout di budget totale, ripresa da local-bridge offline, gating escalation premium. Cablato in produzione: `app.py:1542` |
| 6 | Monitoraggio esecuzione | IMPLEMENTED | `MultiStageExecutor.status()`/`run_once()` (loop 2s default, thread background), `last_tick_at`/`last_error_class` esposti; sezione `system` di Executive State mostra anche lo stato multi-stage |
| 7 | Gestione approval | IMPLEMENTED | `WAITING_APPROVAL` del figlio si propaga allo step del genitore; `executive_v1/state.py::unified_approvals()` unisce approvazioni task/revenue-draft/agency in una lista cross-dominio con campi costo/rischio |
| 8 | Aggiornamento Executive State | IMPLEMENTED, oltre il pianificato | `executive_v1/state.py::ExecutiveStateBuilder` — 9 domini (system/tasks/approvals/revenue/trading/social/ai_fashion_agency/finance/infrastructure), ogni provider isolato (`_safe()` — un provider che fallisce produce `UNAVAILABLE`, mai un crash), cache 10s, `overall_progress` ponderato per maturità (mai un numero inventato se <3 domini hanno maturità nota) |
| 9 | Report/briefing | IMPLEMENTED | `executive_v1/conversation.py` — `domain_brief()`, `overview_answer()`, `top_alert()`, `top_problem_answer()`, `spend_answer()`, `activity_answer()`, tutti letti dal vero Executive State |
| 10 | Alert e notifiche | PARTIAL | `alert_engine()` reale; `multi_stage_executor.py`'s `notification_sink` cablato a `_operations_jarvis_sink` in `app.py:1544` e a `telegram_adapter.py` — **non riverificato in questa passata** se il sink raggiunge davvero Telegram end-to-end (territorio di [LOCAL_INFERENCE_CONNECTIVITY_V1](LOCAL_INFERENCE_CONNECTIVITY_V1.md), già verificato per `/mistral` in quella sessione) |
| 11 | Consegna output | IMPLEMENTED per Telegram | Adapter + `render_response()`, costruiti e testati in questa sessione |

## Output
Task completate, decisioni supportate, automazioni attive.

## Self-improvement locale

| Item | Stato |
|---|---|
| KPI tempi/qualità | PLANNED |
| Problemi/opportunità | PLANNED |
| Tuning routing/classificazione | PLANNED |
| Test sandbox | PLANNED |
| Confronto performance | PLANNED |
| Feedback al consiglio globale | PLANNED |

Nessuna eccezione — tutto il self-improvement di questo reparto, nonostante sia il più maturo sul lato esecuzione, resta da costruire.

## Gate e capability
`CapabilityResolver`/`SkillRegistry` fail-closed; `premium_allowed` + controllo tier target prima di trattare un'attesa come "serve premium" (in `multi_stage_executor.py`).

## Verificatori
Verifica indipendente per-step prima della costruzione del `RESULT_PACKET_V1` finale.

## Error handling / retry
Timeout di budget totale task, ripresa da local-bridge offline — entrambi reali in `multi_stage_executor.py`.

## Approvazioni
Propagazione `WAITING_APPROVAL` figlio→genitore; lista unificata cross-dominio in `unified_approvals()`.

## Dipendenze
Orchestrator/TaskQueue/EventLedger condivisi; tutti gli altri 6 reparti (Jarvis è il punto di aggregazione, non un silo).

## Nota di non-duplicazione (verificata)
`local_operations.py` (pianificazione/proiezione, nessuna autorità di esecuzione — dichiarato nel proprio docstring) vs `multi_stage_executor.py` (coordinamento esecuzione — crea/interroga solo figli) vs `executive_v1/` (aggregazione stato cross-dominio, sola lettura) vs `service.py` (dispatch Telegram-facing) sono **livelli puliti, non sovrapposti**. Il diff di 277 righe di `service.py` è coerente con il cablaggio di questi tre nuovi moduli, non con una duplicazione del lavoro `/mistral`/`/task`/`/handoff` di questa stessa sessione.
