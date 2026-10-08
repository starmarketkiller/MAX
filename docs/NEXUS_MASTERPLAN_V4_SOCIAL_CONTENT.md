# NEXUS MASTERPLAN V4 — Reparto Social / Content

Vedi [NEXUS_MASTERPLAN_V4.md](NEXUS_MASTERPLAN_V4.md) per legenda di stato e provenienza. Fonte: census read-only di questa sessione.

## Scoperta principale

**Non esiste un reparto Social/Content a sé stante.** È interamente assorbito dentro `server/business_units/ai_fashion_agency/social.py`. Nessun hit per `ContentAgent`/`SocialAgent` fuori da quella cartella. Il playbook che l'infografica implica (`marketing/ai-creator/VIRAL_PLAYBOOK.md`) non esiste più a quel percorso — è stato spostato (non duplicato) in `server/business_units/ai_fashion_agency/playbooks/VIRAL_PLAYBOOK.md`. Questo è un documento breve e onesto, non un workflow di 9 step gonfiato artificialmente — il dettaglio implementativo vive nel documento [AI Fashion Agency](NEXUS_MASTERPLAN_V4_AI_FASHION_AGENCY.md).

## Processo interno (verdetto per i 9 step dell'infografica)

| # | Step | Stato | Evidenza |
|---|---|---|---|
| 1 | Pianificazione editoriale | PARTIAL | `content_engine.py::brief_card()`/`create_content_package()` — nessun concetto di calendario editoriale dedicato |
| 2 | Scelta piattaforma e formato | IMPLEMENTED | `social.py::create_post_draft(store, package_id, platform=None, adapter="POSTIZ")` |
| 3 | Scrittura hook/script/caption | IMPLEMENTED (a livello di skill) | `skills.py` — rami reali `VIRAL_FORMAT_ANALYSIS`, `CONTENT_BRIEF_DRAFT`, `CONTENT_REVIEW` ancorati al playbook migrato |
| 4 | Creazione o adattamento | PARTIAL | `create_content_package(media_refs, review)` esiste; pipeline di generazione media reale non tracciata in profondità |
| 5 | Scheduling multi-canale | IMPLEMENTED | `social.py::transition_post(store, post_id, target, actor, approved_by, planned_at)` — state machine reale |
| 6 | Pubblicazione | **PARTIAL, deliberatamente non live** | `PostizAdapter` docstring: "Payload builder only. No HTTP client ships in V2." `build_payload()` imposta sempre `"dry_run": True`. `ManualExportAdapter` è l'unico percorso non simulato (manuale, eseguito da un umano) — guardrail corretto e intenzionale, coerente col vincolo di questo task |
| 7 | Engagement e community | PLANNED | Nessun codice trovato |
| 8 | Analisi performance | IMPLEMENTED | `kpis.py::agency_kpis()/model_kpis()/campaign_kpis()` |
| 9 | Ottimizzazione e riproposta | PLANNED | Nessuna logica di repurposing/iterazione trovata |

## Self-improvement locale

| Item | Stato |
|---|---|
| KPI reach/CTR/retention | IMPLEMENTED (via `kpis.py`, aggregazione generica agency/model/campaign — non confermato campo-per-campo per reach/CTR specifici) |
| Lead social | Non trovato come metrica distinta |
| Sandbox creativa | PARTIAL — `dry_run_v2.py`/`simulation.py` esistono a livello agency, non social-specifici |
| Confronto risultati | Non trovato come comparatore dedicato |
| Feedback al consiglio globale | PLANNED — nessun consiglio esiste (confermato indipendentemente anche dal census Trading) |

## Nota di reuse per l'architecture review
`SocialAdapter` (classe base) + `PostizAdapter`/`ManualExportAdapter` sono già a forma di adapter, non specifici alla fashion agency nella meccanica (solo i parametri `store`/`package_id` li legano a quel modello dati). Candidato di estrazione futura se un secondo reparto produttore di contenuti comparirà — non urgente oggi con un solo consumatore. Vedi [architecture review](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md).

## Non verificato in questo census
`pipeline.py` (descritto dal playbook come autoritativo sulle regole di compliance/approvazione vincolanti, sopra la prosa del playbook stesso) — chi userà questo documento per lavoro futuro dovrebbe leggerlo direttamente.
