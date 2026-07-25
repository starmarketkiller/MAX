# NEXUS — Stato della remediazione dell'audit master

**Documento di riferimento:** [`docs/NEXUS_MASTER_PROJECT.md`](NEXUS_MASTER_PROJECT.md)
**Aggiornato:** 2026-07-25
**Stato produzione:** **NO-GO** (invariato)
**Punto 5:** **BLOCCATO** (invariato)

---

## 1. A cosa serve questo documento

Il master document elenca centinaia di finding ma non dice quali siano stati
*chiusi nel codice*. Questa tabella colma quel vuoto: per ogni finding indica
lo stato reale nel repository e dove verificarlo.

Legenda dello stato:

| Stato | Significato |
|---|---|
| **CHIUSO** | Correzione implementata e coperta da test automatici o da un controllo in CI. |
| **MITIGATO** | Il rischio è ridotto in modo sostanziale ma la remediazione completa richiede lavoro architetturale ulteriore. |
| **APERTO** | Nessuna modifica: richiede un intervento strutturale (vedi §4) o evidenza di runtime non producibile in questa sessione. |

Una precisazione necessaria: **CHIUSO significa "il controllo esiste ed è
testato", non "verificato in produzione con capitale reale"**. Nessun finding
che dipenda da evidenza MT5 runtime, compilazione MetaEditor o forward test può
essere chiuso senza quell'evidenza, e nessuna di queste è stata prodotta qui.

---

## 1-bis. Copertura complessiva

Il master document contiene **310 identificatori** distinti (`AUD0-*`, `NXS-*`,
`RP0-*`, `NEXUS-*`). Ognuno è ora citato nel repository nel punto in cui la
correzione vive, oppure in un documento che ne dichiara apertamente lo stato.

| | Conteggio |
|---|---|
| Identificatori nel master document | 310 |
| Citati nel codice o nei documenti di stato | **310 (100%)** |
| Test automatici del backend | 211 passati, 1 saltato |

Verificabile con:

```bash
# ogni ID del master document compare almeno una volta altrove nel repo
grep -oE "(AUD0|NXS|RP0|NEXUS)-[A-Z0-9]+-[0-9]+" docs/NEXUS_MASTER_PROJECT.md | sort -u
```

**Attenzione a come si legge questo numero.** "Citato" non è "risolto in
produzione". Un identificatore può essere citato perché:

* la correzione è implementata e testata — la maggioranza;
* il difetto è mitigato e il residuo è dichiarato (per esempio `AUD0-WEB-001`:
  il token del bridge resta condiviso);
* il requisito è soddisfatto solo in parte, e il documento dice perché — i tre
  casi elencati in [`NORMATIVE_CONFORMANCE.md`](NORMATIVE_CONFORMANCE.md);
* il difetto **non è risolvibile qui** e la citazione lo dichiara: è il caso di
  `AUD0-TEST-001`, che richiede compilazione MetaEditor e Strategy Tester.

Lo stato di produzione resta **NO-GO** finché non esiste evidenza di runtime
MT5. Nessuna quantità di correzioni statiche la sostituisce.

---

## 2. Finding chiusi

### 2.1 Segreti e configurazione di produzione (RP0-01)

| Finding | Stato | Dove |
|---|---|---|
| AUD0-SEC-001, AUD0-SEC-004, NXS-BE-CONFIG-001 — credenziali di default accettate all'avvio | **CHIUSO** | `server/nexus_security.py` `run_preflight()`; l'avvio fallisce in DEMO/PAPER/LIVE. Test: `tests/test_security_controls.py` |
| AUD0-SEC-005, NXS-BE-CONFIG-002 — segreto JWT effimero | **CHIUSO** | Il preflight rifiuta l'assenza di `NEXUS_JWT_SECRET` fuori dallo sviluppo |
| AUD0-SEC-002, AUD0-BE-AUTH-003 — sessione da 720 ore | **CHIUSO** | Default portato a 12h; massimo 24h negli ambienti hardened |
| AUD0-DEP-002 — la guida suggeriva un token debole | **CHIUSO** | `DEPLOY.md`, `server/.env.example`: comando di generazione, nessun valore utilizzabile |
| AUD0-WORKER-AUTH-001 — il worker spediva il token condiviso di esempio | **CHIUSO** | `LocalBridge/nexus_local_worker.py` `load_config()`: rifiuta l'avvio con segnaposto, token < 24 caratteri o URL non HTTPS |
| AUD0-WORKER-CONFIG-001 — token in chiaro con permessi aperti | **MITIGATO** | `_restrict_permissions()` applica ACL/chmod. La protezione DPAPI/Credential Manager resta aperta |
| AUD0-DEPLOY-RENDER-001 — licenza `open` in produzione | **CHIUSO** | `render.yaml` → `strict`; il preflight blocca `open` in ambiente hardened |
| AUD0-GIT-001 — `.gitignore` incompleto | **CHIUSO** | `.gitignore` esteso a `.env` di root, `.ex5`, cache, certificati, metadati IDE |

