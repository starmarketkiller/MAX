# NEXUS — piano operativo per agenti desktop (V1.1)

Data del piano precedente: 4 novembre 2026. Questa revisione: 5 novembre 2026, Europe/Roma.

V1.1 non esegue il Task 00, non modifica codice operativo e non assegna punti. Il nucleo resta `BASELINE_PENDING` finché `ACCEPTANCE_V1.md` non è congelato da T00 sul checkout che misura.

## Cosa rende V1.1 eseguibile

Il piano del 4 novembre descrive il ciclo giusto e i vincoli giusti. V1.1 aggiunge il contratto che impedisce a un agente di inventare la percentuale, di riscrivere moduli già presenti o di committare il tree sporco di un altro writer.

1. Ogni criterio ha scope, classe di prova minima e un solo task che può assegnare i 5 punti.
2. Esiste un tetto di punteggio per task. Un test verde fuori scope vale zero.
3. Le prove candidate sono nominate. Sono ipotesi da rieseguire, non PASS.
4. I path già sporchi in questo checkout sono stranieri: si leggono, non si revertono e non si includono in `git add`.
5. Un lock di writer rende operativo il vincolo «un solo scrittore sul core».
6. T00 pubblica un solo prompt successivo, scelto con una tabella di blocco. Il rischio raggiungibile precede l'ordine numerico, e lo fa in un unico prompt.

## Osservazione di contesto, non baseline

Lettura statica del 5 novembre 2026 (Europe/Roma) sul checkout locale:

| Campo | Valore osservato |
|---|---|
| Repo | `C:\Users\User\ClaudeWork\MAX` |
| Branch | `cursor/edge-freeze-credit-safe-loop-5198` |
| HEAD | `cfa275366626b2e3c348226ad00a755528aafd36` |
| Remoto del branch | behind 2 rispetto a `origin/cursor/edge-freeze-credit-safe-loop-5198` al momento dello status iniziale |
| main citato il 4 novembre | `111431ad01eaab76009303bbffc95b2f8d1d04c2`, CI run 922 verde il 30 ottobre 2026 |

HEAD di questo checkout e lo SHA di main citato il 4 novembre sono diversi. T00 rilegge branch, HEAD, `git status --porcelain` e la CI da GitHub Actions. Lo stato CI dentro executive state è una osservazione su file (`executive_observations_v1.json` o `NEXUS_CI_STATUS`); il documento `docs/NEXUS_EXECUTIVE_STATE_AND_JARVIS_CONVERSATION_V1.md` dice che il backend non osserva Actions da solo.

Path del core già modificati o non tracciati in quello status. T00 conferma l'elenco completo; questo è il sottoinsieme che tocca il nucleo:

- Modificati: `contracts/context-packet.schema.json`, `contracts/result-packet.schema.json`, `contracts/review-result.schema.json`, `server/app.py`, `server/orchestrator_v1/core/capability.py`, `server/orchestrator_v1/core/deterministic_worker.py`, `server/orchestrator_v1/core/local_agent_bridge.py`, `server/orchestrator_v1/core/ollama_worker.py`, `server/orchestrator_v1/core/orchestrator.py`, `server/orchestrator_v1/core/router.py`, `server/orchestrator_v1/core/task_queue.py`, `server/orchestrator_v1/nxs_schema_validator.py`, `server/tests/test_durable_queue_dispatcher_v1.py`
- Non tracciati: `server/jarvis_v1/execution_grants.py`, `server/jarvis_v1/execution_grant_routes.py`, `server/orchestrator_v1/runtime_state/`

Una prova su questo tree dimostra il worktree, incluso il diff non committato. Il report registra l'hash del diff dei file citati. `staging/` non esiste e non risulta ignorato: i report di T00 nascono lì e restano fuori da `git add` generico.

## Contratto di punteggio

Venti criteri, cinque punti ciascuno, denominatore 20. Stati ammessi: `PASS`, `FAIL`, `UNKNOWN`, `STALE`.

