# NEXUS MASTERPLAN V4.1 — Department Teams (Ruoli Logici)

Vedi [NEXUS_MASTERPLAN_V4_1.md](NEXUS_MASTERPLAN_V4_1.md) per indice e provenienza. Questo documento definisce i **ruoli logici** richiesti dalla task per ciascun reparto — non sette nuovi modelli AI residenti (vietato esplicitamente), ma funzioni/fasi di un workflow che compilano verso [NEXUS_WORKFLOW_DEFINITION_V1](../contracts/nexus-workflow-definition-v1.schema.json) ed eseguono tramite l'infrastruttura già reale (`MultiStageExecutor`, `CapabilityResolver`, worker esistenti). Ogni ruolo = un nodo del workflow, non un processo persistente.

Stato reale di ogni reparto: vedi i 7 documenti V4 ([NEXUS_MASTERPLAN_V4_TRADING.md](NEXUS_MASTERPLAN_V4_TRADING.md) ecc.) — qui non ripeto quel census, definisco solo come i ruoli richiesti da V4.1 si allineano a quanto già trovato.

---

## 1. Trading Intelligence Room

**Riferimento concettuale dichiarato dall'utente**: un sistema pubblico a 6 bot (Scout/News/Sentiment/Charts/Risk/Decision) — usato come ispirazione di STRUTTURA, non copiato: NEXUS ha già un proprio motore di validazione (Evidence Ladder) più rigoroso che questi ruoli devono rispettare, non bypassare.

| Ruolo | Responsabilità | Mappa su infrastruttura esistente |
|---|---|---|
| Scout | Scansiona mercato per movimenti anomali | `research_scripts/` esistenti (scouting già IMPLEMENTED per V4) |
| News | Verifica cosa è successo (catalizzatori, notizie) | Nuovo nodo — nessun componente dedicato trovato nel census V4 |
| Sentiment | Legge cosa dice il mercato (bullish/bearish/hype) | Nuovo nodo — nessun componente dedicato trovato |
| Charts | Segna livelli chiave (trend/entry/stop/target) | Analisi tecnica già presente in `research_scripts/` (ad hoc, da formalizzare come nodo) |
| Deterministic Risk Gate | Riduce o rifiuta qualunque trade — **mai controllato dall'LLM** | `NXS_RiskShield.mqh` (già IMPLEMENTED e verificato forensicamente) + imbuto di validazione (`edge-validation-registry.json`) |
| Decision/Synthesis | Sintetizza i segnali in BUY/WAIT/SKIP | **Manca**: questo è esattamente il "gate go-live" identificato come gap #1 nell'[Architecture Review V4](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#1-high_impact-codificare-il-gate-go-live-per-le-strategie-di-trading) |
| Evidence & Causality Verifier | Verifica che l'evidenza sia causale, non correlazionale | Coerente con la disciplina di preregistrazione già applicata a VOLBRK Serious 3Y — da generalizzare, non reinventare |

**Workflow**: `market_data → data_validation → {Scout, News, Sentiment, Charts} (parallelo) → evidence_aggregation → Risk_Gate (deterministico) → Decision/Synthesis → Evidence_Verifier → research_result`

**Vincolo esplicito, già rispettato dall'architettura esistente**: un risultato `CANDIDATE` non è mai un ordine BUY. Il Risk Gate resta deterministico (`NXS_RiskShield.mqh`), mai un giudizio LLM. Nessuna modifica alla logica di trading live — questo workflow produce *ricerca*, non esecuzione diretta.

**Collegamento obbligatorio**: ogni esecuzione di questo workflow deve attraversare l'Evidence Ladder esistente (Idea → Backtest → OOS → Cost Stress → Robustness → Shadow → eventuale Live Eligibility) — il workflow qui sopra descrive COME si produce un candidato, l'Evidence Ladder resta la sola via per farlo diventare eleggibile al live.

---

## 2. Revenue Office

