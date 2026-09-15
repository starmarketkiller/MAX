# NEXUS — Serious Backtest Candidate Triage & Python↔MQL5 Parity

Segue [[NEXUS - 37 Strategy Cost-Calibrated Re-Evaluation]] (commit `ff9f0e5`). Obiettivo: ridurre i 18 `SERIOUS_BACKTEST_CANDIDATE` a pochi candidati **verificati semanticamente** prima del primo backtest serio su MT5. Nessun full MT5 backtest eseguito, nessuna ottimizzazione, nessuna combinazione di strategie.

## 1. Tabella completa dei 18 candidati

| Strategia | Selector MQL5 | TF Python | TF MQL5/profile | Provenienza TF | n | PF base | PF cons. | PF stress | Expectancy | DD% | Gross PF | Cost drag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BREAKOUT_ACC | 9 | 1d | D1 | EXPLICIT_PROFILE | 40 | 2.34 | 2.33 | 2.28 | 0.636 | 3.02 | 2.39 | 2.1% |
| LIQ_SWEEP | 7 | 1d | D1 | EXPLICIT_PROFILE | 42 | 1.85 | 1.83 | 1.79 | 0.448 | 4.00 | 1.88 | 3.0% |
| DARVAS_BOX | — | 1d | — | FAMILY_ASSUMPTION | 40 | 1.78 | 1.76 | 1.72 | 0.410 | 5.13 | 1.82 | 3.5% |
| DONCHIAN_TURTLE | — | 1d | — | FAMILY_ASSUMPTION | 45 | 1.71 | 1.70 | 1.66 | 0.386 | 5.13 | 1.75 | 3.4% |
| SAR_FLIP | — | 4h | — | FAMILY_ASSUMPTION | 111 | 1.61 | 1.59 | 1.51 | 0.346 | 5.81 | 1.69 | 8.3% |
| CISD_TRUE | — | 4h | — | FAMILY_ASSUMPTION | 92 | 1.54 | 1.50 | 1.41 | 0.322 | 7.90 | 1.64 | 11.8% |
| MACD | 3 | 4h | H4 | EXPLICIT_PROFILE | 231 | 1.46 | 1.44 | 1.37 | 0.262 | 10.13 | 1.52 | 9.3% |
| SAR | 4 | 4h | H4 | EXPLICIT_PROFILE | 305 | 1.45 | 1.43 | 1.36 | 0.259 | 9.32 | 1.51 | 9.6% |
| JUDAS_SWING | 29 | 15m | **nessun profilo TF documentato** | FAMILY_ASSUMPTION (problematica, v. §3) | 37 | 1.42 | 1.38 | 1.27 | 0.205 | 4.29 | 1.55 | 18.5% |
| ADX_RSI | 1 | 1d | D1 | EXPLICIT_PROFILE | 38 | 1.39 | 1.38 | 1.35 | 0.225 | 4.97 | 1.41 | 5.3% |
| MALAYSIAN_SNR_V2_STAGE3 | — | 30m | — | FAMILY_ASSUMPTION | 126 | 1.39 | 1.30 | 1.04 | 0.348 | 12.03 | 1.76 | 38.4% |
| EMA_PULLBACK | 11 | 4h | H4 | EXPLICIT_PROFILE | 75 | 1.37 | 1.35 | 1.28 | 0.234 | 7.47 | 1.44 | 12.8% |
| SAR_ADX20 | — | 4h | — | FAMILY_ASSUMPTION (var. SAR) | 248 | 1.34 | 1.32 | 1.26 | 0.221 | 10.65 | 1.40 | 12.3% |
| FVG_MIT_WINDOW | 39 | 4h | H4 | EXPLICIT_PROFILE | 244 | 1.29 | 1.23 | 1.05 | 0.193 | 17.83 | 1.58 | 41.3% |
| Z_SCORE_BREAKOUT | 42 | 1h | H1 | EXPLICIT_PROFILE | 460 | 1.23 | 1.19 | 1.07 | 0.130 | 24.44 | 1.33 | 27.5% |
| FVG_CONT | 8 | 4h | H4 | EXPLICIT_PROFILE | 212 | 1.19 | 1.17 | 1.12 | 0.137 | 12.69 | 1.24 | 19.3% |
| **LIQ_VOID** | 34 | 4h | H4 | EXPLICIT_PROFILE | 212 | 1.19 | 1.17 | 1.12 | 0.137 | 12.69 | 1.24 | 19.3% |
| ICHIMOKU | 13 | 4h | H4 | EXPLICIT_PROFILE | 79 | 1.08 | 1.06 | 1.02 | 0.062 | 9.93 | 1.12 | 36.1% |

