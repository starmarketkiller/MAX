# NEXUS - Phase 7.9C BREAKOUT_ACC Event-Level Parity Decomposition

**Baseline:** `2e991fcf2cf315312e6c6951ce0137fa417d4ce6` (Phase 7.9B). Nessun nuovo Serious backtest, nessuna optimization, nessun cambio strategia, nessun P&L usato per la diagnosi.

**Il punto di partenza è l'obiezione metodologica dell'utente su 7.9B**: "semantic parity = MINOR_DIFFERENCE" non equivale a "Python strategy == MT5 strategy empiricamente" — n=27 (Python) contro n=4 (MT5) è di per sé una divergenza enorme di frequenza, non solo "campione MT5 piccolo". Domanda centrale: **perché Phase E ha osservato solo 4 trade MT5 eseguiti mentre il dataset Python ne suggeriva molto di più?**

---

## 1. Metodo — due stream di segnale indipendenti, granularità identica

**Lato MT5** (`NXS_BreakoutAccSignalDiagnostic.mq5`): script **read-only**, nessun include NEXUS_v1, nessun trading, nessun P&L. Legge le barre D1 **storiche reali** della cache del terminale (2008-2026) con funzioni native (`iHighest`/`iLowest`/`iClose`/`iMA`), replica bar-per-bar la logica esatta di `NXS_Strat_BreakoutAcc()` + il gate HTF nativo (`NEXUS_EA_v2.mq5` righe ~631-646), verificata riga per riga contro il sorgente reale. Classifica ogni barra: `RAW → BLOCKED_COOLDOWN | BLOCKED_HTF | SIGNAL_FIRE`. Bug trovato e corretto in corsa: `FILE_TXT` invece di `FILE_CSV` concatenava i campi senza delimitatore — individuato ispezionando i byte grezzi, corretto, rieseguito (stessi conteggi aggregati).

**Lato Python**: le stesse funzioni **già esistenti** in `server/backtest.py` (`sig_breakout_acc`, `_breakout_acc_cooldown_series`, il gate `htf_native_ema` introdotto in Fase D) — **importate senza alcuna modifica**, applicate agli stessi dati Dukascopy reali già usati da `run_backtest`. Nessuna nuova logica di strategia.

**Scoperta preliminare importante**: il dataset Python originale di Phase E (`n=27`, citato ovunque come riferimento) **non applicava mai `htf_native_ema`** — verificato: `phase_e_breakoutacc_findings.json` non menziona mai "htf_native_ema" o "EMA200". Applicando correttamente il gate HTF nativo (che è reale e attivo per BREAKOUT_ACC, `htf=true` nel profilo), il conteggio Python cambia radicalmente.

## 2. Risultato centrale — gli stream di segnale sono quasi identici in scala

| | MT5 (broker reale) | Python (Dukascopy, stesso motore di gate) |
|---|---|---|
| Barre caricate | 1944 | 2194 |
| Segnali grezzi (Acceptance) | 203 | 228 |
| Bloccati da cooldown | 96 | 127 |
| Bloccati da HTF | 27 | 18 |
| **SIGNAL_FIRE** | **80** | **83** |

**80 vs 83** — non 27 vs 4, non 101 vs 4. Con lo stesso gate applicato su entrambi i lati, la definizione del segnale produce conteggi **comparabili in scala** tra i due motori indipendenti.

## 3. Pairing evento-per-evento

Match per data+direzione, tolleranza ±3 giorni, **mai il P&L usato per decidere un match**: **66 matched**, 14 MT5_ONLY, 17 PYTHON_ONLY (~78-80% match rate). Il residuo è classificato `FEED_BAR_DIFFERENCE` (dominante) — coerente con differenze OHLC reali fra broker (MT5) e Dukascopy (Python) sugli stessi timestamp nominali (2194 vs 1944 barre caricate, un delta reale, verificato), **non** con `RANGE_INDEX_DIFFERENCE`/`COOLDOWN_STATE_DIFFERENCE`/`HTF_GATE_DIFFERENCE` (la logica dei tre gate è identica riga-per-riga su entrambi i lati — un bug di logica produrrebbe un ordine di grandezza diverso, non un residuo del 20-25%).

## 4. Signal parity vs execution parity — separate esplicitamente

**Signal parity: `SIGNAL_PARITY_PARTIAL`.** Scala quasi identica (83 vs 80), ~78-80% match diretto. La definizione del segnale **non è** la causa del gap verso i 4 trade osservati da Phase E.