| Ruolo | Mappa su infrastruttura esistente |
|---|---|
| Opportunity Scout | `funding_v1/market_scout.py` (IMPLEMENTED) |
| Prospect Researcher | Parte di `revenue_agent.py` (IMPLEMENTED, bounded) |
| Qualification | `revenue_agent.py::RevenueLocalTaskHandler` + `verify_revenue_output()` (IMPLEMENTED, verificatore anti-allucinazione reale) |
| Offer Builder | **PARTIAL** — nessun tipo di task "preventivo strutturato" dedicato (vedi census V4 Revenue) |
| CRM Coordinator | **PARTIAL** — `FirstRevenueStore`/`RevenueVentureRegistry`, non un vero CRM relazionale |
| Follow-up | `RevenueScheduler` (IMPLEMENTED, solo bozza — nessun invio automatico per design) |
| Conversion Analyst | `compute_revenue_metrics()`/`venture_metrics()` (IMPLEMENTED) |

**Workflow**: `opportunity → scouting → provenance → qualification → CRM → proposal → approval → outreach → response → conversion → delivery → revenue_attribution`

**Vincolo già rispettato**: conversione/pagamento restano BLOCKED by design (nessuna integrazione di pagamento, nessun invio automatico) — non toccare questa scelta di pivot senza una decisione esplicita dell'utente.

---

## 3. AI Fashion Agency Studio

| Ruolo | Mappa su infrastruttura esistente |
|---|---|
| Trend Scout | `scouting.py` V2 (IMPLEMENTED) |
| Casting Director | `roster.py::score_models` (IMPLEMENTED per assegnazione; generazione roster `CASTING_DRAFT`, PARTIAL) |
| Stylist / Creative Director | `content_engine.py::brief_card()` (IMPLEMENTED) |
| Model Coordinator | `roster.py` (IMPLEMENTED) |
| Store Gatekeeper | `pipeline.py::transition_product()`/`compliance_check()` (IMPLEMENTED, gate a `ValueError`) |
| Production Coordinator | `build_generation_pack()`/`approve_generation_pack()` (IMPLEMENTED, gate a match esatto sui crediti) |
| Compliance Reviewer | `compliance_check()` (IMPLEMENTED) |
| Campaign Analyst | `kpis.py` (IMPLEMENTED) |

**Workflow**: `trend/product → classification → Store_Gate → creative_brief → model_assignment → Higgsfield_estimate → approval → generation → review → Social → analytics → Revenue`

**Vincolo già rispettato, verificato a livello di codice**: nessuna spesa di crediti reale, nessuna pubblicazione (`PUBLISH` hard-disabled by policy). Questo reparto è già il più maturo dei 7 (vedi [census V4](NEXUS_MASTERPLAN_V4_AI_FASHION_AGENCY.md)) — i ruoli sopra sono quasi tutti già reali, non da costruire da zero.

---

## 4. Social Content Studio

**Nota architetturale importante**: questo "reparto" **non esiste come modulo a sé** — è assorbito in `business_units/ai_fashion_agency/social.py` (vedi [census V4](NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md)). I ruoli sotto sono quindi concettuali/futuri, non un'estrazione da fare ora (l'Architecture Review V4 l'ha già classificata come non urgente con un solo consumatore).

| Ruolo | Mappa su infrastruttura esistente |
|---|---|
| Trend Analyst | Assente, concettualmente sovrapposto a Trend Scout dell'Agency |
| Editorial Planner | **PARTIAL** — `content_engine.py::brief_card()`, nessun calendario editoriale |
| Script Writer | `skills.py::CONTENT_BRIEF_DRAFT` (IMPLEMENTED a livello skill) |
| Content Producer | `create_content_package()` (PARTIAL) |
| Channel Adapter | `social.py::SocialAdapter`/`PostizAdapter`/`ManualExportAdapter` (IMPLEMENTED, dry-run by design) |
| Scheduler | `social.py::transition_post()` (IMPLEMENTED) |
| Community Analyst | PLANNED — nessun codice trovato |
| Performance Evaluator | `kpis.py` (IMPLEMENTED) |

**Raccomandazione**: non istanziare questo reparto come team separato finché non esiste un secondo consumatore di contenuti oltre l'Agency (coerente con [Architecture Review V4](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md)).

---

## 5. Engineering Lab (System & Development)