- `PASS` = 5 punti, solo con la classe di prova minima, lo scope congelato e la validità ancora vera.
- `FAIL` = 0 punti ed entra nella copertura.
- `UNKNOWN` = 0 punti, fuori copertura.
- `STALE` = 0 punti, fuori copertura. È una prova scaduta, non un fallimento nuovo.
- Non esiste uno stato `PARTIAL` per il punteggio. Evidenza incompleta resta `UNKNOWN`.
- `BASELINE_PENDING` finché `frozen` è false. In JSON la percentuale è `null`, mai `0`, prima del congelamento.
- Copertura = criteri in `PASS` o `FAIL` / 20.
- Un denominatore diverso è V2, con ricalcolo comparabile.

Classi di prova: `STATIC`, `AUTOMATED_TEST`, `LOCAL_RUNTIME`, `REMOTE_RUNTIME`. I mock restano etichettati `MOCK` e non soddisfano una classe runtime.

Validità:

| Classe | Resta valida |
|---|---|
| STATIC | finché il blob dei file citati è identico |
| AUTOMATED_TEST | finché i blob del test e dei file di implementazione citati sono identici |
| LOCAL_RUNTIME | 24 ore, oppure fino a riavvio del processo, cambio configurazione o cambio modello |
| REMOTE_RUNTIME | 24 ore e solo per il release id citato |

Allo scadere, lo stato diventa `STALE` e i punti scendono.

### Tetto assegnabile

Il tetto è il massimo, non il risultato atteso. Un criterio entra nel punteggio solo se la prova minima è stata rieseguita sul checkout misurato.

| Dopo | Può aggiungere | Tetto se tutto il precedente è PASS |
|---|---|---|
| T00 | C01, C02, C04, C05, C06, C08, C17 | 35 |
| T01 | C03, C07, C09, C12, C13 | 60 |
| T02 | C11, C16, C18 | 75 |
| T03 | C10, C14, C15 | 90 |
| T04 | nessuno nuovo; può far scadere o far fallire C01 e C02 | 90 |
| T05 | C19 | 95 |
| T06 | C20 | 100 |

T07–T12 hanno denominatori propri. Non si sommano al nucleo e non si mediano con `overall_progress`.

`overall_progress` in executive state è la media di `MATURITY_WEIGHTS` sui domini business con maturità nota. Resta quel numero. Il punteggio 20×5 è un altro registro.

### Criteri e prova minima

Scope comune del nucleo, salvo nota diversa: un processo, store JSON della `TaskQueue`, dati isolati. Due processi sullo stesso file non sono una garanzia V1: il modulo dichiara un `RLock` di processo. Dimostrare il rifiuto o l'assenza di guardia è lavoro di T02 e non alza C18 oltre lo scope single-process.