**Execution parity: la vera scoperta.** MT5 genera **80 SIGNAL_FIRE reali** sui suoi stessi dati storici — ma Phase E ha osservato solo **4 trade effettivamente eseguiti** nel Tester reale (5% di execution rate). Una simulazione deterministica e conservativa "one-position-at-a-time + MaxHold pieno (40 giorni)" applicata agli 80 fire reali riduce il conteggio a **~40 eseguibili**, non a 4. **Il gap residuo (~40 → 4, un fattore 10x) non è attribuito con certezza da questa fase** — i log del Tester run originale di Phase E (16/09) non sono più disponibili nel terminale (verificato: solo `20260917.log` e `20260922.log` presenti), e strumentare un nuovo run diagnostico nel vero Tester è fuori scope di un audit statico/bar-based.

## 5. Verdetto finale

**`EXECUTION_GAP_DOMINANT`.** Il problema non è nella definizione del segnale (parità ragionevole, stessa scala) — è in qualcosa che accade **dopo** il segnale, nel percorso di esecuzione reale MT5 (possibili cause non verificate qui: RiskShield/preflight in `NXS_OpenTrade`, margine, o un problema di history-quality specifico del vero Model=1 su 7,5 anni), onestamente dichiarato **UNKNOWN** nel suo meccanismo esatto piuttosto che indovinato.

## 6. Prossima decisione (NON eseguita in questa fase)

**`FIX_PARITY_BEFORE_STATISTICS`.** Non `REANALYZE_EXISTING_RAW_RESULTS`: né il dataset Python (83 segnali, o le vecchie cifre 27/101 mai riprodotte) né i 4 trade MT5 di Phase E rappresentano fedelmente "quanti trade la strategia oggi formalizzata produrrebbe realmente in esecuzione" — il gate di esecuzione reale (che riduce 80 segnali a soli 4 trade, un fattore ~20x) è esso stesso non caratterizzato. Fare statistica su un campione la cui provenienza non è capita produrrebbe un numero preciso ma privo di significato. Non `DATA_SOURCE_SENSITIVITY_STUDY`: il gap non è primariamente feed-dependent (la signal parity è già buona con feed diversi) — è un gap di esecuzione, categoria concettualmente diversa.

Passo concreto suggerito (non eseguito): strumentare `NXS_OpenTrade` (o un wrapper diagnostico che non modifica la strategia) per loggare la ragione esatta di ogni blocco sui timestamp degli 80 signal_fire già identificati — un esperimento mirato, non un nuovo Serious backtest.

## Questioni aperte dichiarate onestamente

- `n=27` (la cifra Python storicamente citata) **non è stata riprodotta** in questa fase con nessuna combinazione di parametri provata (range osservato: 74-85 con `breakout_acc_cooldown=True`, con/senza `htf_native_ema`) — provenienza esatta non accertata oltre quanto già dichiarato nel file originale.
- Il meccanismo esatto che riduce ~40 (stima one-at-a-time) a 4 trade realmente eseguiti nel Tester reale resta **UNKNOWN**.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog.

## Deliverables

`breakout_acc_python_event_stream_v1.csv/json`, `breakout_acc_mt5_event_stream_v1.csv/json`, `breakout_acc_event_parity_matrix_v1.json`, `breakout_acc_parity_decision_v1.json`, `build_breakoutacc_parity_decomposition.py`, `build_python_event_stream.py`, `verify_breakoutacc_parity_decomposition.py`, `test_phase_7_9c.py`, più i raw file dello script diagnostico MT5 (`server/research_scripts/NXS_BreakoutAccSignalDiagnostic.mq5`, `raw_data/nxs_breakoutacc_mt5_signal_stream.csv`, `raw_data/python_breakoutacc_full_signal_stream.json`).

## Regressione

18/18 PASS sulla nuova suite 7.9C. Regressione Phase 7 completa: invariata rispetto a 7.9B (34/36, i 2 fallimenti noti da 7.8E/7.8H).

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9C: COMPLETATA ✓
BREAKOUT_ACC: signal_parity = SIGNAL_PARITY_PARTIAL (80 MT5 vs 83 Python, 66 matched)
              execution_parity = EXECUTION_GAP_DOMINANT (80 segnali -> 4 trade eseguiti, 5%)
SCOPERTA CENTRALE: NON e' un problema di definizione del segnale (scala comparabile
                    80 vs 83, non piu' 27-vs-4/101-vs-4) - il collasso avviene DOPO
                    il segnale, nell'esecuzione reale MT5, causa esatta UNKNOWN
PROSSIMO: FIX_PARITY_BEFORE_STATISTICS (non eseguito - richiede strumentazione
          del vero Tester per isolare la causa del gap di esecuzione)
```
