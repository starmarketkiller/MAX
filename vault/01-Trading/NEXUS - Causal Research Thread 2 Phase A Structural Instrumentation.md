# NEXUS Causal Research Thread 2 — Fase A: Instrumentazione del Lifecycle Strutturale

Segue [[NEXUS - Causal Research Thread 2 Reclaim False Break Feasibility]] (commit `abde2a5`, verdict `HOLD_NEEDS_CAUSAL_HOOKS`). Percorso scelto: **B — instrumentare il codice**. Target esplicitamente approvati: **SNXSSweepExt** (detector) e **SH_BMS_RTO** (V1, lifecycle consumer). Nessun'altra strategia toccata. Nessuna logica di trading modificata: solo osservazione read-only aggiuntiva.

## 1. File modificati

| File | Modifica |
|---|---|
| `MQL5/Include/NEXUS_v1/NXS_StructuralResearchLog.mqh` | **Nuovo file.** Struct evento, storage, derivazione id, dedup, snapshot regime/trend, funzioni `NXS_Structural_On*`, summary. |
| `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` | Aggiunto `InpStructuralResearchEventLog` (default `false`). |
| `MQL5/Include/NEXUS_v1/NXS_Strategies_SMC.mqh` | `SNXSSHBmsState` esteso con 3 campi additivi (`structLevelId`, `structSide`, `structDir`); `NXS_SHBMS_Reset()` li azzera; 6 chiamate di log inserite in `NXS_SHBMS_UpdateSide()` nei punti causali dove lo stato è **già** mutato — nessuna condizione spostata o modificata. |
| `MQL5/Experts/NEXUS_EA_v2.mq5` | `#include` del nuovo file (prima di `NXS_Strategies_SMC.mqh`); chiamata `NXS_Structural_PrintSummary()` in `OnDeinit`. |

Nessun file di execution/risk/gate toccato. Nessuna strategia diversa da SH_BMS_RTO (V1) modificata.

## 2. Schema evento (`SNXSStructuralEvent`)

Campi implementati, tutti presenti nel codice esistente o calcolati read-only al momento dell'evento — nessun concetto inventato:

`event_id, structural_level_id, timestamp, event_type, source, source_tf, side, direction, level_price, price_at_event, penetration_pips, created_time, age_seconds, state_before, state_after, regime_at_event, structure_trend_at_event, consumer`

- `event_type` ∈ {SWEEP, TRUE_BREAK, RETEST, INVALIDATE} — solo questi 4, come richiesto.
- `source` = `"SNXSSweepExt"` sempre in questa fase (unico detector strumentato).
- `consumer` = `"SH_BMS_RTO"` sempre in questa fase (unico consumer che scrive nel log).
- `regime_at_event` = `NXS_RegimeName(NXS_DetectRegime())`, chiamata pura, read-only, valutata al momento dell'evento.
- `structure_trend_at_event` = mappatura di `g_struct.trend` (+1→UP, -1→DOWN, 0→RANGE), letto al momento dell'evento, mai scritto.
- `created_time`: per Daily/Weekly/Monthly-High/Low = apertura del periodo precedente (`iTime(shift=1)`, lo stesso riferimento già usato internamente da `NXS_DetectSweepExt()` per calcolare pdh/pwh/pmh); per Asia-High/Low = apertura del giorno corrente; per Equal-High/Equal-Low = **0 (NOT_CAUSALLY_RECOVERABLE)**, dichiarato esplicitamente perché un cluster di 2+ swing non ha un istante di nascita causalmente pulito.
- `age_seconds` = `timestamp - created_time` quando `created_time>0` e `<=timestamp`, altrimenti `-1`.

## 3. Strategia dell'id strutturale (`structural_level_id`)

`structural_level_id = levelTag + "_" + data_ancora_di_calendario`, dove l'ancora dipende dal tag (`sw.levelTag`, già calcolato da `NXS_DetectSweepExt()`, mai reinventato):

- `Daily-High/Low` → data del D1 shift=1 (lo stesso bar usato per calcolare pdh/pdl).
- `Weekly-High/Low` → data del W1 shift=1.
- `Monthly-High/Low` → data del MN1 shift=1.
- `Asia-High/Low` → data del giorno corrente (il detector scansiona una finestra Asia "del giorno", stesso limite già presente nel detector, non introdotto qui).
- Equal-High/Low (o tag non riconosciuto) → **eccezione dichiarata**: nessun periodo di calendario pulito esiste per un cluster di 2+ swing; usato il timestamp pieno (data+minuti) del bar sweepato come discriminante. Documentato esplicitamente nel codice (`_NXS_Structural_ComputeLevelId`) come convenzione diversa dagli altri tag.

L'id è quindi deterministico, stabile e distingue livelli dello stesso tipo su giorni diversi, come richiesto — non è un contatore non riproducibile.

**Limite noto e dichiarato**: l'id viene calcolato con il simbolo/timeframe correnti al momento della chiamata (`g_sym`, `tf` passato); non è quindi portabile cross-simbolo (non necessario in questa fase, EA single-symbol per run).

