# MT5 Terminal Identity Guard V1

**Stato:** implementato, test locali verdi, **non committato** (in attesa di review esplicita, come richiesto). Nessuna modifica a MQL5/trading logic/risk/execution/runtime di produzione, nessun terzo terminale creato, nessuna VM/containerizzazione.

## Architettura

Schema implementato, esattamente come richiesto:

```
requested role (terminal_role in nexus_worker.config.json)
  → resolve terminal profile (nexus_terminal_profiles.config[.example].json)
  → verify terminal path (mt5_path vs expected_terminal_path_substring)
  → verify data directory (mql5_experts/../.. vs expected_data_dir_substring)
  → verify identity/fingerprint (hash derivato dai due path sopra + pin opzionale — path-based, NON attestazione crittografica del binario, vedi §Limiti)
  → verify allowed operation (allowed_operations / forbidden_operations per ruolo)
  → acquire lock (file lock esclusivo per ruolo, atomic create, liveness-aware — vedi §Lock safety)
  → execute (il worker chiama l'handler esistente, invariato)
```

Integrato nel punto di dispatch già esistente del worker (`main()`, subito prima di `handler(cfg, payload)`), non in ogni singolo handler — un solo punto di ingresso, zero duplicazione.

## File

- **`LocalBridge/nexus_terminal_identity_guard.py`** (nuovo) — tutta la logica: `resolve_and_verify()`, `acquire_lock()`, `release_lock()`, due eccezioni (`IdentityMismatch`, `LockBusy`). Nessun import di `nexus_local_worker` (evita import circolare) — puro, stateless salvo il lock su filesystem.
- **`LocalBridge/nexus_terminal_profiles.config.example.json`** (nuovo) — registro versionato (`schema_version: 1`) dei due profili `LIVE_TERMINAL`/`TESTER_TERMINAL`, con i path reali già documentati in `docs/MT5_TERMINAL_ISOLATION_POLICY_V1.md` (`C:\Program Files\MetaTrader 5`, `C:\MT5-Tester`). Un `nexus_terminal_profiles.config.json` reale (se mai creato) è già gitignored dal pattern esistente `LocalBridge/*.config.json`.
- **`LocalBridge/nexus_local_worker.py`** (modificato, diff minimo): nuovo campo `terminal_role` in `CONFIG_TEMPLATE`; un import; wiring nel dispatch loop (~15 righe, wrappa la chiamata esistente all'handler in un blocco che verifica identità+lock prima e rilascia il lock in un `finally`). **Nessun handler esistente modificato.**
- **`LocalBridge/nexus_worker.config.example.json`** (modificato): aggiunto `terminal_role` come campo documentato.
- **`server/tests/test_mt5_terminal_identity_guard_v1.py`** (nuovo) — 15 test, tutti verdi.

## Test eseguiti

```
20 passed in 1.69s  (test_mt5_terminal_identity_guard_v1.py, --basetemp dedicata, dopo revisione del lock)
```

Coperti esplicitamente: live profile corretto, tester profile corretto, terminal path mismatch, data-dir mismatch, operation not allowed (sia da `forbidden_operations` sia da allowlist), `terminal_role` mancante/invalido (fail-closed), concurrent lock rejection, lock rilasciato correttamente permette un nuovo acquire, **stale lock recovery con processo morto** (reclaim immediato indipendentemente dall'età), **lock di un processo ANCORA VIVO ma "vecchio" (oltre `STALE_LOCK_SEC` ma sotto `HARD_STALE_LOCK_SEC`) NON viene scippato** (`LockBusy`, lock originale intatto — il punto esplicitamente richiesto in review), **valvola di sicurezza `HARD_STALE_LOCK_SEC`** (anche un processo vivo perde il lock oltre 900s, altrimenti un processo bloccato per sempre lo terrebbe per sempre), 3 test diretti su `_pid_is_alive()`, release idempotente, registro profili mancante (fail-closed).

**Regressione sulla suite esistente:** intera suite `server/tests/` eseguita in background (185.75s, supera il timeout di foreground di questo ambiente) — **835 passed, 1 skipped, 2 failed**. I 2 fallimenti (`test_contextual_edge_phase1_foundation.py::test_preregistration_hash_and_diagnostic_outcome_blindness`, `::test_execution_result_preserves_frozen_family_and_no_promotion`) sono nel modulo MACD Phase 1 di Codex (`server/research_scripts/contextual_edge_phase1/`), **confermato senza alcun riferimento** a `LocalBridge`/`terminal_role`/`terminal_identity` (grep esplicito eseguito) — preesistenti e scollegati da questo lavoro, non causati da questa modifica. `test_command_contract.py` (che referenzia esplicitamente `LocalBridge/nexus_local_worker.py`) è incluso nei 835 passati.

**Non eseguito, limite dichiarato:** nessun test contro un vero terminale MT5 (nessun MetaEditor/Strategy Tester disponibile in questo ambiente) — i test sono unit test puri su path finti, non un test end-to-end del worker reale.

## Decisioni di design e perché

- **Fail-closed per-comando, non all'avvio del worker.** `terminal_role` mancante/invalido fa fallire ogni singolo comando (`IdentityMismatch` → `PermanentCommandError` → `FAILED_FINAL`, stesso meccanismo già esistente), ma non termina il processo worker come fa `load_config()` per `backend_url`/`bridge_token`/`host_id`. Scelta deliberata: un worker già in esecuzione su una macchina reale senza questo campo configurato continuerebbe a battere heartbeat e rispondere, ma rifiuterebbe ogni azione con un errore chiaro — più diagnosticabile di un crash immediato all'avvio, e non costringe a un riavvio sincronizzato con la configurazione.
- **`compile_ea` vietato per `LIVE_TERMINAL`** (unica regola asimmetrica tra i due ruoli nei profili di esempio) — motivato direttamente dall'incidente reale già documentato (MetaEditor risolve gli include dal terminale sbagliato). Tutte le altre operazioni sono permesse su entrambi i ruoli nel profilo di esempio; l'enforcement reale è "il path/data-dir deve corrispondere al ruolo dichiarato", non una lista arbitraria di restrizioni per ruolo.
- **Lock per-ruolo, non per-host.** Due worker configurati con ruoli diversi sulla stessa macchina non si bloccano a vicenda — solo due operazioni sullo stesso ruolo.
- **Lock safety a due livelli, non un semplice TTL** (punto aggiunto in review, prima della chiusura): il reclaim di un lock stale NON si basa solo sull'età. Prima si verifica se il processo che lo detiene (`pid` registrato) è ancora vivo (`tasklist /FI "PID eq <pid>"` su Windows, `os.kill(pid, 0)` altrove — in caso di incertezza il default è "vivo", cioè conservativo, mai aggressivo). Se il processo è morto → reclaim immediato, indipendentemente dall'età. Se il processo è **vivo**, il lock non viene mai scippato solo perché "vecchio" — serve superare `HARD_STALE_LOCK_SEC` (900s, soglia distinta e molto più alta di `STALE_LOCK_SEC`=180s) come valvola di sicurezza esplicita contro un deadlock permanente, loggata ad alta visibilità (`print` dedicato), non silenziosa. Il lock registra anche `job_id` (il `command_id` reale del comando, non solo il tipo di azione) per diagnosticare esattamente quale comando lo detiene.
- **Fingerprint path/config-based, esplicitamente NON un'attestazione crittografica del binario/terminale** — limite rafforzato in review: il docstring del modulo ora dice esplicitamente "verifica che il worker punti alla directory attesa per questo ruolo, NON che questo sia esattamente il binario/istanza di terminale attesa" — nessun claim di attestazione crittografica in nessun log/doc/messaggio di errore. Un mismatch di path/profilo resta comunque fail-closed (`IdentityMismatch`, non ritentabile) indipendentemente da questo limite — il limite riguarda cosa significa "verificato", non se un mismatch viene bloccato.

## Limiti residui (dichiarati, non implementati qui)

- Il lock protegge da **comandi concorrenti dello stesso worker/processo** (es. due istanze del worker avviate per errore) — **non** da un operatore umano che apre MetaEditor/Strategy Tester manualmente in parallelo mentre il worker lavora. Nessun meccanismo di questo tipo esiste né è stato costruito qui.
- Nessuna verifica che il terminale sia effettivamente **in esecuzione** con le credenziali/account attesi (account/broker mismatch) — il guard verifica solo path/data-dir configurati, non lo stato runtime del terminale.
- `RESEARCH_TERMINAL` resta fuori scope (coerente con la policy — non esiste oggi).
- Nessun `handle_run_tester` creato — questo guard rende *sicuro* un futuro comando di questo tipo quando verrà costruito (richiederebbe solo aggiungerlo a `HANDLERS` e al profilo giusto), non lo implementa.
- Il profilo di esempio ha `pinned_terminal_id: null` per entrambi i ruoli — il pin esatto è un'opzione lasciata a chi gestisce la macchina reale, non popolata qui (nessun dato macchina-specifico reale disponibile/da inventare in questo ambiente).

---

MT5_TERMINAL_IDENTITY_GUARD_V1_READY_FOR_REVIEW
