# NEXUS - Phase 7.8E Final Data Freeze

**Baseline:** `a5a79723bd13543e179b506abbd91d04fa4a356c` (Phase 7.8D, `PRE_RUN_SEAL_VERIFIED_READY_TO_RUN`). L'utente ha ispezionato direttamente gli artifact 7.8D e ha trovato due problemi tecnici concreti prima di autorizzare il RUN: il timezone dichiarato non era mai stato misurato, e l'hash "dataset" hashava solo il report di coverage, non i dati reali che il Tester userà.

**Conferma esplicita: SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED. NO TRADE RESULTS GENERATED.**

---

## Problema 1 — Timezone: misurato, non assunto

Il manifest 7.8D dichiarava GMT+2 (dalla costante di progetto `InpServerGMTOffset=2`, mai misurata direttamente). Il log reale mostrava un `server_time_now` ~3h avanti rispetto all'UTC di generazione — incompatibile con +2.

Scritto **`NXS_VolBrkTimezoneMeasure.mq5`** — script READ-ONLY che legge nello stesso istante `TimeCurrent()`, `TimeTradeServer()`, `TimeGMT()`, `TimeLocal()`. Compilato (0 errori/0 warning), deployato, lanciato via `terminal64.exe /config:` (pattern consolidato, atteso via marker file reale).

**Misura reale:**

| | |
|---|---|
| `TimeTradeServer` | 2026.09.22 01:03:04 |
| `TimeGMT` | 2026.09.21 22:03:04 |
| `TimeLocal` | 2026.09.22 00:03:04 |
| `broker_utc_offset_seconds = TimeTradeServer - TimeGMT` | **10800s = +3h (UTC+3)** |

**Scoperta onesta sulla causa probabile:** `TimeLocal() - TimeGMT() = 7200s = +2h` — il fuso del PC locale (CEST) coincide esattamente con la vecchia costante di progetto `InpServerGMTOffset=2`. Ipotesi più probabile: il fuso del PC è stato storicamente scambiato per il fuso del server broker, mai verificato empiricamente prima d'ora. Annotato come `likely_root_cause`, non asserito con certezza; nessuna costante di progetto modificata retroattivamente (fuori scope).

**Correzione dichiarata:** il futuro Serious validation e qualunque calcolo di timestamp relativo a questo broker/account deve usare **+3h (10800s)**, non `InpServerGMTOffset=2`.

**Caveat DST esplicito:** la misura riflette un singolo istante — va ri-misurata se il RUN avviene in una stagione DST diversa (MQL5 non espone una funzione nativa per lo stato DST server-side).

## Problema 2 — Dataset hash: dati reali, non il report

7.8D hashava solo il coverage-audit CSV/summary — un fingerprint del controllo, non dei dati sottostanti. Se MT5 risincronizza/corregge tick tra seal e run, il report può restare identico mentre i dati cambiano.

**Soluzione:** costruito un manifest ordinato dei file `.tkc`/`.hcc` REALI che intersecano `PRIMARY_FRESH_VERDICT_WINDOW`:

- **27 file tick mensili** (`ticks/GOLD/*.tkc`, `202312` → `202602`)
- **4 file barre annuali** (`history/GOLD/2023.hcc` → `2026.hcc`)
- **31 file totali, 0 mancanti**

Ogni entry: `relative_path`, `size_bytes`, `mtime_utc`, `sha256` (hash streaming, mai saltato per dimensione). Il manifest stesso è poi hashato canonicamente. Non è stato necessario ricorrere all'alternativa (snapshot MQL5 deterministico) perché i file grezzi erano mappabili in sicurezza.

**Scoperta empirica sulla volatilità dei dati:** `history/GOLD/2026.hcc` è risultato già cambiato (mtime/contenuto diversi) tra l'esecuzione 7.8D (2026-09-21 23:44) e questa misura 7.8E — non un'ipotesi teorica, un fatto osservato. Per questo il seal finale include un campo esplicito e obbligatorio `reverification_required_before_run=True`: l'hash di oggi non è un pin permanentemente valido, va ricontrollato al momento del RUN reale, e un mismatch deve bloccare, mai essere ignorato silenziosamente.

