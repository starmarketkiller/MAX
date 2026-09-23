# NEXUS - Phase 7.10 Retroactive Strategy Integrity Audit — BREAKOUT_ACC Certified Case

**Baseline:** `651d3a2a10e5c58acfc22ba820f518810356a73c` (Phase 7.9G). Nessuna optimization, nessuna ricerca di edge, nessun nuovo Serious backtest, nessun parameter tuning, nessuna modifica a strategie oltre a quanto già fatto in 7.9G, nessun dataset economico costruito.

---

## 1. L'inversione only_a/only_b — confermata, corretta alla fonte

**Verificata direttamente sul codice, non assunta.** `pair_dates()` (introdotta in 7.9G) è posizionale: `only_a` nel dict di ritorno è sempre il residuo del *primo* argomento passato, `only_b` del secondo — indipendentemente da quale stream logico (A/B/C) venga passato per primo. Le chiamate originali passavano lo stream offline come primo argomento e quello live come secondo, per **tutte e tre** le sezioni di pairing — quindi `only_a` conteneva in realtà il residuo di B (offline) e `only_b` il residuo di A (live), invertiti rispetto alla convenzione narrativa del report.

**I numeri e il verdetto sostanziali non erano mai sbagliati**: `matched=67`, `parity_passed=True`, `next_decision=BUILD_CANONICAL_BREAKOUT_ACC_DATASET` — tutti invariati prima/dopo, perché il codice di decisione compensava correttamente lo scambio posizionale. Solo i **nomi dei campi** nell'artifact JSON erano fuorvianti.

Corretto alla fonte in 3 script (`build_postfix_signal_parity.py`, `build_phase7_9g_decision.py`, `test_phase_7_9g.py`) — argomenti riordinati per corrispondere sempre al nome della sezione. Artifact 7.9G rigenerati con gli stessi conteggi. **Dati originali preservati** in `phase7_10/raw_data/*_ORIGINAL_pre_label_fix.json`. Nessun altro script del progetto (7.9C-7.9F usano nomi di campo espliciti e diversi) consumava il pattern ambiguo — il problema era isolato alla sola 7.9G.

## 2. Failure Memory generale: CROSS_TIMEFRAME_STATE_CONTAMINATION

**Definizione**: una strategia stateful viene chiamata durante passaggi TF che non appartengono al proprio profilo; il risultato viene scartato dal router, ma gli effetti collaterali sullo stato persistono e modificano il comportamento sul TF canonico — un caso classico di *"discard output, keep side effect"*.

**Perché la signal parity normale può non rilevarlo**: un confronto tradizionale (offline già isolato a un TF vs conteggio finale live) non replica la cadenza multi-pass reale — il sintomo (meno segnali del previsto) viene facilmente mal-attribuito a differenze di feed/dati, come è successo inizialmente in 7.9C.

**Prevenzione**: verifica esplicita `tf == NXS_Profile_TF(nome)` prima di qualunque lettura/scrittura di stato persistente — non solo prima di produrre un segnale.

## 3. Audit statico di 20 strategie stateful — non solo BAR_UPDN

Scansionato l'intero percorso `NXS_CollectAllSignals → activation TF → strategy function → state mutation → profile TF filtering` su tutti i file `NXS_Strategies*.mqh`. Nessuna correzione applicata.

| Classificazione | N | Strategie |
|---|---|---|
| **DEFECT_CONFIRMED** | 11 | BREAKOUT_ACC (fixato in 7.9G), BAR_UPDN, PIVOT_WICK, PMAX, TSI, BB_SQUEEZE, ORDER_BLOCK, SH_BMS_RTO, SH_BMS_RTO_V2, SILVER_BULLET, RANGE_FADE |
| **SUSPECT** | 5 | MACD_SMA200, ICHIMOKU_HULL_MACD, 3COMMAS_BOT, RSI_DIV_PINE, BOLLINGER |
| **SAFE** | 4 | LEVEL_CONFLUENCE(_M5), LEVEL_REACTION(_M5), WEEKLY_EXP, WICK_SWEEP_RECLAIM/REV |

