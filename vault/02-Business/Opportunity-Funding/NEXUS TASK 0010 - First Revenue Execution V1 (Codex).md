# NEXUS TASK #0010 — First Revenue Execution V1 (bookkeeping, lavoro Codex)

**Commit:** `01e6180` (`feat: add first revenue execution v1`, autore `codex-local`). **Dettaglio tecnico completo:** [[docs/NEXUS_FIRST_REVENUE_EXECUTION_V1]] — questa nota è solo il ponte vault, non duplica il contenuto.

## Decisione

Aggiungere solo la contabilità operativa mancante al Funding Framework già esistente ([[NEXUS TASK 0005 - Funding Priority and Opportunity Framework V1]], [[NEXUS TASK 0007 - Adopt Funding Framework V1 and Vault Namespace Cleanup]]): record di Offer, Lead, Payment osservato (Revolut), Revenue. Il flusso minimale:

```
OPPORTUNITY → OFFER → LEAD → OUTREACH → DELIVERY → PAYMENT → REVENUE → LEARNING
```

Nessun CRM, nessuna API bancaria, nessun movimento di denaro autonomo. `CONTACTED` richiede sempre un record di approvazione umana esplicita legato a un fingerprint del messaggio. `PAID`/Revenue richiedono sempre un riferimento esterno osservato, mai una dichiarazione del sistema.

## Cosa aggiunge

- `server/funding_v1/first_revenue.py` (`FirstRevenueStore`, state machine `LEAD_TRANSITIONS`: DISCOVERED→QUALIFIED→CONTACT_READY→CONTACTED→REPLIED→INTERESTED→WON/LOST).
- `server/funding_v1/market_scout.py` — valutazione locale bounded (via Orchestrator esistente, `LOCAL_STRONG_MINISTRAL3B`), accesso a rete/outreach/pagamento disabilitato, non può scegliere business/target/prezzo finale.
- 4 nuovi schema di contratto: `lead-v1`, `offer-v1`, `payment-v1`, `revenue-v1`.
- `contracts/nexus-event.schema.json` esteso in modo additivo con `FIRST_REVENUE_RECORD_UPDATED`.

## Relazione con l'esperimento manuale in corso

Questo è infrastruttura di bookkeeping, parallela e complementare (non in conflitto) al vero esperimento FIRST_REVENUE eseguito manualmente in questa stessa finestra temporale — vedi [[NEXUS TASK 0011 - First Revenue Manual Experiment (Lead Research Service)]]. Il lead PNT Solutions contattato manualmente il 2026-10-05 **non è ancora stato registrato** in `FirstRevenueStore` (nessun task di import/backfill eseguito) — gap noto, non un conflitto.

## Limiti dichiarati (dal file docs originale)

- Delivery non duplicata: un lead approvato può referenziare una normale NEXUS Queue task, governata da Router/verifier/Approval Gate esistenti.
- Revenue è un segnale osservato, non una prova automatica che un'offerta sia validata.
- Fuori scope esplicitamente: discovery prospect automatizzata, sync CRM, riconciliazione bancaria, fatturazione, contratti, outreach autonomo, billing ricorrente.

## Evidenza/test

`run_market_scout_example.py`: primo run rifiutato da validazione deterministica (`missing_info` oltre il limite di 2 voci), retry canonico riuscito, review tecnica ha confermato entrambe le evidence grounded sui fatti forniti. Artifact preservato: `first_revenue_market_scout_example_v1.json` — esplicitamente non una decisione di business né un'approvazione di outreach.

## Blocker

Nessuno — pull fast-forward già integrato in locale (`git merge --ff-only origin/main`), nessun conflitto.

## Prossimo passo

Nessuna azione pianificata su questo modulo per ora; non è sulla strada critica del trading historical audit.
