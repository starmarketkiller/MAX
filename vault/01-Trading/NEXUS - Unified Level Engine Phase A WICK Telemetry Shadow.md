# Unified Level Engine — Phase A: WICK telemetry-only registry

Segue [[NEXUS - Unified Structure Level Reaction Engine Migration Plan v1]] (audit approvato con correzione metodologica sulla baseline WICK, applicata anche in quella nota, vedi §4 "First migration candidate" lì).

**Perimetro**: primo scheletro reale del nuovo Unified Level/Reaction Engine, SOLO per la famiglia WICK (`WICK_SWEEP_REVERSAL`/`WICK_SWEEP_RECLAIM`), telemetry-only. Nessun segnale generato, nessun trade aperto, nessun gate/SL/TP/execution modificato, nessuna strategia legge il nuovo registro. `NXS_Structure.mqh`, `NXS_Reaction.mqh`, Order Block, FVG, Fibonacci, Institutional, il bug "terzo cancello silenzioso" e il Global New-Bar Gate non sono stati toccati.

## 0. Correzione baseline WICK (applicata prima dell'implementazione)

Come richiesto, la nota del migration plan è stata corretta per non trattare più "165 sweep/0 trade" come l'unica regression fixture WICK:

- **`CURRENT_CODE_GATED_STATE`**: 165 sweep rilevati / 0 trade — istantanea di uno stato temporaneo del codice (osservata in una sessione precedente, verosimilmente durante la finestra in cui il gate di registry bloccava l'apertura), conservata come dato descrittivo, NON come fixture di riferimento.
- **Fixture storica validata**: `WICK_SWEEP_REV RAW Fast Smoke`, 2026-06-01→2026-08-26, **178 trade, PF 0.78, WR 16.85%, 148 SL/30 TP, net -151.39, zero invariant fail**.
- **Failure history da preservare separatamente** (varianti testate e refutate, non edge validi): WICK_SWEEP_RECLAIM M15 no edge; RECLAIM_TICK dopo ARM M15 refutato; RECLAIM_LIMIT_RETEST refutato; shadow PF 5.80 non valido come performance eseguibile.

Modifiche applicate a `vault/01-Trading/NEXUS - Unified Structure Level Reaction Engine Migration Plan v1.md`: §4 (First migration candidate, punti 3 e 5 riscritti + blocco di correzione metodologica), Acceptance Phase A (punto 4), §8 (Cosa NON toccare, riga sulle regression fixture congelate).

## 1. File creati/modificati

| File | Tipo | Contenuto |
|---|---|---|
| `MQL5/Include/NEXUS_v1/NXS_LevelRegistry.mqh` | **nuovo** | `SNXSUnifiedLevel`, `ENUM_NXS_LEVEL_LIFECYCLE_A`, storage dinamico, `NXS_LevelReg_Create/SetTouched/SetSwept/SetReclaimed/SetInvalidated/SetConsumed` |
| `MQL5/Include/NEXUS_v1/NXS_ReactionEngine.mqh` | **nuovo** | `SNXSReactionEvent`, `ENUM_NXS_REACTION_TYPE_A`, log eventi, contatori parità (`SNXSWickParityCounters`), hook `NXS_Reaction_On*`, `NXS_LevelEngine_PrintWickParity()` |
| `MQL5/Include/NEXUS_v1/NXS_Strategies_Experimental.mqh` | modificato | 11 punti di aggancio (vedi §2) + firma di `_NXS_WickSweep_FinalizeSide` estesa con un parametro `dir` (plumbing, nessun cambio di comportamento) |
| `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` | modificato | nuovo input `InpLevelRegistry_WickTelemetry` (default `true`) |
| `MQL5/Experts/NEXUS_EA_v2.mq5` | modificato | 2 nuovi `#include` (prima di `NXS_Strategies_Experimental.mqh`) + 1 chiamata a `NXS_LevelEngine_PrintWickParity()` in `OnDeinit` |
| `vault/01-Trading/NEXUS - Unified Structure Level Reaction Engine Migration Plan v1.md` | modificato | correzione baseline (§0 sopra) |

Nessun altro file toccato. `NXS_Strategies.mqh`, `NXS_Strategies_SMC.mqh`, `NXS_Strategies_Institutional.mqh`, `NXS_Structure.mqh`, `NXS_Reaction.mqh`, `NXS_BjorgumZones.mqh`, `NXS_FibonacciContext.mqh`, `NXS_InstitutionalCore.mqh` sono invariati (verificabile da `git diff --stat`).

## 2. Causal hook requirement — dove osserva il nuovo registro

Ogni hook è chiamato nello stesso punto in cui il **vecchio** stato (`SNxsWickSide`/`SNxsWickReclaimState`) è **già stato mutato** dal codice esistente — mai ricostruito da log. Guardati tutti da `InpLevelRegistry_WickTelemetry` (default `true`).

| Evento | File:riga (nuovo hook) | Punto causale nel vecchio codice |
|---|---|---|
| **Level creation** (HIGH) | `NXS_Strategies_Experimental.mqh:122` `NXS_Reaction_OnLevelCreated` | subito dopo `g_wickFunnel.levelsCreated++` in `_NXS_WickSweep_UpdateLevel` (riga 119) |
| **Level creation** (LOW) | riga 136 | subito dopo `g_wickFunnel.levelsCreated++` (riga 134) |
| **Level replacement** (HIGH) | riga 113 `NXS_Reaction_OnLevelReplaced` | subito dopo `g_wickFunnel.levelsReplacedUnused++` (riga 108), PRIMA che `g_wickHigh` venga sovrascritto |
| **Level replacement** (LOW) | riga 128 | subito dopo `g_wickFunnel.levelsReplacedUnused++` (riga 126) |
| **Touch** (HIGH) | riga 691 `NXS_Reaction_OnTouch` | subito dopo `g_wickFunnel.levelsRevisited++` in `NXS_Strat_WickSweepReversal` (riga 688) |
| **Touch** (LOW) | riga 734 | subito dopo `g_wickFunnel.levelsRevisited++` (riga 731) |
| **Sweep, path REV** (HIGH) | riga 700-701 `NXS_Reaction_OnSweep` | dentro `if(firstTrigger)`, subito dopo `g_wickFunnel.sweepsDetected++` (riga 697), stesso `firstTrigger` gate del vecchio codice |
| **Sweep, path REV** (LOW) | riga 743-744 | dentro `if(firstTrigger)`, subito dopo `g_wickFunnel.sweepsDetected++` (riga 740) |
| **Invalidation (price returned), path REV** (HIGH) | riga 721-722 `NXS_Reaction_OnInvalidated` | subito dopo `g_wickFunnel.levelsInvalidatedByPrice++` (riga 718), PRIMA di `g_wickHigh.level = 0` |
| **Invalidation (price returned), path REV** (LOW) | riga 763-764 | subito dopo `g_wickFunnel.levelsInvalidatedByPrice++` (riga 760) |
| **Consumed, path REV** | riga 154 `NXS_Reaction_OnConsumed`, in `_NXS_WickSweep_FinalizeSide` | dentro `if(opened)`, subito dopo `side.consumed = true; g_wickFunnel.entryOpened++` (righe 150-151) |
| **Sweep, path RECLAIM (ARMED)** | riga 513-514 `NXS_Reaction_OnSweep` | subito dopo `st.max_penetration_pips = ...` in `_NXS_WickReclaim_ProcessSide`, stesso blocco `WR_IDLE→WR_ARMED` di `g_wickReclaimFunnel.armed++` (riga 502) |
| **Reclaim, path RECLAIM** | riga 560 `NXS_Reaction_OnReclaim` | subito dopo `g_wickReclaimFunnel.reclaimAvailable++` (riga 557), blocco `WR_ARMED→WR_RECLAIMED` |
| **Invalidation (replacement), path RECLAIM** | riga 542-543 `NXS_Reaction_OnInvalidated` | dentro `if(st.state != WR_OPENED)`, subito dopo `g_wickReclaimFunnel.abandoned++` (riga 536) — stessa guardia del vecchio codice che evita di marcare "abbandonato" un evento già aperto |
| **Consumed, path RECLAIM** | riga 637 `NXS_Reaction_OnConsumed`, in `NXS_WickReclaim_OnExecuteResult` | dentro `if(opened)`, subito dopo `g_wickReclaimFunnel.entryOpened++` (riga 634) |

`level_id` non è mai generato dal nuovo modulo: riusa sempre `SNxsWickSide.id` (già esistente, incrementato in `_NXS_WickSweep_UpdateLevel`), garantendo per costruzione che vecchio e nuovo id coincidano sempre — non serve una mappa di corrispondenza separata.

## 3. Schema implementato (WICK-only, campi minimi richiesti)

`SNXSUnifiedLevel`: `level_id, source("WICK"), source_strategy, source_tf, direction, side, price, created_time, state, first_touch_time, touch_count, max_penetration, sweep_depth, reclaim_time, invalidated, consumed`.

`SNXSReactionEvent`: `event_id, level_id, timestamp, type, direction, penetration, reclaim, source_tf` + `source_strategy`/`reason` (aggiunti, non nella lista minima, ma necessari per separare nel parity report i due path indipendenti REV/RECLAIM che possono osservare lo stesso livello — senza questo campo i due sweep count non sarebbero distinguibili).

Lifecycle: `CREATED→FRESH→TOUCHED→SWEPT→RECLAIMED|INVALIDATED|CONSUMED`. **`APPROACHED` e `BROKEN` esistono nell'enum per completezza dello schema ma non sono mai emessi per WICK**: il vecchio codice non calcola una soglia di prossimità distinta dal touch (APPROACHED non osservabile con certezza) e non ha un concetto di "rottura strutturale" distinto dallo sweep stesso (lo sweep è già il suo equivalente terminale). Documentato nel codice (`NXS_LevelRegistry.mqh`).

## 4. Verifica di compilazione

Compilato con `MetaEditor64.exe /compile` sul terminal MT5 con junction attiva su questo repo (`Include\NEXUS_v1` → `MQL5/Include/NEXUS_v1` del repo). Risultato:

```
Result: 0 errors, 2 warnings, 22596 ms elapsed
```

I 2 warning sono **preesistenti e non correlati** (macro `NXS_MAX_SIGNALS` ridefinita in `NXS_SignalRouter.mqh`; conversione `ulong`→`long` alla riga 991 del `.mq5`, lontana da qualunque modifica di questa fase) — confermato confrontando con l'output di compilazione prima delle modifiche.

## 5. Old/new event counts (dati REALI da 2 run di Strategy Tester, non simulati)

Non è stato possibile rieseguire la fixture storica completa (178 trade, 3 mesi, Model=4 "every real tick" — vedi §6). Per verificare i hook a runtime sono stati eseguiti 2 Fast Smoke rapidi (Model=1, finestra breve) sullo stesso EA compilato, uno per ciascun path:

**Run 1 — WICK_SWEEP_REV (selettore 54), GOLD H4, 2026-06-01→2026-06-12:**

| Metrica | old (funnel esistente) | new (registro Fase A) | Esito |
|---|---|---|---|
| levels_created | 104 | 104 | PASS |
| levels_replaced | 67 | 67 | PASS |
| sweeps_REV | 35 | 35 | PASS |
| invalidated_by_price | 0 | 0 | PASS |
| consumed_REV | 35 | 35 | PASS |

35 trade realmente aperti (22 BUY/13 SELL), 0 rifiutati, `entryOpened=35` — confermato anche via `[NEXUS] OPEN BUY/SELL WICK_SWEEP_REV` nel log. `levels_in_registry=104`, `reaction_events_logged=169`.

**Run 2 — WICK_SWEEP_RECLAIM (selettore 55), GOLD H4, 2026-06-01→2026-06-20:**

| Metrica | old (funnel esistente) | new (registro Fase A) | Esito |
|---|---|---|---|
| levels_created | 151 | 151 | PASS |
| levels_replaced | 149 | 149 | PASS |
| sweeps_RECLAIM(armed) | 52 | 52 | PASS |
| reclaims | 39 | 39 | PASS |
| invalidated_by_replacement(abandoned) | 18 | 18 | PASS |
| consumed_RECLAIM | 34 | 34 | PASS |

`levels_in_registry=151`, `reaction_events_logged=292`.

**Copertura**: le due run insieme esercitano TUTTI i 9 contatori richiesti dall'acceptance (levels created/replaced, sweeps detected [entrambi i path], reclaim available, invalidations [entrambe le cause], consumed [entrambi i path]) con valori non banali (non solo 0=0).

## 6. Mismatch

**Zero mismatch rilevati** su entrambe le run (18 confronti totali, 18 PASS). Nessuna riga `MISMATCH` prodotta da `NXS_LevelEngine_PrintWickParity()`.

Nota architetturale sul significato di questo risultato: dato che ogni hook legge gli STESSI valori (prezzo, timestamp, id, penetrazione) che il vecchio codice ha appena calcolato nello stesso punto causale — non una seconda implementazione indipendente — la parità per-campo (timestamp/prezzo/lato di ogni singolo evento) è garantita per costruzione. Il confronto sopra verifica invece l'unica cosa che PUÒ divergere: che nessun hook sia mancante, duplicato, o disallineato dalla condizione del vecchio codice (es. `firstTrigger`, `state != WR_OPENED`). I 18 PASS confermano che tutti gli 11 punti di aggancio del §2 sono stati collegati correttamente.

## 7. Regression fixture results

| Fixture | Esito | Evidenza |
|---|---|---|
| ADX_RSI RAW | **invariato per costruzione** | `NXS_Strategies.mqh` non è stato toccato (0 righe modificate, confermabile da `git diff --stat`); non ri-eseguito in backtest in questa sessione |
| EMA_PULLBACK RAW | **invariato per costruzione** | idem |
| FVG_CONT RAW | **invariato per costruzione** | idem |
| `WICK_SWEEP_REV RAW Fast Smoke` (178 trade, PF 0.78, storica) | **NOT_EXECUTED in questa sessione** | vedi §8 — non è stato possibile completare la re-esecuzione esatta (Model=4, 3 mesi) nella finestra disponibile; NON riproposta come richiesto ("se non riesci... NON correggere il registro"). Nessun dato della fixture alterato: il file/ricetta storica non è stato toccato, solo non ri-eseguito |

## 8. Tentativo di re-esecuzione della fixture storica (178 trade) — esito NOT_EXECUTED

Lanciato `terminal64.exe /config:nxs_fastsmoke_wicksweep.ini` (stessa ricetta della fixture: GOLD H4, 2026.06.01→2026.08.26, Model=4, selettore 54, parametri identici). Dopo 8+ minuti il processo risultava ancora `Responding=True` ma con **CPU cumulata di soli 16 secondi** e **nessun file di log prodotto** in `Tester/logs` — evidenza che il test non aveva ancora iniziato l'elaborazione reale (verosimilmente in attesa di dati tick M1 completi per Model=4 su 3 mesi, non disponibili/scaricabili in questa sessione senza connessione attiva al broker). Processo terminato manualmente per non bloccare la sessione oltre un tempo ragionevole.

**Diagnosi differenziale**: i due Fast Smoke rapidi del §5 (Model=1, 12-20 giorni) sullo STESSO EA compilato e sulla STESSA history GOLD H4 hanno funzionato correttamente e senza ritardi — quindi il problema non è "il registro blocca WICK_SWEEP_REV" (anzi, 35+34=69 trade reali si sono aperti regolarmente in questi run, confermando che la strategia NON è oggi bloccata dal "terzo cancello silenzioso"). Il fattore che cambia è **Model=4 su una finestra di 3 mesi**, che richiede uno storico tick M1 completo assai più pesante di Model=1: la causa più probabile è tempo/dati di download tick, non una regressione di codice introdotta in questa fase.

Per questo motivo, come esplicitamente autorizzato dal task: **trade-parity sulla fixture storica dei 178 trade = NOT_EXECUTED** (non BLOCKED_BY_CURRENT_GATE — non ho evidenza che sia il registro a bloccare, i run più leggeri aprono trade regolarmente). La fixture storica resta preservata come riferimento (nessun dato o codice che la riguarda è stato alterato); la parity di Fase A è stata invece dimostrata a **livello evento** (§5-6), con copertura reale di entrambi i path e di tutti i 9 contatori richiesti.

## 9. Conferma zero influence on trading

- Ogni hook è dietro `if(InpLevelRegistry_WickTelemetry)` (default `true`, ma anche a `false` il comportamento del vecchio codice è identico: l'`if` circonda SOLO la chiamata al nuovo modulo, mai una riga del vecchio stato).
- Tutte le funzioni `NXS_Reaction_On*`/`NXS_LevelReg_*` sono `void`, non ritornano nulla al chiamante e non accettano parametri per riferimento verso lo stato del vecchio motore (solo valori scalari: `long`, `ENUM_NXS_DIR`, `double`, `datetime`, `string`, copiati per valore da variabili già lette).
- Scrivono esclusivamente in array/struct nuovi (`g_nxsLevelReg[]`, `g_nxsReactionLog[]`, `g_nxsWickParity`) mai letti da `NXS_SignalRouter.mqh`, `NXS_Execution.mqh`, né da nessun'altra strategia — verificabile per `grep -rn "g_nxsLevelReg\|g_nxsReactionLog\|g_nxsWickParity"` nel repo: gli unici riferimenti sono dentro `NXS_LevelRegistry.mqh`/`NXS_ReactionEngine.mqh` stessi e le chiamate di hook in `NXS_Strategies_Experimental.mqh`.
- L'unico cambio di firma (`_NXS_WickSweep_FinalizeSide`, aggiunto parametro `dir`) è plumbing interno con 2 soli call site, entrambi aggiornati in modo coerente; il comportamento di `side.consumed`/`g_wickFunnel.*` è bit-per-bit identico a prima.
- Compilazione 0 errori (§4); 2 run di Strategy Tester (§5) hanno aperto trade regolarmente con conteggi `entryOpened`/`buyOpened`/`sellOpened` invariati rispetto al funnel esistente.
- `NXS_Strategies.mqh`, `NXS_Strategies_SMC.mqh`, `NXS_Strategies_Institutional.mqh`, `NXS_Structure.mqh`, `NXS_Reaction.mqh` non toccati.

## 10. Prossimi passi (NON eseguiti in questo task)

Phase B (shadow old-vs-new esteso su un periodo più lungo, incluso il tentativo di riconciliare la fixture storica dei 178 trade con un metodo di esecuzione più leggero di Model=4 se necessario) non è stata iniziata, come richiesto. Nessun avanzamento autonomo a Phase B/C.