| ID | Capacità | Prova minima | Scope che vale 5 punti | Prove candidate da rieseguire | Assegnabile da |
|---|---|---|---|---|---|
| C01 | Identità del runtime interrogato | LOCAL_RUNTIME | processo realmente interrogato, con SHA o versione di build osservata | `GET /api/ready`, `GET /api/jarvis/dispatcher/status`. In sviluppo il dispatcher risulta disabilitato di default (`docs/NEXUS_DURABLE_QUEUE_DISPATCHER_V1.md`) | T00, solo se il processo risponde |
| C02 | Gateway e modello senza segreti | LOCAL_RUNTIME | health del gateway già in esecuzione e identità modello osservata, segreti assenti dal report | `provider_policy_registry_v1.json` marca `OLLAMA_LOCAL` `AVAILABLE` con `last_health_check: null` e modello `ministral-3:3b`. Quel record non è un health check. Test: `test_nexus_local_inference_gateway_v1.py`, `test_local_agent_bridge_v1.py` | T00 solo su processo già acceso; altrimenti T03/T04 |
| C03 | Input con hash e provenienza | AUTOMATED_TEST o LOCAL_RUNTIME | hash dentro il context packet canonico | `core/context_packet.py`, `contracts/context-packet.schema.json` (schema sporco in questo checkout) | T01 |
| C04 | Task canonico nello scope corretto | AUTOMATED_TEST | `JarvisService` o `TaskQueue` canonica, non uno store laterale | `test_task_creates_a_real_canonical_task` | T00 se rieseguito |
| C05 | Obiettivo e criteri persistiti | AUTOMATED_TEST | campi sul record canonico | `test_task_without_objective_prompts_usage`, schema task manifest | T00 se rieseguito |
| C06 | Duplicato senza effetti duplicati | AUTOMATED_TEST | stessa `idempotency_scope` + `idempotency_key` su una `TaskQueue` | `TaskQueue.submit_idempotent`; `test_claim_prevents_double_execution`. L'idempotenza Telegram è un altro strato e non chiude da sola C06 | T00 se rieseguito sullo store canonico |
| C07 | Contesto limitato, segreti esclusi | AUTOMATED_TEST | packet canonico o errore sanitizzato sul percorso del task | `dispatcher._sanitized_error`; `test_sanitized_error_has_no_raw_bearer_value` | T01 |
| C08 | Caso adatto risolto senza LLM | AUTOMATED_TEST | `route()` verso `TIER0_DETERMINISTIC` e worker deterministico, zero chiamate modello | `deterministic_worker.ACTIONS`; `test_dispatcher_does_not_bypass_router_or_premium_gate` | T00 se rieseguito |
| C09 | Caso adatto sul modello locale reale | LOCAL_RUNTIME | chiamata osservata al modello locale, id modello nel report | registro: `ministral-3:3b`. Il runtime va riletto dal processo | T01. Se il modello non è già disponibile, il criterio resta UNKNOWN; un mock non lo chiude |
| C10 | Routing e origine di costo, senza chiamata a pagamento | LOCAL_RUNTIME del run misurato | provider id e cost class del run, zero invocazioni premium in quel run | Il router produce `ESCALATION_REQUIRED` e il suo docstring dichiara di non invocare Claude/Codex. `ProviderConnectorV1`, nel test `test_groq_unavailable_falls_back_to_codex_or_claude`, chiama l'adapter Codex mock quando Groq è `OFFLINE` e Codex è `AVAILABLE`. È un MOCK della preferenza, non un incidente live e non una prova che la chiamata a pagamento sia impossibile. Registry: `CLAUDE` e `CODEX_OPENAI` `OFFLINE`, `configured: false`. Policy `quality_and_risk_override_cost: true` | T03 |
| C11 | Errore, timeout e retry delimitati | AUTOMATED_TEST | transizioni reali del dispatcher su store isolato | `test_pre_execution_failure_is_released_with_backoff`; `test_exception_after_running_is_blocked_not_replayed` | T02 |
| C12 | Verifier rifiuta un risultato piantato errato | AUTOMATED_TEST o LOCAL_RUNTIME | il verifier canonico rifiuta il fixture errato e il task non risulta accettato | `test_local_verifier_rejected_review_v1.py` usa mock di review. Un reject stubbato che solo instrada la review è UNKNOWN per C12 | T01 |
| C13 | Risultato corretto accettato con riferimenti | LOCAL_RUNTIME o AUTOMATED_TEST sul percorso T01 | result packet con riferimenti alle prove del caso | da produrre in T01 | T01 |
| C14 | Handoff compatto esportabile | AUTOMATED_TEST | artefatti da `write_task_artifacts` sul record canonico, senza segreti e senza secondo store | `render_handoff_md`, `test_handoff_known_task_writes_and_reports_artifact_paths` | T03. Un file di handoff generico non chiude l'import del successore |
| C15 | Esito del successore importato e correlato | LOCAL_RUNTIME, anche manuale se dichiarato | correlazione a task, attempt e SHA | lo stato `ESCALATION_REQUIRED` da solo non è un import | T03 |
| C16 | Riavvio conserva coda e risultato terminale | AUTOMATED_TEST | riapertura dello stesso file JSON: `QUEUED` ancora in coda, stato terminale invariato | T00 cerca il test esistente prima di scriverne uno | T02 |
| C17 | RUNNING ambiguo non rieseguito | AUTOMATED_TEST | classificazione `ORPHANED_RUNNING_AFTER_RESTART` o `DISPATCH_EXECUTION_AMBIGUOUS`, stato bloccato, nessun secondo effetto | `test_restart_blocks_orphaned_running_fail_closed`; `test_exception_after_running_is_blocked_not_replayed`. I file di coda e il test sono sporchi in questo checkout: la prova è del worktree | T00 se rieseguito e il diff è registrato |
| C18 | Yield interattivo e concorrenza uno | AUTOMATED_TEST | un consumer, `yield_predicate` vero sospende il background | `test_interactive_gate_makes_dispatcher_yield_background_work` | T02 |
| C19 | Consegna persistita e executive coerente coi dati vecchi | AUTOMATED_TEST più una consultazione persistita | proiezione executive e risposta letta dallo stato persistito; dato assente o scaduto visibile come tale | `test_no_invented_numbers`; `test_stale_account_telemetry_is_never_shown`; `test_state_is_schema_valid_and_reports_real_blockers`. Il sink Telegram isolato è di T05 e serve a C19 perché il criterio include la consegna | T05 |
| C20 | Tre prove congelate, una con escalation, senza duplicati | LOCAL_RUNTIME | serie eseguita sul runtime locale; l'escalation è un handoff il cui successore è una sessione reale, oppure il criterio resta UNKNOWN | nessuna prova candidate storica chiude la serie | T06 |

