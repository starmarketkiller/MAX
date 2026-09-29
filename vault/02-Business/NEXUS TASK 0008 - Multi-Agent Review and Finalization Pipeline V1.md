# NEXUS TASK #0008 — Multi-Agent Review & Finalization Pipeline V1

**Baseline:** `f928f4e3ae6a2d578fe3c97c4ecf8e526cd4b7c3` (Jarvis Access Layer V1 di Codex, `WAITING_DEPLOY_APPROVAL`). Sottomessa insieme a un'azione diretta separata ("TASK PER CLAUDE" — Render/Telegram, vedi nota in fondo).

## Routing (test centrale)

Sottomessa realmente all'Orchestrator (`run_nexus_task_0008_submit.py`): `ESCALATION_REQUIRED → TIER3_CLAUDE`, classificazione `ROUTER_DIRECT_ESCALATION` — nessuna capacità locale copre "progettare una pipeline di revisione multi-agente" (`required_capabilities=["multi_agent_pipeline_design", "orchestrator_architecture_extension"]`), stesso comportamento corretto di #0005. Risolta in questa conversazione (non un'API premium separata), poi registrata via `run_nexus_task_0008_finalize.py`.

## Cosa fa la pipeline

```
User → Jarvis → Orchestrator → Producer → Verifier → Reviewer (se richiesto)
     → Correction/Merge → Finalization Gate → FINAL_RESULT → Jarvis → User
```

`WORK_PRODUCT_V1` (11 stati, fail-closed, `MAX_REVIEW_LOOPS=2`) segue ogni pezzo di lavoro da `DRAFT` a `DELIVERED`. Nessuna `FINAL DELIVERY` finché una review richiesta non è passata — imposto dal Finalization Gate, non da una convenzione.

## Componenti consegnati

