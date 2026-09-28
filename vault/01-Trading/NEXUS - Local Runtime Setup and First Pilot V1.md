# NEXUS - Local Runtime Setup + First NEXUS Pilot V1

**Baseline:** `453f2ff` (Orchestrator V1 Architecture + Environment Discovery, `ORCHESTRATOR_ARCHITECTURE_READY` + `LOCAL_RUNTIME_NEEDS_SETUP`). Nessuna modifica MQL5/logiche di trading. Nessun deploy. Nessuna optimization. Nessun nuovo backtest.

**Obiettivo**: installare/configurare davvero il runtime locale raccomandato nella fase precedente (Ollama + Qwen2.5 3B/7B), misurarlo con benchmark REALI su task rappresentative NEXUS, valutare Hermes Agent come possibile runtime agentic, ed eseguire il PRIMO pilota reale (backfill `temporal_concentration` per BREAKOUT_ACC e ORDER_BLOCK) usando il worker locale — con la regola esplicita: **Claude installa, configura, osserva, verifica; non fa il lavoro scientifico al posto del worker.**

**Correzione dell'utente rispetto alla fase precedente**: la gerarchia raccomandata andava invertita — **Qwen 3B = worker quotidiano di default, Qwen 7B = escalation locale**, non il contrario, su questo hardware specifico. Confermato empiricamente in questa fase (vedi sotto).

---

## A. Runtime — Ollama

Installato via `winget install --id Ollama.Ollama` (nativo Windows, hash installer verificato da winget). Verificato:

| Voce | Valore |
|---|---|
| Versione | `0.34.4` |
| Servizio attivo | Sì (`ollama app.exe` PID 18988, `ollama.exe` PID 26228) |
| Endpoint | `http://127.0.0.1:11434` |
| Esposizione | **Solo localhost** — verificato con `Get-NetTCPConnection -LocalPort 11434`, nessun binding pubblico |
| Auto-start | Sì — collegamento `Ollama.lnk` in Startup folder utente |
| Account/API key/cloud | Nessuno richiesto |

## B. Modelli installati

Solo i due richiesti, nessun altro:

- `qwen2.5:3b-instruct` — 1.9GB, `parameter_size:3.1B`, `quantization_level:Q4_K_M`
- `qwen2.5:7b-instruct` — 4.7GB, `parameter_size:7.6B`, `quantization_level:Q4_K_M`

