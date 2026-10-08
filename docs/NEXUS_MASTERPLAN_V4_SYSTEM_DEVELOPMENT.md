# NEXUS MASTERPLAN V4 — Reparto System & Development

Vedi [NEXUS_MASTERPLAN_V4.md](NEXUS_MASTERPLAN_V4.md) per legenda di stato e provenienza. Fonte: census read-only di questa sessione — nessun file executor/dispatcher/bridge/CI toccato.

**Sintesi**: forte e rigoroso sul lato CI/deploy (Safe Deploy V1 è reale, non solo documentato). Debole sul lato "NEXUS sviluppa se stesso": un solo template Ministral bounded esiste, ed è read-only.

## Input
Richieste, bug, nuove idee, feedback reparti.

## Processo interno

| # | Step | Stato | Evidenza |
|---|---|---|---|
| 1 | Analisi requisiti e priorità | PARTIAL | `review_matrix.py` + `premium_budget_policy.py` classificano work_type/priorità, ma nessuna fase di triage distinta dalla creazione task stessa |
| 2 | Progettazione architettura | PLANNED | Nessuno step/artefatto di design codificato — avviene ad hoc nei doc prima dell'implementazione, mai come stage gated |
| 3 | Sviluppo e implementazione | IMPLEMENTED | Due percorsi reali: `free_coding_worker.py::FreeCodingWorkerHandler` (fail-closed su `files_allowed` vuoto, riga 109; `verify()`/`apply()` bounded su `allowed_paths`/`forbidden_paths`); `local_bounded_task_handler.py` + `ministral_task_compiler.py` — **un solo template esiste, `REPO_INSPECTION_V1`**, esplicitamente read-only |
| 4 | Test e validazione | IMPLEMENTED | `.github/workflows/ci.yml`: job `backend-tests` (`validate_registry.py` + pytest), `security-preflight` (scan segreti + test dedicati), `docker-smoke` (build+smoke reale dell'immagine), `frontend-build` |
| 5 | Sandbox/staging | IMPLEMENTED per task di codice; PARTIAL in generale | `FreeCodingWorkerHandler` scrive in `workspace_root` isolato, mai nel repo live direttamente; nessun ambiente di staging separato oltre il docker-smoke di CI |
| 6 | Deploy con gate | IMPLEMENTED, rigoroso | `render.yaml`: `autoDeployTrigger: off`; `.github/workflows/safe-deploy.yml` scatta solo dopo CI verde su main, esegue `classify_deploy_risk.py` prima di qualunque deploy hook, `concurrency` evita deploy sovrapposti |
| 7 | Monitoraggio e osservabilità | PARTIAL | Dockerfile healthcheck + `/api/ready`; `learning_telemetry.py` è specifico alla review pipeline, non cross-reparto |
| 8 | Manutenzione e aggiornamenti | PARTIAL | Nessuna automazione di aggiornamento dipendenze/manutenzione pianificata trovata |
| 9 | Documentazione | IMPLEMENTED come pratica, PARTIAL come infrastruttura | Decine di `docs/NEXUS_*_V1.md`, uno per fase/feature; nessun checker di copertura/staleness documentale in CI |

## Output
Sistema stabile, nuove funzioni, agenti attivi, riduzione errori, report tecnici.

## Self-improvement locale

| Item | Stato |
|---|---|
| KPI stabilità/performance | PARTIAL — `learning_telemetry.py` esiste solo per la review pipeline |
| Rilevazione colli di bottiglia | PLANNED |
| Idee di refactor | PLANNED — nessun meccanismo strutturato, solo review umana/Claude |
| Confronto versioni | PARTIAL — `classify_deploy_risk.py` confronta SHA per rischio deploy, non per qualità/performance |
| Feedback al consiglio globale | PLANNED |

## Gate e capability
`files_allowed`/`files_forbidden` fail-closed; `read_only=True` sui template; scan segreti CI; `finalization_gate.py` (scansione deterministica pre-FINALIZED per pattern di chiavi reali — OpenAI/Anthropic-style, PAT GitHub, PEM, Telegram bot-id:secret — non bypassabile).

## Verificatori
`FreeCodingWorkerHandler.verify()`, `BoundedLocalTaskHandler.verify()`, `finalization_gate.py`, suite pytest CI, `validate_registry.py`.

## Error handling / retry
Gestito a livello Orchestrator condiviso (non reimplementato qui).

## Approvazioni
Deploy: gate CI + classificazione rischio prima del deploy hook. Codice: `approval_required` nei manifest task.

## Dipendenze
Orchestrator/TaskQueue/EventLedger condivisi; `provider_policy.py` per il budget premium.

## Nota architetturale (non una duplicazione da unire)
`server/orchestrator_v1/core/local_agent_bridge.py` (job store server-side, outbound-only lease model) + `LocalBridge/nexus_agent_bridge.py` (client) sono una coppia; `LocalBridge/nexus_local_worker.py` + `nexus_terminal_identity_guard.py` sono un'altra coppia, per un dominio diverso (operazioni terminale MT5, command-based non job-lease). **Due coppie client/server indipendenti che condividono una macchina, non un'implementazione ridondante della stessa cosa** — non un candidato QUICK_WIN di merge, vedi [architecture review](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md).