## Identità temporale — ricontrollata, non ricalcolata

`TOTAL_TEST_WINDOW`, `PRIMARY_FRESH_VERDICT_WINDOW`, `PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW`, `NEWLY_ELAPSED_TAIL_SEGMENT`, T1/T2/T3: tutti copiati verbatim da 7.8D e confrontati byte-per-byte. `no_boundary_changed=True`, `no_recalculation_based_on_outcomes=True`. Nessun confine è stato toccato in base a outcome (che restano comunque non visti).

## Tester config — congelata, mai lanciata

Scritto (non eseguito) l'`.ini` finale del Tester futuro: `Expert=Experts\NEXUS_EA_v2` (file verificato esistente su disco), `Symbol=GOLD`, `Period=H4`, `Model=4`, `FromDate`/`ToDate` derivati da `PRIMARY_FRESH_VERDICT_WINDOW`, `InpStrategySelector=56` (verificato contro `contracts/strategy-registry.json`, non assunto a memoria), ottimizzazione disabilitata, modalità visuale disabilitata, input strategy congelati. Hashato canonicamente. `not_launched=True`.

## Final seal

Pin: offset broker misurato (10800s), hash del data manifest a 31 file, hash tester config, commit strategy frozen (`f035d30`), hash prereg 7.8B, hash autorizzazione 7.8C, hash manifest 7.8D precedente, hash cost model, SHA del codice. Più `reverification_required_before_run` (obbligatorio, motivato dal cambio osservato di `2026.hcc`).

## Seal verification (doppia — builder + verificatore indipendente)

Il builder ricalcola e riporta 8 controlli, tutti `True`. Uno **script indipendente separato** (`verify_volatility_breakout_final_data_freeze.py`) non si fida di quel blocco: ri-legge il file grezzo di misura timezone e ricalcola l'offset da zero; ri-scansiona TUTTI e 31 i file dati reali su disco e ricalcola ogni hash/size indipendentemente (fail-closed su qualunque mismatch/file mancante); ricalcola l'hash del manifest dati e della tester config; incrocia gli hash di protocollo con l'artifact 7.8D reale su disco; incrocia le finestre temporali con 7.8D reale; verifica il selector contro il registro reale; scansiona ricorsivamente per campi di outcome vietati.

**Risultato: tutti i controlli `[PASS]`, 0 file mancanti, 0 file cambiati rispetto al seal, verdetto indipendente identico a quello del builder.**

## Final verdict

**`FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE`**

## Regressione

72/72 PASS sulla nuova suite dedicata. **0 regressioni** sulle altre 29 suite Phase 7 (30 totali).

## Deliverables

`NXS_VolBrkTimezoneMeasure.mq5` (script sorgente), `nxs_volbrk_timezone_measure.txt`/`nxs_volbrk_timezone_done.txt` (output reali, in `phase7_8d/raw_coverage_audit/`), `build_volatility_breakout_final_data_freeze.py`, `verify_volatility_breakout_final_data_freeze.py`, `test_volatility_breakout_final_data_freeze.py`, `volatility_breakout_final_data_freeze_v1.json`.

---

**SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED. NO TRADE RESULTS GENERATED.**

**Il RUN resta non autorizzato automaticamente da questo seal — passo separato e successivo, a discrezione esplicita dell'utente.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
7.8E:
FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE ✓
(timezone misurato, dati reali hashati, doppia verifica indipendente)
PROSSIMO:
autorizzazione esplicita del RUN
```

Il seal è su GitHub, verificabile riga per riga. La catena è ora completa fino all'ultimo dettaglio tecnico sollevato: hypothesis frozen → VoI → decision rules → execution rules → data identity (misurata, non assunta) → temporal partitions (ricontrollate, non ricalcolate) → tester config (congelata, mai lanciata) → doppio seal verificato → outcomes ancora non visti. Manca solo l'autorizzazione esplicita a eseguire.
