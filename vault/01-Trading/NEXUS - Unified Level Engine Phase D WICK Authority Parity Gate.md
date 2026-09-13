# Unified Level Engine — Phase D: WICK authority parity gate + migration readiness

Segue [[NEXUS - Unified Level Engine Phase C WICK Read Path Migration]] (commit `8c8e643`, PASS_TO_PHASE_D). Selector 55 non toccato. `SNxsWickSide`/`SNxsWickReclaimState` non rimossi. `NXS_Structure.mqh`, `NXS_Reaction.mqh`, execution, SL/TP, risk, strategy registry, Global New-Bar Gate: invariati.

## File modificati (permanenti)

| File | Modifica |
|---|---|
| `MQL5/Include/NEXUS_v1/NXS_ReactionEngine.mqh` | aggiunta `NXS_LevelEngine_PrintStateConsistency()` — diagnostica pura (solo `Print`, nessuna mutazione), confronta a fine run `level_id`/`consumed`/`invalidated`/`last_attempt_bar` legacy vs registro per il livello corrente di ogni lato, e scansiona l'intero registro per livelli "vecchi" rimasti non-terminali |
| `MQL5/Experts/NEXUS_EA_v2.mq5` | 1 chiamata aggiunta in `OnDeinit` (`NXS_LevelEngine_PrintStateConsistency()`) |

**Nessuna traccia della fault injection temporanea** (vedi §5): `git diff` su `NXS_Strategies_Experimental.mqh` conferma **0 righe di differenza** rispetto al commit Fase C — l'iniezione è stata aggiunta, testata e rimossa completamente prima di questo commit.

Compilazione finale: **0 errori, 2 warning preesistenti** (invariati dalle fasi precedenti).

## 1. Run matrix

| # | Finestra | Config | Selettore | sha256(NEXUS_trades.csv) | Trade |
|---|---|---|---|---|---|
| 1 | Corta (14gg, 2026-06-01→06-15) | LEGACY (ReadPath=false) | 54 | `513aeb1f4f675ab5...decfdce9e6a` | vedi §2 |
| 2 | Corta | NEW-authority (ReadPath=true) run #1 | 54 | `513aeb1f4f675ab5...decfdce9e6a` | idem |
| 3 | Corta | NEW-authority run #2 (determinismo) | 54 | `513aeb1f4f675ab5...decfdce9e6a` | idem |
| 4 | Lunga (30gg, 2026-06-01→07-01) | LEGACY (ReadPath=false) | 54 | `979325de0339d2d5...48a9d44` | 146 (73+73) |
| 5 | Lunga | NEW-authority run #1 | 54 | `979325de0339d2d5...48a9d44` | idem |
| 6 | Lunga | NEW-authority run #2 (determinismo) | 54 | `979325de0339d2d5...48a9d44` | idem |

Tutte e 6 le run usano lo stesso EA compilato, stessa history GOLD H4, stesso `InpWickSweep_*`. L'unica variabile cambiata fra riga 1/4 e 2-3/5-6 è `InpLevelRegistry_WickReadPath`.

### Campi confrontati (oltre allo sha256, che li copre tutti bit-a-bit)

Poiché lo sha256 dell'intero CSV coincide su ogni riga (1-2-3 fra loro, 4-5-6 fra loro), ogni singolo campo richiesto (trade count, entry/exit timestamp, direction, entry/SL/TP, exit reason, PnL) è per costruzione identico — non serve un confronto colonna-per-colonna separato quando l'artefatto intero combacia. Report `.htm` confermano PF/DD/balance finale identici (finestra lunga: Profitto -12.57, DD 82.49/7.94%, PF 0.95 — stessi valori di Fase B/C).

## 2. Determinismo

Righe 2-3 (corta) e 5-6 (lunga) della matrice sopra sono coppie di run identiche in autorità new-engine: **stesso sha256 in entrambi i casi**. Determinismo confermato, nessuna divergenza fra ripetizioni.

## 3. Decision checks / mismatch / fallback

| Run | checks | mismatches | field_mismatches (state-check) | stale_active_levels |
|---|---|---|---|---|
| Corta, LEGACY | 804 | 0 | 0 | 0 |
| Corta, NEW #1 | 804 | 0 | 0 | 0 |
| Corta, NEW #2 | 804 | 0 | 0 | 0 |
| Lunga, LEGACY | 1718 | 0 | 0 | 0 |
| Lunga, NEW #1 | 1718 | 0 | 0 | 0 |
| Lunga, NEW #2 | 1718 | 0 | 0 | 0 |

**mismatch = 0 e fallback_due_to_mismatch = 0 su tutte le 6 run.** `total_levels` nel registro: 104 (finestra corta), 224 (finestra lunga) — coerente con Fase B/C.

## 4. State-consistency check (nuovo, Fase D)

`NXS_LevelEngine_PrintStateConsistency()` confronta a fine run, per il livello attivo di ciascun lato:

- `level_id` legacy (`g_wickHigh.id`/`g_wickLow.id`) vs presenza nel registro — **sempre trovato** (nessun `field=existence` mai emesso)
- `consumed` legacy vs registro — **0 discrepanze**
- `invalidated` (derivato da `g_wickHigh.level<=0`/`g_wickLow.level<=0` sul lato legacy) vs registro — **0 discrepanze**
- `last_attempt_bar` legacy vs registro — **0 discrepanze**
- scansione dell'intero registro per livelli "sostituiti" (id diverso da quello corrente per il proprio lato) rimasti in stato non-terminale — **0 livelli stale** su tutte le run (104 e 224 livelli totali rispettivamente)

