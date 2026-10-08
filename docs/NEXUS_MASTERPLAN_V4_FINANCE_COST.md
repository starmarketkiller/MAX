# NEXUS MASTERPLAN V4 — Reparto Finance & Cost

Vedi [NEXUS_MASTERPLAN_V4.md](NEXUS_MASTERPLAN_V4.md) per legenda di stato e provenienza. Fonte: census read-only di questa sessione — nessun file budget/executor toccato (lavoro concorrente di Codex su "gestione del budget" rispettato).

**Sintesi onesta**: Finance & Cost **non esiste come reparto coeso**. Quello che è reale sono due frammenti stretti costruiti per altri scopi — gating della spesa LLM premium (territorio System&Development/Jarvis) e tracking margine first-revenue (territorio Revenue) — più un calcolatore ROI locale all'AI Fashion Agency. Una vera capacità cross-reparto di costo/ricavo/forecast è interamente PLANNED.

## Input
Entrate da reparti, costi operativi, costi AI/tools, budget, investimenti.

## Processo interno

| # | Step | Stato | Evidenza |
|---|---|---|---|
| 1 | Raccolta e normalizzazione dati | PARTIAL | Nessun modulo di ingestione unificato — `EventLedger.payload.cost_usd` per chiamate premium (`executive_v1/sections.py:336-337`), `first_revenue.py:253-257` traccia `amount`/`cost`/`gross_margin` via `Decimal` per pagamento. Nessuno schema normalizzato unico che li unisca |
| 2 | Attribuzione per reparto/progetto | PLANNED | Nessun codice attribuisce costo/ricavo a un reparto specifico. `financial_risk` sui manifest task (`jarvis_v1/service.py:947`) è **hardcoded alla stringa letterale "NONE"** su ogni task — placeholder statico, non calcolato |
| 3 | Report costi e ricavi | PARTIAL | `executive_v1/sections.py` aggrega `premium_model_cost_usd` nell'Executive State (reale, sommato dal ledger, esposto via `conversation.py:251`) — ma scoped solo a spesa LLM premium, non costi operativi/infra/ricavi ampi |
| 4 | Alert budget e margini | PARTIAL (via prevenzione, non alert) | `review_pipeline_v1/premium_budget_policy.py::allow_premium()` — 5 livelli, fail-closed su livello sconosciuto, reale e testato. È prevenzione della spesa, non un alert di soglia superata |
| 5 | Pianificazione costi | PLANNED | Nessun modulo di forecasting/pianificazione costi trovato |
| 6 | Calcolo ROI/ROAS/unit economics | PARTIAL, scoped a un reparto | Reale solo dentro `business_units/ai_fashion_agency/kpis.py`/`projection.py`. Nessun calcolatore riusabile per Trading/Revenue |
| 7 | Forecast e scenario planning | PLANNED per Finance generale; `projection.py` dell'agency è l'unico forecasting trovato, locale a quel reparto |
| 8 | Raccomandazioni decisionali | PLANNED | Nessun codice sintetizza costo+ricavo in raccomandazioni cross-reparto |

## Output
Monitoraggio costi, ricavi per reparto, decisioni finanziarie, forecast, report economici — tutti scoped oggi, nessuno cross-reparto.

## Self-improvement locale

| Item | Stato |
|---|---|
| KPI economici | PARTIAL — `premium_model_cost_usd` è un KPI reale, scope stretto |
| Anomalie/allocazioni | PLANNED |
| Ipotesi di allocazione / simulazioni sandbox | PLANNED |
| Confronto scenari | PLANNED |
| Feedback al consiglio globale | PLANNED |

## Gate e capability
`premium_budget_policy.py::allow_premium()` — unico gate Finance reale, vive dentro il motore di esecuzione (`provider_policy.py`/`provider_connector.py`), non come servizio Finance a sé.

## Dipendenze
`executive_v1` (unico posto dove il costo premium è davvero mostrato a un umano); routing premium di Jarvis & Automation/System & Development.

## Nota di confine (verificata, non sovrapposta)
Il lavoro concorrente di Codex su budget in `multi_stage_executor.py` usa `task_total_budget_seconds` — un budget di **tempo** per task, non denaro. `dispatcher.py` non ha riferimenti a budget/costo. Nessuna sovrapposizione con questo census.

## Priorità per il futuro
Questo è il gap più grande e più semplice da colmare tra i 7 reparti: i pezzi riusabili esistono già (ledger eventi con `cost_usd`, store margine first-revenue, ROI agency) — serve un aggregatore sottile che li unisca, non un sistema nuovo. Vedi [architecture review](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md) per la proposta classificata.