`ESCALATION_REQUIRED` nel router è una decisione. Non conta come C14, C15 o C20.

### Registro

`staging/nexus_operational_core_v1/PROGRESS_V1.json`:

```json
{
  "registry_id": "NEXUS_JARVIS_CORE_ACCEPTANCE_V1",
  "frozen": false,
  "baseline_status": "BASELINE_PENDING",
  "denominator": 20,
  "points_per_pass": 5,
  "source_sha": null,
  "worktree_diff_hash": null,
  "observed_at": null,
  "environment": null,
  "score": {"points": null, "percent": null, "delta_points": null},
  "coverage": {"pass_or_fail": null, "denominator": 20},
  "next_task": "T00_BASELINE",
  "criteria": {}
}
```

Ogni criterio, una volta misurato: `status`, `points`, `scope`, `proof_class`, `evidence_refs`, `valid_until`, `blob_shas`, `notes`.

Formato di aggiornamento, dopo il congelamento:

```text
Task: ID — criteri di task PASS/previsti.
Nucleo Jarvis V1: X/20, Y%, delta +/-Z punti; copertura W/20.
Altri reparti: baseline non stabilita, oppure la metrica propria.
Prova nuova: percorso + SHA + timestamp Europe/Roma + classe.
Prossimo blocco: un solo prompt.
```

Prima del congelamento la riga del nucleo è `BASELINE_PENDING`.

## Lock di writer

Prima di modificare codice, l'agente scrive `staging/nexus_operational_core_v1/WRITER_LOCK.json` con `task_id`, `paths`, `pid`, `hostname`, `source_sha`, `started_at`, `expires_at`. Scadenza massima 12 ore, rinnovata dallo stesso task.

Se il lock è nel futuro e il pid è vivo, l'agente si ferma. Se è scaduto, registra `STALE_LOCK` e può prendere solo path disgiunti. Ricerca in sola lettura può procedere in parallelo. MT5 Tester e benchmark locali pesanti non partono insieme.

Owner dei path, quando il task arriva a modificare:

| Task | Può modificare | Lascia intatti |
|---|---|---|
| T00 | solo file sotto `staging/nexus_operational_core_v1/T00_BASELINE/` | tutto il codice |
| T01 | collegamento mancante dimostrato fra service, handler, executor, handoff e orchestratore | semantica di claim e transizioni di coda |
| T02 | `task_queue.py`, `dispatcher.py` e i loro test | policy provider |
| T03 | policy, connector, import/export handoff e i loro test | claim del dispatcher |
| T04 | bridge locale, gateway, script di operazioni in copia isolata | coda |
| T05 | proiezione `server/executive_v1/` e lettura del registro | un secondo store di KPI |
| T06 | niente, review in worktree separato allo SHA consegnato | — |

`execution_grants.py` e `execution_grant_routes.py` si leggono in T00 e T09. Nessun altro task li adotta come secondo sistema di autorizzazione.

## Blocco comune

Anteporre questo blocco a un solo prompt di task.

