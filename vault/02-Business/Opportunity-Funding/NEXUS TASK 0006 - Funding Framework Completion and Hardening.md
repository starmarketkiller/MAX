# NEXUS TASK #0006 — Funding Framework Completion & Hardening

**Baseline:** `5e8bb48`. Dipendenza: #0005. Non una riprogettazione: hardening additivo del framework già consegnato in #0005, che resta `FRAMEWORK_READY_AWAITING_ADOPTION` fino a questo completamento.

## Perché questa task esiste

L'utente ha esplicitamente rifiutato di adottare #0005 come canone: "Claude ha realizzato il nucleo V1, non tutto il sistema che vogliamo." Il punto critico: punteggi come 81.25 o 47.75 sono output matematico corretto dello scoring, ma senza una distinzione esplicita fra assunzione e dato reale rischiano di leggersi come evidenza di mercato che non esiste. #0006 aggiunge gli 11 componenti mancanti (hard gates, capital scenarios, capability coverage, lifecycle, next-cheapest-validation-step, self-funding loop, learning-readiness, opportunity brief, dataset a 13 nuove hypothesis, no-fake-precision) **senza toccare** lo scoring/i pesi già verificati in #0005.

## Test centrale della sessione: routing (#0006 punto 14)

L'utente ha posto esplicitamente la domanda: *NEXUS riesce a estendere un framework progettato da Claude usando principalmente TIER0 + Ministral, senza richiamare Claude?*

