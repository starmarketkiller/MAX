# NEXUS MASTERPLAN V4.1 — Distributed Self-Improvement (7 cicli)

**Stato: PROPOSTA, non implementata.** Estende [NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md) (già scritto in V4) con il ciclo a 9 fasi e le metriche per-reparto richieste esplicitamente da V4.1. Non sostituisce il documento V4 — lo rende operativo con dettaglio per-reparto.

## Il ciclo (identico per tutti e 7 i reparti, solo le metriche cambiano)

```
OBSERVE → DIAGNOSE → HYPOTHESIZE → PLAN → EXPERIMENT → EVALUATE → REVIEW → PROMOTE/REJECT → MONITOR
```

| Fase | Cosa fa | Componente riusato (mai nuovo) |
|---|---|---|
| OBSERVE | Legge la baseline/KPI già reale del reparto | `executive_v1/sections.py` (già IMPLEMENTED per 9 domini) |
| DIAGNOSE | Rileva un'anomalia/opportunità rispetto alla baseline | Nuova funzione leggera, sopra dati esistenti |
| HYPOTHESIZE | Formula un'ipotesi di miglioramento | Registro ipotesi — nuovo, piccolo (vedi schema sotto) |
| PLAN | Pianifica un esperimento isolato con soglia pre-registrata | `NEXUS_WORKFLOW_DEFINITION_V1` (proposto in V4.1) |
| EXPERIMENT | Esegue in sandbox/branch, mai sul percorso live di default | `FreeCodingWorkerHandler.workspace_root`, `dry_run_v2.py`/`simulation.py` (già reali per Agency) |
| EVALUATE | Confronta baseline vs variante sulla soglia dichiarata | [Independent Reviewer](NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md) (proposto in V4) |
| REVIEW | Verdetto L0-L3 secondo [NEXUS_INDEPENDENT_REVIEW_V1](NEXUS_INDEPENDENT_REVIEW_V1.md) | Stesso componente |
| PROMOTE/REJECT | Promozione controllata o rigetto, mai silenzioso | Evento `IMPROVEMENT_PROMOTED`/`IMPROVEMENT_ROLLED_BACK` (additivo a `nexus-event.schema.json`, proposto in V4) |
| MONITOR | Osserva la metrica dopo la promozione, pronto al rollback | `executive_v1` stesso, nessun nuovo monitor |

**Baseline → Improvement Backlog → Hypothesis Registry → Experiment Plan**: tre registri leggeri, additivi, non tre nuovi sistemi — possono vivere come sotto-sezioni dell'evento `IMPROVEMENT_EXPERIMENT_STARTED` già proposto in V4, con un campo `backlog_ref`/`hypothesis_id` ciascuno.

---

## Metriche specifiche per reparto (dalla task, ancorate a cosa è già reale)

### Trading
OOS performance, robustezza, drawdown, costi di esecuzione, qualità dell'evidenza (grado di evidenza, non solo profitto).
**Stato reale**: `mt5_data_v1/analytics.py` (IMPLEMENTED, questa sessione) già calcola profit factor/win rate/drawdown proxy — base pronta per OBSERVE. OOS/robustezza vivono nel registro edge-validation (`forward_validation_status`), già IMPLEMENTED come dato, PLANNED come ciclo di miglioramento automatico.

### Revenue
Response rate, conversione, profitto, costo per prospect.
**Stato reale**: `RevenueTelemetry`/`compute_revenue_metrics()` (IMPLEMENTED) già tracciano conversione/intervento-umano-richiesto — base pronta.

### AI Fashion Agency
Costo asset, visual consistency, retention, conversione.
**Stato reale**: `kpis.py` (IMPLEMENTED) già copre costo/campagna; "visual consistency" è una metrica nuova, da definire (nessun componente oggi la misura).

### Social Content
Views, watch time, CTR, engagement, conversione.
**Stato reale**: `kpis.py` dell'Agency (IMPLEMENTED, scope agency-wide non social-specifico) — vedi [nota di confine](NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md).

### Engineering
CI reliability, incidenti, performance, regressioni.
**Stato reale**: CI già produce questi segnali (pass/fail rate, `docker-smoke`) ma non aggregati come KPI storico — `learning_telemetry.py` esiste solo per la review pipeline, non per CI in generale.

### Finance
Accuratezza attribuzione, budget variance, costo operativo.
**Stato reale**: quasi tutto PLANNED (vedi [census V4 Finance](NEXUS_MASTERPLAN_V4_FINANCE_COST.md)) — questo ciclo di self-improvement non può partire prima che esista l'aggregatore proposto ([Architecture Review V4 #4](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#4-high_impact-aggregatore-finance--cost-cross-reparto)).

### Jarvis
Accuratezza intent, latenza, qualità risposta, notification noise (rumore di notifica).
**Stato reale**: nessuna di queste è oggi misurata sistematicamente — `classify()` non ha un tasso di accuratezza tracciato, `multi_stage_executor.py` ha `last_tick_at`/`last_error_class` (operativo, non qualitativo). Candidato naturale come primo pilota (vedi sotto).

---

## Vincolo esplicito, ripetuto da V4: nessun deploy autonomo di cambiamenti sensibili

PROMOTE richiede sempre il verdetto del Revisore Indipendente (L2 minimo per codice, L3 per azioni ad alto rischio — spesa, pubblicazione, trading live). Nessun reparto può autopromuoversi.

## Reparto pilota raccomandato

**Jarvis Operations** o **AI Fashion Agency** — entrambi i più maturi (vedi [NEXUS_MASTERPLAN_V4_GAP_ANALYSIS.md](NEXUS_MASTERPLAN_V4_GAP_ANALYSIS.md)), quindi con baseline già misurabili senza lavoro preliminare. Finance è esplicitamente **sconsigliato** come pilota — non ha ancora una baseline reale da cui partire.

## Checklist prima di implementare
- [ ] Conferma utente sul design (eredita la checklist di [NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md)).
- [ ] `NEXUS_INDEPENDENT_REVIEW_V1` implementato prima che PROMOTE sia azionabile per qualunque reparto.
- [ ] Reparto pilota scelto e baseline confermata leggibile da `executive_v1`.