```text
Lavori su NEXUS, repository https://github.com/starmarketkiller/MAX, sul desktop autorizzato.
Leggi AGENTS.md se presente nel checkout e docs/NEXUS_OPERATIONAL_CORE_DESKTOP_PLAN_V1.md.
Registra percorso, branch, HEAD, porcelain e divergenza da origin/main e dal remoto del branch.
Il checkout può essere sporco e diverso da main 111431ad e da HEAD cfa275366626b2e3c348226ad00a755528aafd36.
Conserva ogni modifica preesistente. I path già sporchi sono stranieri: leggili, calcola il diff, non reverterli e non includerli nel commit.
Commit locale solo dei path elencati nel report del task. Comando di stage esplicito per quei path. Nessun push, merge, deploy, Telegram, email, social, acquisto, API a pagamento, modifica account o trading reale.
Runtime di prova su dati isolati. Non interrompere processi o terminali già aperti. Non avviare Ollama, tunnel o MetaTrader se non è il compito del task e il servizio è già spento.
Prima di creare un modulo, cerca con rg implementazione, contratto, test e report. Riusa queue, ledger, orchestrator, gateway, context/result packet, research registry e verifier canonici.
Una fonte inaccessibile resta UNKNOWN. Un mock resta MOCK.
Ogni claim ha fonte, SHA o configurazione, timestamp Europe/Roma e classe STATIC | AUTOMATED_TEST | LOCAL_RUNTIME | REMOTE_RUNTIME.
Consegna in staging/nexus_operational_core_v1/<TASK_ID>/. Aggiorna PROGRESS_V1.json secondo il contratto V1.1. Se frozen è false, baseline_status resta BASELINE_PENDING e percent resta null.
Rispetta il tetto del task. Non assegnare punti a un criterio di un task successivo.
Prendi il lock di writer prima di modificare codice. Fermati al perimetro. Una necessità nuova è un task separato, non lavoro extra in questo prompt.
```

## Riuso già localizzato

Questi simboli esistono. Il task li legge e li cita. Ne crea uno nuovo solo se il collegamento manca ed è dimostrato.

| Bisogno | Dove |
|---|---|
| Stati e transizioni | `TaskQueue.STATES`, `ALLOWED_TRANSITIONS` in `server/orchestrator_v1/core/task_queue.py`. Quattordici stati, inclusi `WAITING_REVIEW_PROVIDER`, `PROPOSAL_ACCEPTED`, `PROPOSAL_REJECTED` |
| Idempotenza | `TaskQueue.submit_idempotent` |
| Coda single-process | docstring del modulo: `RLock`, replace atomico, multi-process fuori scope |
| Dispatcher | `DurableQueueDispatcher`: claim dei soli `QUEUED`, concorrenza un consumer, `yield_predicate`, RUNNING orfano bloccato |
| Routing senza chiamata premium nel router | `server/orchestrator_v1/core/router.py` |
| Fallback di review, oggi coperto da mock | `ProviderConnectorV1` e `test_local_verifier_rejected_review_v1.py` |
| Policy | `server/orchestrator_v1/provider_policy_registry_v1.json`: ordine `DETERMINISTIC`, `LOCAL`, `FREE_ONLINE`, `PREMIUM`; `fail_closed: true`; `unverified_production_eligible: false`; `quality_and_risk_override_cost: true` |
| Handoff | `server/jarvis_v1/task_handoff.py`: `write_task_artifacts`, `render_handoff_md` |
| Coordinamento a stadi | `server/jarvis_v1/multi_stage_executor.py` |
| Handler locale | `server/jarvis_v1/local_bounded_task_handler.py` |
| Ingresso Jarvis | `server/jarvis_v1/service.py` |
| Executive | `server/executive_v1/`, test `test_executive_state_and_conversation_v1.py` |
| Leakage storico | `server/research_scripts/phase5_5/leakage_guard.py` dichiara modalità AUDIT e un `ROOT` assoluto di questa macchina |
| Leakage successivo da leggere prima di dichiarare un buco | `server/research_scripts/phase7/phase7_2/apply_leakage_guard_and_ontology_update.py`, `sequence_semantic_leakage_guard_v1.json` |
| Grant non tracciati | `server/jarvis_v1/execution_grants.py`, `execution_grant_routes.py` |

## Confronto esterno