Risultato:
- **13/13 narrative** (description/technical_rationale/funding_rationale per le 13 INITIAL_HYPOTHESIS) generate via Task Queue → Router → Ministral (`ministral-3:3b`) → verify fail-closed. `tier_counts: {"TIER1_LOCAL_CHEAP": 13}` — **zero escalation premium**.
- **18/18 brief** (`short_voice_summary` per tutte le opportunity, comprese le 5 originali di #0005) generati allo stesso modo, **al primo tentativo**, zero escalation.
- 2 sotto-task (`OPP_LEAD_CAPTURE_FOLLOWUP_PACK`, `OPP_AI_CUSTOMER_SUPPORT`) sono arrivati a `ESCALATION_REQUIRED` durante un retry intermedio (vedi sotto) — mai una vera chiamata premium (`premium_allowed=False` nel manifest), risolti correggendo il **prompt**, non il modello.

Risposta alla domanda dell'utente: **sì**, con un'unica correzione di harness in corsa (vedi sotto), non un intervento di contenuto.

## Bug reali trovati e corretti durante l'esecuzione

1. **`capability_coverage.py`**: `blockers` includeva anche lo stato `PARTIAL`, contraddicendo la descrizione dello schema stesso ("solo MISSING/EXTERNAL_SERVICE_REQUIRED"). Trovato per auto-review dopo il primo run end-to-end, corretto prima di generare il dataset finale.
2. **Verificatore delle narrative troppo permissivo (2 iterazioni)**: la prima versione di `HypothesisNarrativeHandler.verify()` non controllava affatto il markdown (a differenza del verificatore per `short_voice_summary`, che lo controllava fin dall'inizio) — 6/13 narrative contenevano `**grassetto**`. Corretto il verificatore, rieseguito: **1 caso residuo** (`*enfasi singola*`) è sfuggito perché il primo fix controllava solo `"**"` letterale, non il singolo `*`. Corretto di nuovo (stesso set di caratteri della `VoiceSummaryHandler` già corretta). Infine, per i 5 casi che continuavano a fallire anche con verificatore corretto, la causa reale era il **prompt**, che non istruiva esplicitamente Ministral a non usare markdown — aggiunta l'istruzione esplicita, rieseguiti solo i 5 casi: 13/13 completati puliti.

Disciplina seguita in ogni caso: mai patchare a mano il testo generato — sempre corretto l'harness (verificatore o prompt) e rieseguita la generazione, con provenance tracciata tramite ID di task incrementali (`_V2`, `_V3`, `_V4` nel runtime state locale, non committato).

## Hard gate: la prova che uno score alto non bypassa mai un blocco

`OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION` ha `funding_priority.score=75.25` (alto, per automazione/ricorrenza) ma `legal_or_policy_risk_flag=True` (vendita di segnali di trading è attività regolamentata in molte giurisdizioni) → `hard_gate=BLOCKED_BY_LEGAL_OR_POLICY_RISK`, con precedenza assoluta su qualunque punteggio. Verificato sia nel dataset reale sia in un test unitario dedicato che forza la precedenza (legal > capital > capability > evidence).

Sui 18 casi reali: 12× `BLOCKED_BY_CAPITAL` (a `BOOTSTRAP_0_100`), 3× `RESEARCH_REQUIRED`, 2× `BLOCKED_BY_CAPABILITY` (mancano `crm`/`image_video` nelle capacità NEXUS attuali), 1× `BLOCKED_BY_LEGAL_OR_POLICY_RISK`. Nessuna opportunity oggi `READY_FOR_MVP` o oltre — coerente con un dataset interamente `INITIAL_HYPOTHESIS`/`ASSUMPTION`.

## Separazione funding/technical confermata sul dataset esteso

Top per `funding_priority`: tool compliance (81.2), Digital Menu (80.8), abbonamento segnali (75.2, ma bloccato). Top per `technical_priority`: Orchestrator locale-first, AI Receptionist, NEXUS/Jarvis external product (tutti 100.0) — nessuno dei tre compare fra i primi per funding. Esattamente il comportamento richiesto dall'utente fin da #0005: "X è interessante, però Y può generare cassa prima."

## No fake precision

Tutte le 18 opportunity: `input_type=ASSUMPTION`, `priority_status` in `{PROVISIONAL, HYPOTHESIS_BASED}`, mai `VALIDATED`, `evidence_confidence` mai `VALIDATED` — verificato sia da test dedicato sia dal verificatore indipendente.

## Deliverables

`contracts/`: `capability-coverage.schema.json`, `opportunity-lifecycle.schema.json`, `opportunity-brief.schema.json`, `self-funding-loop.schema.json` (nuovi), `opportunity.schema.json` (esteso additivamente, 10 nuovi campi required).
`server/funding_v1/`: `capability_coverage.py`, `capital_scenarios.py`, `hard_gates.py`, `opportunity_lifecycle.py`, `self_funding_loop.py`, `opportunity_assembly.py`, `opportunity_brief_builder.py`, `initial_hypothesis_inputs.py` (13 hypothesis), `build_opportunity_lifecycle_instance.py`, `build_self_funding_loop_instance.py`, `build_example_opportunities.py` (esteso a 18 opportunity), `opportunity_briefs_v1.json` (18 brief), `example_instances/opportunity_lifecycle_v1.json`, `example_instances/self_funding_loop_v1.json`.
`server/orchestrator_v1/`: `run_nexus_task_0006_generate_dataset.py`, `run_nexus_task_0006_generate_briefs.py`, `verify_nexus_task_0006.py`, `nexus_task_0006_narratives_v1.json` (13 narrative verificate).
`server/tests/test_funding_v1.py`: esteso da 8 a 21 test.

## Regressione

`verify_nexus_task_0006.py`: **PASSED** (ricalcolo indipendente di score/hard gate/capital scenarios/capability coverage su tutte le 18 opportunity, schema di tutti gli artifact canonici validati, 0 escalation premium confermata, no-fake-precision confermata). `test_funding_v1.py`: 21/21. Suite completa `server/orchestrator_v1/` + `server/tests/`: 327 passed — 2 fallimenti transitori attesi (`test_no_pre_existing_contracts_modified`/`test_verifier_reports_zero_errors` dell'Orchestrator V1 Core, guardie che confrontano `git diff` con HEAD: falliscono per costruzione mentre le modifiche a `contracts/` restano non committate, si risolvono dopo il commit) — 1 fallimento **pre-esistente e non correlato** (`test_research_control_plane_v2.py::test_safety_net_registries_are_projected_without_reinterpretation`, `assert 9 == 8`, confermato fallire anche su HEAD pulito via `git stash`, fuori scope di questa task, segnalato ma non toccato).

## Decisione finale

**`FUNDING_FRAMEWORK_V1_READY_FOR_ADOPTION`** — stato `WAITING_APPROVAL`, confidence HIGH. Nessuna azione commerciale, nessuna spesa, nessun deploy, nessuna chiamata premium automatica in tutta l'esecuzione. Resta in attesa di conferma esplicita dell'utente prima di diventare canone per Jarvis/futuri task NEXUS.