## 4. Instrumentazione del lifecycle SH_BMS_RTO

State machine **invariata al 100%** — nessuna condizione spostata, nessun refactor del percorso di trading. Aggiunte solo:
- 3 campi additivi allo stato (`structLevelId/structSide/structDir`), scritti UNA VOLTA alla transizione IDLE→SWEPT e letti (mai scritti da altrove) nelle chiamate successive.
- 6 chiamate a `NXS_Structural_On*()` nei punti in cui lo stato è **già** stato mutato dalla logica esistente:

| Punto causale (riga originale) | Evento |
|---|---|
| IDLE→SWEPT (`sw.confirmed && sw.dir==wantSweep`) | SWEEP |
| SWEPT→IDLE per reclaim prima dell'MSS | INVALIDATE (state_before=SWEPT) |
| SWEPT→IDLE per timeout MSS (`barsWaited > InpSHBMS_MaxMSSBars`) | INVALIDATE (state_before=SWEPT) |
| SWEPT→WAITING_RETURN (MSS confermato) | TRUE_BREAK |
| WAITING_RETURN→IDLE per timeout ritorno | INVALIDATE (state_before=WAITING_RETURN) |
| WAITING_RETURN→IDLE per invalidazione profonda | INVALIDATE (state_before=WAITING_RETURN) |
| WAITING_RETURN→entry (touch zona origine) | RETEST |

Correzione fatta **durante** l'implementazione (non nella spec iniziale): nei punti successivi allo SWEEP, il parametro `sw` passato alla funzione è il rilevamento **corrente del tick**, non lo sweep originale — usarlo direttamente per `side`/`direction` in TRUE_BREAK/RETEST/INVALIDATE avrebbe loggato dati sbagliati/vuoti. Risolto congelando `side`/`direction` nello stato (`structSide`/`structDir`) al momento dello SWEEP e riusando quelli nelle chiamate successive.

## 5. Deduplicazione

**Chiave di unicità**: `(structural_level_id, event_type, timestamp di barra)`. Un evento con la stessa terna non viene riscritto; occorrenze successive dello stesso id in un momento diverso (es. lo stesso `Daily-High` sweepato di nuovo su una barra successiva) restano eventi distinti e vengono loggate normalmente.

**Motivazione della chiave**: l'architettura multi-TF-pass di `NEXUS_EA_v2.mq5` (`NXS_CollectAllSignals`) richiama `NXS_DetectSweepExt()` e la funzione di update della strategia una volta per ogni "pass" TF prima di filtrare per profilo — quindi la stessa transizione di stato di SH_BMS_RTO può essere osservata più volte all'interno dello stesso bar reale. La chiave (id+tipo+timestamp) collassa questi duplicati indipendentemente dal meccanismo che li produce.

**Cross-consumer**: in questa fase l'unico *writer* del log è SH_BMS_RTO — nessun'altra strategia chiama `NXS_Structural_On*()`. Non può quindi verificarsi doppio conteggio cross-strategia per costruzione (un solo scrittore). La chiave di dedup, però, **non include il nome del consumer**: se in una fase futura un secondo consumer venisse strumentato e osservasse lo stesso `(level_id, event_type, timestamp)`, il duplicato verrebbe comunque soppresso automaticamente. Questo è dichiarato come limite/scope di questa fase, non come problema irrisolto: il meccanismo di dedup è già generale, semplicemente non ancora esercitato da un secondo scrittore.

**Prova quantitativa**: nel run di feasibility (§7) sono stati soppressi **3896 duplicati** a fronte di **3456** eventi effettivamente loggati — la ripetizione multi-pass è reale e frequente, non un caso limite teorico.

## 6. Sicurezza causale

Verificato riga per riga che nessun campo legga stato futuro:
- `price_at_event`/`penetration_pips` usano sempre `iClose(tf,1)` (la barra appena chiusa che ha causato la transizione) o il prezzo di ingresso calcolato nello stesso istante per RETEST — mai barre successive.
- `created_time`/`age_seconds` derivano da barre shift≥1, mai dalla barra corrente.
- `state_before`/`state_after` sono stringhe letterali che descrivono la transizione già decisa dal codice esistente, non un valore riletto dopo il fatto.
- `regime_at_event`/`structure_trend_at_event` sono snapshot immediati (`NXS_DetectRegime()`, `g_struct.trend`), mai riletti in un secondo momento.
- Nessun campo di trade result, MFE/MAE, exit reason, reclaim futuro o dati di barre successive è presente nello schema.

## 7. Gating e parità/regressione

`InpStructuralResearchEventLog` (default `false`) è l'unico gate. A `false`: `_NXS_Struct_LogEvent()` ritorna immediatamente, nessuna scrittura nell'array, nessun Print. L'unico lavoro svolto incondizionatamente (anche a `false`) è il calcolo di `structural_level_id`/`structSide`/`structDir` nello stato SH_BMS_RTO (dato inerte, mai letto da alcuna condizione di trading, costo trascurabile).