Le fonti del 4 novembre restano valide come metodi, non come prova di superiorità. Classificazione obbligatoria: `PRESENT_VERIFIED`, `PRESENT_UNVERIFIED`, `PARTIAL`, `ABSENT`, `NOT_NEEDED`.

| Riferimento | Decisione | Correzione V1.1 |
|---|---|---|
| QuantConnect, live e backtest sullo stesso periodo | Protocollo dati, barre, indicatori, segnali, ordini | T07 nomina lo script di parity esistente prima di scriverne uno |
| Nautilus, riconciliazione | Lifecycle e blocco di nuova esposizione se l'esito è ambiguo | Request, order, deal e position restano distinti. `PLACED` non è una posizione |
| Freqtrade, lookahead e warmup | Riusare i guard già presenti, aggiungere solo il prefisso mancante | Partire da phase 7.2, non solo da `leakage_guard.py` |
| Temporal | Proprietà verificabili sulla coda esistente | Una coda nuova richiede un task dedicato |
| Ollama e Claude Code | Compiti piccoli sul modello locale; handoff manuale ammesso | Compatibilità di API e qualità di coding si misurano separatamente. Nessuna invocazione cloud senza prova di costo zero |
| MQL5 `OnTradeTransaction` | La prova include duplicati ed eventi fuori ordine | Una richiesta può emettere più transazioni; l'ordine di arrivo non è garantito dalla documentazione citata |

## Task

### T00_BASELINE — baseline, riuso, congelamento

Obiettivo: dire cosa funziona su questo checkout, senza modificare codice operativo.

Può assegnare al massimo C01, C02, C04, C05, C06, C08, C17. C02 solo se un processo locale è già acceso. C01 solo se quel processo risponde. Gli altri criteri restano `UNKNOWN`.

Controlli:

1. Checkout, writer, directory persistenti, CI letta da Actions.
2. Percorso richiesta, Jarvis, queue, dispatcher, worker, verifier, result packet, handoff, executive. Wiring attivo distinto da modulo presente.
3. Health del PC senza cambiare configurazione e senza avviare servizi spenti. Se il runtime non risponde, sandbox dichiarata come sandbox.
4. Congela in `ACCEPTANCE_V1.md` scope, fixture, soglia, validità e classe di prova di tutti i 20 criteri, usando la tabella V1.1. Un criterio si allarga solo con una motivazione scritta; il denominatore resta 20.
5. Confronto esterno classificato sui file letti.

Consegna: `BASELINE_REPORT.md`, `REUSE_MATRIX.md`, `ACCEPTANCE_V1.md`, `PROGRESS_V1.json` con `frozen: true` solo dopo i cinque controlli. Poi la prima percentuale. Prima di quel momento `percent` è `null`.

Prossimo prompt, uno solo, in quest'ordine:

1. C17 rieseguito e `FAIL`: prompt T02 limitato al difetto riprodotto.
2. Una chiamata premium live osservata: prompt T03 limitato a impedire quella chiamata.
3. Un bypass di identità raggiungibile dal percorso Jarvis attuale: prompt T09 limitato a quel caso.
4. Altrimenti il prompt T01.

### T01_VERTICAL_SLICE — primo ciclo Jarvis

Dipende da T00 accettato. Può aggiungere C03, C07, C09, C12, C13.

Riusa `service.py`, `local_bounded_task_handler.py`, `multi_stage_executor.py`, `task_handoff.py` e l'orchestratore indicati dalla `REUSE_MATRIX`. Input congelato con un fallimento noto. Il modello classifica e sintetizza. Conteggi ed esiti escono da strumenti deterministici. Collegare solo il tratto mancante dimostrato: hash, task, context packet, percorso, verifier, result packet, artefatti, consultazione.

Prove: caso corretto, input incompleto, risultato inventato respinto. C09 richiede il modello locale reale. Se è spento, C09 resta `UNKNOWN` e il report lo dice.

Accettazione: quattro controlli, i tre casi più il percorso tracciato. Nessuna promozione di provider.

### T02_RECOVERY — durabilità e concorrenza

Dipende da T01. Può aggiungere C11, C16, C18.

Legge tutte le transizioni, inclusi i quattordici stati, prima di modificare. Conserva yield e fail-closed sul RUNNING ambiguo.

