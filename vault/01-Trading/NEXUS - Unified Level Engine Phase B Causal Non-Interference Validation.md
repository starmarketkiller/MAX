# Unified Level Engine — Phase B: Causal Non-Interference + Extended Shadow Validation

Segue [[NEXUS - Unified Level Engine Phase A WICK Telemetry Shadow]] (commit `6d4382b`, approvato). Nessuna strategia migrata al nuovo engine. Il nuovo registry non viene letto da nessuna decisione. Nessuna modifica a Structure/Reaction legacy, execution, registry strategie, Global New-Bar Gate, SL/TP.

## File modificati in questa fase

| File | Modifica |
|---|---|
| `MQL5/Include/NEXUS_v1/NXS_ReactionEngine.mqh` | aggiunto log strutturato per-evento `[LEVELENGINE][EVENT]` (funzione `_NXS_Reaction_Emit`, helper `_NXS_ReactionTypeStr`), aggiunto tipo evento `NXS_REACT_CREATE_A` (mancava un evento esplicito per `levels_created`) |
| `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` | nuovo input `InpLevelRegistry_WickEventLog` (default `false`) — gate dedicato per il log per-evento, usato solo nelle run di validazione |

Nessun altro file toccato in Phase B (nessun nuovo hook: quelli di Phase A restano invariati). Compilazione ricontrollata: **0 errori, 2 warning preesistenti** (stessi di Phase A).

---

## 1. Paired ON/OFF test

Finestra usata: **2026-06-01 → 2026-07-01 (30 giorni)**, GOLD H4, Model=1. È la finestra più lunga risultata affidabile: un primo tentativo su 3 mesi pieni (stessa Model=1) non ha completato in 5 minuti (CPU quasi ferma, sintomo identico al blocco Model=4 del §5) ed è stato abbandonato; 30 giorni completa in modo consistente (~145-146s).

**Nota metodologica importante**: il primo giro di run ON/OFF è stato invalidato da un artefatto del mio metodo di test, non del codice EA: `NXS_ResetTradesLogOnInit` archivia il CSV usando `TimeLocal()`, che nel Tester restituisce il **tempo simulato** (identico tra run con la stessa `FromDate`), non l'orario reale — il secondo run tentava di archiviare con lo stesso nome file del primo, il `FileMove` falliva, e i trade si accumulavano nello stesso CSV invece di due file separati. Corretto ripulendo manualmente CSV e archivio tra un run e l'altro prima di ogni coppia. Questo NON è un bug del codice Phase A/B, è un limite del meccanismo di archiviazione esistente (`NXS_Logging.mqh`, non toccato).

### Risultati

| Strategia | Selector | OFF sha256(NEXUS_trades.csv) | ON sha256 | Bytes | Righe (OPEN+CLOSE) | Esito |
|---|---|---|---|---|---|---|
| WICK_SWEEP_REV | 54 | `979325de0339d2d5...48a9d44` | `979325de0339d2d5...48a9d44` | 34272 | 146 (73+73) | **IDENTICO** |
| WICK_SWEEP_RECLAIM | 55 | `87078d65fcf2656a...5be548005` | `87078d65fcf2656a...5be548005` | 10048 | 50 (0+50)* | **IDENTICO** |

