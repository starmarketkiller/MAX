# NEXUS — Ministral Task Compiler V1

**Commit:** `682c276` (compiler + bounded handler + persistenza). Riusa `core/router.py` (già esistente, catena TIER0_DETERMINISTIC → TIER1/2_LOCAL → ESCALATION_REQUIRED → MANUAL_REVIEW) e la Dynamic Specialist Review già esistente — nessuna nuova infrastruttura di escalation creata.

## Decisione

Dare a Ministral un ruolo di delega **bounded e read-only**, non un agente libero: ogni task deve passare per un `MinistralTaskTemplate` pre-approvato (schema input/output fisso), mai un prompt libero. Qualunque template con `read_only=False` è esplicitamente rifiutato da `BoundedLocalTaskHandler` — nessuna eccezione silenziosa.

## Cosa cambia

- `server/jarvis_v1/ministral_task_compiler.py` — dataclass `MinistralTaskTemplate` + registry `TEMPLATES`. Primo (e unico ad oggi) template: `repo_inspection_v1` (`task_type=DOCUMENTATION`, `work_type=routine_summary`, `read_only=True`) — confermato coerente con la Review Matrix esistente (`review_required=False`, `producer_default=LOCAL_GENERALIST`), nessuna nuova regola di review creata.
- `server/jarvis_v1/local_bounded_task_handler.py` — `BoundedLocalTaskHandler`, generico su qualunque template futuro, riusa `core/orchestrator.py::_run_local()` (lo stesso motore di esecuzione già usato da `FreeCodingWorkerHandler`) — **non modificato**, per vincolo esplicito dell'utente.
- `server/jarvis_v1/delegation_report.py` — proiezione pura sul Ledger esistente (nessun nuovo storage), per rendere leggibili gli esiti delle delega.
- `PERSIST_MINISTRAL_BOUNDED_OUTPUT_V1`: l'output validato viene codificato (`encode_bounded_output()`) e persistito nel campo **già esistente** `RESULT_PACKET_V1.artifacts_created`, con prefisso `"ministral_bounded_output_v1:"` — nessun nuovo campo di schema, nessuna nuova tabella.

## Bug trovato e fix (durante smoke reali)

Il primo smoke reale su hardware reale (i5-7200U, no GPU) andava in timeout: `_run_local()` chiama `ollama_worker.call_local_model()` senza `json_mode=True` e con il timeout di default di 180s, **non configurabile per singola chiamata** nel codice attuale. Per esplicita richiesta dell'utente ("opzione 1 soltanto: niente modifiche a `core/orchestrator.py`"), il fix è stato ristretto al solo prompt del template `repo_inspection_v1` (accorciato, enum esplicitati) — non alla pipeline di esecuzione. Risultato dopo il fix: 2/3 run completati entro il budget di 180s nei re-test.

## Limiti dichiarati

- Un solo template esiste oggi (`repo_inspection_v1`); l'architettura è pronta per altri ma nessun altro è stato scritto.
- Resta vincolato dallo stesso hardware-gating di `JARVIS_MINISTRAL_ROUTER_V1`: 1/3 run anche dopo il fix non è rientrato nel budget — non un sistema a latenza garantita.
- Nessuna escalation automatica END-TO-END testata con un vero task scientifico/di codice ad alto rischio: solo la catena FAST→STRONG→specialist già esistente in `core/router.py`, non nuova logica di escalation.

## Evidenza/test

Suite automatica (compiler, handler, encode/decode, report) verde; smoke reali registrati nel Ledger (eventi `TOOL_USED`/`RESULT_DELIVERED` con `artifacts_created` popolato dal prefisso `ministral_bounded_output_v1:`).

## Blocker

Nessuno attivo.

## Prossimo passo

In pausa deliberata — priorità passata a FIRST_REVENUE. Da riprendere solo se emerge un uso interno concreto per un secondo template.