Entrambi confermati `size_vram:0` (puramente CPU, nessuna accelerazione — coerente con l'hardware, GPU Intel HD 620 senza supporto utile).

## C. Benchmark reale (10 task NEXUS-rappresentative, num_ctx=8192)

Misure prese dai contatori ufficiali di Ollama (`eval_count`/`eval_duration`), non stimate. Script: `server/orchestrator_v1/build_model_benchmark.py`.

| | Qwen2.5 3B | Qwen2.5 7B |
|---|---|---|
| tok/s task brevi (1-9) | 5.76 – 8.93 | 2.97 – 4.75 (~metà del 3B, atteso dal ratio parametri) |
| Wall time task brevi | 1.64s – 21.21s | comparabile, leggermente più lento |
| JSON via `format:"json"` | Affidabile (raw_valid+extracted_valid True) | Affidabile (idem) |
| JSON via prompt grezzo | Meno affidabile (prosa+markdown fence attorno) | Idem |
| Contesto lungo (~4K token, **fresco**, no cache) | **~297s prompt-eval, ~304s totali** (lento ma completa) | **TIMEOUT a 600s, non completa** |
| RAM delta osservato | ~2.1GB | ~2.86GB |

**Nota metodologica importante (auto-scoperta e corretta in questa fase)**: la prima misura di contesto lungo sul 3B, ripetuta con lo STESSO prompt, ha mostrato un tempo artificiosamente basso (0.32s) per via del prompt-prefix caching di Ollama (KV-cache riuso su contenuto già visto) — non rappresentativo di contenuto realmente nuovo. Corretto introducendo un "salt" per forzare contenuto fresco ad ogni misura di contesto lungo; il numero onesto (297s/304s) è quello riportato sopra, recuperato dalla prima esecuzione (il file salvato riporta invece il numero cache-hit, sostituito dalla seconda esecuzione — divergenza documentata esplicitamente, non nascosta).

## D. Contesto pratico

- **Qwen 3B**: 8192 utilizzabile come tetto, ma un contesto di ~4K token **fresco** richiede ~5 minuti a freddo su questa CPU — non pratico per uso frequente/interattivo di contenuti lunghi, accettabile per backfill/batch non presidiati.
- **Qwen 7B**: anche ~4K token freschi **non completano entro 10 minuti** — su questo hardware il 7B va riservato a prompt BREVI (poche centinaia di token), indipendentemente dal context window configurato. La guidance della fase precedente ("8-16K pratico, mai 128K") si conferma per il 3B ma va **rivista al ribasso per il 7B**.

## E. Hermes Agent — valutato, NON installato

Ricerca (non installazione, per evitare di introdurre dipendenze inutili prima di verificarne la compatibilità):

- Requisito dichiarato: **minimo 64K di contesto** per l'uso agentic/tool-use — in conflitto diretto con il tetto pratico di questo hardware (ben sotto gli 8K per il 7B).
- Requisito CPU dichiarato: 4 core fisici raccomandati — questo hardware ne ha 2 fisici.
- Bug di stabilità noto e **non risolto** (issue GitHub #25629): Ollama si blocca indefinitamente con `stream=true` + definizioni di tool, riscontrato anche su hardware nettamente più potente (Ryzen 5 7430U, 64GB RAM) del nostro.
- Supporto Windows nativo vs WSL2: fonti in conflitto, non risolto con certezza.

**Decisione**: non installato. Il solo requisito dei 64K di contesto è sufficiente a squalificarlo per questo hardware, aggravato dal bug di stabilità noto. Usato invece l'endpoint HTTP diretto di Ollama (`/api/generate`, `format:"json"` per output strutturato) — **Hermes ≠ Jarvis ≠ Orchestrator**, resta un runtime sostituibile e qui sostituito dalla via più semplice, esattamente come previsto dal task stesso.

## F. Accesso al repository — verificato

Lettura (`nxs_breakoutacc_dataset_loader.py`, `canonical_economic_dataset_v1.json`, file di riferimento Phase 7.25), scrittura solo in sandbox nuova e dedicata (`server/research_scripts/phase7/phase7_28/`, mai toccata prima), `git diff`/`git status` verificati prima di ogni commit, **nessun push automatico durante il pilota** (rispettato in tutti e 4 i tentativi).

## G. Vault — sola lettura, verificato

Lette (mai scritte) le fonti: dataset BREAKOUT_ACC (phase7_21), dataset canonico ORDER_BLOCK (phase7_22), codice di riferimento per lo stile (phase7_25). Nessuna scrittura nel Vault stesso durante il pilota.

## H/I/J/K. Primo pilota — backfill `temporal_concentration` BREAKOUT_ACC + ORDER_BLOCK

Regola seguita rigorosamente: Claude ha fatto SOLO i passi deterministici (leggere input, costruire il prompt, chiamare il modello, salvare l'output, eseguirlo in sandbox, verificarlo indipendentemente con un calcolo di riferimento scritto separatamente) — **mai** scritto la logica di aggregazione al posto del worker.

| Tentativo | Modello | Esito |
|---|---|---|
| 1 | Qwen 3B | **Timeout 600s** sulla prima chiamata (BREAKOUT_ACC) — verosimilmente congestione residua dal test di contesto lungo appena eseguito sul 7B |
| 2 | Qwen 3B (retry pulito, stesso task, nessuna modifica di scope — 1 retry delimitato per policy) | Completato ma FALLITO: codice generato usa `defaultdict`/funzione `_dt` senza importarli (copiati per stile dal riferimento); ORDER_BLOCK produce una funzione valida ma MAI invocata (nessuna riga di stampa, nonostante richiesta esplicita nel prompt) — un "falso successo silenzioso" più pericoloso di un crash |
| 3 | Qwen 3B (dopo un fix DETERMINISTICO dell'harness — import+invocazione forniti dall'impalcatura, non dal modello, classificato come rimedio ambientale/TIER 0, non lavoro scientifico) | Completato ma ANCORA fallito: nuovo errore diverso (il modello copia letteralmente l'import `nxs_liq_sweep_edge_dataset_loader` dal riferimento, e tratta `entry_time(e)`/`net_pnl(e)` come funzioni invece che chiavi dict) — pattern CONSISTENTE: il modello 3B copia identificatori specifici dal riferimento di stile invece di astrarre al nuovo schema dati esplicitamente fornito |
| 4 | Qwen 7B (escalation locale, per la gerarchia corretta dall'utente) | **Timeout >600s** sulla prima chiamata — Ollama restava comunque responsivo (`/api/version` e `/api/ps` rispondevano normalmente, modello ancora residente in memoria), quindi non un crash totale del servizio, ma una generazione anomalmente lunga/instabile anche su un prompt di dimensione comparabile a task completati in 15-35s durante il benchmark |

**Esito complessivo: FALLITO su tutti e 4 i tentativi**, con 2 modelli, con un fix legittimo dell'harness nel mezzo (mai una correzione della logica del worker). Nessun push automatico eseguito in nessun momento; ogni fallimento preservato in un file `_ATTEMPTN_FAILED_` separato prima del tentativo successivo, per tracciabilità completa.

**Classificazione di escalation** (per la Routing Policy definita nella fase precedente): `COMPLEX_CODE` → questo specifico task va ora assegnato a Claude/Codex, non ritentato una quinta volta in locale.

## Decisione finale

**`LOCAL_WORKER_OPERATIONAL_WITH_LIMITATIONS`**

Runtime e modelli funzionano in modo affidabile per task BREVI (risposta diretta, JSON strutturato via `format:"json"`, riassunto, log analysis, instruction-following, italiano/inglese — tutti completati con successo nel benchmark). Il worker locale è quindi già oggi operativo per il ruolo TIER 1 (LOCAL_FAST). Il ruolo TIER 2 (LOCAL_STRONG, coding) **non ha superato il primo pilota reale** con nessuno dei due modelli — richiede o task di coding più semplici/meglio scaffolded (niente file di riferimento con identificatori specifici del progetto), o l'escalation a Claude/Codex già prevista dall'architettura per questi casi.

## Deliverables

`server/orchestrator_v1/build_model_benchmark.py`, `run_pilot_worker.py`, `build_setup_report.py`, `verify_setup_report.py`, 2 file di benchmark, 3 file di risultato pilota (tutti i tentativi preservati), `local_runtime_setup_report_v1.json`, `server/tests/test_orchestrator_v1_local_runtime_setup.py`, questo vault report. Codice generato dal modello nei 2 tentativi finali preservato in `server/research_scripts/phase7/phase7_28/` come esempio documentato di fallimento (non come artifact scientifico valido).

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`. Nessuna fase Phase 7 tracciata modificata. Nessun modello/cache/segreto/credenziale committato (verificato via `git status` prima dello staging). Nessun deploy. Nessuna optimization. Nessun nuovo backtest. Nessuna installazione di Hermes (valutato, non installato, motivazione documentata).

## Regressione

Suite `server/orchestrator_v1/` + nuovo test file: verificatore `verify_setup_report.py` PASSED (riscontro live con Ollama attivo). 6/6 test nuovi PASSED.

---

```
ORCHESTRATOR V1: LOCAL RUNTIME SETUP + FIRST PILOT - COMPLETATO
(CON LIMITAZIONI DOCUMENTATE, NON NASCOSTE)

CORREZIONE UTENTE APPLICATA: Qwen 3B = default, Qwen 7B = escalation
  locale - confermato empiricamente (7B ~metà tok/s del 3B su task
  brevi, e va in timeout anche su contesto medio dove il 3B almeno
  completa, sia pure lentamente)

OLLAMA: v0.34.4, nativo Windows via winget, solo localhost, auto-start
  configurato, nessun account/cloud

MODELLI: solo qwen2.5:3b-instruct + qwen2.5:7b-instruct (Q4_K_M),
  nessun altro installato

BENCHMARK REALE (contatori ufficiali Ollama, non stimati): 3B 5.76-
  8.93 tok/s task brevi, 7B 2.97-4.75 tok/s (~meta', atteso).
  format:"json" affidabile su entrambi. Contesto lungo fresco (~4K
  token): 3B completa in ~297-304s (lento ma completa), 7B TIMEOUT
  oltre 600s (non completa)

HERMES: valutato, NON installato - richiede minimo 64K contesto
  (incompatibile con questo hardware) + bug noto/irrisolto di hang
  Ollama+tool - usato invece Ollama diretto via endpoint HTTP

PILOTA (backfill temporal_concentration BREAKOUT_ACC+ORDER_BLOCK):
  4 tentativi (2x 3B, 1x timeout iniziale, 1x 7B escalation), TUTTI
  FALLITI - 1 fix legittimo dell'harness (import/invocazione, non
  logica) nel mezzo - pattern di fallimento consistente: i modelli
  copiano identificatori dal file di riferimento di stile invece di
  astrarre al nuovo schema dati - MAI corretto da Claude al posto
  del worker, ogni fallimento documentato e preservato

DECISIONE: LOCAL_WORKER_OPERATIONAL_WITH_LIMITATIONS - operativo per
  TIER 1 (task brevi/JSON/log/riassunti), NON ancora per TIER 2
  (coding) - task di coding di questo tipo restano da escalare a
  Claude/Codex
```
