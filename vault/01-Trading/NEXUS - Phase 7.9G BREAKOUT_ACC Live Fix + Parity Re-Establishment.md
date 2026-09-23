# NEXUS - Phase 7.9G BREAKOUT_ACC Live Fix + Parity Re-Establishment

**Baseline:** `8d2cde76f4233aa0da3ffa83778eee421a60093c` (Phase 7.9F). **Prima modifica all'EA live in questa serie di fasi, esplicitamente autorizzata dall'utente** per correggere il difetto implementativo confermato (`IMPLEMENTATION_DEFECT_CONFIRMED`, Phase 7.9F). Nessuna optimization, nessun parameter tuning, nessun cambio di design performance-driven.

---

## 1. Freeze pre-fix + fix minimale

Congelati gli hash sorgente pre-fix (`NXS_Strategies.mqh` sha256 `eb7888db...`) insieme al meccanismo del difetto e alle due identità (`BREAKOUT_ACC_IMPLEMENTED_V1` / `BREAKOUT_ACC_INTENDED_D1_V1`, già definite in 7.9F).

**Fix applicato** (`NXS_Strategies.mqh`, `NXS_Strat_BreakoutAcc()`): una guardia precoce subito dopo `tf = NXS_EffTF()`, **prima** di qualunque lettura/scrittura di `g_breakoutAccState`:

```mql5
if(tf != NXS_Profile_TF("BREAKOUT_ACC")) return s;
```

Usa `NXS_Profile_TF()` come fonte di verità (non un `PERIOD_D1` hardcoded) per rispettare anche il meccanismo esistente `InpScalpTFOverride` se mai attivato. **Nessun'altra logica toccata**: range (n=20), shift semantics, trigger a doppia chiusura, cooldown (8 barre, invariato), SL/TP, gate HTF, trailing, risk sizing, architettura del router.

## 2. BAR_UPDN — solo segnalazione, nessun fix

