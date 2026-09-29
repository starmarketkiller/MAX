# NEXUS TASK #0009 — Jarvis Multi-Agent Finalization Integration

**Baseline:** `0fddc9b` (#0008 approvata come framework, integrazione ancora aperta). Dipendenze: #0007, #0008.

## Routing

Sottomessa realmente all'Orchestrator: `ESCALATION_REQUIRED → MANUAL_REVIEW` (`ROUTER_DIRECT_ESCALATION`) — non `TIER3_CLAUDE` come #0005/#0008/#0007, perché `code_risk=MEDIUM` (non `HIGH`) e `scientific_risk=LOW`: nessuna capacità locale dimostrata copre `required_capabilities=["jarvis_service_integration", "state_machine_integration"]`, ma il profilo di rischio dichiarato non attraversa la soglia che il Router userebbe per instradare a Codex/Claude in automatico. Risolta comunque in questa conversazione, zero chiamate premium.

## Cosa cambia

`server/jarvis_v1/service.py`: `follow_up()` ora, quando un task raggiunge `COMPLETED`, chiama `_run_review_pipeline()` → `review_pipeline_v1.process_work_product()` prima di rispondere. Mai più uno stato `DRAFT`/`UNDER_REVIEW`/`REVISION_REQUIRED` o un'escalation aperta presentati come risultato finale:

- se il work product arriva a `FINALIZED` → risposta formattata da `jarvis_delivery.format_task_completed_summary` (`status="FINALIZED"`);
- se serve una review e il provider non è connesso → `status="ESCALATION_READY_FOR_MANUAL_DELIVERY"`, messaggio esatto: *"Il lavoro locale è completato, ma la policy richiede una review {ruolo} - il provider non è ancora connesso in automatico. Ho preparato il pacchetto di escalation, serve invio manuale."*
- risultato cachato per `task_id` (`self._work_product_cache`, process-local come `self.conversations`) — un follow-up ripetuto non ri-esegue la pipeline né ri-tenta un'escalation già aperta.

**Invariante preservato**: `create_task()` non è stata toccata — Jarvis continua a non scegliere mai un executor (`record["executor"] is None` alla creazione, verificato sia dai test esistenti sia dal verificatore indipendente).

## Limitazione dichiarata esplicitamente (non un bug, una scelta onesta)

`TASK_MANIFEST_V1` non ha un campo `work_type`/`metadata` — estenderlo avrebbe richiesto toccare `contracts/task-manifest.schema.json`, fuori dai `files_allowed` dichiarati per questa task. Ogni task creata da Jarvis usa quindi il default `business_analysis`, che nella Review Matrix impone `review_required=True`. Finché nessun provider `STRATEGIC_GENERALIST`/`SCIENTIFIC_RESEARCHER` è realmente connesso, **ogni** task Jarvis che raggiunge `COMPLETED` produce oggi `ESCALATION_READY_FOR_MANUAL_DELIVERY`, mai `FINALIZED` — dimostrato nei test con il registry reale. Il percorso `FINALIZED` è comunque provato end-to-end forzando `work_type="routine_summary"` (equivalente a come si comporterà un futuro `work_type` dichiarato via manifest).

Inoltre: questo repo non ha ancora un ciclo che esegua realmente `orchestrator.process_task()` per le task create da Jarvis (Jarvis le sottomette soltanto) — l'integrazione si attiva correttamente non appena una task Jarvis raggiunge `COMPLETED` per qualunque via, ma quel ciclo di esecuzione resta un passo futuro non coperto da questa task.

## Bug trovati durante l'esecuzione (non nel codice nuovo — regressione mancata di #0008)

Girando per la prima volta l'intera `server/tests/` (non solo il sottoinsieme controllato in #0008), sono emersi 2 fallimenti reali causati dall'estensione additiva del capability registry in #0008: `test_agent_capability_registry_has_two_ministral_agents` e `test_agent_registry_unchanged_since_bakeoff` assumevano che il registry contenesse **esattamente** i 2 agenti Ministral del bake-off — invariante rotta (correttamente) dai 3 nuovi record di readiness. Corretti per verificare che i 2 agenti Ministral restino un **sottoinsieme** invariato, non l'insieme totale. Lezione: la regressione di #0008 andava fatta su `server/tests/` per intero, non su un sottoinsieme scelto a mano — annotato per le prossime task.

## Deliverable

`server/jarvis_v1/service.py` (modificato), `server/tests/test_jarvis_access_layer_v1.py` (+3 test, 11→14), `server/tests/test_orchestrator_v1_bakeoff.py` + `test_orchestrator_v1_core.py` (corretti), `server/orchestrator_v1/run_nexus_task_0009_submit.py`/`_finalize.py`, `verify_nexus_task_0009.py`.

## Regressione

`verify_nexus_task_0009.py`: **PASSED**. `test_jarvis_access_layer_v1.py`: 14/14. Suite completa `server/tests/`+`server/orchestrator_v1/`: 351/351 (+1 fallimento pre-esistente e non correlato in `test_company_control_plane.py`, confermato via `git stash` fallire anche su HEAD pulito, fuori scope).

## Decisione finale

**`JARVIS_MULTI_AGENT_INTEGRATION_V1_OPERATIONAL_WITH_LIMITATIONS`** — stato `WAITING_APPROVAL`. Nessun deploy, nessuna azione commerciale, nessuna chiamata premium automatica.

## Prossimo passo indicato dall'utente

Provider connectors (incluso ChatGPT) — perché `ESCALATION_READY_FOR_MANUAL_DELIVERY` diventi l'eccezione e non il default corrente, e perché NEXUS possa consultare Claude/Codex/ChatGPT direttamente invece che tramite copia-incolla manuale. Cambio di paradigma dichiarato: da "tu → Claude → NEXUS" a "tu → Telegram/Jarvis → NEXUS → agenti → Jarvis → tu".
