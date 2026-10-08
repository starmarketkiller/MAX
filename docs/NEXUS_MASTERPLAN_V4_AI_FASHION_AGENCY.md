# NEXUS MASTERPLAN V4 — Reparto AI Fashion Agency

Vedi [NEXUS_MASTERPLAN_V4.md](NEXUS_MASTERPLAN_V4.md) per legenda di stato e provenienza. Fonte: census read-only di questa sessione.

**Sintesi**: il reparto più maturo dei 7. 32 test reali (13 + 19 funzioni `def test_` confermate per conteggio diretto), state machine prodotto reale con gate che sollevano eccezione (non skip silenzioso) se mancano requisiti, zero nuovi agenti creati (riusa Orchestrator/Router/skill pack esistenti). **Pubblicazione e monetizzazione sono esplicitamente hard-disabled by policy** — coerente con il vincolo di questo stesso task ("NON pubblicare contenuti... NON spendere crediti").

## Input
Trend moda, prodotti, viral format, richieste brand/clienti, feedback audience.

## Processo interno

| # | Step | Stato | Evidenza |
|---|---|---|---|
| 1 | Scouting e analisi trend | IMPLEMENTED | `scouting.py` V2 — `SCOUT_RESULT_V1` con provenienza (source/url/observed_at/evidence/confidence/dedup_key). Nessun crawling autonomo — collector sono `SUPPLIED_SESSION_TOOL` o `MANUAL`; SearXNG/Crawl4AI esplicitamente `NOT_INSTALLED` |
| 2 | Store setup e compliance | IMPLEMENTED | `pipeline.py:56-134` — state machine reale `DISCOVERED→EVALUATING→STORE_PENDING→STORE_READY→...→RETIRED` (`transition_product()`), `STORE_READY` richiede un riferimento di listing reale + approvazione umana (solleva `ValueError` se mancanti). `compliance_check()` (riga 146): AI-label, disclosure, no riuso footage reale, audio licenziato, no claim assoluti, 21+, no contenuto esplicito |
| 3 | Casting/roster modello AI | PARTIAL | `roster.py` — 5 archetipi definiti ma `CASTING_DRAFT` (nessuna generazione); 2 modelle (Elena, Nova) hanno identity sheet/prompt seed/wardrobe reali dal seed pack V2 |
| 4 | Brief creativi e assegnazione | IMPLEMENTED | `content_engine.py` — brief card (hook ≤8 parole, formato, modella, prodotto, piattaforma, compliance, store gate, costo, approvazione); assegnazione modella via `roster.score_models` |
| 5 | Preventivo generazione | IMPLEMENTED | `build_generation_pack()` pianifica chiamate Higgsfield, richiede quota ≤7 giorni o imposta `WAITING_QUOTE`. Esempio reale: 2.25 crediti/2 varianti, `submitted: false` confermato in `examples/e2e_simulation_v1.json` |
| 6 | Approval crediti/asset | IMPLEMENTED | `approve_generation_pack()` — gate a match esatto (`expected_credits == quoted_credits`), nessun overspend silenzioso |
| 7 | Generazione contenuti | PARTIAL by design | NEXUS non esegue Higgsfield da sé — avviene in una sessione Claude approvata; `record_generation_result()` rifiuta step non approvati o spesa oltre quota. **Zero crediti spesi in questo codebase** (confermato: `submitted: false`) |
| 8 | Editing e post-produzione | PLANNED/assorbito | Nessuno step distinto trovato oltre l'assemblaggio del content package |
| 9 | Packaging per social/ads | IMPLEMENTED (packaging); **PUBLISH hard-disabled** | `social.py:12,135` — docstring: "PUBLISH action... is hard-disabled by policy"; `require_approval("PUBLISH", ...)` commentato "hard-disabled in V2". Adapter Postiz dry-run only |
| 10 | Pubblicazione/distribuzione → Monetizzazione | **BLOCKED by policy deliberata** | Pubblicazione/sponsorship/contatto brand/pagamenti tutti hard-disabled anche con approvazione (README, sezione Policy) — coerente col vincolo di questo task. `AGENCY_REVENUE_EVENT_V1` esiste in codice ma è naturalmente vuoto (nessun evento possibile pre-pubblicazione) |

## Output
Contenuti generati, campagne attive, prodotti promossi, portfolio modelle, ricavi/insight (oggi: nessun ricavo reale, per via del blocco sopra).

## Self-improvement locale

| Item | Stato |
|---|---|
| Analisi KPI contenuti | IMPLEMENTED — `kpis.py`, esplicito `UNAVAILABLE` quando mancano dati (mai zero fabbricato) |
| Problemi/opportunità | PARTIAL — rigetti compliance e blocchi store-gate sono visibili ma nessun detector automatico di opportunità |
| Proposte nuovi format/modelle | PLANNED |
| Esperimenti sandbox | PARTIAL — `simulation.py`/`dry_run_v2.py` sono dry run reali a costo zero, basati su evidenza, ma non un framework A/B ripetibile |
| Confronto creatività | PLANNED |
| Feedback al consiglio globale | PLANNED — nessun consiglio esiste ancora (vedi [proposta](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md)) |

## Gate e capability
`policy.py::AGENTIC_AUTOMATION_POLICY_V1` — livelli autonomo/approvazione/hard-disabled. Riusa `MultiStageExecutor`, `RevenueSkill` pack, `agency_bounded_task` skill, `premium_allowed=False` default P2.

## Verificatori
`compliance_check()`, gate a `ValueError` su store/approvazione, gate a match esatto su crediti, 32 funzioni di test reali.

## Error handling / retry
Delegato all'Orchestrator condiviso; nessun retry custom trovato in questo reparto.

## Approvazioni
Umana su: store listing, crediti/asset, pubblicazione (quest'ultima sempre negata oggi per policy).

## Dipendenze
Jarvis (`/agency` + routing NL con precedenza esplicita sulla creazione task generica), Revenue (store revenue separato — **non** ancora nel registro delle 4 venture zero-budget, mismatch di schema segnalato come gate futuro, non nascosto), Social/Content (**assorbito qui**, non un reparto separato — vedi [NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md](NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md)).

## Guardrail confermati per il vincolo "nessuna pubblicazione/spesa live" di questo task
Reali, a livello di codice, non solo di documentazione: gate `ValueError` su store listing + approvazione, gate a match esatto sui crediti di generazione, percorso PUBLISH gated e definito "disabled" nel docstring stesso.