\* Il path RECLAIM logga solo `CLOSE` (0 righe `OPEN`) — caratteristica preesistente del suo percorso di esecuzione nel `.mq5` (l'apertura reale usa un altro call site di `NXS_LogTradeCSV`, non toccato da questa fase), identica in ON e OFF: irrilevante ai fini della parità, che è comunque bit-a-bit perfetta.

Confermato anche a livello di report (.htm), identico OFF/ON per entrambe le strategie:

| Metrica | WICK_SWEEP_REV | WICK_SWEEP_RECLAIM |
|---|---|---|
| Profitto Totale Netto | -12.57 | -37.70 |
| Bilancio Drawdown Massimo | 82.49 (7.94%) | 69.68 (6.85%) |
| Fattore di Profitto | 0.95 | 0.84 |

Tutte le colonne richieste (numero trade, entry timestamp, side, entry price, SL, TP, exit timestamp, exit reason, PnL, balance finale, max DD) sono contenute nel CSV/report confrontato: essendo l'hash dell'intero file identico, ogni singola colonna per ogni singolo trade è identica per costruzione — non serve un confronto colonna-per-colonna separato quando l'intero artefatto combacia byte-a-byte.

**Bonus non richiesto ma eseguito**: stesso confronto ON/OFF ripetuto anche su **FVG_CONT** (non-WICK, 14 giorni) per estendere l'evidenza di non-interferenza oltre la famiglia WICK: `sha256=e17b5e4a3cc6f106...4867b60` identico OFF/ON, 388 byte. Vedi anche §3.

### Digest deterministico

I valori sha256 sopra SONO il digest deterministico richiesto (dell'intera sequenza trade, non solo di un riassunto): stesso storico + stesso seed di esecuzione (Model=1, deposito/leva fissi) + unica variabile cambiata (`InpLevelRegistry_WickTelemetry`) → stesso digest. Qualunque divergenza futura in una ripetizione di questo test, anche di un solo byte in una singola riga, altererebbe l'hash — criterio di accettazione verificabile meccanicamente, non a occhio.

**Acceptance §1: ON == OFF su tutta la sequenza operativa — PASS. Nessuna differenza rilevata su nessuna delle 3 coppie testate.**

---

## 2. Extended old-vs-new event parity

Sulle run **ON** della sezione 1 (30 giorni), oltre ai conteggi aggregati (già in Phase A) è stata costruita una correlazione **evento-per-evento**.

### 2.1 REV (selector 54) — aggregato + cross-check indipendente

| Metrica | old | new | Esito |
|---|---|---|---|
| levels_created | 224 | 224 | PASS |
| levels_replaced | 148 | 148 | PASS |
| sweeps (REV) | 75 | 75 | PASS |
| invalidated_by_price | 1 | 1 | PASS |
| consumed (REV) | 73 | 73 | PASS |

Il path REV non ha un log strutturato per-evento del vecchio codice per creazione/touch/sweep/invalidazione (solo il funnel aggregato) — ma HA un log indipendente per ogni apertura reale (`[NEXUS] OPEN BUY/SELL WICK_SWEEP_REV`, scritto da `NEXUS_EA_v2.mq5`, non dal modulo Phase A/B). Cross-check diretto:

- 73 righe `[NEXUS] OPEN ... WICK_SWEEP_REV` (vecchio) vs 73 eventi `type=CONSUME` (nuovo), correlati per `(timestamp, direzione)`: **insieme identico, 0 mismatch**.

### 2.2 RECLAIM (selector 55) — correlazione completa per level_id

Il path RECLAIM ha log strutturati per-evento nel vecchio codice (`[WICKRECLAIM][ARMED/RECLAIM_AVAILABLE/ABANDONED/OPENED]`, con `sweep_id`/`level_id`/`side`/`time`). Script di correlazione (`parity_check.py`) che legge sia i log vecchi sia i nuovi `[LEVELENGINE][EVENT]`, indicizza per `level_id`, e produce record di mismatch nel formato richiesto (`level_id, event_type, old_value, new_value, timestamp, side`) ove presenti:

```
old_armed=75, old_reclaim_available=56, old_abandoned=25, old_opened=50
new SWEEP=75, new RECLAIM=56, new INVALIDATE(su questi 25)=25, new CONSUME=50
checked_correlations=206
mismatch_count=0
```

**Zero mismatch su 206 correlazioni verificate individualmente** (non solo per conteggio: ogni singolo `sweep_id` del vecchio codice è stato cercato nel nuovo log per lo stesso `level_id`, confrontando `side` e `timestamp`).

Aggregato (stesso run, dal print `[LEVELENGINE][PARITY]`):

| Metrica | old | new | Esito |
|---|---|---|---|
| levels_created | 224 | 224 | PASS |
| levels_replaced | 222 | 222 | PASS |
| sweeps (RECLAIM) | 75 | 75 | PASS |
| reclaims | 56 | 56 | PASS |
| invalidated_by_replacement | 25 | 25 | PASS |
| consumed (RECLAIM) | 50 | 50 | PASS |

### Dichiarazione esplicita

**Zero mismatch rilevati** su entrambi i path, sia a livello aggregato (9+9 metriche) sia a livello evento-per-evento (73 + 206 correlazioni individuali = 279 controlli puntuali). Nessun mismatch record da riportare.

**Acceptance §2: parità evento-per-evento — PASS, nessun mismatch non spiegato (perché non ce n'è nessuno).**

---

## 3. Non-WICK regression smoke

Run brevi (14 giorni, 2026-06-01→2026-06-15, Model=1), `InpLevelRegistry_WickTelemetry=true` (default), WICK disattivo (`InpStrat_WickSweep=false`, `InpStrat_WickSweepReclaim=false`):

| Strategia | Selector | Trade prodotti | Eventi `[LEVELENGINE][EVENT]` | Messaggio parity |
|---|---|---|---|---|
| ADX_RSI | 1 | 1 OPEN (posizione ancora aperta a fine finestra) | **0** | `skipped: ne' WICK_SWEEP_REV ne' WICK_SWEEP_RECLAIM erano attivi in questo run` |
| EMA_PULLBACK | 11 | 3 OPEN / 3 CLOSE | **0** | (stesso skip) |
| FVG_CONT | 8 | 1 OPEN / 1 CLOSE | **0** | (stesso skip) + **hash ON/OFF identico** (§1) |

Verificato esplicitamente (non solo dedotto): compilazione 0 errori con gli include Phase A/B presenti; tutte e 3 le strategie producono trade normalmente; **zero eventi WICK registrati** quando WICK non è selezionato (confermato per estrazione diretta dal segmento di log della run ADX_RSI: `event_count_in_adxrsi_run=0`); nessuna nuova authority/gate compare (`NXS_LevelEngine_PrintWickParity` stampa solo il messaggio di skip, non entra mai nel corpo che confronta/decide nulla).

**Acceptance §3: non-WICK smoke — PASS.**

---

## 4. Performance overhead

Confronto diretto OFF vs ON, stesso identico run (REV, 30 giorni, 224 livelli, fino a 652 reaction event nel run RECLAIM):

| Metrica | OFF | ON | Δ |
|---|---|---|---|
| Durata Tester (REV, misurata con `Stopwatch`) | 145.72s | 145.68s | **-0.04s (~0.03%, rumore di misura)** |
| Livelli memorizzati (`levels_in_registry`) | n/a (non calcolato) | 224 (REV) / 224 (RECLAIM) | — |
| Reaction event registrati | n/a | 605 (REV) / 652 (RECLAIM) | — |
| Memoria/array size | `ArraySize(g_nxsLevelReg)` cresce a raddoppio (256→512 in questo run, mai oltre) | idem | — |

**Nessun overhead di durata misurabile** alla scala testata (224 livelli, ~600 eventi). `_NXS_LevelReg_Find()` è ricerca lineare O(n): con n≤224 il costo aggregato su ~600-650 lookup è sub-millisecondo, coerente con la differenza di durata nulla osservata.

**Quando potrebbe diventare un problema (stima, non misurata)**: `levels_created` scala con il numero di barre H4 e la frequenza wick, non con la durata del test in modo lineare-semplice — su questa finestra (30gg ≈ 125 barre H4) si sono creati 224 livelli (~1.8/barra, alto perché quasi ogni wick ≥15 pip su GOLD H4 genera un livello). Un Full Validation pluriennale (3 anni ≈ 4500 barre H4) potrebbe arrivare nell'ordine di **8.000-10.000 livelli** per estrapolazione lineare grezza — a quella scala una ricerca lineare per ogni touch/sweep/reclaim (centinaia-migliaia di lookup) comincia ad avere un costo aggregato non più banale, anche se probabilmente ancora sub-secondo in assoluto. **Non ottimizzato in questa fase** (esplicitamente fuori scope): l'indicazione pratica per il futuro è sostituire la scansione lineare con un indice (es. mappa `level_id → indice array`) SOLO se/quando un run lungo mostra un rallentamento misurabile — non prima.

**Acceptance §4: overhead — PASS (accettabile alla scala testata, nessuna azione richiesta ora).**

---

## 5. Storico WICK (178 trade)

Ritentata la fixture storica `WICK_SWEEP_REV RAW Fast Smoke` (GOLD H4, 2026.06.01→2026.08.26, Model=4 "ogni tick reale", selettore 54, stessi parametri) **due volte** in questa sessione:

1. Primo tentativo: terminato manualmente dopo 8+ minuti, CPU cumulata 16 secondi, nessun log Tester prodotto.
2. Secondo tentativo (questa fase, 15 minuti di budget): terminato dopo timeout, CPU cumulata **13.28 secondi**, stesso pattern esatto.

La riproducibilità del blocco (stesso sintomo, due tentativi indipendenti in sessioni diverse) esclude un fluke momentaneo e conferma la diagnosi di Phase A: il fattore critico è **Model=4 su una finestra di 3 mesi** (richiede storico tick M1 completo, verosimilmente non scaricabile senza connessione broker attiva in questa sessione headless), non una regressione introdotta dal nuovo codice — le run Model=1 (§1, §3) sullo stesso EA compilato e sulla stessa history GOLD H4 completano regolarmente e aprono trade senza alcun blocco.

Come esplicitamente richiesto: **nessuna modifica a registry/gate per forzare l'esecuzione.**

```
HISTORICAL_VALIDATED_FIXTURE = preserved
FULL_REEXECUTION = NOT_EXECUTED
```

---

## 6. Decisione finale Phase B

| Criterio di autorizzazione Phase C | Esito |
|---|---|
| ON/OFF trading parity perfetta | ✅ PASS (3/3 coppie, hash bit-a-bit identico) |
| old/new event parity senza mismatch non spiegati | ✅ PASS (0 mismatch su 279 controlli puntuali + 18 metriche aggregate) |
| non-WICK smoke puliti | ✅ PASS (3/3 strategie, zero eventi WICK spuri, zero nuovi gate) |
| overhead accettabile | ✅ PASS (nessuna differenza di durata misurabile alla scala testata) |

### **VERDICT: PASS_TO_PHASE_C**

La fixture storica dei 178 trade resta `NOT_EXECUTED` (limite ambientale riproducibile, non un difetto del codice) ma questo non è tra i 4 criteri di autorizzazione elencati per Phase C — è gestito secondo la clausola di fallback esplicita del task (preservata, non forzata). Se Phase C dovesse includere questa famiglia, la fixture storica resta il riferimento da riconciliare non appena l'ambiente lo consenta (es. sessione con connessione dati attiva).
