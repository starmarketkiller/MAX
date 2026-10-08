# NEXUS MASTERPLAN V4 — Documento Canonico

**Stato:** canonicalizzazione documentation-first di un masterplan comunicato dall'utente tramite due infografiche di visione (missione, 7 reparti, leve di velocità, layer infrastruttura, roadmap di maturità) e di un testo di task molto dettagliato. **Nessuna specifica scritta "Masterplan V4" preesisteva nel repository o nel Vault** (verificato con ricerca esplicita prima di iniziare — vedi §0). Questo documento e i suoi satelliti traducono quella visione in realtà verificata: ogni affermazione di stato è ancorata a codice/test letti davvero in questa sessione, non alla prosa delle infografiche.

**Non è un documento di sola aspirazione**: distingue sempre **IMPLEMENTED** (codice e test reali, citati file:riga) da **PARTIAL** (esiste ma incompleto o non cablato end-to-end) da **PLANNED** (solo intento, nessun codice) da **BLOCKED** (gate esplicito a decisione umana). Nessuno stato "implementato" è dichiarato senza una citazione verificabile.

---

## §0. Provenienza

- **Visione**: le due infografiche fornite dall'utente in chat (missione, 7 reparti con relativi 8-11 step di processo ciascuno, 10 "leve di velocità", 11 layer di infrastruttura, roadmap di maturità in 5 fasi).
- **Requisiti strutturali**: il testo della task stessa (quali campi deve avere ogni workflow di reparto, distinzione IMPLEMENTED/PARTIAL/PLANNED/BLOCKED, deliverable richiesti).
- **Realtà**: census read-only di questa sessione, 9 agenti paralleli (uno per reparto + 2 sull'infrastruttura condivisa), ciascuno con istruzione esplicita di citare file:riga e non indovinare mai.
- **Dove la visione e la realtà divergono**, questo documento lo dice esplicitamente — non arrotonda per eccesso.

---

## §1. Missione e obiettivi finali

**Missione** (dall'infografica, invariata): creare un ecosistema automatizzato di trading, contenuti, agency e servizi digitali che generi entrate, apprendimento continuo e crescita scalabile nel tempo.

**Obiettivi finali** (dall'infografica): entrate costanti e scalabili, crescita capitale, automazione end-to-end, libertà di tempo, espansione multi-progetto, sicurezza e controllo, vita equilibrata, impatto globale, team di agenti AI, sistema auto-migliorante.

Questi restano obiettivi dichiarati dall'utente, non verificabili come "raggiunti" — il resto del documento misura quanta infrastruttura reale esiste oggi per perseguirli.

---

## §2. Legenda di stato (usata in ogni documento di questo set)

| Stato | Significato | Criterio |
|---|---|---|
| **IMPLEMENTED** | Codice reale, funzionante, con test | Citazione file:riga + (dove rilevante) nome del test |
| **PARTIAL** | Esiste ma incompleto, non cablato end-to-end, o scoped più stretto del previsto | Citazione + cosa manca esplicitamente |
| **PLANNED** | Solo intento — nessun codice trovato | Nessuna citazione possibile; mai confuso con PARTIAL |
| **BLOCKED** | Gate esplicito e deliberato a decisione umana (non un gap, una scelta) | Citazione della policy/soglia che blocca |

---

## §3. I sette reparti — stato in sintesi

| # | Reparto | Documento | Stato complessivo | Nota principale |
|---|---|---|---|---|
| 1 | Trading | [NEXUS_MASTERPLAN_V4_TRADING.md](NEXUS_MASTERPLAN_V4_TRADING.md) | PARTIAL, meccanica forte / imbuto di validazione quasi vuoto | 83 strategie in registro, **0 VALIDATED**; esecuzione e RiskShield solidi e già verificati |
| 2 | Revenue | [NEXUS_MASTERPLAN_V4_REVENUE.md](NEXUS_MASTERPLAN_V4_REVENUE.md) | PARTIAL, delivery/pagamento deliberatamente manuali | Scouting/qualifica/follow-up reali e bounded; conversione e pagamento BLOCKED by design |
| 3 | AI Fashion Agency | [NEXUS_MASTERPLAN_V4_AI_FASHION_AGENCY.md](NEXUS_MASTERPLAN_V4_AI_FASHION_AGENCY.md) | Il più maturo dei 7 | 32 test reali, pipeline store/compliance/preventivo/approvazione crediti IMPLEMENTED; pubblicazione **hard-disabled by policy** |
| 4 | Social / Content | [NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md](NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md) | Non esiste come reparto a sé | Assorbito interamente in AI Fashion Agency (`social.py`) — documentato come scelta architetturale, non come gap da colmare ora |
| 5 | System & Development | [NEXUS_MASTERPLAN_V4_SYSTEM_DEVELOPMENT.md](NEXUS_MASTERPLAN_V4_SYSTEM_DEVELOPMENT.md) | Forte su CI/deploy, debole su auto-sviluppo | Safe Deploy V1 (gate CI→rischio→deploy) reale e rigoroso; un solo template Ministral bounded esiste (read-only) |
| 6 | Finance & Cost | [NEXUS_MASTERPLAN_V4_FINANCE_COST.md](NEXUS_MASTERPLAN_V4_FINANCE_COST.md) | In gran parte PLANNED | Nessun reparto Finance coeso — solo frammenti dentro altri reparti (budget premium, margine first-revenue, ROI agency) |
| 7 | Jarvis & Automation | [NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md](NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md) | Il cervello centrale, sorprendentemente maturo | Executive State a 9 domini, esecuzione multi-stage, planning/capability resolver tutti IMPLEMENTED e cablati |

**Osservazione cross-dipartimentale più significativa, confermata indipendentemente da OGNI singolo census**: **nessun Global Improvement Council esiste in nessuna forma, in nessun reparto.** Il ciclo di self-improvement locale è quasi ovunque PLANNED. Vedi [§6](#6-self-improvement-distribuito-e-coordinamento-proposta) e il documento dedicato.

---

## §4. Infrastruttura condivisa — stato in sintesi

| Layer | Stato | Evidenza chiave |
|---|---|---|
| **Queue Manager** | IMPLEMENTED | `task_queue.py` — stati reali, lease-based claim, `WAITING_DEPENDENCY`. Priorità reale è `URGENT/HIGH/NORMAL/LOW`, **non** lo schema P0-P4 dell'infografica (mismatch terminologico, non un gap — vedi architecture review) |
| **Executive State** | IMPLEMENTED | `server/executive_v1/` — 9 domini, isolamento per-provider (`_safe()`), cablato in `service.py:483` |
| **Capability Registry** | PARTIAL/schema-only | `contracts/agent-capability-registry.schema.json` esiste, **nessuna istanza popolata trovata nel repo** — niente si registra oggi |
| **Responsabili di reparto** | PARTIAL | Nessuna interfaccia formale `DepartmentResponsabile` — ogni reparto è cablato ad hoc in `service.py`; "mai aggirare l'Orchestrator" è rispettato per convenzione, non imposto da un contratto (vedi proposta in [§7](#7-modello-di-coordinamento-dei-responsabili-proposta)) |
| **Security & Control** | IMPLEMENTED, single-role | Auth reale (sessione/JWT/bearer/webhook secret), un solo ruolo `admin` — nessuna RBAC granulare. **Due meccanismi di audit log separati**: `EventLedger` generico (nessuna hash chain) vs `trade_events` (hash chain reale + trigger di immutabilità) — postura di sicurezza non uniforme tra tipi di dato |
| **Monitoring & Dashboard** | PARTIAL | `/api/health` vs `/api/ready` reali e distinti; nessun endpoint di metriche/KPI unificato cross-reparto |
| **Tools & Integrazioni** | PARTIAL, disciplina dry-run coerente | Telegram/Ollama reali; adapter di pubblicazione social e generazione Higgsfield sempre `dry_run`/gated — nessuna spesa o pubblicazione reale possibile oggi |
| **Agents & Skills** | PLANNED/schema-only + 2 skill reali | Solo `mql5-engineering` e `ui-ux-pro-max` esistono in `.claude/skills/` |
| **Deploy pipeline (Safe Deploy V1)** | IMPLEMENTED, rigoroso | `autoDeployTrigger: off`, gate CI→`classify_deploy_risk.py`→deploy hook, nessun deploy automatico diretto da commit |

---

## §5. Principi chiave (dall'infografica, verificati contro il codice)

| Principio | Stato reale |
|---|---|
| Event-driven, non polling | PARTIAL — il dispatcher dell'Orchestrator fa polling configurabile (`dispatcher.py`), non è puramente event-driven; Telegram è webhook-based (event-driven) |
| Fast path / Deep path | IMPLEMENTED — `local_operations.py::is_complex_mistral_request()`, euristica singola (non ancora auto-tunata) |
| Deterministico prima del LLM | IMPLEMENTED — `classify()` (regex, sempre attivo) prima di `ministral_router.py` (cognitivo, OFF di default) |
| Reuse-first | IMPLEMENTED come disciplina osservata — confermato ripetutamente nei census (AI Fashion Agency: "zero nuovi agenti creati"; Revenue: nuova proiezione additiva senza duplicare lo store esistente) |
| Approval solo per azioni rischiose | IMPLEMENTED — `approval_required` nei manifest task, gate espliciti su spesa/pubblicazione |
| Queue e priorità P0-P4 | PARTIAL — la coda esiste ed è reale, ma usa `URGENT/HIGH/NORMAL/LOW`, non `P0-P4` |
| Sandbox + verifier | IMPLEMENTED — `FreeCodingWorkerHandler`'s workspace isolato, `finalization_gate.py`, CI multi-stage |
| Executive State sempre aggiornato | IMPLEMENTED — cache 10s, non "sempre" in tempo reale ma aggiornato su ogni lettura oltre la cache |

---

## §6. Self-improvement distribuito e coordinamento (proposta)

**Stato reale, confermato da tutti e 7 i census indipendentemente**: ogni singolo reparto ha "feedback al consiglio globale" come **PLANNED** — zero eccezioni. Non esiste nessun Global Improvement Council, in nessuna forma, oggi.

Design proposto (non implementato, descritto in dettaglio in [NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md)): ogni reparto mantiene il proprio ciclo locale (baseline misurabile → esperimento isolato → revisore indipendente → promozione controllata → rollback), il Global Improvement Council **coordina risorse/dipendenze/conflitti**, non revisiona in modo sincrono ogni micro-operazione — esattamente come richiesto dalla task, riusando l'`EventLedger` già esistente come canale di raccolta feedback invece di costruirne uno nuovo.

## §7. Modello di coordinamento dei responsabili (proposta)

Vedi [NEXUS_MASTERPLAN_V4_RESPONSABILE_COORDINATION_MODEL.md](NEXUS_MASTERPLAN_V4_RESPONSABILE_COORDINATION_MODEL.md). Riusa la forma già reale delle sezioni di Executive State (`status, health, source, confidence, blockers, next_actions`) estesa con `provenance`/`approval_required`, invece di inventare un'interfaccia nuova.

## §8. Revisore indipendente (proposta)

Vedi [NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md](NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md). Estende `review_pipeline_v1`/`finalization_gate.py` già esistenti, non li sostituisce.

---

## §9. Roadmap di maturità — riconciliata con la realtà

L'infografica propone 5 fasi con stime temporali (1-3 mesi, 3-6, 6-12, 12-24, 24+). **Le stime temporali sono l'aspirazione dell'utente, non misurate in questa sessione — riportate come tali, non convalidate.** Quello che il census permette di dire con certezza è **dove siamo oggi rispetto ai contenuti di ciascuna fase**:

| Fase | Contenuto (infografica) | Dove siamo davvero oggi |
|---|---|---|
| 1 — Foundation | Setup infrastruttura, dati e integrazioni base, primi agenti/workflow | **In gran parte fatto**: Queue/Orchestrator/EventLedger/Executive State/CI-deploy sono IMPLEMENTED e testati |
| 2 — Stabilizzazione | Ottimizzazione processi, affidabilità, più contenuti/lead | **In corso, disomogeneo**: AI Fashion Agency e Jarvis sono maturi; Finance è quasi vuoto; Trading ha un imbuto di validazione quasi vuoto |
| 3 — Ottimizzazione | Scaling operativo, automazione avanzata, performance | **Non iniziata in modo coordinato** — nessun Global Improvement Council, nessun ciclo di self-improvement attivo in nessun reparto |
| 4 — Espansione | Nuovi mercati/progetti, più agenti/servizi, crescita ricavi | Non raggiungibile in modo sano prima che la Fase 3 esista davvero (coerente con la logica "non costruire la Fase 4 su una Fase 3 assente") |
| 5 — Indipendenza | Sistema auto-sufficiente, entrate scalabili | Obiettivo finale, nessuna misura possibile oggi |

**Raccomandazione di sequenza** (non una decisione presa, solo l'implicazione diretta della tabella sopra): i QUICK_WIN e HIGH_IMPACT dell'architecture review che chiudono il gap della Fase 3 (Global Improvement Council minimo, revisore indipendente esteso) valgono più, oggi, di qualunque nuova feature di Fase 4.

---

## §10. Indice completo dei documenti di questo set

1. **NEXUS_MASTERPLAN_V4.md** (questo documento) — canonico, mission, stato per reparto/infra, principi, roadmap riconciliata.
2. [NEXUS_MASTERPLAN_V4_TRADING.md](NEXUS_MASTERPLAN_V4_TRADING.md)
3. [NEXUS_MASTERPLAN_V4_REVENUE.md](NEXUS_MASTERPLAN_V4_REVENUE.md)
4. [NEXUS_MASTERPLAN_V4_AI_FASHION_AGENCY.md](NEXUS_MASTERPLAN_V4_AI_FASHION_AGENCY.md)
5. [NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md](NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md)
6. [NEXUS_MASTERPLAN_V4_SYSTEM_DEVELOPMENT.md](NEXUS_MASTERPLAN_V4_SYSTEM_DEVELOPMENT.md)
7. [NEXUS_MASTERPLAN_V4_FINANCE_COST.md](NEXUS_MASTERPLAN_V4_FINANCE_COST.md)
8. [NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md](NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md)
9. [NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md) — proposta
10. [NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md](NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md) — proposta
11. [NEXUS_MASTERPLAN_V4_RESPONSABILE_COORDINATION_MODEL.md](NEXUS_MASTERPLAN_V4_RESPONSABILE_COORDINATION_MODEL.md) — proposta
12. [NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md) — revisione critica, Improvement Card, top 10
13. [NEXUS_MASTERPLAN_V4_GAP_ANALYSIS.md](NEXUS_MASTERPLAN_V4_GAP_ANALYSIS.md) — sintesi breve, rimanda ai documenti di reparto per il dettaglio

---

NEXUS_MASTERPLAN_V4_CANONICAL_DOCUMENTED (vedi nota finale nel report di consegna su cosa resta da fare prima di dichiararlo definitivo)