**Scoperta critica — LIQ_VOID**: nel motore Python, `LIQ_VOID` è letteralmente un **alias della stessa funzione** di `FVG_CONT` (`sig_fvg_cont_ext`, stesso oggetto funzione — verificato con `is`). I numeri identici riga per riga non sono una coincidenza: **LIQ_VOID non ha mai testato la sua vera logica** ("Liquidity Void", `NXS_Strat_LiquidityVoid` in MQL5) — è un placeholder. **Escluso da qualunque considerazione ulteriore.**

## 2. Penalizzazione dell'evidenza debole

`LOW_SAMPLE_HIGH_PF` (n<50 e PF>1.5): **BREAKOUT_ACC** (n=40), **LIQ_SWEEP** (n=42, PF 1.85 — al limite), **DARVAS_BOX** (n=40), **JUDAS_SWING** (n=37) — riportati con questo flag, non automaticamente preferiti nonostante il PF alto.

`FAMILY_ASSUMPTION` senza alcun profilo MQL5 rintracciabile (**nessun selector live**): DARVAS_BOX, DONCHIAN_TURTLE, SAR_FLIP, SAR_ADX20, CISD_TRUE, MALAYSIAN_SNR_V2_STAGE3 — per queste **non esiste un equivalente MQL5 da verificare** (vedi §4, `NO_MQL5_EQUIVALENT`), indipendentemente da quanto buono sia il PF Python.

## 3. Cinque semifinalisti

Selezionati **solo** tra i candidati con selector MQL5 reale, funzione Python distinta (LIQ_VOID escluso) e diversificazione di famiglia (evitate le varianti quasi-identiche: SAR_FLIP/SAR_ADX20 sono varianti dirette di SAR, i 5 `MALAYSIAN_SNR_V2_*` sono varianti fra loro, CISD_TRUE/DARVAS_BOX/DONCHIAN_TURTLE non hanno comunque un selector):

1. **BREAKOUT_ACC** (sel. 9, D1) — famiglia breakout/acceptance
2. **LIQ_SWEEP** (sel. 7, D1) — famiglia SMC liquidity sweep
3. **MACD** (sel. 3, H4) — famiglia indicatore classico
4. **SAR** (sel. 4, H4) — famiglia indicatore classico (logica distinta da MACD)
5. **FVG_CONT** (sel. 8, H4) — famiglia SMC Fair Value Gap

`JUDAS_SWING` escluso dai semifinalisti nonostante il PF: nessun profilo TF MQL5 documentato in `NXS_StrategyProfiles.mqh` (né in `NXS_Profile_Get` né in `NXS_Profile_TF`) — l'assunzione "15m" per famiglia è **problematica**, perché senza un profilo esplicito l'EA reale userebbe `PERIOD_CURRENT` (fallback D1 per costruzione, vedi commento nel codice) — un TF **completamente diverso** da quello testato in Python. Segnalato esplicitamente come TF assumption problematica.

## 4. Semantic audit Python ↔ MQL5

**Scoperta sistemica #1 — SL/TP generico, non nativo**: verificato che **nessuno** script dell'intera sessione (compreso l'originale `nucleus_cost_reverify_14-08.py`) ha mai passato `strategy_profiles` a `run_backtest()`. Tutte le 67 strategie del rerun precedente sono state testate con `atr_sl=1.5/atr_tp=3.0` generico, **mai** i moltiplicatori nativi di `NXS_StrategyProfiles.mqh`. Corretto e ri-testato per i 5 semifinalisti (valori NON inventati, letti da `NXS_Profile_Get`):

| Strategia | SL/TP testato (generico) | SL/TP nativo (corretto) | n (nativo) | PF base (nativo) | DD% (nativo) | Expectancy (nativo) |
|---|---|---|---|---|---|---|
| BREAKOUT_ACC | 1.5/3.0 | **1.0/4.5** | 36 | **2.79** | 6.00 | **1.118** |
| LIQ_SWEEP | 1.5/3.0 | 1.5/3.0 (invariato) | 42 | 1.85 | 4.00 | 0.448 |
| MACD | 1.5/3.0 | **2.0/8.0** | 130 | **1.60** | 11.27 | **0.403** |
| SAR | 1.5/3.0 | **1.0/6.0** | 271 | 1.35 | **15.80** | 0.313 |
| FVG_CONT | 1.5/3.0 | **1.5/6.0** | 157 | **1.49** | 13.64 | **0.383** |

Con i moltiplicatori corretti, BREAKOUT_ACC/MACD/FVG_CONT **migliorano** sostanzialmente; **SAR peggiora** (DD quasi raddoppiato, 9.32%→15.80%) — la configurazione "generica" che avevo testato per errore era, per SAR, MIGLIORE di quella nativa documentata.