**Compilazione**: `MetaEditor64.exe /compile`, entrambi i terminali (live e test, ciascuno con il proprio eseguibile locale — vedi nota sotto). **0 errori**, 2 warning preesistenti e non correlati (`macro 'NXS_MAX_SIGNALS' redefinition`, `possible loss of data ulong→long` a riga 1003, presenti prima di questa modifica).

**Nota tecnica**: durante questa fase si è confermato che il terminale di test (`C:\MT5-Tester`) ha un proprio `MetaEditor64.exe` locale, che risolve correttamente gli include dalla propria cartella; usare invece il `MetaEditor64.exe` condiviso di `C:\Program Files\MetaTrader 5` contro il path del terminale di test produce un errore fuorviante (`file non trovato`) perché risolve gli include dalla cartella del terminale live. Non è un problema del codice, ma va sempre usato l'eseguibile del terminale che si intende compilare.

### Parità — SH_BMS_RTO (selettore 21, GOLD H4, 2026.01.01→2026.05.01, Model=1)

| | OFF | ON |
|---|---|---|
| `NEXUS_trades.csv` | assente (0 trade) | assente (0 trade) — identico |
| CERT SUMMARY | `generated=0 blocked=0 opened=0` verdict=FAIL/MISSING_TELEMETRY | `generated=0 blocked=0 opened=0` verdict=FAIL/MISSING_TELEMETRY — identico |
| `[STRUCTLOG]` nel log | 0 righe | 3456 eventi |

Il verdict FAIL/MISSING_TELEMETRY del Certificate è un limite preesistente e indipendente (il trace del Test Validity Certificate non risulta attivo per questo selettore) — identico in entrambe le run, quindi non è una regressione introdotta qui.

### Parità — WICK_SWEEP_REV (selettore 54, consumer di SNXSSweepExt **non** strumentato direttamente, GOLD H4, 2026.06.01→2026.06.15, Model=1)

| | OFF | ON |
|---|---|---|
| Righe `NEXUS_trades.csv` | 70 | 70 |
| SHA256 `NEXUS_trades.csv` | `513aeb1f4f675ab5e9e4ec6bfc9a3db9839b087076d007e966107decfdce9e6a` | **identico** |

Prova diretta che l'esistenza del nuovo modulo/input non altera in alcun modo un consumer di `SNXSSweepExt` che non è stato strumentato.

Nessuna variazione di PF/numero trade/PnL attribuibile all'instrumentazione in nessuna delle due coppie di run. Nessun doppio executor introdotto (il modulo non chiama mai funzioni di esecuzione/risk). Nessuna modifica a risk/execution.

## 8. Campione di feasibility (SOLO conteggio, nessuna analisi predittiva)

Run: SH_BMS_RTO (selettore 21), logging ON, GOLD H4, 2026.01.01→2026.05.01 (~4 mesi), Model=1.

| Metrica | Valore |
|---|---|
| Eventi totali loggati | **3456** |
| SWEEP | **1304** |
| TRUE_BREAK | **143** |
| RETEST | **30** |
| INVALIDATE | **1979** |
| Livelli strutturali unici (da SWEEP) | **681** |
| Duplicati soppressi (dedup multi-pass) | **3896** |

Nessuna interpretazione predittiva effettuata su questi numeri, come richiesto — servono solo a dimostrare che il canale produce dati reali e in volume sufficiente per un futuro dataset causale.

## 9. Limiti noti / cosa NON è stato fatto in questa fase

- Solo SH_BMS_RTO (V1) scrive nel log; SH_BMS_RTO_V2, SilverBullet e altri consumer di `SNXSSweepExt` non sono strumentati (fuori scope esplicito di questa fase).
- Nessun dataset esportato su CSV/file esterno in questa fase: gli eventi vivono solo in `g_nxsStructEvents[]` in memoria durante il run e vengono stampati come `[STRUCTLOG][EVENT]` nel log del Tester — l'estrazione in un dataset strutturato è lavoro di una fase successiva.
- Il verdict FAIL/MISSING_TELEMETRY del Test Validity Certificate per selettore 21 è preesistente e non indagato in questa fase (fuori scope: instrumentazione, non certificazione).
- Cross-consumer dedup non esercitato da un secondo scrittore reale (vedi §5).

## Verdict

### **READY_FOR_STRUCTURAL_DATASET**

L'instrumentazione è read-only, gated, causalmente sicura, e dimostrata bit-identica a baseline sia OFF che ON su una strategia direttamente strumentata (SH_BMS_RTO, 0 trade in entrambi i casi ma CERT/log identici) sia su un consumer non strumentato di SNXSSweepExt (WICK_SWEEP_REV, digest SHA256 identico su 70 trade). Il campione di feasibility conferma volume reale di eventi (3456 loggati, 3896 duplicati correttamente soppressi) sufficiente per costruire un dataset di ricerca causale in una fase successiva.
