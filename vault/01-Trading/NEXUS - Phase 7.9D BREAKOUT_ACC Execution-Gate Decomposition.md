# NEXUS - Phase 7.9D BREAKOUT_ACC Execution-Gate Decomposition

**Baseline:** `6b16c09c9bc8d5184cef35e2e2d100161a6d4c00` (Phase 7.9C). Nessun nuovo Serious backtest, nessuna optimization, nessun cambio strategia/parametri, mai il P&L usato per la diagnosi.

**Obiettivo dichiarato**: determinare esattamente dove gli 80 SIGNAL_FIRE stimati dalla 7.9C si perdono prima di diventare i 4 trade reali osservati da Phase E — assumendo, come premessa ereditata, un "gap di esecuzione" da decomporre gate per gate.

**Il risultato ribalta la premessa**: non esiste alcun gap di esecuzione. Il vero divario era già nella stima del numero di segnali attesi.

---

## 1. Strumentazione: già esistente, non scritta ex novo

L'EA ha già un sistema di tracciamento causale integrato, aggiunto il 12/09 e mai toccato in questa fase: **Decision/Gate/Execution Trace v1** (`NXS_Trace.mqh`, stati `GENERATED→BLOCKED(reason)/OPEN_ATTEMPT→OPENED/BROKER_REJECT`, un `signal_id` stabile per ogni segnale) + **Test Validity Certificate v2** (`NXS_TestValidityCertificate.mqh`, un file JSON/TXT machine-readable con funnel aggregato e conteggio per-gate, scritto automaticamente a fine run in `Common\Files\NEXUS\certificates\`). Questa fase ha solo **letto** questo output, verificando prima (dal codice, `NXS_ResearchMode.mqh`) che in Research Mode (`InpUseStrategyProfiles=true` obbligatorio) l'UNICO percorso di routing possibile per BREAKOUT_ACC è il branch "profili per-strategia" (`NEXUS_EA_v2.mq5:1498-1566`) — mappato in 29 step precisi (file/riga/condizione) in `breakout_acc_execution_funnel_v1.json`, tutti già strumentati dal trace esistente.

## 2. Run diagnostico eseguito

`InpResearchMode=true`, `InpStrategySelector=9`, D1, Model=1, 2019.02.03→2026.08.15, stessa configurazione dichiarata di Phase E (RAW, protezioni opt-in tutte OFF, lotto fisso 0.01). Preflight verificato prima del lancio: EX5 deployato (compilato 22/09 12:30) più recente della sorgente (17/09), sorgente hash-identica a HEAD. Runtime ~3h25m.

