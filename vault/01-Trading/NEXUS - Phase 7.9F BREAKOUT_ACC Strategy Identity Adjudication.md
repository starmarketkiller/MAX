# NEXUS - Phase 7.9F BREAKOUT_ACC Strategy Identity Adjudication

**Baseline:** `e78a17e4c738586c4c16805ae8915c6e29874354` (Phase 7.9E). Nessuna modifica all'EA live, nessuna modifica a Python, nessun backtest di performance, nessuna optimization — verificato (hash `NEXUS_EA_v2.mq5`/`NXS_Strategies.mqh`/`server/backtest.py` invariati rispetto a HEAD).

**Domanda centrale**: la mutazione cross-timeframe di `g_breakoutAccState` (scoperta in 7.9E) è parte intenzionale di BREAKOUT_ACC, o un difetto implementativo rispetto all'identità congelata della strategia? Da rispondere PRIMA di forzare la parity Python al comportamento a 4 trade attuale — perché riprodurre fedelmente un bug non è la stessa cosa che riprodurre fedelmente la strategia.

---

## 1. Autorità di specifica — 6 fonti indipendenti, consenso univoco

Raccolte cronologicamente: il commento originale della funzione, il commit `7871e96` (02/09) che introduce il cooldown, il commento sull'input `InpBreakoutAccCooldownBars`, la dichiarazione di profilo `NXS_Profile_TF("BREAKOUT_ACC")=D1`, il registro strategie, e l'audit di identità più recente (Phase 7.9B, 21/09).

**Tutte e 6, senza eccezioni, descrivono il cooldown in termini esclusivamente D1/singola-istanza**: "blocca lo stesso verso per N barre dopo un ingresso", "evitare l'inseguimento ripetuto dello stesso movimento". **Nessuna fonte, in nessun momento della storia del progetto, menziona o giustifica una condivisione cross-timeframe.**

Fatto cronologico rilevante: l'architettura multi-TF (`NXS_CollectAllSignals` con passaggi per timeframe distinto) era già in produzione da **~54 giorni** quando il cooldown è stato introdotto (10/07 vs 02/09) — non era una novità di cui il fix doveva tener conto per la prima volta, ma nemmeno una giustificazione per assumere che la condivisione fosse voluta (zero menzioni in entrambe le direzioni).

**Analogia strutturale rafforzativa**: lo stesso identico pattern (struct globale non scoped per-TF) è stato applicato nello STESSO commit a `BAR_UPDN` (`g_barUpDnState`) — coerente con una svista di design copiato fra due strategie, non una decisione ponderata specifica per BREAKOUT_ACC.

## 2. Semantica del cooldown — risposta esplicita

`InpBreakoutAccCooldownBars=8` nel codice significa oggi: *8 barre di QUALUNQUE `g_activeTF` sia attivo al momento della chiamata* (`cooldownSec = 8 * PeriodSeconds(NXS_EffTF())`, dinamico). L'intento documentato, univoco su 6 fonti: *8 barre D1*. **Discrepanza confermata**, non `UNKNOWN` — l'evidenza documentale è insolitamente non ambigua.

## 3. Architettura "scarta l'output, mantieni l'effetto collaterale"

Sequenza verificata a codice: `NXS_ActivateTF(pass)` → `NXS_Strat_BreakoutAcc()` chiamata **incondizionatamente** (il suo gate dipende solo dal selettore, non dal TF attivo) → muta `g_breakoutAccState` usando il TF del pass corrente → **solo dopo**, nel loop chiamante, `if(NXS_Profile_TF(strat) != passes[p]) continue;` scarta il risultato se il pass non è D1 — **ma lo stato già mutato non viene annullato**. Nessuno scopo funzionale legittimo identificato per le chiamate durante i pass non-D1: il loro output è sempre scartato, solo l'effetto collaterale sopravvive.

**Esempio causale concreto, con timestamp reali**: il 2019.04.17 12:45 il pass M5 trova una propria Acceptance (direzione SELL) e aggiorna `lastFireTime[SELL]`. Il 2019.04.18 00:00, quando il pass D1 trova la propria Acceptance genuina (stessa direzione), il cooldown condiviso appare ancora attivo — il segnale D1 viene bloccato 92 volte nello stesso giorno (rivalutato ad ogni tick M15 finché la barra D1 resta la stessa).

## 4. Replica esatta del router — ordine bit-per-bit reale

Calcolato **programmaticamente** (non a mano) dall'attraversamento di `NXS_StrategyIdAt(0..52)` e `NXS_Profile_TF(id)` per ciascuno, dedup al primo TF distinto: **H1 → D1 → M30 → M15 → H4 → M5** (H1 primo, per `3COMMAS_BOT` in posizione 0 del registro). Rieseguito l'esperimento di 7.9E con questo ordine esatto: `raw=205 cooldown_pass_isolato=95`, **`con stato condiviso e ordine esatto=0`** (non 4). Il meccanismo dominante è confermato con l'ordine reale (collasso quasi totale, stessa direzione/ordine di grandezza), **ma la cifra esatta (4) non è riprodotta** — dichiarato onestamente come limite non risolto in questa fase, non forzato a coincidere.

