# NEXUS - Phase 7.9E BREAKOUT_ACC Offline-vs-Live Signal Semantics Decomposition

**Baseline:** `ee469d4fa62a6c6aba8b228c16a422540e05c189` (Phase 7.9D). Nessun cambio strategia, nessuna optimization, nessuna analisi di performance, nessun rescue, **nessuna modifica all'EA live** (verificato: hash `NEXUS_EA_v2.mq5`/`NXS_Strategies.mqh` invariati rispetto a HEAD).

**Obiettivo**: la 7.9D ha dimostrato che il funnel di esecuzione è pulito (0 blocchi, 4/4 trade identici a Phase E) — quindi il gap 80-vs-4 non è mai stato esecutivo. Questa fase identifica **dove esattamente**, nella generazione del segnale, la ricostruzione offline (7.9C read-only + funzione Python pre-esistente) diverge dal vero collector live.

---

## Metodo: due esperimenti diagnostici nel vero Tester, zero rischio

Due nuovi EA standalone (nessuna inclusione di `NEXUS_v1`, nessun ordine, nessuna modifica all'EA live), eseguiti nel Tester reale (Model=1, stessa finestra 2019.02.03–2026.08.15):

- **Esperimento A** (`NXS_BreakoutAccCadenceDiagnostic.mq5`): replica fedele della cadenza reale — New Bar Gate su M15 (come `OnTick`), poi tentativo di attivazione D1 con gli **stessi 10 handle indicatori** del router reale (ADX/RSI/Bollinger/MACD/SAR/ATR/EMA200/EMA9/EMA21/Ichimoku — nessuno dei quali usato da BREAKOUT_ACC), poi — solo se l'attivazione riesce — controllo Acceptance identico a `NXS_Strat_BreakoutAcc()`. Stato di cooldown **isolato** (solo D1 lo tocca), come baseline di controllo.
- **Esperimento B** (`NXS_BreakoutAccSharedStateDiagnostic.mq5`): stessa cadenza, ma con lo stato di cooldown **condiviso fra 6 pass multi-TF** (M5/M15/M30/H1/H4/D1) ad ogni tick M15 — esattamente come fa il router reale, dove `NXS_Strat_BreakoutAcc()` viene richiamata ad OGNI pass (il suo gate di selettore non dipende dal TF attivo).

## Risultato 1 — cadenza e attivazione indicatori: ESCLUSE come causa

`n_m15_passes=177808`, `n_activation_success=177808`, `n_activation_fail=0`, `n_new_d1_bar_after_success=1944` (= il numero reale di barre D1 nella finestra). Ogni singola nuova barra D1 viene correttamente rilevata e valutata. Nessun fallimento di attivazione indicatori su ~178mila tentativi. `EVALUATION_CADENCE_DIFFERENCE` è **esclusa**.

## Risultato 2 — la matematica c1/c2/range dello script 7.9C: nessun bug

Riverificata algebricamente la parametrizzazione ad array ascendente dello script 7.9C: con la sostituzione `I = i+1` (I = barra shift0/appena aperta), gli indici usati (`c1=rates[i]`, `c2=rates[i-1]`, range `[i-21,i-2]`, evento riportato a `rates[i+1].time`) coincidono **esattamente** con gli shift reali (`c1=shift1`, `c2=shift2`, range shift[3..22], evento a shift0). Nessun bug di indicizzazione — il sospetto iniziale era sbagliato.

## Risultato 3 — il gate HTF (shift0 vs shift1): contributo reale ma minore

Il gate HTF reale usa `px200 = iClose(EffTF, shift0)` — la barra D1 **ancora in formazione**, non la chiusura confermata (shift1) usata dagli script offline precedenti. Testato empiricamente per la prima volta: riduce 95→75 cooldown-pass (-21%). Reale, ma **non dominante**.

## Risultato 4 — la scoperta centrale: stato condiviso cross-timeframe

`g_breakoutAccState` (`NXS_Strategies.mqh:1531-1532`) è un **unico struct globale**, non scoped per-timeframe. `NXS_Strat_BreakoutAcc()` viene richiamata **una volta per ogni pass multi-TF** del router (M5/M15/M30/H1/H4/D1, l'insieme completo di timeframe usati da *qualunque* strategia nel registro, non solo da quelle abilitate dal selettore) — perché il suo gate `NXS_SelectorAllows(9)` non dipende dal TF attivo. Un pass su un timeframe più veloce (H4, M30...) che trova una propria "Acceptance" sui *suoi* bar aggiorna `lastFireTime` con un timestamp molto più recente — quando arriva il pass D1 vero, il cooldown condiviso appare erroneamente ancora attivo.

**Prova sperimentale diretta**: Esperimento A (stato isolato) → 95 cooldown-pass, 75 post-HTF — stesso ordine di grandezza della stima offline 7.9C (80). Esperimento B (stato condiviso, stessa run) → **0** segnali D1 sopravvivono, con 12.234 "spari" su altri timeframe che hanno continuamente toccato/sporcato lo stato condiviso. Collasso quasi totale, stessa direzione e ordine di grandezza del vero gap osservato (95/75 offline vs 4 EA reale). Lo scarto residuo fra 0 (esperimento semplificato) e 4 (EA reale) è attribuito all'ordine esatto dei pass nel registro reale, non riprodotto bit-per-bit — dichiarato onestamente come limite, non forzato a coincidere.

## Forensics su 3 eventi specifici (2019-04-18, 2019-05-15, 2019-06-21)

Tutti e tre risultano **pienamente validi in isolamento** (setup, trigger, cooldown E gate HTF tutti soddisfatti secondo l'Esperimento A) ma **assenti nell'EA reale** (nessuno dei 4 `signal_id` del run 7.9D corrisponde a queste date). Il pattern è identico per tutti e tre: la logica di BREAKOUT_ACC stessa non è la causa — la spiegazione è la contaminazione dello stato condiviso, dimostrata a livello di meccanismo (non isolato l'evento specifico su un altro TF che ha sporcato lo stato in ciascuna data esatta — fuori scope).

## Verdetto finale

**`STATE_SEMANTICS_MISMATCH`.** Causa primaria: stato di cooldown BREAKOUT_ACC condiviso indebitamente fra tutti i timeframe del router multi-TF, non scoped al proprio TF di profilo (D1). Causa secondaria minore: semantica shift0 del gate HTF, mai testata prima. Cadenza, attivazione indicatori e indicizzazione bar-shift: escluse con prove dirette.

## Prossima decisione (NON eseguita)

**`BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY`.** Il meccanismo causale è identificato con prove sperimentali dirette, ma nessuna replica offline è stata corretta e verificata a produrre esattamente i 4 eventi reali (date/direzioni esatte) — il target di parity dichiarato non è raggiunto. `REBUILD_CANONICAL_BREAKOUT_ACC_DATASET` sarebbe prematuro per la stessa ragione già identificata dalla 7.9D. Passo concreto suggerito (non eseguito): correggere la replica Python (`server/backtest.py:sig_breakout_acc`/`_breakout_acc_cooldown_series`) per condividere lo stato di cooldown fra tutti i timeframe usati da qualunque strategia nel motore di backtest — replicando fedelmente il comportamento reale, non "correggendo" la strategia — con un artifact before/after congelato e prova di parity esatta prima di qualunque nuova statistica.

## Storico superato, non cancellato

- **7.9C**: `EXECUTION_GAP_DOMINANT` — assumeva che gli 80 SIGNAL_FIRE offline fossero equivalenti ai segnali GENERATED reali. Artifact **non modificato**.
- **7.9D**: il funnel di esecuzione è pulito — l'assunzione 7.9C era nel posto sbagliato. Artifact **non modificato**.
- **7.9E**: il vero gap è nella generazione del segnale stesso, causato da contaminazione di stato cross-timeframe nel router live — non un problema di esecuzione né (principalmente) di feed/gate HTF.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog. **L'EA live non è stato modificato** — solo due nuovi script diagnostici standalone, a rischio zero, non inclusi da nessun file live.

## Deliverables

`breakout_acc_live_vs_offline_semantics_diff_v1.json`, `breakout_acc_missing_event_forensics_v1.json`, `breakout_acc_reconstruction_parity_v1.json`, `breakout_acc_reconstruction_decision_v1.json`, 3 builder, verificatore indipendente, 22 test di consistenza (22/22 PASS), vault report, più i due script diagnostici standalone (`server/research_scripts/NXS_BreakoutAccCadenceDiagnostic.mq5`, `NXS_BreakoutAccSharedStateDiagnostic.mq5`) e i raw output dei run reali.

## Regressione

- **Suite propria 7.9E**: 22/22 PASS
- **Phase 7 totale inclusa la suite corrente**: 37/39 PASS
- **Fallimenti noti legacy** (esclusa la suite corrente, 38 rimanenti): 2/38 — invariati (7.8E, 7.8H).

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9E: COMPLETATA ✓
BREAKOUT_ACC: execution funnel = pulito (7.9D)
              signal generation = STATE_SEMANTICS_MISMATCH (7.9E)
SCOPERTA CENTRALE: g_breakoutAccState e' globale, condiviso fra TUTTI i
                    timeframe del router multi-TF - un TF piu' veloce
                    "sporca" il cooldown prima che D1 possa sparare -
                    provato sperimentalmente: 95(isolato)->0(condiviso),
                    reale=4
PROSSIMO: BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY - correggere la
          replica Python per condividere lo stato cross-TF, poi
          verificare parity esatta 4/4 - non eseguito
```