`BAR_UPDN` ha lo stesso identico pattern strutturale (`g_barUpDnState`, introdotto nello stesso commit del 02/09) — **non corretto in questa fase** (l'autorizzazione copriva solo BREAKOUT_ACC). Backlog item creato: `POSSIBLE_SAME_SCOPING_DEFECT_BAR_UPDN`.

## 3. Recompile + freeze identità post-fix

Compilazione: **0 errori, 2 warning** — gli stessi due già noti e non correlati (macro `NXS_MAX_SIGNALS` redefinition, conversione `ulong→long`). Nuovo hash `NXS_Strategies.mqh`: `9f7bb47a...`. `NEXUS_EA_v2.mq5` invariato (hash identico pre/post — solo l'header è cambiato).

## 4. Verifica statica

Provato dal codice, non assunto: il guard precede testualmente **ogni** occorrenza di `g_breakoutAccState.` nel corpo della funzione. Prova esplicita per ciascuno dei 6 pass reali: D1 → consentito; H1/M30/M15/H4/M5 → non toccato (return immediato).

## 5. Run diagnostico di parity post-fix — risultato sorprendentemente forte

Stessa identica configurazione di Phase E/7.9D (selector=9, D1, Model=1, 2019-2026, RAW, lotto fisso 0.01, leva 1:500), runtime ~3h35m. **Certificato reale**:

```
generated=67  blocked=11  opened=47  broker_reject=9
```

(accounting riconciliato: 11+9+47=67). **Da 4 trade pre-fix a 47 trade reali post-fix** — un salto di oltre 10x. Il gate `OPEN_POSITION` (10 occorrenze) ora è finalmente significativo, com'era atteso con una frequenza di segnale realistica.

## 6-8. Confronto a tre vie — parity same-feed quasi-esatta

| Stream | Definizione | N |
|---|---|---|
| **A** — EA live post-fix | Certificato/Journal reale | **67** |
| **B** — MQL5 offline isolato a D1 | Script 7.9E, già D1-only per costruzione, nessuna modifica necessaria | **75** |
| **C** — Python | `server/backtest.py:sig_breakout_acc`, invariato, mai esposto alla contaminazione cross-TF | **83** |

**Same-feed parity (A vs B, stesso feed broker/cache)**, pairing per data+direzione (tolleranza 3gg): **matched=67, only_b=0 (0%), only_a=8 (10.7% di B)**. **Tutti e 67 gli eventi generati dal vero EA hanno una controparte identica nella ricostruzione offline** — il fix spiega il 100% del comportamento reale osservato. Residuo: 8 eventi che la ricostruzione idealizzata prevede ma il vero Tester non genera (date esatte nell'artifact) — dichiarato onestamente come **residuo aperto**, non nascosto, non ulteriormente diagnosticato in questa fase.

Confronto con il pre-fix: il gap era 95% inspiegato (76/80); ora è un residuo del 10.7%, e — criticamente — **asimmetrico nella direzione giusta**: zero eventi reali senza spiegazione offline, solo eventi offline "in eccesso" rispetto alla realtà (friction realistica del vero Tester, non ancora isolata nel dettaglio).

## 9. Python — nessuna modifica necessaria

`server/backtest.py` non è mai stato esposto alla contaminazione cross-TF (il motore Python simula una strategia alla volta su un solo TF, senza il loop multi-pass dell'EA MQL5) — **`sig_breakout_acc`/`_breakout_acc_cooldown_series` erano già, per costruzione, la rappresentazione corretta di `BREAKOUT_ACC_INTENDED_D1_V1`**. Nessuna modifica applicata in questa fase.

## 10. Criterio di parity — mai il P&L

Decisione basata esclusivamente su: identità evento, timestamp, direzione, stato (esito cooldown/HTF). Mai PF, expectancy, win rate, DD.

## 11-12. Migrazione di identità canonica + invalidazione esplicita dell'evidenza storica

Con parity superata (quasi-esatta, criterio dichiarato: 0% residuo lato EA reale, <15% lato offline):

- `BREAKOUT_ACC_IMPLEMENTED_V1` → **`DEPRECATED_HISTORICAL_CONTAMINATED_IMPLEMENTATION`**
- `BREAKOUT_ACC_INTENDED_D1_V1` → **canonica**, ma esplicitamente **`NOT_YET_VALIDATED`** (nessuna promozione a evidenza sull'edge — richiede il dataset canonico dedicato, fase successiva)

Marcati esplicitamente (nessun artifact cancellato o modificato): i 4 trade di Phase E e il risultato 7.9D → `HISTORICAL_IMPLEMENTATION_EVIDENCE` / `NOT_EVIDENCE_FOR_CANONICAL_D1`.

## 13. Gate alla fase successiva

**`next_decision = BUILD_CANONICAL_BREAKOUT_ACC_DATASET`** — non eseguito in questa fase.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog. 7.9C/7.9D/7.9E/7.9F restano frozen, non modificati.

## Deliverables

`breakout_acc_live_fix_before_after_v1.json`, `breakout_acc_fixed_identity_v1.json`, `breakout_acc_postfix_signal_parity_v1.json`, `breakout_acc_stale_evidence_reclassification_v1.json`, `breakout_acc_phase7_9g_decision_v1.json`, `breakout_acc_bar_updn_structural_warning_v1.json`, builder, verificatore indipendente (verifica anche che solo `NXS_Strategies.mqh` sia cambiato e che Python sia invariato), 29 test di consistenza (29/29 PASS), vault report.

## Regressione

- **Suite propria 7.9G**: 29/29 PASS
- **Phase 7 totale inclusa la suite corrente**: 35/41 PASS
- **Fallimenti — 6 totali, tutti spiegati, nessuna regressione reale**:
  - 2 **noti da prima** (7.8E whole-file-hash legacy, 7.8H riferimento a EX5 non aggiornato) — invariati.
  - **4 nuovi, tutti con la STESSA causa attesa**: `test_phase_7_9b.py`, `test_phase_7_8i.py`, `test_phase_7_9e.py`, `test_phase_7_9f.py` verificano (nei loro verificatori indipendenti) che `NXS_Strategies.mqh` sia byte-identico a un hash congelato PRIMA di questa fase — ora legittimamente diverso a causa del fix autorizzato. Non sono regressioni: sono la conseguenza diretta, prevista e corretta della modifica live autorizzata in 7.9G. Nessun altro tipo di fallimento presente in nessuna delle 4 suite (verificato leggendo il dettaglio di ciascuna).

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9G: COMPLETATA ✓
BREAKOUT_ACC: fix live applicato (guard TF-scoped, minimale)
              4 trade pre-fix -> 47 trade post-fix (10x)
              same-feed parity: 100% EA reale spiegato, 10.7% residuo solo offline
              identita' canonica: BREAKOUT_ACC_INTENDED_D1_V1 (NOT_YET_VALIDATED)
PROSSIMO: BUILD_CANONICAL_BREAKOUT_ACC_DATASET - non eseguito
          poi: EDGE DECOMPOSITION -> PATH ANATOMY -> NATURAL HORIZON -> MECHANISM DISCOVERY
```