| Ruolo | Mappa su infrastruttura esistente |
|---|---|
| Diagnostic Analyst | **PARTIAL** — `review_matrix.py`, nessuna fase di triage dedicata |
| Capability Scout | `core/capability.py::find_capable_agents` (IMPLEMENTED, ma registry schema-only — vedi census V4 infra) |
| Architect | PLANNED — nessuno step di design codificato |
| Developer | `FreeCodingWorkerHandler` (IMPLEMENTED, fail-closed) + `local_bounded_task_handler.py` (IMPLEMENTED, solo `REPO_INSPECTION_V1` read-only) |
| Test Runner | CI reale (`backend-tests`, `docker-smoke` — vedi [census infra](NEXUS_GITHUB_CICD_GOVERNANCE.md)) |
| Security Reviewer | `security-preflight` CI job + `finalization_gate.py` (IMPLEMENTED) |
| Deployment Controller | Safe Deploy V1 (IMPLEMENTED, rigoroso — gate CI→classificazione rischio→deploy) |
| Observability Analyst | **PARTIAL** — nessun tool di monitoring dedicato oltre `/api/health`/`/api/ready` (vedi census infra) |

**Workflow**: `issue → diagnosis → reuse_first_check → design → isolated_branch → implementation → test → independent_review → CI → authorized_deploy → monitoring → rollback_or_feedback`

**Nota**: questo è il reparto che la sessione corrente (Claude) e Codex incarnano già nella pratica — il workflow sopra descrive formalmente quello che sta già succedendo, non introduce un nuovo processo.

---

## 6. Finance Control Room

| Ruolo | Mappa su infrastruttura esistente |
|---|---|
| Cost Collector | **PARTIAL** — `EventLedger.payload.cost_usd`, `first_revenue.py` margine, nessuna raccolta unificata |
| Reconciliation | PLANNED |
| Attribution Analyst | PLANNED — `financial_risk` hardcoded a `"NONE"` su ogni task |
| Budget Controller | `premium_budget_policy.py::allow_premium()` (IMPLEMENTED, ma è prevenzione spesa, non controllo budget generale) |
| Forecast Analyst | PLANNED (eccetto `projection.py` locale all'Agency) |
| ROI Evaluator | PARTIAL, scoped solo all'Agency (`kpis.py`/`projection.py`) |

**Workflow**: `economic_events → collection → normalization → reconciliation → attribution → budget_check → analysis → forecast → report`

**Dati mancanti = `UNAVAILABLE`, mai zero fabbricato** — stesso principio già applicato in `executive_v1/sections.py`.

**Priorità già identificata**: vedi [Architecture Review V4 #4](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#4-high_impact-aggregatore-finance--cost-cross-reparto) — un aggregatore sottile sopra i 3 frammenti già esistenti, non un sistema nuovo.

---

## 7. Jarvis Operations

| Ruolo | Mappa su infrastruttura esistente |
|---|---|
| Intent Router | `classify()` (IMPLEMENTED, sempre attivo) + `ministral_router.py` (IMPLEMENTED, dormiente) |
| Context Retriever | `vault_context.py` (IMPLEMENTED, questa sessione — retrieval bounded su vault/skills) |
| Executive State Reader | `executive_v1/state.py::ExecutiveStateBuilder` (IMPLEMENTED, 9 domini) |
| Task Coordinator | `multi_stage_executor.py` (IMPLEMENTED, sostanziale) |
| Approval Coordinator | `unified_approvals()` (IMPLEMENTED) |
| Personal Assistant Coordinator | `/mistral` diretto (IMPLEMENTED, questa sessione) |
| Delivery Coordinator | `telegram_adapter.py` (IMPLEMENTED) + `notification_sink` (IMPLEMENTED, cablato) |

**Workflow**: `user_or_event → intent → context → fast_or_deep_path → authorized_tool_or_task → verification → executive_state_update → jarvis_response`

**Jarvis resta l'unica interfaccia executive dell'utente** — già vero oggi (confermato dal census V4: ogni reparto comunica verso l'utente solo tramite Jarvis/Telegram, mai direttamente).

---

## Principio comune a tutti i 7 reparti

Nessun ruolo sopra richiede un nuovo agente LLM persistente. Ogni ruolo è un **nodo** di un `NEXUS_WORKFLOW_DEFINITION_V1`, eseguito da worker/capability già esistenti (`FreeCodingWorkerHandler`, `BoundedLocalTaskHandler`, `RevenueLocalTaskHandler`, skill pack dell'Agency) o da funzioni deterministiche nuove ma leggere (Risk Gate, Verifier). Questo rispetta esplicitamente il vincolo "non creare sette nuovi modelli o sette orchestratori" — confermato già rispettato nella pratica da ogni census di reparto in V4.
