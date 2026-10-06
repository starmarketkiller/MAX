# MT5 Terminal Isolation Policy V1

**Stato:** policy di design, non committata. Nessuna implementazione di orchestration/VM/containerizzazione. Nessuna modifica a codice/worker/MQL5 — solo formalizzazione di uno stato già in parte reale e in parte da costruire, chiaramente distinti sotto.

## 0. Ispezione preliminare — cosa esiste già (prima di definire qualunque policy nuova)

- **`LocalBridge/nexus_worker.config.example.json`**: un **solo** set di path (`mt5_path`, `metaeditor`, `mql5_include`, `mql5_experts`) — nessuna distinzione live/tester/research nel config del worker oggi. Questo è il gap reale confermato, non ipotetico.
- **`LocalBridge/nexus_local_worker.py`**: `handle_compile_ea` (compile via `metaeditor.exe /compile:... /log:... /portable`, path-containment, timeout), `handle_restart_mt5` (kill+relaunch del **solo** processo che corrisponde esattamente all'eseguibile configurato — `_terminal_pids()`, già corretto da un bug precedente che uccideva ogni `terminal64.exe` della macchina, incluse installazioni non gestite da questo worker), `handle_deploy_files` (staging atomico + rollback, checksum SHA-256 obbligatorio).
- **Due terminali reali, già esistenti, non ipotetici**: `vault/01-Trading/NEXUS - Causal Research Thread 2 Phase A Structural Instrumentation.md:87` documenta che `C:\MT5-Tester` ha un proprio `MetaEditor64.exe` locale; usare invece il `MetaEditor64.exe` condiviso di `C:\Program Files\MetaTrader 5` contro il path del terminale di test produce un errore fuorviante ("file non trovato") perché **risolve gli include dalla cartella del terminale live**. `vault/01-Trading/NEXUS - Phase 7.15 Integration Closure Report.md:45` cita due cartelle dati reali per hash: `D0E8209F...` (terminale verificato/pulito in quella fase) e `7F8EC41F...` (il "secondo terminale", mai toccato in quella fase).
- **Junction già in essere** (nota utente, non verificata nuovamente qui): `Include\NEXUS_v1` in entrambi i terminali è una junction verso lo stesso clone del repo git — gli include non possono più divergere per copia manuale dimenticata. **`NEXUS_EA_v2.mq5` (l'Expert stesso) non è una junction** — resta copiato manualmente per terminale, unico punto residuo di sync manuale.
- **Nessun lock/coda per il Strategy Tester trovato** — confermato dal comportamento noto ("/config non accoda") e dall'assenza di un `handle_run_tester` nel worker.
- **Nessun generatore `.set`/`.ini`** — i preset esistenti (`MQL5/Presets/Research/*.set`, `MQL5/Demo/*.set`) sono file statici creati a mano, nessuna provenance machine-readable.

## 1. I quattro ruoli

### LIVE_TERMINAL

- **Data directory:** l'installazione reale, oggi `C:\Program Files\MetaTrader 5` + il suo profilo dati MetaQuotes (hash `D0E8209F...` osservato in una fase reale — da confermare come stabile, non garantito immutabile da MT5 stesso).
- **Permessi:** scrittura/esecuzione riservata a capitale reale o demo-live-equivalente. Nessun processo di ricerca/tester deve scrivere qui.
- **Operazioni permesse:** avvio/arresto EA live, deploy di build verificate (via `handle_deploy_files`, checksum obbligatorio), lettura stato/posizioni.
- **Operazioni proibite:** compilazione di build sperimentali/diagnostiche non destinate al live; esecuzione Strategy Tester (MT5 non permette comunque live+tester concorrenti sullo stesso processo, ma il punto resta: non va mai *tentato*); accesso da credenziali/token non espliciti.
- **Lock/concorrenza:** un solo processo `terminal64.exe` per questo path alla volta — già garantito da `_terminal_pids()` (match esatto sull'eseguibile) per restart, **non ancora garantito per un eventuale avvio/compile parallelo non passato dal worker**.
- **Restart/recovery:** `handle_restart_mt5` kill+relaunch, già idempotente e scoped al solo eseguibile configurato. Nessun meccanismo di "ultimo stato noto" oltre a quanto l'EA stesso persiste (fuori scope di questa policy).
- **Artifact location:** log/report di questo terminale non vanno mai copiati/confusi con quelli del tester (vedi §3, oggi senza garanzia tecnica, solo per separazione di path).
- **Credential scope:** token/bridge_token del worker, scope pieno sulle operazioni di deploy/restart configurate — nessuna differenziazione di scope oggi tra "posso fare deploy live" e "posso fare deploy tester" nello stesso worker/config.

### TESTER_TERMINAL

- **Data directory:** `C:\MT5-Tester` (reale, confermato), con il proprio `MetaEditor64.exe` locale — **la regola fondamentale, già documentata da un incidente reale**: va sempre usato l'eseguibile MetaEditor che appartiene a questo stesso terminale per compilare contro i suoi include, mai quello condiviso di `C:\Program Files\MetaTrader 5`.
- **Permessi:** esecuzione Strategy Tester, compile diagnostico/sperimentale, nessun capitale reale.
- **Operazioni permesse:** Strategy Tester (manuale oggi, `/config`), compile via il proprio MetaEditor, scrittura di report/log/trade-snapshot.
- **Operazioni proibite:** deploy su conto live; uso del MetaEditor del terminale live contro questo path (causa l'errore "file non trovato" già documentato); lettura/scrittura di stato del terminale live.
- **Lock/concorrenza:** **nessuno oggi** — "/config non accoda" (nota operativa già nota), nessun job-id, nessuna seriallizzazione. Due lanci Strategy Tester concorrenti sullo stesso terminale non sono prevenuti da nulla nel codice attuale.
- **Restart/recovery:** nessun meccanismo di recovery da crash/kill a metà run — un run di Tester interrotto non lascia un job marcato "failed" da nessuna parte, perché non esiste un concetto di job per il Tester oggi.
- **Artifact location:** report `.htm` del Tester, oggi letti manualmente da `server/research_scripts/parse_mt5_tester_report.py` dopo un run manuale — nessun aggancio automatico.
- **Credential scope:** stesso worker/config del LIVE_TERMINAL se lo stesso host li gestisce entrambi — **nessuna separazione di credenziali tra i due ruoli nel config attuale**, segnalato come gap, non silenziato.

### COMPILE_WORKSPACE

**Non un terzo terminale MT5 — un workspace logico**, per evitare di inventare una terza installazione fisica dove basta un concetto. È l'insieme di: (a) l'albero sorgente condiviso `MQL5/Include/NEXUS_v1/` (già junction-ato in entrambi i terminali, quindi un solo "vero" sorgente); (b) `NEXUS_EA_v2.mq5` (non junction, copiato manualmente — punto di divergenza possibile); (c) la toolchain di compile del worker (`handle_compile_ea`).

- **Data directory:** il repo git stesso per gli include (già unificato); le due cartelle `Experts/` dei due terminali per `NEXUS_EA_v2.mq5` (non unificate).
- **Permessi:** scrittura solo tramite commit/deploy verificato (checksum), mai scrittura diretta non tracciata su un terminale.
- **Operazioni permesse:** compile contro **l'uno o l'altro** terminale, a patto di usare il MetaEditor di quel terminale specifico.
- **Operazioni proibite:** compilare con un MetaEditor diverso dal terminale target (causa esattamente l'incidente già documentato); assumere che una compile riuscita contro un terminale sia valida per l'altro senza ricompilare.
- **Lock/concorrenza:** nessuna race condition strutturale nota se si segue la regola "un MetaEditor = un terminale", ma **nessun lock esplicito previene due `handle_compile_ea` concorrenti sullo stesso MetaEditor** — non verificato se MetaEditor stesso serializza internamente compilazioni concorrenti (non testato qui).
- **Restart/recovery:** N/A (compile è un'operazione singola, non un processo persistente).
- **Artifact location:** `.ex5` prodotto nella cartella `Experts/` del terminale target; log di compile al path passato a `/log:`.
- **Credential scope:** stesso worker; nessuna differenziazione.

### RESEARCH_TERMINAL

**Non trovato come installazione fisica separata — non esiste oggi.** Non invento una terza installazione: il Tester (`TESTER_TERMINAL`) copre oggi anche l'uso "research" (backtest/diagnostica). Se in futuro servisse un terminale dedicato a osservazione di mercato/demo-account distinto dal Tester (es. per il Modello Istituzionale in shadow-mode con dati live ma senza capitale e senza Strategy Tester), andrebbe istanziato come una **terza installazione reale**, con le stesse regole di isolamento di TESTER_TERMINAL (proprio MetaEditor, propria data directory, mai condiviso col live). Questa sezione resta una definizione pronta per quando (se) servirà, non una descrizione di qualcosa che già esiste.

## 2. Invariante

**Mai usare lo stesso terminale/data directory per live e tester concorrenti.** Oggi questo vale **per fortuna di separazione fisica delle due installazioni** (`C:\Program Files\MetaTrader 5` vs `C:\MT5-Tester`), **non perché il codice lo imponga**. Nulla nel worker impedirebbe oggi di puntare `mt5_path` del config al terminale sbagliato e lanciare un'operazione lì. Questa policy lo rende esplicito; applicarlo in codice (es. un campo `terminal_role: live|tester` nel config, con un controllo che rifiuti un comando "tester-only" se `terminal_role != tester`) è il prossimo passo implementativo naturale, **non eseguito in questo documento**.

## 3. Verifiche richieste, una per una

| Rischio | Stato oggi | Evidenza |
|---|---|---|
| Collisioni su `terminal64.exe` | **Mitigato per il restart**, non per avvii fuori dal worker | `_terminal_pids()` match esatto sull'eseguibile, già corretto da un bug che uccideva ogni terminale sulla macchina |
| MetaEditor compile race | **Non verificato** | Nessun lock trovato nel worker; non testato se MetaEditor stesso serializza |
| Strategy Tester lock | **Assente, gap reale confermato** | "/config non accoda" (nota operativa), nessun `handle_run_tester` |
| Account/broker mismatch | **Non verificato a livello di worker** | Nessun controllo trovato che confermi "questo terminale è loggato sull'account atteso" prima di un'operazione |
| Symbol suffix | **Gestito**, ma a livello strategia non di terminale | `NXS_SymbolProfile.mqh` (auto-config broker suffix) — non pertinente alla separazione terminali in sé |
| Timezone / broker time | **Non specifico ai terminali** | `TimeCurrent()` è tempo broker/server (vedi `.claude/skills/mql5-engineering/SKILL.md` §5) — nessuna gestione differenziata trovata tra live e tester, presumibilmente lo stesso broker per entrambi ma non verificato esplicitamente |
| `.set`/`.ini` provenance | **Assente, gap reale confermato** | File statici creati a mano, nessun metadato di provenienza |
| Stale process detection | **Esiste per il restart live**, non per il Tester | `_terminal_pids()` esiste; nessun equivalente per un run Tester appeso |
| Orphaned job recovery | **Esiste concettualmente per comandi generici** (journal + `PermanentCommandError`/`RetryableCommandError`), **non applicato al Tester** perché il Tester non è un "comando" nel sistema attuale | `docs/REMEDIATION_STATUS.md` §2.4; nessun job-id per run Tester |

## 4. Non implementato in questo documento

Nessun codice, nessuna VM, nessun container, nessun campo di config nuovo scritto. Questa è la specifica da cui costruire (se autorizzato in un task separato) `MT5_AUTOMATED_TESTER_CONTROL_PLANE_V1`/`MT5_RUN_ARTIFACT_CONTRACT_V1` già candidati in `docs/EXTERNAL_TRADING_SYSTEMS_REUSE_GAP_ANALYSIS_V1.md`.

---

MT5_TERMINAL_ISOLATION_POLICY_V1_READY_FOR_REVIEW