- `REVIEW_MATRIX_V1` (`server/review_pipeline_v1/review_matrix.py`): 8 work_type, dati non prompt — un work_type sconosciuto eredita il default **più cauto** (review richiesta, budget `PREMIUM_IF_NEEDED`), mai il più permissivo.
- `SPECIALIST_REGISTRY` esteso additivamente (`contracts/agent-capability-registry.schema.json` + `server/orchestrator_v1/agent_capability_registry_v1.json`): 7 `specialist_role`, 5 agenti totali (2 locali già operativi + 3 record di **readiness** per Claude/Codex/ChatGPT). Nessuno dei 3 provider remoti è dichiarato disponibile in automatico — riflette lo stato *reale* osservato in questa sessione (nessun connector verso Claude nel codice dell'Orchestrator; Codex MCP `CONNECTION_CLOSED`; ChatGPT senza alcun connector nel repo).
- `PREMIUM_BUDGET_POLICY_V1` (5 livelli, regole deterministiche — mai "a sensazione").
- `REVIEW_CONTEXT_PACKET_V1` / `REVIEW_RESULT_V1` / `FINAL_RESULT_PACKET_V1` (contracts + motore).
- Escalation flow: `core/retry_escalation.py` esteso additivamente con `STRATEGIC_AMBIGUITY` (8ª classificazione).
- Finalization Gate deterministico (`finalization_gate.py`) — include uno scanner di pattern secret-like sull'output finale (chiavi `sk-`/`ghp_`, chiavi private, token Telegram) come controllo reale, non solo dichiarato.
- Confidence Model (`confidence_model.py`) — mai auto-dichiarata: derivata da verifier/review/test/limitations.
- `server/review_pipeline_v1/jarvis_delivery.py` — formato di consegna compatto + query esplicite ("chi ha lavorato", "perché Claude", "cosa ha corretto il reviewer") lette dal packet, mai inventate. **Non ancora collegato a `jarvis_v1/service.py`** (fuori scope file di questa task) — libreria pronta, integrazione resta un passo successivo esplicito.
- Learning telemetry (`learning_telemetry.py`, JSONL append-only, stessa disciplina del ledger).
- `contracts/nexus-event.schema.json` esteso additivamente con 14 eventi del ciclo di vita `WORK_PRODUCT_V1`.

## I 5 acceptance test (rieseguiti dal verificatore, non solo dichiarati)

- **Test A** (locale, `routine_summary`): `DELIVERED`, `premium_calls=0`.
- **Test B** (`scientific_research`, verifica fallita 2 volte): con il registry **reale** del repo, Claude è OFFLINE/`NOT_CONFIGURED` → esito genuino `ESCALATION_READY_FOR_MANUAL_DELIVERY`, nessun bypass. Testato *anche* con un registry fittizio con Claude disponibile, per provare che il ramo "review → merge → FINALIZED" funziona quando un provider è davvero raggiungibile.
- **Test C** (`complex_code`, Codex + test passati): `DELIVERED` via solo verifier deterministico, nessuna review.
- **Test D** (reviewer chiede correzioni poi approva): `revision_count=1`, `changes_made_during_review` popolato, `DELIVERED`.
- **Test E** (provider con quota `EXHAUSTED`): `BLOCKED` con motivo esplicito, nessun bypass silenzioso — più un test aggiuntivo che verifica `MAX_REVIEW_LOOPS` (3° loop → `BLOCKED`, mai un ciclo infinito).

## Bug/gap trovati e corretti durante l'esecuzione

- `select_specialist("DETERMINISTIC", ...)` non avrebbe mai trovato un candidato (il worker deterministico non è un "agente" nel registry) — corretto con `_resolve_role()`, uno shortcut esplicito che tratta `DETERMINISTIC` come sempre disponibile invece di forzare una voce fittizia nel registry.
- Verificato (non assunto) che i 3 nuovi record readiness (Claude/Codex/ChatGPT) non alterano il routing esistente: `find_capable_agents()` li esclude sempre per `availability!=ONLINE`/`quota_state` non disponibile — nessuna regressione sui task reali già instradati.
- La fixture di esempio dell'Orchestrator V1 Core originale (`build_example_instances.py`, precedente a #0005) usava un `AGENT_CAPABILITY_REGISTRY_V1` con agenti fittizi diversi da quelli del bake-off — anch'essa necessitava di `specialist_role`/`integration_status` dopo l'estensione additiva dello schema; corretta e rigenerata (`validated_examples_v1.json`).

## Deliverable

`contracts/`: work-product(.schema/-lifecycle).schema.json, review-matrix, review-context-packet, review-result, final-result-packet, premium-budget-policy (nuovi); agent-capability-registry.schema.json, nexus-event.schema.json (estesi additivamente).
`server/review_pipeline_v1/`: work_product.py, review_matrix.py, premium_budget_policy.py, specialist_registry.py, escalation.py, finalization_gate.py, confidence_model.py, review_engine.py, jarvis_delivery.py, learning_telemetry.py, 3 builder + example_instances.
`server/orchestrator_v1/`: agent_capability_registry_v1.json rigenerato (5 agenti), core/retry_escalation.py esteso, run_nexus_task_0008_submit.py/_finalize.py, verify_nexus_task_0008.py.
`server/tests/test_review_pipeline_v1.py` (30 test).

## Regressione

`verify_nexus_task_0008.py`: **PASSED** (schemi validati, 5 acceptance test rieseguiti con esito reale, nessun provider premium dichiarato disponibile senza esserlo, regressione `test_review_pipeline_v1.py`+`test_funding_v1.py` PASS). Suite completa Orchestrator+funding+jarvis+knowledge_browser+review_pipeline: 99/99 (+ 2 fallimenti transitori attesi, stessa causa nota di #0006/#0007 — `git diff` su `contracts/` non ancora committato, si risolvono dopo il commit).

## Decisione finale

**`MULTI_AGENT_FINALIZATION_PIPELINE_V1_OPERATIONAL_WITH_LIMITATIONS`** — stato `WAITING_APPROVAL`, confidence MEDIUM. Limitazioni dichiarate esplicitamente: nessun provider premium è oggi richiamabile in automatico (readiness-only, per design — punti 14-15 della spec); il re-verify dopo una revisione è assunto PASS dal motore in una pipeline sincrona (una futura pipeline asincrona dovrà ri-eseguire davvero il verifier del chiamante); `jarvis_delivery.py` non ancora collegato a `jarvis_v1/service.py`. Nessun deploy, nessuna azione commerciale, nessun live trading, nessuna spesa, nessuna chiamata premium automatica non autorizzata.

## Nota sulla parte "TASK PER CLAUDE" (Render/Telegram) ricevuta nello stesso messaggio

Preflight eseguito e confermato: `HEAD == origin/main == f928f4e3ae6a2d578fe3c97c4ecf8e526cd4b7c3` (fast-forward locale eseguito, nessun commit incompatibile). `scripts/check_production_alignment.py` confermato funzionante: produzione attuale = `PRODUCTION_UNKNOWN` (nessun `/api/version` nella build live, come atteso — non ancora deployata la baseline con Jarvis Access Layer V1). Oltre il preflight, questa parte richiede accesso reale a Render (dashboard/API) e al bot Telegram che questa sessione **non possiede** (nessuna credenziale in ambiente, nessuna sessione browser attiva) — riportato separatamente all'utente in chat con l'elenco preciso di cosa serve da parte sua, coerente con la regola esplicita "nessun secret in chiaro in chat".