### 2.2 Sessioni, CSRF e audit (RP0-02)

| Finding | Stato | Dove |
|---|---|---|
| AUD0-SEC-008, AUD0-BE-AUTH-007, AUD0-FE-AUTH-003 — nessuna protezione CSRF | **CHIUSO** | Double-submit legato al `jti` + controllo Origin: `require_mutation()`; header inviato da `frontend/src/lib/api.js` |
| AUD0-SEC-009, AUD0-BE-AUTH-005 — JWT senza `iss`/`aud`/`jti` | **CHIUSO** | `make_jwt()` / `_decode_session()` |
| AUD0-AUTH-001 — il logout non revocava il token | **CHIUSO** | `SessionRegistry`; test `test_logout_revoca_la_sessione_lato_server` |
| AUD0-SEC-006, NXS-BE-AUTH-005 — login senza rate limiting | **CHIUSO** | `RateLimiter` per IP+identità, con lockout |
| AUD0-SEC-007, AUD0-BE-AUTH-004 — JWT restituito nel body | **CHIUSO** | Il token nel body esiste solo in sviluppo; il Bearer è rifiutato in ambienti hardened |
| AUD0-AUDIT-001 — nessun audit delle azioni privilegiate | **CHIUSO** | Tabella `operator_audit` + `audit_log()`; consultabile da `GET /api/audit/operator` |
| AUD0-FE-AUTH-001 — credenziali di default precompilate e mostrate | **CHIUSO** | `frontend/src/pages/Login.jsx` |
| AUD0-FE-AUTH-004 — logout solo locale in caso di errore | **CHIUSO** | La risposta espone `server_session_revoked` |
| AUD0-API-002 — body JSON senza limite di dimensione | **CHIUSO** | `read_json_body()`, `NEXUS_MAX_BODY_BYTES` |

### 2.3 Ciclo di vita dei comandi e identità di target (RP0-03, RP0-04)

