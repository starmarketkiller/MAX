# NEXUS MASTERPLAN V4.1 — Workflow Contracts

**Stato: PROPOSTA, 4 schemi JSON scritti e validati sintatticamente, nessun codice che li produce/consuma implementato.** Questo documento spiega i 4 contratti e come si relazionano tra loro e con l'infrastruttura reale già esistente.

## I 4 contratti

| Contratto | File | Scopo |
|---|---|---|
| `NEXUS_WORKFLOW_DEFINITION_V1` | [`contracts/nexus-workflow-definition-v1.schema.json`](../contracts/nexus-workflow-definition-v1.schema.json) | Il DAG dichiarativo di un workflow di reparto — nodi, archi, dipendenze, parallelismo, branching, policy di verifica/retry/recovery |
| `NEXUS_WORKFLOW_RUN_STATE_V1` | [`contracts/nexus-workflow-run-state-v1.schema.json`](../contracts/nexus-workflow-run-state-v1.schema.json) | Stato runtime di un'esecuzione — proiezione sopra i task figli reali |
| `DEPARTMENT_RESULT_PACKET_V1` | [`contracts/nexus-department-result-packet-v1.schema.json`](../contracts/nexus-department-result-packet-v1.schema.json) | Output strutturato di un responsabile di reparto |
| `NEXUS_VISUAL_WORKFLOW_STATE_V1` | [`contracts/nexus-visual-workflow-state-v1.schema.json`](../contracts/nexus-visual-workflow-state-v1.schema.json) | Proiezione sola-lettura per il Visual Operations Center |

Più, correlato ma documentato separatamente: `NEXUS_INDEPENDENT_REVIEW_V1` ([`contracts/nexus-independent-review-v1.schema.json`](../contracts/nexus-independent-review-v1.schema.json), vedi [NEXUS_INDEPENDENT_REVIEW_V1.md](NEXUS_INDEPENDENT_REVIEW_V1.md)).

## Come si relazionano (catena di derivazione, mai duplicazione)

```
NEXUS_WORKFLOW_DEFINITION_V1 (dichiarativo, versionato, scritto una volta)
        │ compila verso task figli reali
        ▼
MultiStageExecutor (già reale, server/jarvis_v1/multi_stage_executor.py)
        │ crea/interroga TASK_MANIFEST_V1 via Orchestrator/TaskQueue canonici
        ▼
NEXUS_WORKFLOW_RUN_STATE_V1 (proiezione runtime, derivata da TaskQueue+EventLedger)
        │
        ├──► DEPARTMENT_RESULT_PACKET_V1 (quando il reparto riporta un esito a Jarvis)
        │
        └──► NEXUS_VISUAL_WORKFLOW_STATE_V1 (quando il Visual Operations Center la legge)
```

**Nessun campo è duplicato senza motivo**: `NEXUS_VISUAL_WORKFLOW_STATE_V1` non ricalcola nulla, proietta solo un sottoinsieme di `NEXUS_WORKFLOW_RUN_STATE_V1` pensato per il rendering. `DEPARTMENT_RESULT_PACKET_V1` riusa la stessa forma già reale di `executive_v1/sections.py` (status/health/key_metrics/blockers/next_actions), estesa con i campi di provenienza/verifica/approvazione richiesti esplicitamente dalla task.

## Perché questi contratti e non un'estensione diretta di `RESULT_PACKET_V1`

`core/result_packet.py::RESULT_PACKET_V1` (già reale, `contracts/result-packet.schema.json`) descrive l'esito di **un singolo task** eseguito da **un singolo executor** (Tier 0-4). I nuovi contratti operano a un livello sopra: un **workflow** è una composizione di più task (nodi), un **reparto** è il proprietario logico di quella composizione. `NEXUS_WORKFLOW_RUN_STATE_V1` non sostituisce `RESULT_PACKET_V1` — lo aggrega.

## Compatibilità con l'esecutore esistente

Il census ha confermato che `multi_stage_executor.py` già crea record figli `TASK_MANIFEST_V1` reali e costruisce `RESULT_PACKET_V1` solo quando ogni step è `VERIFIED` indipendentemente (vedi [NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md](NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md)). Se le sue capacità risultassero insufficienti per un workflow con parallelismo/branching complesso, le estensioni necessarie vanno **documentate qui come requisito**, non implementate modificando il file (territorio concorrente di Codex, fuori scope per questa sessione).

**Estensione potenzialmente necessaria, non implementata, solo segnalata**: `multi_stage_executor.py` oggi (per quanto osservato nel census) gestisce una sequenza di step; `parallel_groups` e `branching_conditions` di `NEXUS_WORKFLOW_DEFINITION_V1` potrebbero richiedere una capacità di esecuzione non ancora presente. Verificare con Codex prima di qualunque implementazione.

## Validazione

Tutti e 5 i file (4 contratti + Independent Review) sono stati validati come JSON sintatticamente corretto in questa sessione. Validazione semantica completa contro lo schema stesso (`validate_registry.py` o equivalente) non eseguita — nessuna istanza di dato reale esiste ancora da validare.

## Checklist prima di implementare
- [ ] Conferma utente sul design dei 4 contratti.
- [ ] Verifica con Codex se `multi_stage_executor.py` supporta già `parallel_groups`/`branching_conditions` o se serve un'estensione.
- [ ] Reparto pilota (vedi [Self-Improvement V1](NEXUS_DISTRIBUTED_SELF_IMPROVEMENT_V1.md)) come primo a produrre un'istanza reale di questi contratti.