**Scoperta sistemica #2 — filtro HTF mai applicato**: `NXS_Profile_Get` dichiara `htf=true` per **BREAKOUT_ACC, LIQ_SWEEP, MACD, FVG_CONT** (tutti tranne SAR, `htf=false`). `run_backtest()` supporta `htf_filter`, ma **non è mai stato passato** in nessun test di questa sessione (rerun 67, audit precedenti, nucleus originale). Il filtro HTF è un gate reale della strategia MQL5, non un dettaglio — la sua assenza è una **differenza materiale**, non cosmetica, per 4 dei 5 semifinalisti.

### Confronto dettagliato e verdict

| Strategia | Entry | Direction | TF | SL/TP | Trailing/BE | Session filter | Signal timing | Verdict |
|---|---|---|---|---|---|---|---|---|
| **BREAKOUT_ACC** | Verificato identico (accettazione 2 chiusure consecutive fuori range, range esclude le 2 barre di conferma — stesso offset in entrambi) | Identica | Identico (D1) | Corretto e ri-testato | Cooldown 8 barre per-direzione in MQL5, **assente in Python** | N/A | Barra chiusa in entrambi | **MATERIAL_DIFFERENCE** (HTF filter mancante + cooldown mancante) |
| **LIQ_SWEEP** | Struttura logica allineata (corpo≥0.7×ATR, candela concorde a `sw.dir`) | Identica | Identico (D1) | Coincide col nativo (nessuna correzione necessaria) | — | Sweep basato su livelli PDH/PDL/Asia — non verificato bit-per-bit | Barra chiusa | **MATERIAL_DIFFERENCE** (HTF filter mancante + trade-level parity fallita, v. §5 — timing sweep sostanzialmente diverso, causa non diagnosticata) |
| **MACD** | Verificato **identico** (3 condizioni: MACD vs signal, stesso lato dello zero, prezzo vs EMA200 — già corretto/documentato in precedenza) | Identica | Identico (H4) | Corretto e ri-testato | — | Nessuno in entrambi | Barra chiusa in entrambi | **MATERIAL_DIFFERENCE** (solo per HTF filter mancante — logica di entry altrimenti impeccabile) |
| **SAR** | Verificato **identico** (SAR vs prezzo + allineamento EMA9/EMA21 — già verificato riga-per-riga in precedenza) | Identica | Identico (H4) | Corretto (ma degrada DD, v. sopra) | Filtri opzionali `InpSAR_RequireCandleAlign`/`RequirePressureContrary`: default **false** in MQL5, coerente con Python (nessuno dei due li applica) | Nessuno | **Differenza reale**: MQL5 tick-driven può ri-valutare/ri-entrare più volte nella stessa barra H4; Python valuta una volta per barra chiusa (v. §5) | **MINOR_DIFFERENCE** (unico gap sostanziale: granularità del timing, spiegabile e documentata) |
| **FVG_CONT** | Struttura allineata (gap a 3 barre, stesso offset i/i-2 ↔ shift1/shift3) | Identica | Identico (H4) | Corretto e ri-testato | — | Trend esterno H1 (`g_structH1.trend` MQL5 vs `choch_ext` Python) — concetto allineato, algoritmo non verificato bit-per-bit | Barra chiusa in entrambi | **MATERIAL_DIFFERENCE** (HTF filter mancante) |

## 5. Trade-level parity (finestra comune 2026-06-01 → 2026-09-01, GOLD)

Eseguito su MT5 Research Mode (selector isolato, costi nativi Tester — nessuno spread a 25 pip aggiunto) e confrontato con una simulazione Python a singola posizione (stessa logica "un trade alla volta" del motore, SL/TP nativi corretti) sulla stessa identica finestra.

| Strategia | n trade MT5 | n trade Python (stesso motore, stessa finestra) | Corrispondenza |
|---|---|---|---|
| BREAKOUT_ACC | **0** | 3 | **FAIL** — Python trova 3 setup validi, MT5 nessuno. Coerente con l'HTF filter mancante (§4) che in MQL5 filtra via alcuni/tutti questi setup. |
| LIQ_SWEEP | 2 (apre 06-08, 06-25) | 2 (apre 07-23, 08-10) | **FAIL** — stesso numero di trade, ma su **date completamente diverse** (oltre un mese di scarto sul primo). Causa non diagnosticata in questo audit: il rilevamento sweep (`_sweep_ext_at` Python vs `NXS_DetectSweepExt` MQL5) diverge sostanzialmente, non solo per un dettaglio di sessione/arrotondamento. |
| MACD | 5 | 4 | **ACCEPTABLE** — stesso ordine di grandezza, prima apertura 06-02 in entrambi con direzione SELL concorde; alcune differenze di timing spiegabili dal filtro HTF mancante in Python. |
| SAR | 37 | 25 | **ACCEPTABLE** — prima apertura quasi identica (06-01 01:00/01:30, stessa direzione BUY, prezzo coerente). La differenza di conteggio è spiegata da un meccanismo reale e documentato: MT5 (tick-driven) può chiudere e riaprire più volte nella stessa barra H4 (osservato: chiusura 11:23:40 e riapertura 11:30:00, stessa barra), Python valuta una sola volta per barra chiusa — granularità diversa, sequenza logica comunque spiegabile. |
| FVG_CONT | 6 | 8 | **ACCEPTABLE** — stesso ordine di grandezza, prima apertura 06-01/06-05 coerente per periodo, differenze attribuibili all'HTF filter mancante. |

