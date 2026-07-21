# PR 8 — Command and LocalBridge contract

Rende robusto il ciclo di vita dei comandi (doc 09): prima `bridge_commands`
faceva `pending → sent → done/error` senza lease, retry, conteggio tentativi o
dead-letter; un worker che moriva dopo il poll lasciava il comando bloccato in
`sent` per sempre. Inoltre il worker esisteva in **due copie byte-identiche**.

## Contratto (`server/command_contract.py`) — pura logica testabile

- **Stati canonici**: `PENDING`, `LEASED`, `RUNNING`, `SUCCEEDED`,
  `FAILED_RETRYABLE`, `FAILED_FINAL` (dead-letter), `EXPIRED`, `CANCELLED`,
  con mappa di transizioni e mappa di compatibilità col vocabolario legacy.
- **Busta canonica**: `command_id`, `command_type`, `schema_version`,
  `created_at/by`, `target` scoped (instance/host/account/symbol), `payload`,
  **`idempotency_key`** deterministico, `expires_at`, `attempts`, `max_attempts`.
- **Lease/retry/dead-letter** come funzioni pure: `lease` (incrementa attempts,
  imposta scadenza), `reclaim_if_expired_lease` (torna PENDING o dead-letter),
  `complete` (SUCCEEDED / FAILED_RETRYABLE / FAILED_FINAL), `expire_if_past_ttl`.

## Backend (`bridge_commands`, migrazione additiva)

Colonne nuove (righe storiche valide con NULL): `lease_until`, `attempts`,
`max_attempts`, `canonical_status`, `idempotency_key`, `schema_version`,
`dead_letter_reason`. Comportamento:
- `poll`: **reclaim** delle lease scadute (→ pending o dead-letter), poi **lease
  atomico** del più vecchio pending (attempts++, scadenza, `canonical_status=LEASED`);
- `ack ok` → `SUCCEEDED`; `ack error` → **retry** (torna pending) finché
  `attempts < max_attempts`, poi **dead-letter** `FAILED_FINAL`;
- `enqueue`: **idempotente** per `idempotency_key` (stesso comando attivo → no dup);
- nuovo `GET /api/local_bridge/commands` → stato canonico + lista dead-letter
  (la UI mostra lo stato dal backend, non presume l'esecuzione dall'enqueue).

Backward-compatible: il worker continua a usare `pending/sent/done/error`; il
`canonical_status` viaggia in parallelo.

## Worker deduplicato

`server/nexus_local_worker.py` è la **fonte unica**;
`LocalBridge/nexus_local_worker.py` diventa uno shim (`runpy.run_path`) che esegue
la fonte canonica. Niente più due copie da tenere in sync (prima 11 KB × 2).

## Manifest di deployment

`contracts/deployment-manifest.json` (versionato): versioni/percorsi di backend,
worker (fonte canonica + entrypoint shim), EA, e i contratti collegati
(strategy registry, settings schema, command schema version) + gli stati comando.

## Verifica (backend/Python — testato davvero)

`server/tests/test_command_contract.py` → 12 test (stati/transizioni, lease,
reclaim→pending→dead-letter, complete, idempotenza, expire, enqueue idempotente,
poll-lease/ack, retry→dead-letter end-to-end, endpoint, worker deduplicato,
manifest). Suite backend completa: **58/58**.

## Follow-up (non in questo PR)

- **EA commands** (`ea_commands`): stesso schema lease/target-scoping (oggi consuma
  il più vecchio globalmente prima della conferma) — migrazione analoga.
- **Sicurezza**: `host_id` emesso server-side, validazione per-tipo dei payload,
  conferma UI sui comandi distruttivi, transizioni nel ledger eventi (PR9).
- **Frontend**: mostrare `canonical_status` e la coda dead-letter.
