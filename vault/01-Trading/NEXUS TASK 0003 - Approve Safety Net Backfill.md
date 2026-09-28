# NEXUS TASK #0003 — Approve Safety Net Backfill

**Baseline:** `e9611b6`. Applica al Vault canonico i 6 campi già derivati e verificati da NEXUS TASK #0002, approvati esplicitamente dall'utente in chat — **mai** `ORDER_BLOCK.exit_efficiency` (escalation genuina ancora aperta).

## Vincolo tecnico scoperto durante l'implementazione

Questo repository ha `test_all_artifacts_deterministic` (Phase 7.26): ogni artifact canonico deve essere **esattamente riproducibile** rieseguendo il proprio script builder. Un patch manuale al JSON avrebbe rotto quell'invariante per sempre. **Fix corretto**: le stesse 5 formule già indipendentemente verificate in NEXUS TASK #0001/#0002 sono state incorporate come codice Python deterministico dentro `build_cross_strategy_learning_packet.py` (mai una chiamata LLM in un builder canonico) — l'artifact è stato poi **rigenerato rieseguendo il builder**, non scritto a mano.

**Scoperta collegata**: `cross_strategy_synthesis_v1.json` legge il Learning Packet e la sua stessa verifica di determinismo si rompe se l'upstream cambia senza rigenerare anche lui a cascata — nessuna correzione manuale necessaria (le sue osservazioni sono già parametriche), solo rieseguirlo in sequenza.

## 2 bug reali trovati e corretti nel core dell'Orchestrator (mai nel contenuto)

1. **Approval boundary non applicata al percorso TIER0**: solo le azioni via Ministral rispettavano `approval_required` prima di scrivere un file reale — corretto per valere su qualunque tier, dato che questa è la prima azione TIER0 di questo Core a scrivere davvero un file tracciato.
2. **`RESULT_PACKET_V1.target_tier` non accettava `MANUAL_REVIEW`/`APPROVAL_REQUIRED`** — valori già prodotti dalla logica di escalation ma mai validi contro lo schema. Esteso in modo additivo.

## Esecuzione

Nuova azione deterministica `apply_approved_backfill`: rigenera builder + downstream, verifica che esattamente i 6 campi attesi siano cambiati, `ORDER_BLOCK.exit_efficiency` invariato, nessun campo sensibile (`failure_modes`/`candidate_hypotheses`/`confidence`/`fidelity`/`strategy_identity`/`mechanism`) toccato, suite Phase 7.26 completa (35/35) passa. **Approval**: `AUTO` per questo specifico task — giustificato perché l'utente ha già dato approvazione esplicita in chat a questa esatta applicazione (l'approvazione è avvenuta nel canale umano, non bypassata nel codice).

**Risultato: COMPLETED, confidence HIGH.** Diff reale: `BREAKOUT_ACC` (temporal_concentration, exit_efficiency, execution_degradation, favorable_before_loss, adverse_before_win) + `ORDER_BLOCK.temporal_concentration`. `ORDER_BLOCK.exit_efficiency` confermato intatto (`NOT_AVAILABLE`).

## Decisione finale

**`BACKFILL_APPROVED_AND_APPLIED`**. Premium calls/cost: 0.

## Deliverables

`run_nexus_task_0003_approve_backfill.py`, `verify_nexus_task_0003.py`, `nexus_task_0003_result_v1.json`, fix a `core/orchestrator.py`/`core/deterministic_worker.py`, estensione `contracts/result-packet.schema.json`, fix a `build_cross_strategy_learning_packet.py`, `cross_strategy_learning_packets_v1.json` e `cross_strategy_synthesis_v1.json` rigenerati, `server/tests/test_nexus_task_0003.py` (6 test), questo vault report.

## Regressione

`verify_nexus_task_0003.py`: PASSED (ricalcolo indipendente del builder, diff contro il commit precedente, suite Phase 7.26 completa senza esclusioni, nessun file MQL5/Product-Platform toccato). 6/6 test nuovi + 42/42 suite Orchestrator invariata.