**Nota di gravità**: fra i DEFECT_CONFIRMED, **TSI è il caso più severo trovato** — il suo stato è un doppio smoothing EMA ricorsivo (sm1/sm2/sm1Abs/sm2Abs/signal), dove un singolo pass su un TF sbagliato non corrompe solo la barra successiva ma l'intera catena di smoothing futura. PMAX, ORDER_BLOCK, BB_SQUEEZE e le macchine a stati SMC (SH_BMS_RTO/V2, SILVER_BULLET, RANGE_FADE) sono anch'esse **potenzialmente più gravi** di BREAKOUT_ACC/BAR_UPDN/PIVOT_WICK: lo stato contaminato è un **valore ricorsivo o una macchina a stati** (rischio sia falsi negativi che falsi positivi), non solo un timestamp di cooldown (rischio quasi solo falsi negativi). I 4 SAFE sono verificati per codice: usano un timeframe **hardcoded**, non `NXS_EffTF()` — immuni per costruzione, in un caso (WICK_SWEEP_RECLAIM/REV) già documentato esplicitamente dall'autore originale.

## 4. BAR_UPDN — realmente affetta, non solo sospetta

Il codice di BAR_UPDN è **strutturalmente identico** a BREAKOUT_ACC pre-fix — stesso pattern esatto, introdotto nello **stesso commit** (7871e96, 02/09), con lo stesso cooldown per-direzione non scoped al TF. La classificazione DEFECT_CONFIRMED (non SUSPECT) è giustificata dal fatto che il **meccanismo** è già dimostrato empiricamente per un caso identico — non richiede un nuovo esperimento per essere strutturalmente certo. **L'entità esatta dell'impatto su BAR_UPDN specificamente non è stata misurata** in questa fase (nessun esperimento diagnostico dedicato, coerente con l'istruzione di non testare altre strategie).

## 5. Schema canonico: RETROACTIVE_STRATEGY_INTEGRITY_AUDIT_V1

Pipeline di 13 stage ordinati (`ORIGINAL_PHENOMENON → FORMAL_SPEC → PYTHON_IMPLEMENTATION → MQL5_IMPLEMENTATION → TF/SESSION/HTF → SIGNAL_TIMING → STATEFUL_BEHAVIOR → SL/TP/EXIT → SELECTOR/PROFILE/GATES → SIGNAL → ORDER → FILL → OUTCOME/EVIDENCE`), ciascuno classificabile `MATCHED/PARTIAL/MISMATCH/UNKNOWN/NOT_APPLICABLE`. Due classificazioni finali derivate (**mai dal solo risultato economico**):

- **Evidence integrity**: `GENUINE_REFUTATION / GENUINE_SUPPORT / CONTAMINATED_EVIDENCE / NEVER_REALLY_TESTED / FORMALIZATION_GAP / EXECUTION_GAP / INSUFFICIENT_EVIDENCE`
- **Distortion direction**: `FALSE_NEGATIVE_RISK / FALSE_POSITIVE_RISK / BOTH / NONE_KNOWN`

**BREAKOUT_ACC come primo case study completo**, tutti e 13 gli stage compilati: `STATEFUL_BEHAVIOR` = MISMATCH pre-fix → MATCHED post-fix (il cuore dell'intero filone 7.9E-G); `SIGNAL` = PARTIAL (residuo 10.7% non ancora diagnosticato); `OUTCOME_EVIDENCE` = MISMATCH (il risultato storico appartiene all'implementazione contaminata).

**Verdetto finale**: `evidence_integrity_final = CONTAMINATED_EVIDENCE`, `distortion_direction = FALSE_NEGATIVE_RISK` — il meccanismo dimostrato è quasi esclusivamente soppressivo (blocca segnali D1 genuini), non generativo di falsi segnali. Il risultato storico a 4 trade rischia di essere **sistematicamente più scarso** della vera strategia D1 intesa, non il contrario.

## 6. Prossima singola task

**`BUILD_CANONICAL_BREAKOUT_ACC_DATASET`** (= Phase 7.9H, già autorizzata dal `next_decision` della 7.9G, non ancora eseguita) — costruire il dataset canonico Python per `BREAKOUT_ACC_INTENDED_D1_V1` (Python era già corretto, nessuna modifica di logica necessaria) e **solo allora** procedere a Edge Decomposition. Le 10 strategie DEFECT_CONFIRMED (escludendo BREAKOUT_ACC, gia' fixata) trovate qui restano backlog esplicitamente non prioritario — nessuna blocca il percorso BREAKOUT_ACC.

## Cronologia storica preservata

7.9C (apparente execution gap) → 7.9D (funnel pulito) → 7.9E (scoperta del meccanismo) → 7.9F (difetto confermato) → 7.9G (fix + parity, con correzione di etichetta in 7.10) → **7.10** (generalizzazione, audit di 20 strategie, schema canonico). Nessun artifact cancellato.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog. Nessuna delle 10 strategie DEFECT_CONFIRMED rimanenti corretta in questa fase.

## Deliverables

`breakout_acc_7_9g_label_correction_v1.json`, `cross_timeframe_state_contamination_failure_memory_v1.json`, `stateful_strategy_static_audit_v1.json`, `retroactive_strategy_integrity_audit_schema_v1.json`, `phase_7_10_final_synthesis_report_v1.json`, 5 builder, verificatore indipendente (verifica anche che EA live/Python/artifact frozen restino invariati oltre la correzione autorizzata), 32 test di consistenza (32/32 PASS), vault report, più i dati originali pre-correzione preservati in `raw_data/`.

## Regressione

- **Suite propria 7.10**: 32/32 PASS
- **Phase 7 totale inclusa la suite corrente**: 38/42 PASS
- **Fallimenti — 4 totali, tutti spiegati, nessuna regressione reale**:
  - 2 noti da prima (7.8E whole-file-hash legacy, 7.8H riferimento a EX5 non aggiornato) — invariati.
  - 2 con la stessa causa attesa già documentata in 7.9G (`test_phase_7_8i.py`, `test_phase_7_9b.py` verificano `NXS_Strategies.mqh` contro un hash congelato PRIMA del fix 7.9G) — non regressioni. Nota: `test_phase_7_9e.py`/`test_phase_7_9f.py`, che fallivano subito dopo 7.9G, ora **tornano a passare**: i loro verificatori confrontano contro `git HEAD`, che ora include il fix committato — a differenza di 7.8I/7.9B, che confrontano contro un hash congelato nel proprio artifact, non aggiornato automaticamente.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.10: COMPLETATA ✓
BREAKOUT_ACC: primo case study certificato del Retroactive Strategy
              Integrity Audit - evidence_integrity=CONTAMINATED_EVIDENCE,
              distortion=FALSE_NEGATIVE_RISK
PATTERN GENERALE: CROSS_TIMEFRAME_STATE_CONTAMINATION - 11 strategie
                   DEFECT_CONFIRMED (incl. BREAKOUT_ACC gia' fixato,
                   TSI il caso piu' severo), 5 SUSPECT, 4 SAFE -
                   nessuna corretta in questa fase
SCHEMA CANONICO: RETROACTIVE_STRATEGY_INTEGRITY_AUDIT_V1 (13 stage,
                  pronto per l'audit retrospettivo dell'intero vault)
PROSSIMO: BUILD_CANONICAL_BREAKOUT_ACC_DATASET (Phase 7.9H) - poi
          Edge Decomposition -> Path Anatomy -> Natural Horizon ->
          Mechanism Discovery
```