## 5. Due identità esplicite, nessuna validata

- **`BREAKOUT_ACC_IMPLEMENTED_V1`**: semantica live corrente, cooldown condiviso cross-TF. Risultato empirico: 4 trade/7,5 anni.
- **`BREAKOUT_ACC_INTENDED_D1_V1`**: semantica scoped a D1, supportata dalle 6 fonti documentali. Risultato (solo esperimento diagnostico, mai un Serious backtest): 95 post-cooldown / 75 post-HTF.

Nessuna delle due è "validata" in questa fase — la scelta di quale sia canonica è l'oggetto del verdetto, non un fatto assunto a priori.

## Verdetto finale

**`IMPLEMENTATION_DEFECT_CONFIRMED`.** Il codice condivide lo stato di cooldown fra tutti i timeframe del router multi-TF; la specifica documentata (6 fonti indipendenti, incluso l'audit 7.9B scritto 19 giorni DOPO che il comportamento cross-TF era già in produzione, senza mai notarlo) descrive univocamente un cooldown scoped a D1. Non classificato come `SPEC_AMBIGUOUS`: l'evidenza è insolitamente concorde, non contrastante. Non classificato come `ROOT_CAUSE_CONFIRMED_BUT_INTENT_UNRESOLVED`: il meccanismo esatto (non solo l'esistenza di una causa) è isolato con un esempio causale concreto e l'ordine reale dei pass — resta non riprodotta solo la cifra finale esatta, non l'identità della causa né l'intento documentato.

## Prossima decisione (NON eseguita)

**`FIX_LIVE_IMPLEMENTATION_THEN_REESTABLISH_PARITY`.** La strategia canonica per la ricerca futura è `BREAKOUT_ACC_INTENDED_D1_V1`, non l'implementazione contaminata. **I 4 trade osservati in 7,5 anni non sono più evidenza valida sulla strategia D1 intesa — sono evidenza sulla sua implementazione contaminata.** Passo concreto suggerito (non eseguito, richiede esplicita autorizzazione a modificare l'EA live): scoping di `g_breakoutAccState` per timeframe → recompile → verifica di parity fra nuova implementazione e replica offline corretta → solo allora un nuovo Serious backtest.

**Nessuna replica del bug è stata portata in Python in questa fase** — riprodurre fedelmente un'implementazione probabilmente sbagliata avrebbe prodotto una "vittoria tecnica" di parity ma una pessima scelta scientifica.

## Cronologia storica preservata (non cancellata)

- **7.9C**: `EXECUTION_GAP_DOMINANT` — apparente gap di esecuzione (80 vs 4)
- **7.9D**: il funnel di esecuzione è in realtà pulito (0 blocchi, 4/4 aperti)
- **7.9E**: scoperta della contaminazione di stato cross-timeframe come meccanismo dominante
- **7.9F**: la contaminazione è un difetto implementativo rispetto all'identità documentata, non semantica intenzionale

Tutti gli artifact 7.9C/7.9D/7.9E restano **frozen, non modificati**.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog. **EA live e Python non modificati.**

## Deliverables

`breakout_acc_strategy_identity_authority_v1.json`, `breakout_acc_implemented_vs_intended_semantics_v1.json`, `breakout_acc_exact_router_replication_v1.json`, `breakout_acc_identity_adjudication_v1.json`, 3 builder, verificatore indipendente (verifica anche EA live/Python byte-identici a HEAD), 27 test di consistenza (27/27 PASS), vault report, più i raw output del run diagnostico con ordine esatto (`nxs_breakoutacc_sharedstate_diag_exactorder*`, `nxs_breakoutacc_sharedstate_allfires.csv`).

## Regressione

- **Suite propria 7.9F**: 27/27 PASS
- **Phase 7 totale inclusa la suite corrente**: 38/40 PASS
- **Fallimenti noti legacy** (esclusa la suite corrente, 39 rimanenti): 2/39 — invariati (7.8E, 7.8H)

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9F: COMPLETATA ✓
BREAKOUT_ACC:
  execution funnel: pulito (7.9D)
  root cause cross-TF: confermata (7.9E)
  parity esatta: NON raggiunta (0 vs 4, causa dominante comunque provata)
  identita' canonica: BREAKOUT_ACC_INTENDED_D1_V1 (non l'implementazione attuale)
VERDETTO: IMPLEMENTATION_DEFECT_CONFIRMED - i 4 trade osservati NON sono
          piu' evidenza valida sulla strategia D1 intesa
PROSSIMO: FIX_LIVE_IMPLEMENTATION_THEN_REESTABLISH_PARITY - scoping per-TF
          di g_breakoutAccState, poi parity, poi (solo allora) un nuovo
          dataset - richiede autorizzazione esplicita, non eseguito
```