**Replacement lifecycle confermato coerente**: ogni livello sostituito risulta correttamente `invalidated` (via l'hook `NXS_Reaction_OnLevelReplaced` di Fase A), mai lasciato "appeso" in uno stato apparente-attivo.

## 5. Kill-switch / rollback

Non è stata necessaria una run "extra" dedicata: la matrice stessa lo dimostra. Righe 1 vs 2-3 (corta) e 4 vs 5-6 (lunga) sono, sullo stesso identico binario compilato, l'unica differenza runtime `InpLevelRegistry_WickReadPath=false` vs `=true` — e producono **lo stesso identico sha256**. Non essendoci stato persistente fra run del Tester (ogni run parte da zero), "riportare immediatamente al comportamento legacy" è dimostrato dal fatto che la run LEGACY (flag `false`) e le run NEW-authority (flag `true`) sono bit-a-bit indistinguibili nell'output — il flag non introduce alcuna deriva che debba essere "recuperata".

**Rollback verificato: perfetto, nessun cambio di digest.**

## 6. Failure injection test

Iniezione temporanea (rimossa prima del commit, vedi sopra): in `_NXS_WickReadPath_EvaluateSide`, subito prima del `return true;`, aggiunta la riga

```mql5
outSig.slPrice = outSig.slPrice + 500 * _Point;
```

Compilato (0 errori), eseguita la finestra corta con `InpLevelRegistry_WickReadPath=true`:

```
[LEVELENGINE][READPATH] enabled=true checks=804 mismatches=35
```

35 mismatch = esattamente il numero di trade della finestra (ogni tentativo aveva ora un SL corrotto lato new-engine). Esempio di record:

```
[LEVELENGINE][DECISION_MISMATCH] field=sl time=2026.06.12 04:15:00 |
legacy(should_trade=true dir=1 level_id=96 trigger=4187.48000 sl=4184.98000 tp=4197.48000) |
new(should_trade=true dir=1 level_id=96 trigger=4187.48000 sl=4189.98000 tp=4197.48000)
```

**Verifica**: il CSV dei trade prodotto con l'iniezione attiva è **byte-identico** alla baseline legacy pulita (`513aeb1f4f675ab5...decfdce9e6a`) — il SL corrotto non ha MAI raggiunto un trade reale, il fallback ha usato il legacy in ogni singolo caso (35/35). Dopo la verifica, l'iniezione è stata rimossa; ricompilato (0 errori) e ri-eseguita la stessa finestra: `mismatches=0`, digest tornato identico alla baseline. `git diff` sul file conferma **0 righe di differenza** rispetto al commit di Fase C.

**Fault-injection fail-safe: verificato.**

## 7. Regression

Stessa config di Fase B/C, hash confrontati contro le fixture già stabilite:

| Strategia | Selector | sha256 | Esito |
|---|---|---|---|
| WICK_SWEEP_RECLAIM (legacy-only) | 55 | `87078d65fcf2656a...5be548005` | **MATCH** |
| ADX_RSI RAW | 1 | `af03313d3117cc36...9bb8bce1` | **MATCH** |
| EMA_PULLBACK RAW | 11 | `f6fc623f51c9cde9...095a75277` | **MATCH** |
| FVG_CONT RAW | 8 | `e17b5e4a3cc6f106...4867b60` | **MATCH** |

**4/4 invariati**, nessuna riga di codice toccata in questi percorsi in nessuna delle fasi A-D.

## 8. Nessuna rimozione legacy

`SNxsWickSide`, `SNxsWickReclaimState`, `_NXS_WickSweepReversal_Legacy()` e tutte le funzioni WICK_SWEEP_RECLAIM restano intatte e continuano a scrivere il proprio stato in ogni run. Nessuna strategia oltre a WICK_SWEEP_REV è stata toccata in nessuna fase.

## Verdict finale

| Criterio per MIGRATION_READY | Esito |
|---|---|
| 0 mismatch reali | ✅ (0/804 e 0/1718 su tutte le run pulite) |
| 0 fallback reali | ✅ (nessun `DECISION_MISMATCH` nelle run senza iniezione) |
| Determinismo perfetto | ✅ (run ripetute identiche, stesso sha256) |
| Rollback perfetto | ✅ (legacy/new-authority bit-identici, nessuna deriva) |
| Fault-injection fail-safe verificato | ✅ (35/35 fallback corretti, CSV mai alterato, iniezione rimossa senza traccia) |
| State consistency perfetta | ✅ (0 field_mismatches, 0 stale_active_levels su 104 e 224 livelli) |
| Regression pulite | ✅ (4/4 hash identici) |

### **VERDICT: MIGRATION_READY**

Il read-path di WICK_SWEEP_REV è dimostrato equivalente al legacy su ogni asse testato (finestra corta, finestra lunga, ripetizioni, stato interno, fallimento indotto, regressione incrociata). Come esplicitamente richiesto: **nessuna rimozione del legacy in questa fase** — `MIGRATION_READY` è una dichiarazione di prontezza, non un'azione. La decisione di rimuovere `SNxsWickSide`/il vecchio percorso, o di migrare `WICK_SWEEP_RECLAIM`/altre strategie, resta esplicitamente fuori da questo task.
