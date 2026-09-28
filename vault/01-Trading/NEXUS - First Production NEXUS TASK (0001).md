# NEXUS TASK #0001 — prima task reale attraverso l'Orchestrator

**Baseline:** `7c79052` (Orchestrator V1 Core, `ORCHESTRATOR_V1_OPERATIONAL`). Prima task "vera" (non un acceptance test) inserita nella queue - Claude solo supervisore, mai esecutore del contenuto.

**Task**: backfill `temporal_concentration` + `exit_efficiency` per BREAKOUT_ACC e ORDER_BLOCK (Research Priority Queue, Phase 7.26) - 2 task TIER0 (verifica input) + 4 task TIER2 (Ministral).

## Risultato

Tutti e 6 i task **COMPLETED**, confidence **HIGH** su tutti e 4 i backfill, **zero escalation**, **zero costo/token premium** (nessuna chiamata API Claude/Codex). 2 retry usati (entrambi su BREAKOUT_ACC, classificati `ENVIRONMENT` - timeout di rete a 180s sul primo tentativo, riuscito al secondo) - mai un retry per un errore di logica del modello. Tutti e 4 i risultati **ri-verificati indipendentemente** da Claude con un ricalcolo separato (non solo lettura del file salvato) - match esatto.

Tempo totale: 787s (~13 min) per l'intera pipeline (2 TIER0 + 4 TIER2, incluendo i 2 retry).

## Bug reali trovati e corretti nel core (non nel worker, non nel contenuto)

Durante il primo tentativo, 2 sotto-task erano stati sottomessi PRIMA che la loro dipendenza (verifica input) fosse completata - la macchina a stati del Task Queue non prevedeva la transizione `CREATED -> WAITING_DEPENDENCY`, e non esisteva un meccanismo per promuovere un task da `WAITING_DEPENDENCY` a `QUEUED` quando la dipendenza si completa dopo la sottomissione. Entrambi corretti in `core/task_queue.py`/`core/orchestrator.py` - infrastruttura dell'Orchestrator stesso, mai lavoro di dominio del worker.

## Deliverables

`server/orchestrator_v1/run_nexus_task_0001_backfill.py`, `nexus_task_0001_result_v1.json`, 4 risultati in `server/research_scripts/phase7/phase7_28/nexus0001_result_*.json`, 2 fix in `core/task_queue.py` e `core/orchestrator.py`.

## Nota

Prima dimostrazione che il flusso `NEXUS TASK → Orchestrator → Ministral/deterministic → verifier → risultato` funziona per un lavoro reale a basso rischio senza intervento manuale di Claude sul contenuto. I dati (`temporal_concentration`/`exit_efficiency` per BREAKOUT_ACC/ORDER_BLOCK) restano un risultato quantitativo grezzo - non ancora integrato nella Cross-Strategy Synthesis/Research Priority Queue di Phase 7.26 (fuori perimetro di questa task, che riguardava la meccanica dell'Orchestrator, non l'aggiornamento dei registry scientifici).
