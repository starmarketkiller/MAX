# NEXUS - Phase 7.8I Recompile + Research-Mode Corrected Serious Validation

**Baseline:** `b28416793fd03f33978507d467ee9e28141ec427` (Phase 7.8H). L'utente ha autorizzato esplicitamente ricompilazione + terzo run, ma solo con un config tecnicamente completo — identificando un secondo gap prima di spendere altre 2 ore: `InpResearchMode=true` mai attivato, e il fatto che `NXS_ResearchSelectorName()` non mappa ancora il selector 56 (quindi il sanity gate non doveva dipendere dal nome testuale).

**Questa è la fase in cui il protocollo ha finalmente prodotto un risultato scientifico reale.**

---

## 1. Ricompilazione dal sorgente corrente

Vecchio EX5 preservato con provenienza (`30efb700...`, 2026-09-10, precedente al commit della strategia). Ricompilato `NEXUS_EA_v2.mq5` da HEAD con MetaEditor: **0 errori, 2 warning innocui** (macro redefinition, conversione di tipo — nessuno tocca VOLBRK). Nuovo hash `8149e052...`, mtime 2026-09-22 (successivo al commit `f035d30` del 2026-09-17). Sorgente e Include (`NEXUS_v1`, già junction verso il repo) sincronizzati prima della compilazione.

## 2. Config di ricerca corretto

Partito dal config 7.8H, aggiunti (verificati nel codice, non assunti): `InpResearchMode=true`, `InpResearchExitMode=0`, `InpResearchFixedLot=0.01`, `InpProfileMultiTF=true` (richiesto esplicitamente da `NXS_ResearchPreflight()`, default già `true` ma congelato esplicitamente). Classificazione: **`RESEARCH_EXECUTION_ENABLEMENT_FIX`** — nessun parametro di strategia/entry/SL/TP/timeout/verdetto/finestra dati toccato.

## 3. Preflight tecnico (1 mese, PRIMA di spendere 2 ore)

Mini-run breve (2024.06.01→2024.07.01): **7/7 check PASS**. Conferma diretta: nuovo EX5 caricato, Research Mode riconosciuto (`[RESEARCH][INIT]` presente), preflight passato (0 errori fatali), **3 trade reali generati con `strategy=VOLATILITY_BREAKOUT_CONFIRMED` e `reason=VolBreakout_confirmed`** — il vero codice della strategia viene raggiunto. Nota sull'osservabilità: il log stampa `strategy=selector_56` (fallback, `NXS_ResearchSelectorName` non mappa ancora il case 56) — non trattato come fallimento, dato che il nome reale nel trade log (`VOLATILITY_BREAKOUT_CONFIRMED`, impostato direttamente nella funzione segnale) prova che il codice giusto è stato eseguito.

## 4. Atomic reseal fresco

Ricostruito da zero immediatamente prima del run 3: 27 tick hash ricalcolati, snapshot H4 rigenerato (3.379 barre, invariato), timezone rimisurato (10.800s, invariato), identità ambiente con nuovo EX5/source hash. **Verdetto: `ATOMIC_RESEAL_VERIFIED`**, confermato indipendentemente (22/22).

## 5. Terzo run reale: **206 operazioni totali**

Eseguito (~2h05m, 12:39→14:44). Raccolti e hashati i raw output prima di ogni interpretazione.

## Sanity gate (indipendente dal nome testuale, come richiesto)

`InpResearchMode=true` ✓, `selector=56` ✓, `InpStrat_VolBreakoutConfirmed=true` ✓, 0 errori `[RESEARCH][FATAL]` ✓, `PASS_TRADES_PRESENT` (206 operazioni nel report). Il gate NON dipende dalla stringa `strategy=VOLATILITY_BREAKOUT_CONFIRMED` nel log di init (che stampa il fallback) — dipende dai fatti verificabili sopra.

## Bug di parsing scoperto e corretto durante l'analisi

Il trade log di questo run **non porta la riga di intestazione** (la prima riga è già un record OPEN) — corretto usando l'header autorevole preso da `NXS_LogTradeCSV` nel sorgente, non assunto dalla prima riga. Inoltre: **tutte le righe OPEN hanno `ticket=0`** (l'EA lo logga hardcoded in questo percorso) — un semplice matching per ticket è impossibile; il conto è in **hedging mode**, quindi più posizioni della stessa strategia possono restare aperte simultaneamente (osservato: fino a 5 OPEN consecutive prima di una CLOSE). Implementato un matching **evidence-based** (SL/TP/timeout più vicino al prezzo/tempo di chiusura reale) invece di un FIFO ingenuo, con un bracket worst/best esplicito per i trade ambigui.

## Risultato