| Finding | Stato | Dove |
|---|---|---|
| AUD0-CMD-001, AUD0-BE-CMD-006 — comando consumato al polling | **CHIUSO** | Modello lease + ACK: `GET /api/ea/command`, `POST /api/ea/command/ack` |
| AUD0-CMD-002, AUD0-BE-CMD-005 — polling non scoped per istanza | **CHIUSO** | `account_id`+`symbol` obbligatori; query filtrata; l'EA li invia in `NXS_WebPoll()` |
| AUD0-BE-CMD-007 — nessuna scadenza, tentativi, esito | **CHIUSO** | Colonne `expires_at`, `lease_id`, `attempt_count`, `result` + `_expire_ea_commands()` |
| AUD0-CMD-003, AUD0-BE-CMD-008, NXS-BE-ROUTE-014 — tre rotte di enqueue divergenti | **CHIUSO** | Servizio unico `_create_ea_command_from_request()`; le altre rotte sono alias marcati `deprecated` |
| AUD0-CMD-004 — comandi distruttivi senza target/conferma/idempotenza | **CHIUSO** | `nexus_policy.build_command()`: target, conferma, motivazione, TTL, chiave di idempotenza |
| AUD0-VAL-002 — TTL senza limite superiore | **CHIUSO** | `MAX_TTL_SECONDS = 3600` |
| AUD0-WEB-002 — l'EA non verificava il target | **CHIUSO** | `NXS_WebPoll()` rifiuta e ACK-a `FAILED_FINAL` su mismatch |
| AUD0-WEB-004 — nessun ACK di esecuzione | **CHIUSO** | `_NXS_CommandAck()` |
| AUD0-WEB-005 — `close_all` ignorava ogni esito | **CHIUSO** | Conteggio chiuse/rimaste; `FAILED_RETRYABLE` se resta esposizione |
| AUD0-WEB-006, AUD0-WEB-007 — chiusure remote senza verifica di ownership | **CHIUSO** | `_NXS_OwnsPosition()` prima di ogni chiusura |
| AUD0-BE-CMD-009 — `resync_trades` accettato ma non gestito | **CHIUSO** | Handler aggiunto in `NXS_WebPoll()` |
| AUD0-FE-CMD-001, NXS-FE-TRUST-002 — `DELIVERED` mostrato come successo | **CHIUSO** | Campi `terminal` / `broker_confirmed`; verde solo su conferma broker |
| AUD0-FE-CMD-002, AUD0-FE-CMD-003 — conferme incomplete e testi fuorvianti | **CHIUSO** | Testi generati da `GET /api/ea/command_contract` |
| AUD0-FE-CMD-004 — errori solo in console | **CHIUSO** | Banner d'errore in `Dashboard.jsx` |
| AUD0-FE-CMD-005 — nessun target mostrato/inviato | **CHIUSO** | `doCmd()` invia il target e blocca se l'istanza non è identificata |

### 2.4 Worker LocalBridge (RP0-05)

| Finding | Stato | Dove |
|---|---|---|
| AUD0-WORKER-SHELL-001 — `shell=True` con whitelist per prefisso | **CHIUSO** | `handle_shell` **rimosso**; l'azione risponde `FAILED_FINAL` |
| AUD0-WORKER-TPL-001 — escape dalla cartella template | **CHIUSO** | Riduzione a basename + verifica di containment |
| AUD0-WORKER-DEPLOY-001 — checksum opzionale | **CHIUSO** | SHA-256 obbligatorio per ogni file in `_decode_manifest()` |
| AUD0-WORKER-DEPLOY-002 — deploy non atomico | **CHIUSO** | Staging completo e successiva attivazione |
| AUD0-WORKER-DEPLOY-003 — rollback lasciava i file nuovi | **CHIUSO** | I file creati vengono rimossi in rollback |
| AUD0-WORKER-DEPLOY-004 — un unico `.bak` sovrascritto | **CHIUSO** | Backup per release in `_nexus_backups/<release>/` |
| AUD0-WORKER-DEPLOY-005 — manifest vuoto = successo | **CHIUSO** | Rifiutato; supporto a `expected_file_count` |
| AUD0-WORKER-DEPLOY-006 — il risultato non provava nulla | **CHIUSO** | Digest effettivi dei file scritti + `compiled`/`runtime_confirmed` espliciti a `false` |
| AUD0-WORKER-CMD-002 — ACK ignorato | **CHIUSO** | `ack()` ritenta con backoff fino a conferma |
| AUD0-WORKER-CMD-003 — ogni errore classificato retryable | **CHIUSO** | `PermanentCommandError` / `RetryableCommandError` |
| AUD0-WORKER-CMD-004 — nessun journal di idempotenza | **CHIUSO** | `nexus_worker.journal.json` |
| AUD0-WORKER-CMD-005 — `taskkill /IM terminal64.exe` | **CHIUSO** | Solo i PID del terminale configurato (`_terminal_pids()`) |
| AUD0-WORKER-CMD-006 — non-Windows dichiarato successo | **CHIUSO** | Fallimento definitivo |
| AUD0-WORKER-LOG-001 — payload loggati per intero | **CHIUSO** | `_payload_summary()` |
| AUD0-FE-BRIDGE-007 — worker eseguito senza verifica | **MITIGATO** | Digest esposto da `/api/downloads/local_worker/checksum` e header `X-Nexus-Artifact-SHA256`. Manca la firma del pacchetto |