Scenari, con esito atteso scritto prima della prova:

1. Submit duplicato.
2. Restart prima del claim.
3. Crash dopo il claim.
4. Risultato persistito e audit finale fallito.
5. Risposta tardiva di un tentativo precedente.
6. Restart con terminale già registrato.
7. Due consumer nello stesso processo, e a parte due processi sullo store single-process. Per il secondo è accettabile un rifiuto esplicito dimostrato.
8. Domanda interattiva durante lavoro background. Rieseguire `test_interactive_gate_makes_dispatcher_yield_background_work` prima di scrivere un yield nuovo.

Corregge solo difetti riprodotti, con test di regressione. Nessuna coda nuova.

Accettazione: otto scenari classificati, effetti non duplicati, garanzie e limiti scritti.

### T03_ROUTING_AND_HANDOFF — modelli, quote, handoff

Dipende da T01 e dalle conclusioni di T02 sui tentativi. Può aggiungere C10, C14, C15.

Inventario di runtime, modello, quantizzazione, RAM, CPU, contesto e CLI, senza stampare token. Set congelato: estrazione strutturata, riassunto ancorato, classificazione errore, proposta di patch delimitata. Prima misura `ministral-3:3b` se il processo locale lo espone; il nome nel registry si riconferma sul runtime. Un altro modello locale solo se già presente o se T00 ha congelato un budget di download.

Registra se il run è stato ordinato per costo o spostato da `quality_and_risk_override_cost`. Il fallback mock verso Codex non autorizza una chiamata premium. Provider online gratuiti senza credenziali autorizzate e senza garanzia di non addebito restano `UNKNOWN`.

Handoff sanitizzato e import correlato a task, attempt e SHA. Il passaggio manuale è valido se dichiarato. Automatizza solo un percorso documentato e verificato.

Accettazione: cinque controlli, uno per ciascun punto del task. I rami non eseguiti restano `BLOCKED` e valgono zero.

### T04_LOCAL_OPERATIONS — health e timeout

Dipende da T00 e dal percorso T01. Si coordina col lock di T03. Non aggiunge criteri del nucleo. Può far diventare `STALE` o `FAIL` C01 e C02.

Riusa LocalBridge e `nexus_local_inference_gateway.py`. Sei condizioni: catena di timeout, cold start, warmup, modello assente, errore di autenticazione, perdita di tunnel e ripristino. Health superficiale e capacità di inferenza sono esiti distinti. Script idempotenti in configurazione isolata. URL stabile e startup persistente si preparano con rollback e si applicano solo con autorizzazione successiva. Reboot non eseguito resta non certificato. Readiness remota e delivery stanno in un report separato, fuori dai 20 criteri.

### T05_STATE_AND_PROGRESS — executive e percentuale

Dipende da T00 e T01, integrazione dopo T02. Può aggiungere C19.

Riusa `server/executive_v1/`. La percentuale del nucleo è il registro `PROGRESS_V1.json`. Executive la può proiettare. Non sostituisce `overall_progress` e non crea un secondo KPI store. Dato mancante o scaduto: `UNKNOWN` o `STALE`.

Scenari: nessun dato, dato recente, dato scaduto, regressione, task conclusa con consegna fallita, proposta accettata senza esecuzione. Telegram solo verso sink isolato.

Accettazione: sei scenari, schema valido, fonti visibili, nessun completamento falso.

### T06_INDEPENDENT_REVIEW

Dipende dalle consegne T01–T05. Checkout separato allo SHA esatto. Nessuna correzione durante la review. Può aggiungere C20.

Ripete i comandi forniti. Cerca doppio stato, bypass del verifier, risposte tardive, effetti ripetuti, punti senza prova, regressione del yield, chiamata premium. Serie C20 sul modello locale, con un handoff il cui successore è una sessione reale. Coerenza di output, ledger e stato dopo restart.

Esito: `PASS`, `CHANGES_REQUIRED` o `BLOCKED`, con ricalcolo indipendente. `CHANGES_REQUIRED` produce un task di fix circoscritto. Nessun merge.

Accettazione: riproduzione, prove avverse, serie completa, verifica del registro.

### T07_TRADING_PARITY

