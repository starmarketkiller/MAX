# NEXUS MASTERPLAN V4 — Reparto Revenue

Vedi [NEXUS_MASTERPLAN_V4.md](NEXUS_MASTERPLAN_V4.md) per legenda di stato e provenienza. Fonte: census read-only di questa sessione.

**Sintesi**: scouting, qualifica lead e follow-up sono reali e bounded (delega a Ministral con verificatore anti-allucinazione). Conversione/pagamento sono **deliberatamente bloccati** — nessun invio automatico, nessun CRM, nessuna integrazione di pagamento, per scelta di pivot strategico documentata in sessione precedente (priorità P0 = first revenue manuale, non altra infrastruttura).

## Input
Lead inbound, prospect, richieste servizio.

## Processo interno

| # | Step | Stato | Evidenza |
|---|---|---|---|
| 1 | Scouting e ricerca opportunità | IMPLEMENTED | `funding_v1/market_scout.py` + `opportunity_scoring.py` + `hard_gates.py::compute_hard_gate()` (precedenza fissa legale/policy > fattibilità capitale > copertura capability > confidenza evidenza — un punteggio alto non supera mai un blocco) |
| 2 | Qualificazione lead | IMPLEMENTED | `revenue_agent.py::RevenueLocalTaskHandler` + `verify_revenue_output()` — verificatore anti-allucinazione reale (`_grounded()` rigetta ogni fatto non presente nel testo prospect fornito); `draft_fingerprint()` deduplica per hash contenuto |
| 3 | Pipeline e CRM | PARTIAL | Nessun CRM dedicato; stato vive in `FirstRevenueStore` (JSON idempotente, fsync, loggato su `FIRST_REVENUE_RECORD_UPDATED`) + `RevenueVentureRegistry` per le 4 venture zero-budget. Nessun modello di relazione contatto oltre record prospect piatti |
| 4 | Proposta e preventivo | PARTIAL | Bozze di outreach generiche; nessun tipo di task "preventivo strutturato" dedicato trovato |
| 5 | Follow-up e negoziazione | IMPLEMENTED (solo bozza) | `RevenueScheduler` pianifica follow-up; `RevenueResultDelivery` espone `FOLLOWUP_DUE`/`REPLY_REQUIRES_REVIEW` a Jarvis. **Nessun invio automatico per design** — docstring esplicito: "cannot send email, change price, promise delivery, sign contracts or move money" |
| 6 | Conversione e pagamento | **BLOCKED by design** | `FirstRevenueStore` può registrare ordini pagati, ma nulla automatizza la cattura pagamento/conversione — coerente con la decisione di pivot: "no CRM, no payment integration, no outreach automation" |
| 7 | Delivery e supporto | PARTIAL | `RevenueResultDelivery.poll()` reale e idempotente (dedup via set `delivered` persistito), ma consegna *informazione sull'esito* a Jarvis, non il servizio al cliente — "Nessuna azione esterna eseguita" è hardcoded nel summary dell'evento di valore più alto |
| 8 | Upsell/retention | PLANNED | Nessun codice trovato |
| 9 | Report revenue | IMPLEMENTED | `revenue_agent.py::compute_revenue_metrics()`; `revenue_portfolio.py::venture_metrics()/comparative_score()/portfolio_summary()`. **Nuovo**: `business_units/revenue.py::agency_revenue_projection()` — proiezione additiva che legge gli eventi revenue dell'AI Fashion Agency per mostrarli accanto alle venture esistenti, senza creare un secondo sistema revenue (scoping pulito, nessuna duplicazione) |

## Output
Clienti acquisiti, vendite, pipeline attiva, contratti in corso, nuove opportunità.

## Self-improvement locale

| Item | Stato |
|---|---|
| KPI conversione / colli di bottiglia | IMPLEMENTED — `RevenueTelemetry` (automation.py) registra ogni intervento umano richiesto, segnale reale di collo di bottiglia |
| Test offerte/script, esperimenti funnel, confronto tassi | PLANNED — nessun codice di confronto A/B trovato |
| Feedback al consiglio globale | PARTIAL — `RevenueTelemetry` produce eventi ledger che un consiglio globale *potrebbe* consumare, ma nessuna aggregazione esplicita per quello scopo esiste oggi |

## Gate e capability
`hard_gates.compute_hard_gate()` (deterministico, precedenza fissa).

## Verificatori
`verify_revenue_output()` — grounding/anti-allucinazione sulle bozze Ministral.

## Error handling / retry
Delegato interamente all'Orchestrator/TaskQueue condiviso (riuso corretto, non reimplementato qui).

## Approvazioni
Ogni azione esterna (invio, prezzo, consegna, contratto, pagamento) richiede un umano per costruzione — non un'eccezione, il design stesso.

## Dipendenze
Jarvis (creazione/consegna task), `ministral_task_compiler` (prompt bounded), `EventLedger` condiviso, store eventi revenue dell'AI Fashion Agency (lettura one-way).

**Non analizzati in profondità in questo census** (fuori budget, flag per lavoro futuro): `capital_scenarios.py`, `initial_hypothesis_inputs.py`, script `build_*` generatori di artefatti — probabilmente report builder one-off, non step di pipeline.