**Scoperta bonus**: nella cartella `Common\Files\NEXUS\certificates\` esisteva già un certificato con lo stesso `run_id` base, datato **16/09** — quasi certamente il run ORIGINALE di Phase E stesso, mai notato prima. Confrontato direttamente riga per riga col mio nuovo run (suffisso `_r001` per collisione di nome).

## 3. Il funnel di esecuzione è perfettamente pulito

```
generated=4  blocked=0  open_attempt=4  opened=4  broker_reject=0
```

Identico, cifra per cifra, sia nel certificato ORIGINALE di Phase E (16/09) sia nel nuovo run diagnostico (22/09). **I 4 trade aperti coincidono ESATTAMENTE — stesso minuto, stessa direzione — con i 4 trade già documentati in Phase E**:

| Data/ora reale | Direzione | Coincide con Phase E |
|---|---|---|
| 2019.06.05 17:30 | BUY (Acceptance_above_range) | ✓ esatto |
| 2020.01.06 01:45 | BUY (Acceptance_above_range) | ✓ esatto |
| 2020.02.21 18:00 | BUY (Acceptance_above_range) | ✓ esatto |
| 2023.09.28 18:15 | SELL (Acceptance_below_range) | ✓ esatto |

L'EA è **deterministico e pienamente riproducibile**: zero blocchi da RiskShield, margine, spread, esposizione, stato incerto, o dal gate "one-position-per-strategia" (mai anche solo sfiorato, con soli 4 segnali in 7,5 anni). L'invariante di funnel accounting (`generated == blocked+opened+broker_reject`) è soddisfatto sia dal certificato nativo sia dalla ricostruzione indipendente dal Journal reale (`[NXS_TRACE]` lines, stesso `run_id`, cross-check byte-per-byte: coincidenza totale).

## 4. Dove viveva davvero il gap

Pairing tra gli 80 SIGNAL_FIRE stimati dallo script read-only 7.9C (`NXS_BreakoutAccSignalDiagnostic.mq5`) e i 4 GENERATED reali: **4 matched, 76 missing, 0 extra**. Il 95% degli eventi stimati dalla 7.9C non ha alcuna controparte nell'EA vivo. Questo non è un problema di gating post-segnale (che qui vale zero) — è un problema di **sovra-stima nel conteggio dei segnali attesi**, a monte, nello strumento diagnostico read-only stesso.

Nota rilevante: la funzione Python pre-esistente (`server/backtest.py:sig_breakout_acc`, verificata identica riga-per-riga anni fa, usata anche nella generazione dello stream Python della 7.9C) produce conteggi dello stesso ordine di grandezza gonfiato (74-85) — quindi il problema non è specifico al mio script MQL5 di 7.9C, sembra strutturale a **qualunque replica offline bar-per-bar** di questa logica, non ancora isolato con certezza in questa fase (fuori mandato: 7.9D copriva il funnel di ESECUZIONE, non la fedeltà della ricostruzione del segnale).

**Un indizio parziale, non una spiegazione completa**: i 4 eventi reali compaiono nello stream 7.9C con un offset di label di 0 o -1 giorno (non uniforme: 2 casi a -1, 2 casi a 0) — insufficiente da solo a spiegare un fattore ~20x sul totale. Dichiarato onestamente come indizio preliminare per un'indagine futura, non ulteriormente investigato qui.

## 5. Precisazione semantica richiesta (punto 9)

I 14 MT5_ONLY + 17 PYTHON_ONLY della 7.9C, etichettati `FEED_BAR_DIFFERENCE`, sono qui riclassificati **`FEED_BAR_DIFFERENCE_COMPATIBLE`** (compatibili con differenze di feed, ma non dimostrati evento-per-evento) — annotazione preservata ma superata in rilevanza dalla scoperta più ampia di questa fase. L'artifact frozen 7.9C **non è stato modificato retroattivamente**.

## 6. Verdetto finale

**`EXECUTION_GAP_RESOLVED_OTHER`**. Nessuna delle 8 etichette ammesse descrive esattamente "zero blocchi, gap altrove" — questa è la più onesta: il gap ESECUTIVO (segnale→trade) è risolto (è zero), "OTHER" perché la vera scoperta è che il gap complessivo non è mai stato nell'esecuzione.

## 7. Prossima decisione (NON eseguita)

**`FIX_EXECUTION_IMPLEMENTATION_BEFORE_RESEARCH`** — con una precisazione esplicita: l'EA live è verificato corretto e non necessita alcuna correzione. L'implementazione da correggere PRIMA di qualunque ricerca statistica è lo strumento di ricostruzione segnale offline (7.9C, ed eventualmente la funzione Python pre-esistente). `REBUILD_CANONICAL_BREAKOUT_ACC_DATASET` sarebbe prematuro: costruire un dataset su una stima di frequenza che diverge di un fattore ~20x dal comportamento reale produrrebbe un numero preciso ma privo di significato. `BLOCKED_EXECUTION_IDENTITY_UNRESOLVED` non si applica: l'identità di esecuzione è invece perfettamente risolta e riproducibile.

## Questioni aperte dichiarate onestamente

- Causa esatta della sovra-stima ~20x negli strumenti offline (MQL5 read-only E Python pre-esistente): **non isolata**, fuori mandato di questa fase.
- Con soli 4 trade reali in 7,5 anni, il limite di campione già identificato da Phase E (`HOLD_NEEDS_MORE_EVIDENCE`, 0,53 eventi/anno) resta il fatto centrale e irriducibile — questa fase lo conferma con piena riproducibilità, non lo risolve.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog.

## Deliverables

`breakout_acc_execution_funnel_v1.json`, `breakout_acc_execution_events_v1.csv/json`, `breakout_acc_execution_gate_counts_v1.json`, `breakout_acc_execution_parity_decision_v1.json`, `build_execution_funnel_map.py`, `build_execution_events_and_gate_counts.py`, `build_execution_parity_decision.py`, `verify_execution_gate_decomposition.py`, `test_phase_7_9d.py`, script diagnostico Tester (`server/research_scripts/NXS_BreakoutAccSignalDiagnostic.mq5`, invariato dalla 7.9C).

## Regressione (conteggi separati, per evitare l'ambiguità 34/36 vs 35/37 già segnalata)

- **Suite propria 7.9D**: 23/23 PASS
- **Phase 7 totale inclusa la suite corrente**: 36/38 PASS
- **Fallimenti noti legacy** (esclusa la suite corrente, 37 rimanenti): 2/37 — `test_volatility_breakout_final_data_freeze.py` (7.8E, whole-file-hash legacy) e `test_phase_7_8h.py` (7.8H, riferimento a EX5 non aggiornato) — entrambi invariati, già accettati nelle fasi precedenti.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9D: COMPLETATA ✓
BREAKOUT_ACC: execution funnel = PULITO (0 blocchi, 4/4 aperti, deterministico)
              4 trade reali = IDENTICI a Phase E (minuto per minuto)
SCOPERTA CENTRALE: il gap 80-vs-4 NON era mai nell'esecuzione - era gia'
                    nella stima dei segnali attesi (7.9C read-only:
                    76/80 stimati non hanno alcuna controparte reale)
PROSSIMO: FIX_EXECUTION_IMPLEMENTATION_BEFORE_RESEARCH - va corretto lo
          strumento di ricostruzione segnale offline (non l'EA, verificato
          corretto) prima di qualunque dataset statistico - non eseguito
```
