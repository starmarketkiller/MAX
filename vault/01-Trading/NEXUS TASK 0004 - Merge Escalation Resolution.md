# NEXUS TASK #0004 — Merge Escalation Resolution (ORDER_BLOCK.exit_efficiency)

**Baseline:** `4b9de1f`. Chiude il ciclo aperto da NEXUS TASK #0002: l'unica escalation genuina (`ORDER_BLOCK.exit_efficiency`) risolta da Claude e rimessa in coda a NEXUS per merge — esattamente il flusso proposto dall'utente:

```
NEXUS TASK #0002 → 6 campi verificati → APPROVE (TASK #0003) → Vault
       └─ 1 campo incerto → CLAUDE ESCALATION → review → NEXUS merge (TASK #0004)
```

## Risoluzione Claude (usando solo il CONTEXT_PACKET_V1 già generato da NEXUS)

**Verdetto: `FIELD_VALUE`** (non `KEEP_NOT_AVAILABLE`).

- **Valore**: 0.31 (0.3113124818998961), 13 eventi, 0 esclusi — **ricalcolato indipendentemente** da Claude partendo dal dataset canonico grezzo (Phase 7.22), risultato identico a NEXUS TASK #0001.
- **Perché non doveva restare NOT_AVAILABLE**: il fallimento originale era di generazione narrativa (Ministral ometteva ripetutamente il numero), non di validità del dato — nessuna ambiguità interpretativa reale trovata.
- **Scoperta collaterale durante la verifica**: il campo `direction` nei dataset economici (BREAKOUT_ACC e ORDER_BLOCK) è codificato come **intero** (`1`=BUY, `-1`=SELL), non come stringa `"BUY"`/`"SELL"` — la formula usata finora (anche quella già applicata a BREAKOUT_ACC in TASK #0003) confrontava sempre con la stringa, non intercettando mai il caso BUY. **Verificato algebricamente e numericamente** che per questa specifica formula a rapporto l'errore era innocuo (numeratore e denominatore si negano insieme in modo consistente, il rapporto risultante è identico) — confermato sia per i 13 eventi ORDER_BLOCK sia per i 47 eventi BREAKOUT_ACC già nel Vault. Corretto comunque per robustezza futura, nessun valore già applicato è cambiato.
- **Limitazioni dichiarate**: n=13 (campione minimo, già noto), 1 evento anomalo (ratio=0.125) riportato senza interpretarne la causa.

## Merge (attraverso NEXUS, non applicato a mano)

Riusata la STESSA infrastruttura di TASK #0003 (`apply_approved_backfill`): builder rigenerato, `cross_strategy_synthesis_v1.json` rigenerato a cascata, verificato che **solo** `ORDER_BLOCK.exit_efficiency` sia cambiato, `BREAKOUT_ACC.temporal_concentration` (già applicato) invariato come sentinella di regressione, nessun campo sensibile toccato, suite Phase 7.26 completa (35/35) passa senza esclusioni.

**Risultato: COMPLETED, confidence HIGH.**

## Stato finale della Safety Net

Tutti e 7 i campi originariamente classificati `DERIVABLE_NOW` in NEXUS TASK #0002 sono ora nel Vault canonico: **zero escalation aperte residue** su questo ciclo di backfill.

## Decisione finale

**`ESCALATION_MERGED`**

## Deliverables

`run_nexus_task_0004_merge_escalation.py`, `verify_nexus_task_0004.py`, `nexus_task_0004_result_v1.json`, fix di robustezza in `build_cross_strategy_learning_packet.py` (direction int vs stringa + calcolo `ORDER_BLOCK.exit_efficiency`), `cross_strategy_learning_packets_v1.json`/`cross_strategy_synthesis_v1.json` rigenerati, `server/tests/test_nexus_task_0004.py` (5 test), questo vault report.

## Regressione

`verify_nexus_task_0004.py`: PASSED (ricalcolo indipendente dal dataset grezzo, confronto con NEXUS TASK #0001, suite Phase 7.26 completa senza esclusioni). 5/5 test nuovi.