**Nessuna strategia raggiunge TRADE_PARITY_STRONG** — atteso, dato che nessun test qui applicava l'HTF filter nativo.

## 6. Cost model MT5 usato per il parity test

Costi nativi del Tester/broker (nessuno spread a 25 pip aggiunto artificialmente) — coerente con `InpStructuralResearchEventLog=false`, `InpLogTrades=true`, Model=1. Lato Python: baseline 5.5 pip / conservative 7.0 pip / stress 13.0 pip, come da audit congelato precedente — nessuna modifica.

## 7-8. Promotion — massimo 3, nessun full backtest eseguito

Criteri: `SEMANTIC_PARITY_CONFIRMED` o differenza minore spiegata + trade parity ≥ACCEPTABLE + campione adeguato + baseline/conservative positivi + stress non catastrofico.

**4 su 5 escluse per `MATERIAL_DIFFERENCE`** (HTF filter nativo mai testato — un gate reale, non un dettaglio cosmetico): BREAKOUT_ACC, LIQ_SWEEP, MACD, FVG_CONT. Per queste, i risultati Python (anche quelli "corretti" con SL/TP nativo) **non sono una base sufficiente** per un backtest serio finché il filtro HTF non viene implementato e ri-testato — non è una bocciatura della strategia, è un lavoro di parità ancora da fare.

### FAST_STRUCTURAL_CANDIDATE: 1 su 18

| Strategia | Motivazione quantitativa |
|---|---|
| **SAR** | Unica delle 5 con `htf=false` nativo (nessun gate HTF da recuperare). Entry logic verificata identica in precedenza e riconfermata qui. Trade parity ACCEPTABLE con causa della divergenza (granularità tick vs barra chiusa) identificata e spiegabile, non un mistero. Con SL/TP nativo corretto: n=271 (campione ampio), PF base=1.35, conservative=1.33, stress=1.26 (mai <1, degradazione contenuta), expectancy=0.313 positiva. **Caveat esplicito**: DD nativo (15.80%) sostanzialmente peggiore di quanto stimato con SL/TP generico (9.32%) — accettabile ma non trascurabile, e i filtri opzionali candle-align/pressure-contrary (default OFF) non sono stati verificati contro l'effettiva configurazione di deployment. |

**Nessun'altra strategia promossa.** Non è stato eseguito alcun backtest a 3 anni. La promozione di SAR **non equivale a validazione definitiva** — resta da eseguire il backtest serio vero e proprio, con verifica esplicita che i filtri opzionali candle-align/pressure-contrary siano nello stato atteso.

## Riepilogo

- 18 candidati tabulati; **LIQ_VOID è un duplicato non rilevato di FVG_CONT** (stessa funzione Python) — rimosso da ogni considerazione.
- 5 semifinalisti selezionati per diversificazione di famiglia + selector MQL5 reale.
- **Scoperta sistemica**: SL/TP generico (non nativo) e filtro HTF mai applicato in **nessun** rerun precedente di questa sessione (67 strategie incluse) — correzione SL/TP eseguita per i 5 semifinalisti, HTF filter resta da implementare/testare.
- Semantic parity: 0 `SEMANTIC_PARITY_CONFIRMED`, 1 `MINOR_DIFFERENCE` (SAR), 4 `MATERIAL_DIFFERENCE` (BREAKOUT_ACC, LIQ_SWEEP, MACD, FVG_CONT).
- Trade-level parity: 0 `STRONG`, 3 `ACCEPTABLE` (MACD, SAR, FVG_CONT), 2 `FAIL` (BREAKOUT_ACC, LIQ_SWEEP).
- **FAST_STRUCTURAL_CANDIDATE: 1 (SAR)**, con caveat espliciti su DD e filtri opzionali.

**Commit**: `6deb188` (pushato su `origin/main`)