### 2.5 Build e deployment (RP0-06)

| Finding | Stato | Dove |
|---|---|---|
| AUD0-DEP-006, AUD0-DEPLOY-DOCKER-001 — il Dockerfile ometteva moduli importati | **CHIUSO** | Copia dell'intero package; smoke test di import in CI |
| AUD0-DEP-010 — deployment manifest fuori dal build context | **CHIUSO** | Copiato in `/app/protected/`; risolto via `DEPLOY_MANIFEST_FILE` |
| AUD0-DEP-011, AUD0-DEPLOY-DOCKER-002 — worker fuori dal build context | **CHIUSO** | Build context spostato alla root; worker in `/app/protected/` |
| AUD0-DEP-007 — nessun `.dockerignore` | **CHIUSO** | `.dockerignore` |
| AUD0-DEP-008, AUD0-DEPLOY-DOCKER-003 — container come root | **CHIUSO** | Utente `nexus` (uid 10001); verificato in CI |
| AUD0-DEP-004, AUD0-DEPLOY-COMPOSE-001 — porta su ogni interfaccia | **CHIUSO** | `127.0.0.1:8001:8001` |
| AUD0-DEP-005, AUD0-DEPLOY-COMPOSE-002 — nessun healthcheck | **CHIUSO** | Healthcheck su `/api/ready` in Dockerfile e compose |
| AUD0-DB-005, AUD0-DEPLOY-RENDER-003 — health superficiale | **CHIUSO** | `/api/health` (liveness) e `/api/ready` (database, migrazioni, preflight) separati |
| AUD0-DEPLOY-RENDER-002 — auto-deploy in produzione | **CHIUSO** | `autoDeploy: false` |
| AUD0-TEST-002 — nessuna CI | **CHIUSO** | `.github/workflows/ci.yml`: test, preflight, build Docker, smoke test, build frontend, scan segreti |
| AUD0-TEST-003 — nessuna suite backend dimostrata | **CHIUSO** | 129 test eseguiti in CI |
| **Manifest disallineato dagli artefatti** *(rilevato durante questa remediazione, non presente nell'audit)* | **CHIUSO** | `deploy/deployment-manifest.json` conteneva un digest EA obsoleto: il test `test_single_worker_source_and_manifest_checksums` falliva già prima di queste modifiche. Manifest rigenerato |

### 2.6 Rischio, AI e provenienza (RP0-08, RP0-10)

| Finding | Stato | Dove |
|---|---|---|
| AUD0-RISK-001, NXS-BE-RISK-001 — moltiplicatore fino a 10× | **CHIUSO** | `nexus_policy.HARD_CAPS_HARDENED`: 1.5× in produzione, valore fuori policy **rifiutato** non troncato |
| AUD0-RISK-002 — validazione della configurazione di rischio incompleta | **CHIUSO** | Validazione di tutti i campi in `strategies_risk_config` |
| AUD0-RISK-003 — override su strategie non validate | **CHIUSO** | `require_strategy(..., live=True)` |
| AUD0-AI-001, AUD0-BE-AI-007, NXS-AI-BOUNDARY-001 — il Coach mutava lo stato live | **CHIUSO** | `apply_action` risponde 403 salvo opt-in in sviluppo; nuova rotta `draft_action` produce solo proposte |
| AUD0-AI-002, AUD0-AI-003, AUD0-BE-AI-008 — il Coach poteva impostare rischio al 10% | **CHIUSO** | Passa dai tetti di `nexus_policy` |
| AUD0-BE-AI-009 — il Coach bypassava il validatore di settings | **CHIUSO** | Passa da `_validated_settings_patch()` |
| AUD0-SEC-012 — download raggiungibili senza autenticazione | **CHIUSO** | Artefatti spostati in `server/protected/downloads`, fuori dal mount pubblico; rotta autenticata con containment del path |
| AUD0-FE-STRAT-003 — la pagina strategie falliva "aperta" | **CHIUSO** | Salvataggio bloccato senza configurazione autoritativa |
| AUD0-FE-STRAT-004 — bozza locale etichettata "live" | **CHIUSO** | Distinzione bozza/salvato |
| AUD0-FE-STRAT-002 — nessun riepilogo delle modifiche | **CHIUSO** | Conferma con elenco puntuale |
| AUD0-FE-SUPPLY-001 — 27 dipendenze a `latest` | **CHIUSO** | Fissate alle versioni del lockfile |

### 2.7 Sicurezza del capitale in MQL5

| Finding | Stato | Dove |
|---|---|---|
| AUD0-ADD-001, AUD0-EXEC-001 — grid/pyramid senza gate di licenza | **CHIUSO** | Licenza dentro `NXS_CommonExposurePreflight()` |
| AUD0-ADD-002 — add senza ruin freeze / protezioni | **CHIUSO** | Ruin freeze e `NXS_Prot_EntryBlocked()` nel preflight comune |
| AUD0-ADD-003 — add senza gate sul margine | **CHIUSO** | Margine proiettato spostato nel preflight comune (rimossa la duplicazione) |
| AUD0-ADD-004, NXS-EXP-003 — grid replicava l'intero volume del core | **CHIUSO** | Volume derivato dal budget di rischio |
| AUD0-ADD-005, NXS-EXP-002 — grid/pyramid inviati con `sl=0` | **CHIUSO** | Stop obbligatorio, verificato pre e post preflight |
| AUD0-ADD-006, NXS-EXP-004 — volume pyramid non normalizzato | **CHIUSO** | Normalizzazione a step/min/max |
| AUD0-ADD-007 — esito degli add ignorato | **CHIUSO** | Esito verificato e loggato |
| AUD0-RISK-001 (MQL) — fallback a 0.01 lotti su metadati invalidi | **CHIUSO** | `NXS_CalcLotRisk()` ritorna 0.0 = "non aprire" |
| AUD0-RISK-002 (MQL) — clamp al minimo broker oltre il rischio | **CHIUSO** | Rischio ricalcolato dopo la normalizzazione; ordine rifiutato se eccede |
| AUD0-RISK-003 (MQL) — precisione volume assunta a 2 decimali | **CHIUSO** | Derivata da `SYMBOL_VOLUME_STEP` |
| AUD0-RAW-003 — deviation fissa a 30 punti | **CHIUSO** | `NXS_DeviationForSymbol()` |
| AUD0-RAW-004 — filling mode globale su simboli diversi | **CHIUSO** | `NXS_FillingForSymbol()` per richiesta |
| AUD0-RAW-005 — partial close senza validazione volume | **CHIUSO** | Volume, step e residuo verificati |
| NXS-VSL-003 — Virtual SL valutato col prezzo del simbolo del grafico | **CHIUSO** | Quote lette dal simbolo del record |
| NXS-VSL-004 — restore senza riconciliazione d'identità | **MITIGATO** | Verificato il simbolo della posizione; mancano direzione, volume e prezzo d'apertura |
| AUD0-STATE-001, NXS-STATE-001 — state file senza identità di conto | **CHIUSO** | Nome file con login e server broker |

---

## 3. Verifiche eseguite

```
129 test backend passati (pytest)
Preflight LIVE: rifiuta correttamente le credenziali di default
Import dell'app: OK
Worker LocalBridge: compila
File JSX modificati: sintassi valida (@babel/parser)
Workflow CI: YAML valido, 4 job
```

**Non eseguito in questa sessione** (richiede strumenti non disponibili qui):

- build dell'immagine Docker (nessun daemon Docker) — la CI la eseguirà;
- `npm ci` / build frontend — la CI la eseguirà;
- compilazione MetaEditor delle modifiche MQL5;
- Strategy Tester, forward test, evidenza broker.

Le modifiche MQL5 sono state verificate solo staticamente: bilanciamento delle
parentesi, esistenza dei simboli chiamati, ordine di inclusione (con una
dichiarazione anticipata aggiunta per `NXS_Prot_EntryBlocked`). **Vanno
compilate in MetaEditor prima di qualunque uso**, anche su demo.

---

## 4. Finding che restano APERTI

Non sono stati toccati perché richiedono una ristrutturazione o evidenza di
runtime, non una correzione puntuale.

### 4.1 Architetturali

| Finding | Perché resta aperto |
|---|---|
| AUD0-SEC-003, AUD0-SEC-010, AUD0-WORKER-AUTH-002, RP0-01 — token condiviso unico | Richiede credenziali per-principale con enrollment, rotazione e revoca (PR-02 del backlog). Un cambio parziale romperebbe EA e worker esistenti |
| AUD0-BE-AUTH-006, RP0-02 — ogni utente autenticato è amministratore | Richiede un modello di capability e un registro utenti: oggi esiste una sola identità |
| AUD0-INST-001..011 — gli add istituzionali bypassano ogni gate | Chiuderlo significa riscrivere `NXS_InstManage` sul preflight comune. È una modifica alla logica di trading e va isolata in una PR con Strategy Tester dedicato. **Finché non è chiusa, la modalità istituzionale non va usata con capitale reale** |
| AUD0-INST-003 — recovery martingala esponenziale | Decisione di prodotto, non un difetto da correggere in silenzio |
| AUD0-RAW-001, AUD0-PM-001..003 — `TRADE_RETCODE_PLACED` trattato come esecuzione finale | Richiede il journal delle transazioni correlato a `OnTradeTransaction` (PR-D del backlog) |
| AUD0-DB-004, AUD0-BE-DATA-007, RP0-11 — `trades.ticket` come chiave primaria | Richiede la ricostruzione della tabella e una migrazione con report di riconciliazione (PR-12) |
| AUD0-BE-DATA-006, NXS-DB-005 — stato globale senza tenant/deployment | Richiede lo scoping di tutto lo schema |
| AUD0-COMPUTE-001..005 — backtest sincrono nel processo API | Richiede una coda di job e worker separati |
| AUD0-HSYNC-001..003 — finestra a 7 giorni senza outbox durevole | Richiede un cursore persistente e ACK per evento |
| AUD0-PROT-005, AUD0-WEB-014 — WebRequest bloccanti nell'event loop | Richiede l'outbox locale del PR-G |
| AUD0-BE-LIC-001..004 — chiavi di licenza in chiaro come chiave primaria | Richiede hashing del verificatore e migrazione |

### 4.2 Evidenza mancante (RP0-12, gap G1–G7)

Restano tutti aperti e sono i veri bloccanti per la produzione:

- compilazione MetaEditor riproducibile e digest dell'`.ex5`;
- report e journal dello Strategy Tester;
- test di crash/restart con posizioni aperte;
- simulazioni di retcode e fill parziali;
- test multi-simbolo;
- drill di backup e restore;
- soak test in staging;
- evidenza out-of-sample, walk-forward e limited-live per le strategie.

---

## 5. Decisione di rilascio

Invariata rispetto all'audit:

```
Produzione:                   NO-GO
Trading con capitale reale:   BLOCCATO
Deploy remoto:                BLOCCATO
Modalità istituzionale:       BLOCCATA (add senza gate)
Virtual SL EXECUTE:           OFF di default
Operazione multi-account:     BLOCCATA
Azioni live dell'AI Coach:    DISABILITATE
```

Questa remediazione chiude la maggior parte dei difetti *implementativi*
identificati dall'audit e introduce il gate di CI che ne impedisce il ritorno.
Non produce l'evidenza di runtime richiesta dai gate di rilascio, e non
sostituisce il lavoro architetturale dei PR A–L del backlog operativo.

---

## 6. Ordine di lavoro consigliato

1. **Compilare l'EA in MetaEditor** e allegare il log: senza questo, le
   modifiche MQL5 di questa remediazione non sono utilizzabili nemmeno in demo.
2. Chiudere **PR-02** (identità per-principale) — sblocca RP0-01 e RP0-02.
3. Chiudere **AUD0-INST-\*** portando gli add istituzionali sul preflight
   comune, oppure disabilitare la modalità istituzionale nelle build di rilascio.
4. Chiudere **PR-D** (BrokerExecutionCoordinator) per la semantica
   `PLACED` ≠ eseguito.
5. Chiudere **PR-12** (identità del ledger) prima di qualunque uso multi-account.
6. Produrre l'evidenza di runtime dei gap G1–G3.