- **n nominale FRESH = 183** (≥30, campione sufficiente)
- **12/183 trade (6,6%) con matching OPEN/CLOSE ambiguo** — l'endpoint primario non ne risente (`r_multiple` è letto direttamente dal CSV, indipendente dal matching); solo gli scenari di costo stress dipendono dal matching. **Bracket worst/best verificato: il verdetto resta `FAIL` in entrambi gli scenari** — l'ambiguità non cambia la classificazione.
- **expectancy_R (BROKER_BASELINE) = -0,0673** (negativo)
- **CI95 (moving block bootstrap, L=6) = [-0,281, +0,152]** — include lo zero
- **PF = 0,867** (<1,0)
- **CONSERVATIVE = -0,105 / STRESS = -0,142** (entrambi negativi)
- **Win rate = 50,3%** (Wilson CI95 [43,1%, 57,4%]), payoff ratio 0,858, max consecutive losses 13
- **T1 = -0,205 / T2 = -0,247 / T3 = +0,311** — solo 1/3 segmenti non-negativo (serve ≥2/3)
- **BUY: n=56, expectancy_R=-0,726, PF=0,146 / SELL: n=127, expectancy_R=+0,223, PF=1,625** — asimmetria direzionale marcata (SELL positivo, BUY fortemente negativo), diagnostica pre-registrata, non usata per salvare il verdetto aggregato (`one_side_materially_negative_while_saving_aggregate=false`, dato che l'aggregato stesso è negativo — SELL non "salva" nulla, il verdetto resta FAIL). **Correzione 2026-09-22 (Phase 7.9A):** questa riga riportava in precedenza numeri sbagliati (BUY -0,081/PF 0,842, SELL -0,060/PF 0,881) per un errore di trascrizione — mai presenti nell'artifact canonico `volatility_breakout_serious_3y_result_v1.json` (`canonical_sha256=df2508752c8d53a71d40b140bc1b2416e717f146150a15d83deab8284ed1cd3c`, mai modificato), che ha sempre riportato i valori corretti sopra. Il verificatore indipendente di 7.8I non controllava esplicitamente i numeri di `direction_asymmetry` — gap colmato in 7.9A.
- **0 trade `EXECUTION_ORDER_UNRESOLVED`** per ambiguità SL/TP intrabarra (Model=4 risolve meccanicamente)

**`sign_criterion` (PF>1 AND expectancy_R>0) fallisce nettamente** — non borderline. Nessun rescue applicato: nessun parametro toccato, nessuna direzione eliminata, nessuna soglia aggiustata dopo aver visto il risultato.

## Final verdict

**`FAIL`** — confermato indipendentemente con una reimplementazione separata del matching (20/20 check).

**Next lifecycle state: `ARCHIVE_CURRENT_DESIGN`.**

## I due run precedenti restano archiviati, invariati

- **Run 1 (7.8G):** `TECHNICALLY_INVALID_ZERO_TRADE_RUN` (master switch mancante)
- **Run 2 (7.8H):** `TECHNICAL_EXECUTION_FAILURE_STRATEGY_NEVER_INITIALIZED` (EX5 non aggiornato)

Nessuno dei due è mai stato usato per statistiche di performance.

## Deliverables

`build_research_config_and_classification.py`, `volatility_breakout_research_config_v1.json`, `build_technical_preflight.py`, `volatility_breakout_technical_preflight_v1.json`, `build_atomic_reseal_before_run3.py`, `verify_atomic_reseal_before_run3.py`, `volatility_breakout_atomic_reseal_before_run3_v1.json`, `collect_immutable_run_manifest.py`, `immutable_run_manifest_run3_v1.json` (+ report/ini/journal raw), `compute_serious_validation_verdict.py` (matching evidence-based + bracket), `verify_serious_validation_result.py`, `volatility_breakout_serious_3y_result_v1.json`, `test_phase_7_8i.py`.

## Regressione

23/23 PASS sulla nuova suite. 32/34 delle altre suite Phase 7 passano; **2 falliscono per motivi noti e accettati, non "aggiustati" per un falso verde**: `test_volatility_breakout_final_data_freeze.py` (7.8E, whole-file hash legacy, superseded dal fingerprint window-aware) e `test_phase_7_8h.py` (verificava l'EX5 "corrente" contro quello *stale* documentato in 7.8H — ora intenzionalmente sostituito da questa stessa ricompilazione; il mismatch è la controprova che la correzione ha funzionato, non un difetto).

---

**SERIOUS_VALIDATION_RESULT: PRODOTTO. Classificazione: FAIL.**

**Progresso verso demo: invariato (~68%) — un FAIL onesto non fa avanzare né retrocedere il protocollo, archivia semplicemente questo design.**

```
PRIMO SERIOUS BACKTEST: 100% (completato)
VERSO DEMO: ~68%
RUN 1: invalido (config)
RUN 2: invalido (EX5 stale)
RUN 3: VALIDO - risultato scientifico reale
expectancy_R = -0.067, CI95 include lo zero, PF = 0.867
FINAL: FAIL
PROSSIMO:
ARCHIVE_CURRENT_DESIGN
(nessun rescue - il design testato e' chiuso)
```