Dipende da T00. Esecuzione pesante fuori dai benchmark locali del nucleo. Denominatore proprio.

Una strategia già esistente, un campione discovery non sigillato. Riusa registry, hash, leakage e script di parity. Legge i successori phase 7.2 prima di trattare `leakage_guard.py` come il guard corrente. Holdout chiuso. Nessuna ipotesi nuova oltre il budget già autorizzato.

Livelli e tolleranze scritti prima del confronto. Prova di prefisso temporale solo se manca. Primo livello divergente. Matrice `EXACT` / `APPROXIMATE` / `DIFFERENT` / `UNKNOWN`.

Accettazione: provenienza, causalità, warmup, barre e indicatori, parità segnali. Nessuna dichiarazione di strategia validata.

### T08_EXECUTION_EVIDENCE

Dipende da T00 e dal perimetro T07. Build in MetaEditor isolato, digest EX5, nessuna sostituzione dell'EA operativo.

Scenari: richiesta accettata senza fill, fill parziale, duplicato, fuori ordine, riavvio con esito incerto. Request, order, deal e position separati. `PLACED` non conta come posizione. Harness e tester restano etichettati e distinti dall'evidenza broker. Nuova esposizione bloccata se la riconciliazione è incerta. Posizioni esistenti non toccate. Nessun conto reale.

Accettazione: build riproducibile e cinque scenari.

### T09_SECURITY_AND_STORAGE

Dipende da T00. Può anticipare T01 se T00 ha scelto questo prompt. Audit, più la correzione minima del solo difetto riprodotto prioritario.

Legge prima i grant non tracciati. Fixture: principal A verso B, token revocato, risultato di un tentativo su un altro task, collisione di ticket fra account, restore di identità e provenienza. Capacità non supportata: rifiuto esplicito. Nessuna rotazione di segreti operativi e nessuna migrazione di produzione. Percentuale propria, non sommata al nucleo.

Accettazione: cinque scenari e l'elenco di ciò che resta aperto.

### T10_REVENUE_PILOT

Dipende dal nucleo verificato in T06. Un solo servizio già realizzabile. Lead di prova, qualifica, bozza di offerta, approvazione, esempio, verifica, consegna simulata, costo e ricavo simulato. Revenue, Agency, Social e Finance restano i proprietari descritti nel piano del 4 novembre. Nessun outreach, post, fattura o pagamento. Simulato e reale stanno in campi diversi.

Accettazione: offerta producibile, output verificato, workflow tracciato, costi espliciti, simulazione marcata.

### T11_COST_ACCOUNTING

Dipende da T03 e, se esiste, da T10. Costo marginale API, quota abbonamento, risorse locali, infrastruttura, tempo umano. Misurato, stimato e non osservabile sono colonne diverse. Retry e review non si contano due volte. Cassa aziendale, spese personali e capitale trading restano separati. Nessuna promessa di risparmio senza baseline comparabile.

Accettazione: attribuzione, assenza di doppi conteggi, ignoti espliciti, budget separati, prospetto riproducibile.

### T12_CONTROLLED_IMPROVEMENT

Dipende da un ciclo completo e da una baseline misurata. Un collo di bottiglia, una modifica preregistrata, casi di progetto separati dai casi di verifica. Promozione solo dentro l'autorizzazione locale del task. Esperimenti respinti registrati. Nessun deploy in questo task.

Accettazione: ipotesi congelata, confronto valido, regressioni, decisione con prove, riuso o motivo dello scarto.

## Sequenza

1. Ora: solo T00.
2. Poi l'unico prompt che T00 pubblica.
3. Sul core, un writer alla volta, nell'ordine T01, T02, T03, T04, T05, adattato ai blocchi reali.
4. T06 sullo SHA integrato. Se chiede fix, review nuova sullo SHA del fix.
5. T07, T08 e T09 con prove proprie. T09 anticipa solo se T00 lo ha scelto come prompt unico.
6. T10, T11, T12 dopo il nucleo verificato.

Il 100% dei 20 criteri certifica il nucleo locale nello scope congelato. Telegram, Render, sicurezza completa, capacità commerciale, strategie validate e trading live restano fuori da quel denominatore.
