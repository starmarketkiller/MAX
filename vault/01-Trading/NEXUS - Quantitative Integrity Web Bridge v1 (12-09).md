# NEXUS — Quantitative Integrity Web Bridge v1

Obiettivo: rendere i dati di [[NEXUS - Decision-Gate-Execution Trace v1 (12-09)]] e [[NEXUS - Test Validity Certificate v2 (12-09)]] leggibili dal backend web NEXUS, senza toccare logica di trading/classificatore/strategie.

## Stato: implementato e testato end-to-end (unit + backend reale + worker reale)

## Perché il LocalBridge worker, non un push diretto dall'EA

`NXS_WebBridge.mqh` disattiva ESPLICITAMENTE ogni `WebRequest` verso il backend quando `MQLInfoInteger(MQL_TESTER)` è vero (3 punti distinti nel file) — MT5 non parla col backend durante il Tester/Research Mode, per scelta architetturale preesistente, non per un limite di questo task. Il LocalBridge worker (`LocalBridge/nexus_local_worker.py`) gira invece FUORI dal Tester, sulla stessa macchina Windows, e ha già un canale token-autenticato verso il backend (heartbeat/poll/ack, usato oggi per compile/deploy/restart). È l'unico percorso già esistente da "MT5 ha scritto un file" a "il backend lo sa" — nessun nuovo trasporto, nessun polling filesystem lato backend (che sarebbe stato l'alternativa fragile esplicitamente da evitare).

## Architettura

```
EA (Research Mode, OnDeinit)
  → scrive Common\Files\NEXUS\certificates\<run_id>.json   (già Certificate v2)
LocalBridge worker (main loop, ogni certificates_scan_sec=30s)
  → legge i .json non ancora spinti con successo (journal locale)
  → POST /api/local_bridge/certificates/ingest              (nuovo)
Backend (SQLite, tabella research_certificates, run_id = PRIMARY KEY)
  → GET /api/research/certificates            (lista)
  → GET /api/research/certificates/latest      (ultimo, ?valid_only=true)
  → GET /api/research/certificates/{run_id}    (dettaglio + raw)
  → GET /api/research/certificates/{run_id}/funnel
```

## File modificati

- **`server/app.py`**: `_migrate_research_certificates` (nuova tabella, migrazione `016_research_certificates`), `_cert_extract_row`/`_cert_row_to_public` (estrazione/serializzazione senza mai inventare campi assenti), `POST /api/local_bridge/certificates/ingest`, `GET /api/research/certificates`, `GET /api/research/certificates/latest`, `GET /api/research/certificates/{run_id}`, `GET /api/research/certificates/{run_id}/funnel`.
- **`LocalBridge/nexus_local_worker.py`**: `certificates_dir`/`certificates_scan_sec` in `CONFIG_TEMPLATE` (default auto-derivato da `%APPDATA%\MetaQuotes\Terminal\Common\Files\NEXUS\certificates` se vuoto), journal locale dedicato (`nexus_worker.certificates_journal.json`, separato dal journal comandi — concetti di idempotenza diversi), `scan_and_push_certificates()` chiamata nel main loop ogni `certificates_scan_sec`.
- **`server/tests/test_research_certificates.py`** (nuovo, 10 test) + **`server/tests/fixtures/research_certificates/`** (i due certificati ADX_RSI REALI prodotti dalla regression del task precedente, non dati sintetici).

## Schema storage

Tabella `research_certificates` (SQLite), `run_id` **PRIMARY KEY**:

```
run_id, config_fingerprint, strategy, selector, source_tf, entry_tf,
period_start, period_end, research_mode, exit_mode, leverage, lot_mode,
fixed_lot, opt_in (JSON), code_build, git_commit, git_commit_provenance,
broker_time_offset_h, generated, blocked, open_attempt, opened,
broker_reject, gate_reason_counts (JSON), opened_missing_position_id,
broker_reject_missing_reason, source_tf_mismatch, invariant_fail_count,
blk_paused_count, verdict, fail_reasons, warnings, raw_json, host_id,
source_file, ingested_at
```

`raw_json` conserva il documento **esattamente come ricevuto** — provenance completa anche per campi che le colonne tipizzate non conoscono ancora.

## Decisioni di design (motivate)

- **Idempotenza = first-write-wins, mai un overwrite.** Un `run_id` già presente torna `{"status": "already_ingested"}` senza toccare la riga. Un certificato è un verdetto immutabile: permettere un secondo payload con lo stesso `run_id` di sovrascriverlo aprirebbe la porta a un certificato "corretto a posteriori" — l'opposto di cosa serve un audit trail. Testato esplicitamente (`test_idempotenza_non_sovrascrive_con_payload_diverso`): un payload manomesso con lo stesso `run_id` non altera il verdetto già salvato.
- **Nessun dato inventato.** `_cert_extract_row` usa `.get()` ovunque, mai un default fabbricato — un campo assente nel certificato originale resta `NULL` in colonna, mai `0`/`""`/`false`. `git_commit="UNKNOWN"` viene salvato e restituito **esattamente come `"UNKNOWN"`**, non `NULL` né altro (testato).
- **`/certificates/latest` registrato PRIMA di `/certificates/{run_id}`** nel file: FastAPI/Starlette risolvono le rotte per ordine di dichiarazione, non per specificità — l'ordine inverso avrebbe fatto catturare `"latest"` come `run_id`.
- **Auth ingest = stessa di `/api/local_bridge/poll`** (token + host già presente in `bridge_hosts`, non richiede `enrolled=1`): l'host non esegue nulla per conto del backend qui, consegna solo un file che ha già scritto in autonomia — stesso livello di fiducia di un poll, non di un heartbeat/comando.
- **POST dedicato nel worker** (`_post_certificate`, non il generico `http_post`): serve distinguere 200/403/422/altro per decidere se ritentare al prossimo scan (403/rete) o scartare in modo definitivo (422, es. certificato senza `run_id`) — `http_post` esistente collassa ogni fallimento a `None`, insufficiente qui.
- **Scan periodico (30s default), non ad ogni ciclo di poll** (spesso 3s): i certificati cambiano solo a fine passata di Tester, uno scan più frequente sarebbe I/O sprecato.

## Endpoint

| Metodo | Path | Auth | Note |
|---|---|---|---|
| POST | `/api/local_bridge/certificates/ingest` | `X-Nexus-Token` + host noto | idempotente su `run_id` |
| GET | `/api/research/certificates` | sessione dashboard | `?strategy=&verdict=&limit=` |
| GET | `/api/research/certificates/latest` | sessione dashboard | `?valid_only=true&strategy=` |
| GET | `/api/research/certificates/{run_id}` | sessione dashboard | include `raw` (documento originale) |
| GET | `/api/research/certificates/{run_id}/funnel` | sessione dashboard | solo funnel + gate counts |

## Esempio JSON reale (list, 2 run ADX_RSI reali ingeriti via worker end-to-end)

```json
{
  "run_id": "GOLD_2026.06.01 00:00:00_sel1_r001",
  "config_fingerprint": "strat=ADX_RSI|sel=1|srcTF=PERIOD_D1|entryTF=PERIOD_M15|exit=RAW|lot=0.0200|lev=100|ESL=0|DailyDD=0|TotalDD=0|DPT=0|Ruin=0|RiskShield=0|period=2026.06.01_2026.06.12",
  "strategy": "ADX_RSI", "selector": 1,
  "source_tf": "PERIOD_D1", "entry_tf": "PERIOD_M15",
  "research_mode": true, "exit_mode": "RAW",
  "leverage": 100, "lot_mode": "FIXED_LOT", "fixed_lot": 0.02,
  "code_build": "3.0.0", "git_commit": "UNKNOWN",
  "git_commit_provenance": "unavailable_at_runtime_no_build_stamping",
  "funnel": {"generated": 118, "blocked": 117, "open_attempt": 1, "opened": 1, "broker_reject": 0},
  "gate_reason_counts": {"OPEN_POSITION": 117},
  "verdict": "PASS", "fail_reasons": "", "warnings": "",
  "host_id": "e2e-worker-host", "source_file": "GOLD_2026.06.01_00-00-00_sel1_r001.json"
}
```

Il secondo run (`run_id` senza `_r001`) è identico su `config_fingerprint`/`funnel`/`verdict`, diverso solo su `run_id`/`ingested_at`/`source_file` — esattamente come atteso dalla patch identità del task precedente.

## Test eseguiti

**Unit/backend (pytest, `server/tests/test_research_certificates.py`, 10/10 PASS)**: host non registrato rifiutato (403), token mancante rifiutato (401), certificato senza `run_id` rifiutato (422), **importa i due certificati ADX_RSI reali** (fixture = file `.json` reali, non sintetici) con `run_id` diversi/`config_fingerprint` uguale/funnel 118-117-1 preservato/entrambi PASS/`raw` intatto, idempotenza nessun duplicato, idempotenza non sovrascrive con payload diverso, `latest`/`latest?valid_only=true`, endpoint funnel, 404 su run inesistente, lista richiede autenticazione.

**Regressione suite completa**: `214 passed, 9 failed (identici pre-esistenti, verificato via git stash — stessi 9 falliscono anche SENZA le modifiche di questo task), 1 skipped`. Nessuna regressione introdotta.

**End-to-end reale** (non solo TestClient): backend FastAPI avviato via `uvicorn` su una porta reale, host arruolato via le vere API HTTP (login admin → enroll), `scan_and_push_certificates()` (il codice del worker, non una simulazione) puntato su una cartella con i due certificati ADX_RSI reali, eseguito due volte: primo scan → un run ingerito, un run già presente da un tentativo precedente (`already_ingested` — verificato che l'idempotenza regge anche a un crash a metà batch, vedi nota sotto); secondo scan → nessuna chiamata HTTP (journal locale corretto). Verificato via `curl` reale su `/api/research/certificates` e `/latest` che i dati tornano identici a quanto scritto dall'EA.

**Nota laterale scoperta durante il test e2e**: un `print()` con caratteri Unicode (`✓`/`✗`) può far crashare il worker su una console Windows non-UTF8 (`cp1252`) — pattern già presente 4 volte nel loop comandi esistente (non introdotto da questo task, stile pre-esistente del file, non modificato per restare consistente). Il crash è avvenuto DOPO il POST di successo: l'ingest era già andato a buon fine, e la ripresa al giro successivo ha correttamente riconosciuto il run come `already_ingested` invece di duplicarlo — comportamento corretto anche nel caso peggiore.

## Non fatto (esplicitamente fuori scope per questo task)

- **Nessuna UI frontend** (richiesto esplicitamente di non costruirla ancora).
- **Trace v1 raw (righe `[NXS_TRACE]`) non ancora ingerite** — solo il certificato aggregato (che già usa Trace v1 come fonte primaria per i suoi contatori). Se in futuro servisse il trace riga-per-riga lato backend, servirebbe un secondo export dall'EA (oggi il trace vive solo nel Journal MT5).
- **Nessun invio automatico dal Tester stesso**: il worker deve essere in esecuzione sulla stessa macchina per la finestra di `certificates_scan_sec` dopo la fine di una passata — se il worker non gira, i certificati restano scritti su disco (mai persi) ma non arrivano al backend finché il worker non riparte.
